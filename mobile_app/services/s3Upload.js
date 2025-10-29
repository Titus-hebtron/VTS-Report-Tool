// Upload a local file to a presigned PUT URL. Returns true if upload succeeded.
export async function uploadFileToPresignedUrl(presignUrl, fileUri, contentType = 'image/jpeg') {
  try {
    const resp = await fetch(fileUri);
    const blob = await resp.blob();
    const res = await fetch(presignUrl, {
      method: 'PUT',
      headers: { 'Content-Type': contentType },
      body: blob
    });
    return res.ok;
  } catch (err) {
    console.warn('uploadFileToPresignedUrl error', err);
    return false;
  }
}
