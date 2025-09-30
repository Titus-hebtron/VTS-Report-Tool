-- Database schema for GPS Report Tool

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(50) DEFAULT 'contractor',
    contractor_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Contractors table
CREATE TABLE IF NOT EXISTS contractors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Incident reports table
CREATE TABLE IF NOT EXISTS incident_reports (
    id SERIAL PRIMARY KEY,
    incident_date DATE,
    incident_time TIME,
    caller VARCHAR(255),
    phone_number VARCHAR(50),
    location TEXT,
    bound VARCHAR(50),
    chainage VARCHAR(50),
    num_vehicles INTEGER,
    vehicle_type VARCHAR(100),
    vehicle_condition VARCHAR(100),
    num_injured INTEGER,
    cond_injured VARCHAR(100),
    injured_part VARCHAR(100),
    fire_hazard BOOLEAN DEFAULT FALSE,
    oil_leakage BOOLEAN DEFAULT FALSE,
    chemical_leakage BOOLEAN DEFAULT FALSE,
    damage_road_furniture BOOLEAN DEFAULT FALSE,
    response_time TIMESTAMP,
    clearing_time TIMESTAMP,
    department_contact VARCHAR(255),
    description TEXT,
    patrol_car VARCHAR(100),
    incident_type VARCHAR(100),
    uploaded_by VARCHAR(255),
    contractor_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Incident images table
CREATE TABLE IF NOT EXISTS incident_images (
    id SERIAL PRIMARY KEY,
    incident_id INTEGER REFERENCES incident_reports(id),
    image_data BYTEA,
    image_name VARCHAR(255),
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- Idle reports table
CREATE TABLE IF NOT EXISTS idle_reports (
    id SERIAL PRIMARY KEY,
    vehicle VARCHAR(100),
    idle_start TIMESTAMP,
    idle_end TIMESTAMP,
    idle_duration_min DECIMAL(10,2),
    location_address TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    description TEXT,
    uploaded_by VARCHAR(255),
    contractor_id INTEGER,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- Breaks table
CREATE TABLE IF NOT EXISTS breaks (
    id SERIAL PRIMARY KEY,
    vehicle VARCHAR(100),
    break_start TIMESTAMP,
    break_end TIMESTAMP,
    reason TEXT,
    break_date DATE,
    contractor_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pickups table
CREATE TABLE IF NOT EXISTS pickups (
    id SERIAL PRIMARY KEY,
    vehicle VARCHAR(100),
    pickup_start TIMESTAMP,
    pickup_end TIMESTAMP,
    description TEXT,
    pickup_date DATE,
    contractor_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Accidents table (if needed)
CREATE TABLE IF NOT EXISTS accidents (
    id SERIAL PRIMARY KEY,
    accident_date DATE,
    vehicle VARCHAR(100),
    description TEXT,
    contractor_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);