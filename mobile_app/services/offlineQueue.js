// Simple offline queue: store events in AsyncStorage and sync to backend when online.
// Usage: await enqueueEvent(event); await syncQueue(token);
import AsyncStorage from '@react-native-async-storage/async-storage';

// Optional Expo background/location integration:
let LocationModule = null;
let TaskManager = null;
try {
  // dynamic import so non-Expo environments don't break static analysis
  LocationModule = require('expo-location');
  TaskManager = require('expo-task-manager');
} catch (e) {
  LocationModule = null;
  TaskManager = null;
}

const QUEUE_KEY = 'vts_offline_queue_v1';
export const BG_TASK_NAME = 'VTS_BACKGROUND_LOCATION_TASK';

// add event to queue
export async function enqueueEvent(event) {
  try {
    const raw = await AsyncStorage.getItem(QUEUE_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    arr.push({ id: Date.now() + '_' + Math.random().toString(36).slice(2), event });
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(arr));
    return true;
  } catch (e) {
    console.warn('enqueueEvent error', e);
    return false;
  }
}

// get queue
export async function getQueue() {
  const raw = await AsyncStorage.getItem(QUEUE_KEY);
  return raw ? JSON.parse(raw) : [];
}

// remove items (by ids)
export async function removeFromQueue(ids = []) {
  const raw = await AsyncStorage.getItem(QUEUE_KEY);
  const arr = raw ? JSON.parse(raw) : [];
  const remain = arr.filter(i => !ids.includes(i.id));
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(remain));
}

// sync queue (uploads images first via presign, then posts events)
export async function syncQueue(apiBase, token) {
  const queue = await getQueue();
  if (!queue.length) return { ok: true, synced: 0 };
  // prepare events payload and upload images if any (example meta.photoLocalUri)
  const eventsPayload = [];
  for (const q of queue) {
    const ev = q.event;
    // if ev.meta && ev.meta.photoLocalUri -> upload and replace meta.photo_url
    if (ev.meta && ev.meta.photoLocalUri) {
      try {
        // request presign
        const fname = ev.meta.photoLocalUri.split('/').pop();
        const presignRes = await fetch(`${apiBase}/api/presign?filename=${encodeURIComponent(fname)}`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        });
        const presignJson = await presignRes.json();
        if (presignJson && presignJson.upload_url) {
          // read file as blob (Expo: use fetch on file:// uri)
          const fileResp = await fetch(ev.meta.photoLocalUri);
          const blob = await fileResp.blob();
          await fetch(presignJson.upload_url, {
            method: 'PUT',
            headers: { 'Content-Type': blob.type || 'application/octet-stream' },
            body: blob
          });
          // set key path in meta
          ev.meta.photo_url = presignJson.key;
          delete ev.meta.photoLocalUri;
        }
      } catch (err) {
        console.warn('upload image failed', err);
      }
    }
    eventsPayload.push(ev);
  }

  // post batch
  try {
    const res = await fetch(`${apiBase}/api/events/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ device_id: 'device_x', events: eventsPayload })
    });
    const j = await res.json();
    if (res.ok) {
      // remove all synced items
      const ids = queue.map(q => q.id);
      await removeFromQueue(ids);
      return { ok: true, synced: ids.length, result: j };
    }
    return { ok: false, error: j };
  } catch (err) {
    console.warn('sync error', err);
    return { ok: false, error: err };
  }
}

// ---------------- Background tracking helpers (Expo) ----------------
// Start background location tracking. Requires login/gating in app before call.
// `onLocation` events will be enqueued via enqueueEvent as {event:'location_update', timestamp, location, meta}
// Call with { patrolVehicle, token, apiBase } so event meta contains patrol selection info.
export async function startBackgroundTracking({ patrolVehicle = null, token = null, apiBase = null, distanceInterval = 25, timeInterval = 15000 }) {
  if (!LocationModule || !TaskManager) {
    console.warn('Background tracking requires expo-location and expo-task-manager.');
    return { ok: false, error: 'expo modules missing' };
  }

  // Request permissions (foreground + background)
  try {
    const { status: fgStatus } = await LocationModule.requestForegroundPermissionsAsync();
    if (fgStatus !== 'granted') return { ok: false, error: 'foreground permission denied' };
    // Android: background permission request
    const { status: bgStatus } = await LocationModule.requestBackgroundPermissionsAsync();
    if (bgStatus !== 'granted') {
      console.warn('Background permission not granted; background updates might not work on some platforms.');
    }
  } catch (e) {
    console.warn('Permission error', e);
    return { ok: false, error: e };
  }

  // Define background task handler only once
  if (!TaskManager.isTaskDefined(BG_TASK_NAME)) {
    TaskManager.defineTask(BG_TASK_NAME, ({ data, error }) => {
      if (error) {
        console.error('BG task error', error);
        return;
      }
      if (data) {
        const { locations } = data;
        if (locations && locations.length) {
          const loc = locations[0];
          const ev = {
            patrol_vehicle: patrolVehicle,
           