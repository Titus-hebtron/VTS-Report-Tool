import React, { useState } from 'react';
import { View, TextInput, Button, Text, Alert } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';
import { postMultipart } from '../services/api';

export default function IncidentScreen({ navigation, token }) {
  const [desc, setDesc] = useState('');
  const [image, setImage] = useState(null);

  async function pickImage() {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission required', 'Camera roll permission required.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({ quality: 0.7 });
    const picked = result.assets && result.assets.length ? result.assets[0] : result;
    const cancelledFlag = ('canceled' in result) ? result.canceled : result.cancelled;
    if (!cancelledFlag && picked && picked.uri) setImage(picked);
  }

  async function takePhoto() {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission required', 'Camera permission required.');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.7 });
    const picked = result.assets && result.assets.length ? result.assets[0] : result;
    const cancelledFlag = ('canceled' in result) ? result.canceled : result.cancelled;
    if (!cancelledFlag && picked && picked.uri) setImage(picked);
  }

  async function submitIncident() {
    try {
      const loc = await Location.getCurrentPositionAsync({});
      const formData = new FormData();
      formData.append('description', desc);
      formData.append('timestamp', new Date().toISOString());
      formData.append('location_lat', loc.coords.latitude.toString());
      formData.append('location_lng', loc.coords.longitude.toString());
      if (image) {
        const uriParts = image.uri.split('.');
        let fileType = uriParts[uriParts.length - 1].split('?')[0].toLowerCase();
        if (fileType === 'heic') fileType = 'jpeg';
        formData.append('photo', {
          uri: image.uri,
          name: `incident.${fileType}`,
          type: `image/${fileType}`
        });
      }
      const res = await postMultipart(token, '/incidents', formData);
      if (res && res.ok) {
        Alert.alert('Incident sent');
        navigation.goBack();
      } else {
        Alert.alert('Send failed', JSON.stringify(res));
      }
    } catch (err) {
      Alert.alert('Error', String(err));
    }
  }

  return (
    <View style={{ padding: 20 }}>
      <TextInput
        placeholder="Describe incident"
        value={desc}
        onChangeText={setDesc}
        multiline
        style={{ minHeight: 120, borderColor: '#ccc', borderWidth: 1, padding: 10 }}
      />
      <View style={{ marginVertical: 8 }}>
        <Button title="Pick Image" onPress={pickImage} />
      </View>
      <View style={{ marginVertical: 8 }}>
        <Button title="Take Photo" onPress={takePhoto} />
      </View>
      {image && <Text>Image ready: {image.uri}</Text>}
      <View style={{ marginVertical: 8 }}>
        <Button title="Submit Incident" onPress={submitIncident} />
      </View>
    </View>
  );
}
