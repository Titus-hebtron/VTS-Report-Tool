import 'dart:io';
import 'package:http/http.dart' as http;
import 'dart:convert';

/// Request a presigned PUT URL from backend and upload file to S3 directly.
Future<bool> uploadFileWithPresign({
  required String backendBase,
  required String path, // backend path that creates presign, e.g. '/s3/presign'
  required File file,
  String? authToken,
}) async {
  final metaRes = await http.post(
    Uri.parse(backendBase + path),
    headers: {
      'Content-Type': 'application/json',
      if (authToken != null) 'Authorization': 'Bearer $authToken'
    },
    body: jsonEncode({'filename': file.uri.pathSegments.last, 'content_type': 'image/jpeg'}),
  );
  if (metaRes.statusCode != 200) return false;
  final data = jsonDecode(metaRes.body);
  final presignUrl = data['url'] as String;
  final uploadHeaders = Map<String, String>.from(data['headers'] ?? {});

  final bytes = await file.readAsBytes();
  final res = await http.put(Uri.parse(presignUrl), headers: {
    ...uploadHeaders,
    if (!uploadHeaders.containsKey('Content-Type')) 'Content-Type': 'image/jpeg'
  }, body: bytes);
  return res.statusCode == 200 || res.statusCode == 204;
}
