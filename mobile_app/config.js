// Minimal ready-to-run config. Replace values for production.
export const READY_TO_RUN = true; // set false to require manual config
export const API_BASE = READY_TO_RUN ? 'http://10.0.2.2:8000' : 'https://your-backend.example.com';
export const DEVICE_API_TOKEN = READY_TO_RUN ? 'DEMO_DEVICE_TOKEN' : 'REPLACE_WITH_REAL_TOKEN';

// Default patrol vehicle mapping (can be overridden by app UI)
export const DEFAULT_PATROL_VEHICLE = 'KDG 320Z';

// Background tracking task name (Expo TaskManager)
export const BG_LOCATION_TASK = 'VTS_BACKGROUND_LOCATION_TASK';
