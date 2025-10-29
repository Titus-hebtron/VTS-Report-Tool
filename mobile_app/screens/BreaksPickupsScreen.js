import React, { useState } from 'react';
import { View, TextInput, Button, Text, Alert } from 'react-native';
import { postEvent } from '../services/api';
import * as Location from 'expo-location';

export default function BreaksPickupsScreen({ navigation, token }) {
  const [notes, setNotes] = useState('');
  const [sending, setSending] = useState(false);

  async function sendEvent(type) {
    setSending(true);
    try {
      const loc = await Location.getCurrentPositionAsync({});
      const payload = {
        event: type,
        timestamp: new Date().toISOString(),
        location: { latitude: loc.coords.latitude, longitude: loc.coords.longitude },
        meta: { notes }
      };
      const res = await postEvent(token, '/patrols/checkin', payload); // reuse checkin endpoint for events
      if (res && res.ok) {
        Alert.alert('Saved');
        setNotes('');
      } else {
        Alert.alert('Failed', JSON.stringify(res));
      }
    } catch (e) {
      Alert.alert('Error', String(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <View style={{ padding: 20 }}>
      <TextInput
        placeholder="Notes (who picked up, break reason...)"
        value={notes}
        onChangeText={setNotes}
        multiline
        style={{ minHeight: 80, borderColor: '#ccc', borderWidth: 1, padding: 10 }}
      />
      <View style={{ marginVertical: 8 }}>
        <Button title="Record Break" onPress={() => sendEvent('break')} disabled={sending} />
      </View>
      <View style={{ marginVertical: 8 }}>
        <Button title="Record Pickup" onPress={() => sendEvent('pickup')} disabled={sending} />
      </View>
    </View>
  );
}
