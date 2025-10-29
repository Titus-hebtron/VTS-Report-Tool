import React, { useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from './screens/HomeScreen';
import IncidentScreen from './screens/IncidentScreen';
import BreaksScreen from './screens/BreaksScreen';

const Stack = createNativeStackNavigator();

export default function App() {
  // Replace with secure storage in production
  const [token] = useState('YOUR_DEVICE_API_TOKEN');

  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen name="Home">
          {props => <HomeScreen {...props} token={token} />}
        </Stack.Screen>
        <Stack.Screen name="Incident">
          {props => <IncidentScreen {...props} token={token} />}
        </Stack.Screen>
        <Stack.Screen name="Breaks">
          {props => <BreaksScreen {...props} token={token} />}
        </Stack.Screen>
      </Stack.Navigator>
    </NavigationContainer>
  );
}
