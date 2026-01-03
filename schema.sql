-- Database schema for GPS Report Tool
-- Compatible with both PostgreSQL and SQLite

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'contractor',
    contractor_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contractors table
CREATE TABLE IF NOT EXISTS contractors (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vehicles table
CREATE TABLE IF NOT EXISTS vehicles (
    id SERIAL PRIMARY KEY,
    plate_number TEXT NOT NULL UNIQUE,
    contractor TEXT NOT NULL,
    gps_tracking_enabled BOOLEAN DEFAULT FALSE,
    gps_tracking_activated_at TIMESTAMP,
    gps_tracking_deactivated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Patrol logs table
CREATE TABLE IF NOT EXISTS patrol_logs (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER,
    timestamp TIMESTAMP,
    latitude REAL,
    longitude REAL,
    activity TEXT,
    status TEXT DEFAULT 'offline',
    speed REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

-- Incident reports table
CREATE TABLE IF NOT EXISTS incident_reports (
    id SERIAL PRIMARY KEY,
    incident_date DATE,
    incident_time TIME,
    caller TEXT,
    phone_number TEXT,
    location TEXT,
    bound TEXT,
    chainage TEXT,
    num_vehicles INTEGER,
    vehicle_type TEXT,
    vehicle_condition TEXT,
    num_injured INTEGER,
    cond_injured TEXT,
    injured_part TEXT,
    fire_hazard INTEGER DEFAULT 0,
    oil_leakage INTEGER DEFAULT 0,
    chemical_leakage INTEGER DEFAULT 0,
    damage_road_furniture INTEGER DEFAULT 0,
    response_time TIMESTAMP,
    clearing_time TIMESTAMP,
    department_contact TEXT,
    description TEXT,
    patrol_car TEXT,
    incident_type TEXT,
    uploaded_by TEXT,
    contractor_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Incident images table
CREATE TABLE IF NOT EXISTS incident_images (
    id SERIAL PRIMARY KEY,
    incident_id INTEGER,
    image_data BYTEA,
    image_name TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incident_reports(id)
);

-- Idle reports table
CREATE TABLE IF NOT EXISTS idle_reports (
    id SERIAL PRIMARY KEY,
    vehicle TEXT,
    idle_start TIMESTAMP,
    idle_end TIMESTAMP,
    idle_duration_min REAL,
    location_address TEXT,
    latitude REAL,
    longitude REAL,
    description TEXT,
    uploaded_by TEXT,
    contractor_id INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Breaks table
CREATE TABLE IF NOT EXISTS breaks (
    id SERIAL PRIMARY KEY,
    vehicle TEXT,
    break_start TIMESTAMP,
    break_end TIMESTAMP,
    reason TEXT,
    break_date DATE,
    contractor_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pickups table
CREATE TABLE IF NOT EXISTS pickups (
    id SERIAL PRIMARY KEY,
    vehicle TEXT,
    pickup_start TIMESTAMP,
    pickup_end TIMESTAMP,
    description TEXT,
    pickup_date DATE,
    contractor_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Accidents table (if needed)
CREATE TABLE IF NOT EXISTS accidents (
    id SERIAL PRIMARY KEY,
    accident_date DATE,
    vehicle TEXT,
    description TEXT,
    contractor_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Accident reports data table
CREATE TABLE IF NOT EXISTS accident_reports_data (
    id SERIAL PRIMARY KEY,
    incident_date DATE,
    incident_time TIME,
    caller TEXT,
    phone_number TEXT,
    location TEXT,
    bound TEXT,
    chainage TEXT,
    num_vehicles INTEGER,
    vehicle_type TEXT,
    vehicle_condition TEXT,
    num_injured INTEGER,
    cond_injured TEXT,
    injured_part TEXT,
    fire_hazard INTEGER,
    oil_leakage INTEGER,
    chemical_leakage INTEGER,
    damage_road_furniture INTEGER,
    response_time TIMESTAMP,
    clearing_time TIMESTAMP,
    department_contact TEXT,
    description TEXT,
    patrol_car TEXT,
    incident_type TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Accident reports images table
CREATE TABLE IF NOT EXISTS accident_reports_images (
    id SERIAL PRIMARY KEY,
    image_name TEXT,
    sheet_name TEXT,
    anchor_cell TEXT,
    file_path TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default contractors (only if table is empty)
INSERT INTO contractors (name) VALUES ('Wizpro') ON CONFLICT DO NOTHING;
INSERT INTO contractors (name) VALUES ('Paschal') ON CONFLICT DO NOTHING;
INSERT INTO contractors (name) VALUES ('RE Office') ON CONFLICT DO NOTHING;
INSERT INTO contractors (name) VALUES ('Avators') ON CONFLICT DO NOTHING;