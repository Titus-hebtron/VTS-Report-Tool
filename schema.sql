-- Database schema for GPS Report Tool
-- Compatible with both PostgreSQL and SQLite

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'contractor',
    contractor_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Contractors table
CREATE TABLE IF NOT EXISTS contractors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Vehicles table
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    contractor TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Patrol logs table
CREATE TABLE IF NOT EXISTS patrol_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER,
    timestamp DATETIME,
    latitude REAL,
    longitude REAL,
    activity TEXT,
    status TEXT DEFAULT 'offline',
    speed REAL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

-- Incident reports table
CREATE TABLE IF NOT EXISTS incident_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    response_time DATETIME,
    clearing_time DATETIME,
    department_contact TEXT,
    description TEXT,
    patrol_car TEXT,
    incident_type TEXT,
    uploaded_by TEXT,
    contractor_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Incident images table
CREATE TABLE IF NOT EXISTS incident_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER,
    image_data BLOB,
    image_name TEXT,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incident_reports(id)
);

-- Idle reports table
CREATE TABLE IF NOT EXISTS idle_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle TEXT,
    idle_start DATETIME,
    idle_end DATETIME,
    idle_duration_min REAL,
    location_address TEXT,
    latitude REAL,
    longitude REAL,
    description TEXT,
    uploaded_by TEXT,
    contractor_id INTEGER,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Breaks table
CREATE TABLE IF NOT EXISTS breaks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle TEXT,
    break_start DATETIME,
    break_end DATETIME,
    reason TEXT,
    break_date DATE,
    contractor_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Pickups table
CREATE TABLE IF NOT EXISTS pickups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle TEXT,
    pickup_start DATETIME,
    pickup_end DATETIME,
    description TEXT,
    pickup_date DATE,
    contractor_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Accidents table (if needed)
CREATE TABLE IF NOT EXISTS accidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accident_date DATE,
    vehicle TEXT,
    description TEXT,
    contractor_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Accident reports data table
CREATE TABLE IF NOT EXISTS accident_reports_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    response_time DATETIME,
    clearing_time DATETIME,
    department_contact TEXT,
    description TEXT,
    patrol_car TEXT,
    incident_type TEXT,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Accident reports images table
CREATE TABLE IF NOT EXISTS accident_reports_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_name TEXT,
    sheet_name TEXT,
    anchor_cell TEXT,
    file_path TEXT,
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert default contractors (only if table is empty)
INSERT OR IGNORE INTO contractors (name) VALUES ('Wizpro');
INSERT OR IGNORE INTO contractors (name) VALUES ('Paschal');
INSERT OR IGNORE INTO contractors (name) VALUES ('RE Office');
INSERT OR IGNORE INTO contractors (name) VALUES ('Avators');