import React, { useEffect, useState, useRef } from 'react';
import { View, Text, Button, Alert } from 'react-native';
import * as Location from 'expo-location';
import { postEvent } from '../services/api';

export default function HomeScreen({ navigation, token }) {
  const [location, setLocation] = useState(null);
  const [patrolId, setPatrolId] = useState(null);
  const subscriptionRef = useRef(null);

  useEffect(() => {
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission denied', 'Location permission is required.');
        return;
      }
      const loc = await Location.getCurrentPositionAsync({});
      setLocation(loc.coords);
    })();
    return () => {
      if (subscriptionRef.current) {
        subscriptionRef.current.remove();
      }
    };
  }, []);

  async function startTracking() {
    try {
      subscriptionRef.current = await Location.watchPositionAsync(
        { accuracy: Location.Accuracy.Balanced, timeInterval: 15000, distanceInterval: 10 },
        (pos) => {
          setLocation(pos.coords);
          sendCheckin('location_update', pos.coords);
        }
      );
      const res = await postEvent(token, '/patrols/start', { started_at: new Date().toISOString() });
      if (res && res.patrol_id) {
        setPatrolId(res.patrol_id);
        Alert.alert('Patrol started', `Patrol id ${res.patrol_id}`);
      } else {
        Alert.alert('Start failed');
      }
    } catch (e) {
      Alert.alert('Error', String(e));
    }
  }

  async function stopTracking() {
    try {
      if (subscriptionRef.current) {
        if (typeof subscriptionRef.current.remove === 'function') subscriptionRef.current.remove();
        subscriptionRef.current = null;
      }
      await postEvent(token, '/patrols/stop', { patrol_id: patrolId, stopped_at: new Date().toISOString() });
      setPatrolId(null);
      Alert.alert('Patrol stopped');
    } catch (e) {
      Alert.alert('Error', String(e));
    }
  }

  async function sendCheckin(eventType = 'checkin', coords = null) {
    try {
      const payload = {
        patrol_id: patrolId,
        event: eventType,
        timestamp: new Date().toISOString(),
        location: coords || location || null,
        meta: {}
      };
      await postEvent(token, '/patrols/checkin', payload);
    } catch (e) {
      console.warn('Checkin failed', e);
    }
  }

  return (
    <View style={{ padding: 20 }}>
      <Text style={{ marginBottom: 10 }}>Current location:</Text>
      {location ? (
        <Text>{location.latitude.toFixed(6)} , {location.longitude.toFixed(6)}</Text>
      ) : (
        <Text>Fetching location...</Text>
      )}
      <View style={{ marginVertical: 10 }}>
        <Button title="Start Patrol" onPress={startTracking} disabled={!!patrolId} />
      </View>
      <View style={{ marginVertical: 10 }}>
        <Button title="Stop Patrol" onPress={stopTracking} disabled={!patrolId} />
      </View>
      <View style={{ marginVertical: 10 }}>
        <Button title="Check In" onPress={() => sendCheckin('checkin')} />
      </View>
      <View style={{ marginVertical: 10 }}>
        <Button title="Report Incident" onPress={() => navigation.navigate('Incident')} />
      </View>
      <View style={{ marginVertical: 10 }}>
        <Button title="Record Break / Pickup" onPress={() => navigation.navigate('Breaks')} />
      </View>
    </View>
  );
}
