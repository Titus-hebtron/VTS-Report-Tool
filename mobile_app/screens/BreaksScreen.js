import React, { useState } from 'react';
import { View, Button, Alert, TextInput, Text } from 'react-native';
import * as Location from 'expo-location';
import { postEvent } from '../services/api';

export default function BreaksScreen({ token }) {
  const [onBreak, setOnBreak] = useState(false);
  const [note, setNote] = useState('');

  async function startBreak() {
    try {
      const loc = await Location.getCurrentPositionAsync({});
      await postEvent(token, '/breaks/start', {
        timestamp: new Date().toISOString(),
        location: loc.coords,
        note
      });
      setOnBreak(true);
      Alert.alert('Break started');
    } catch (e) {
      Alert.alert('Error', String(e));
    }
  }

  async function endBreak() {
    try {
      const loc = await Location.getCurrentPositionAsync({});
      await postEvent(token, '/breaks/stop', {
        timestamp: new Date().toISOString(),
        location: loc.coords,
        note
      });
      setOnBreak(false);
      Alert.alert('Break stopped');
    } catch (e) {
      Alert.alert('Error', String(e));
    }
  }

  return (
    <View style={{ padding: 20 }}>
      <Text>Optional note (reason/location):</Text>
      <TextInput value={note} onChangeText={setNote} style={{ borderColor: '#ccc', borderWidth: 1, padding: 8, marginVertical: 8 }} />
      <Button title={onBreak ? "End Break" : "Start Break"} onPress={onBreak ? endBreak : startBreak} />
    </View>
  );
}
