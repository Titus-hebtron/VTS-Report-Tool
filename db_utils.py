# db_utils.py - Simplified SQLite version
from sqlalchemy import create_engine, text
import bcrypt
import pandas as pd
import traceback
import streamlit as st
from datetime import datetime
import os
import sqlite3

# Register datetime adapter for SQLite to avoid deprecation warning in Python 3.12+
def adapt_datetime(dt):
    return dt.isoformat()

sqlite3.register_adapter(datetime, adapt_datetime)

# ------------------- DATABASE CONFIG -------------------
# Auto-detect database type based on environment
# Use PostgreSQL if DATABASE_URL is set (production/Render), otherwise SQLite (development)
DATABASE_URL = os.getenv("DATABASE_URL")

# Debug: Log DATABASE_URL status (without exposing credentials)
if DATABASE_URL:
    if not DATABASE_URL.strip():
        print("⚠️  DATABASE_URL is set but empty - using SQLite")
    elif not DATABASE_URL.startswith(('postgresql://', 'postgres://')):
        print(f"⚠️  DATABASE_URL doesn't start with postgresql:// or postgres:// - using SQLite")
        print(f"    Starts with: {DATABASE_URL[:20]}...")
    else:
        print(f"ℹ️  DATABASE_URL detected: {DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else 'localhost'}")
else:
    print("ℹ️  No DATABASE_URL set - using SQLite for local development")

# Validate DATABASE_URL is not empty and properly formatted
if DATABASE_URL and DATABASE_URL.strip() and DATABASE_URL.startswith(('postgresql://', 'postgres://')):
    # Production: Use PostgreSQL from DATABASE_URL with fallback
    USE_SQLITE = False
    
    try:
        # Render PostgreSQL SSL - use "prefer" for better compatibility
        connect_args = {
            "sslmode": "prefer",  # More compatible than "require"
            "connect_timeout": 30,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5
        }
        
        engine = create_engine(
            DATABASE_URL,
            connect_args=connect_args,
            pool_size=3,
            max_overflow=7,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_timeout=30,
            echo=False
        )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ PostgreSQL connected")
        
    except Exception as e:
        print(f"⚠️  PostgreSQL failed: {e}")
        print("🔄 Using SQLite instead")
        USE_SQLITE = True
        engine = create_engine("sqlite:///vts_database.db", connect_args={"check_same_thread": False})
else:
    # Development: Use SQLite
    USE_SQLITE = True
    engine = create_engine("sqlite:///vts_database.db", connect_args={"check_same_thread": False})

# ------------------- DATABASE INITIALIZATION -------------------
def init_database():
    """Initialize database tables if they don't exist"""
    print("Checking database initialization...")

    # Log database URL for debugging
    if DATABASE_URL:
        print(f"Connected to: {DATABASE_URL.replace(DATABASE_URL.split('://')[1].split('@')[0], '***:***@')}")
    else:
        print("Using SQLite database: vts_database.db")

    try:
        with engine.begin() as conn:
            # Check if users table exists (works for both SQLite and PostgreSQL)
            if USE_SQLITE:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
            else:
                result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name='users' AND table_schema='public'"))
            table_exists = result.fetchone() is not None

            if not table_exists:
                print("Creating database tables...")

                # Read schema file and create tables
                with open('schema.sql', 'r') as f:
                    sql = f.read()

                if USE_SQLITE:
                    # Execute schema using executescript for multiple statements (SQLite)
                    cursor = conn.connection.cursor()
                    cursor.executescript(sql)
                    cursor.close()
                else:
                    # Execute schema for PostgreSQL (split by semicolon and execute each statement)
                    statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
   
                    for statement in statements:
                        if statement and statement.upper().startswith('CREATE TABLE'):
                            if not USE_SQLITE:
                                statement = statement.replace('AUTOINCREMENT', 'SERIAL')
                            try:
                                conn.execute(text(statement))
                                table_name = statement.split('CREATE TABLE')[1].split('(')[0].strip()
                                print(f"Created table: {table_name}")
                            except Exception as e:
                                print(f"Warning creating table: {e}")
                        elif statement and statement.upper().startswith('INSERT'):
                            try:
                                conn.execute(text(statement))
                                print(f"Executed insert: {statement[:50]}...")
                            except Exception as e:
                                print(f"Warning executing insert: {e}")

                print("All tables created successfully!")

                # Add default users using direct SQL to avoid function call issues
                # Note: We need to commit the table creation first before adding users
                # For PostgreSQL, we don't need to commit here as we're in a transaction
                if USE_SQLITE:
                    conn.commit()

                # Add default users directly using a new connection
                users_data = [
                    ('admin', 'Pass@12345', 'Administrator', 3, 're_admin'),
                    ('wizpro_admin', 'Pass@12345', 'Wizpro Admin', 1, 'admin'),
                    ('paschal_admin', 'Pass@12345', 'Paschal Admin', 2, 'admin'),
                    ('wizpro_user', 'Pass@12345', 'Wizpro User', 1, 'contractor'),
                    ('paschal_user', 'Pass@12345', 'Paschal User', 2, 'contractor'),
                    ('avators_user', 'Pass@12345', 'Avators User', 4, 'contractor'),
                    ('patrol_officer_1', 'Pass@12345', 'Patrol Officer 1', 1, 'patrol'),
                    ('patrol_officer_2', 'Pass@12345', 'Patrol Officer 2', 1, 'patrol'),
                    ('patrol_officer_3', 'Pass@12345', 'Patrol Officer 3', 1, 'patrol'),
                ]

                # Use the same connection for user insertion
                for username, plain_password, name, contractor_id, role in users_data:
                    hashed = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()
                    if USE_SQLITE:
                        conn.execute(text("""
                            INSERT OR IGNORE INTO users (username, password_hash, role, contractor_id)
                            VALUES (:username, :password_hash, :role, :contractor_id)
                        """), {
                            "username": username,
                            "password_hash": hashed,
                            "role": role,
                            "contractor_id": contractor_id
                        })
                    else:
                        conn.execute(text("""
                            INSERT INTO users (username, password_hash, role, contractor_id)
                            VALUES (:username, :password_hash, :role, :contractor_id)
                            ON CONFLICT (username) DO NOTHING
                        """), {
                            "username": username,
                            "password_hash": hashed,
                            "role": role,
                            "contractor_id": contractor_id
                        })

                print("Default users added successfully!")

            else:
                print("Database tables already exist")

        # Ensure database initialization runs before any operations
        print("✅ Database initialization completed successfully")

    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise

def get_connection():
    return engine.raw_connection()

def get_sqlalchemy_engine():
    return engine

# ------------------- USER MANAGEMENT -------------------
def add_user(username, plain_password, name, contractor_id=None, role="contractor"):
    """Add a new user with hashed password"""
    hashed = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT OR IGNORE INTO users (username, password_hash, role, contractor_id)
            VALUES (:username, :password_hash, :role, :contractor_id)
        """), {
            "username": username,
            "password_hash": hashed,
            "role": role,
            "contractor_id": contractor_id
        })

def get_user(username, contractor_id=None):
    """Fetch user for login. If contractor_id is passed, restrict login to that contractor."""
    if contractor_id:
        query = text("""
            SELECT id, username, password_hash as password, role, contractor_id
            FROM users
            WHERE username = :username AND contractor_id = :contractor_id
        """)
        params = {"username": username, "contractor_id": contractor_id}
    else:
        query = text("""
            SELECT id, username, password_hash as password, role, contractor_id
            FROM users
            WHERE username = :username
        """)
        params = {"username": username}

    with engine.begin() as conn:
        result = conn.execute(query, params)
        row = result.fetchone()

    return dict(row) if row else None

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

# ------------------- ACTIVE CONTRACTOR -----------------
def get_active_contractor():
    """
    Decide which contractor's data to use:
    - Contractor users → their own contractor
    - RE users → contractor selected in sidebar
    """
    if "role" in st.session_state and st.session_state["role"] == "re_admin":
        return st.session_state.get("active_contractor")
    return st.session_state.get("contractor_id")

def get_contractor_id(name):
    with engine.begin() as conn:
        result = conn.execute(text("SELECT id FROM contractors WHERE name = :name"), {"name": name})
        row = result.fetchone()
    return row[0] if row else None

def get_contractor_name(contractor_id):
    if not contractor_id:
        return None
    with engine.begin() as conn:
        result = conn.execute(text("SELECT name FROM contractors WHERE id = :contractor_id"), {"contractor_id": contractor_id})
        row = result.fetchone()
    return row[0] if row else None

# ------------------- INCIDENT REPORTS ------------------
def clean_data(data: dict):
    """Convert empty strings to None"""
    return {k: (None if v == "" else v) for k, v in data.items()}

def save_incident_report(data, uploaded_by="Unknown"):
    """Save incident report into DB"""
    data = clean_data(data)
    contractor_id = get_active_contractor()

    # Prepare data for insertion
    insert_data = {
        "incident_date": data.get("incident_date"),
        "incident_time": str(data.get("incident_time")) if data.get("incident_time") else None,
        "caller": data.get("caller"),
        "phone_number": data.get("phone_number"),
        "location": data.get("location"),
        "bound": data.get("bound"),
        "chainage": data.get("chainage"),
        "num_vehicles": data.get("num_vehicles"),
        "vehicle_type": data.get("vehicle_type"),
        "vehicle_condition": data.get("vehicle_condition"),
        "num_injured": data.get("num_injured"),
        "cond_injured": data.get("cond_injured"),
        "injured_part": data.get("injured_part"),
        "fire_hazard": data.get("fire_hazard"),
        "oil_leakage": data.get("oil_leakage"),
        "chemical_leakage": data.get("chemical_leakage"),
        "damage_road_furniture": data.get("damage_road_furniture"),
        "response_time": data.get("response_time"),
        "clearing_time": data.get("clearing_time"),
        "department_contact": data.get("department_contact"),
        "description": data.get("description"),
        "patrol_car": data.get("patrol_car"),
        "incident_type": data.get("incident_type"),
        "uploaded_by": uploaded_by,
        "contractor_id": contractor_id,
        "created_at": datetime.now()
    }

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO incident_reports (
                    incident_date, incident_time, caller, phone_number,
                    location, bound, chainage, num_vehicles, vehicle_type,
                    vehicle_condition, num_injured, cond_injured, injured_part,
                    fire_hazard, oil_leakage, chemical_leakage, damage_road_furniture,
                    response_time, clearing_time, department_contact,
                    description, patrol_car, incident_type, created_at,
                    uploaded_by, contractor_id
                ) VALUES (
                    :incident_date, :incident_time, :caller, :phone_number,
                    :location, :bound, :chainage, :num_vehicles, :vehicle_type,
                    :vehicle_condition, :num_injured, :cond_injured, :injured_part,
                    :fire_hazard, :oil_leakage, :chemical_leakage, :damage_road_furniture,
                    :response_time, :clearing_time, :department_contact,
                    :description, :patrol_car, :incident_type, :created_at,
                    :uploaded_by, :contractor_id
                )
            """), insert_data)

            # Get the last inserted row id for SQLite
            result = conn.execute(text("SELECT last_insert_rowid()"))
            row = result.fetchone()
            report_id = row[0] if row else 0
    except Exception as e:
        print(f"Error saving incident report: {e}")
        return 0

    return report_id

def save_incident_image(incident_id, image_bytes, image_name):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO incident_images (incident_id, image_data, image_name)
            VALUES (:incident_id, :image_data, :image_name)
        """), {
            "incident_id": incident_id,
            "image_data": image_bytes,  # SQLite can handle bytes directly
            "image_name": image_name
        })


def get_incident_images(report_id, only_meta=False):
    with engine.begin() as conn:
        if only_meta:
            query = text("""
                SELECT id, image_name
                FROM incident_images
                WHERE incident_id = :incident_id
            """)
            rows = conn.execute(query, {"incident_id": report_id}).mappings().all()
            return rows
        else:
            query = text("""
                SELECT id, image_name, image_data
                FROM incident_images
                WHERE incident_id = :incident_id
            """)
            rows = conn.execute(query, {"incident_id": report_id}).mappings().all()
            return rows

# ------------------- IDLE REPORTS ---------------------
def save_idle_report(idle_df, uploaded_by):
    """Save multiple idle records using bulk insert"""
    if idle_df.empty:
        return
    contractor_id = get_active_contractor()
    idle_df = idle_df.copy()
    idle_df.columns = [c.lower() for c in idle_df.columns]
    idle_df['uploaded_by'] = uploaded_by
    idle_df['contractor_id'] = contractor_id

    # Only keep columns that exist in the database table
    valid_columns = ['vehicle', 'idle_start', 'idle_end', 'idle_duration_min',
                     'location_address', 'latitude', 'longitude', 'description',
                     'uploaded_by', 'contractor_id']
    idle_df = idle_df[[col for col in valid_columns if col in idle_df.columns]]

    try:
        idle_df.to_sql('idle_reports', engine, if_exists='append', index=False)
    except Exception as e:
        print("❌ Error saving idle report:", e)
        traceback.print_exc()

# -------------------------------------------------------

# ------------------- USER MANAGEMENT -------------------
def add_user(username, plain_password, name, contractor_id=None, role="contractor"):
    """Add a new user with hashed password"""
    hashed = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()

    if USE_SQLITE:
        engine = get_sqlalchemy_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT OR IGNORE INTO users (username, password_hash, role, contractor_id)
                VALUES (:username, :password_hash, :role, :contractor_id)
            """), {
                "username": username,
                "password_hash": hashed,
                "role": role,
                "contractor_id": contractor_id
            })
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, contractor_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
            """,
            (username, hashed, role, contractor_id)
        )
        conn.commit()
        cur.close()
        conn.close()

def get_user(username, contractor_id=None):
    """Fetch user for login. If contractor_id is passed, restrict login to that contractor."""
    engine = get_sqlalchemy_engine()

    if contractor_id:
        query = text("""
            SELECT id, username, password_hash as password, role, contractor_id
            FROM users
            WHERE username = :username AND contractor_id = :contractor_id
        """)
        params = {"username": username, "contractor_id": contractor_id}
    else:
        query = text("""
            SELECT id, username, password_hash as password, role, contractor_id
            FROM users
            WHERE username = :username
        """)
        params = {"username": username}

    with engine.begin() as conn:
        result = conn.execute(query, params)
        row = result.fetchone()

    return dict(row) if row else None

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
# -------------------------------------------------------

# ------------------- ACTIVE CONTRACTOR -----------------
def get_active_contractor():
    """
    Decide which contractor's data to use:
    - Contractor users → their own contractor
    - RE users → contractor selected in sidebar
    """
    if "role" in st.session_state and st.session_state["role"] == "re_admin":
        return st.session_state.get("active_contractor")
    return st.session_state.get("contractor_id")

def get_contractor_id(name):
    engine = get_sqlalchemy_engine()
    with engine.begin() as conn:
        result = conn.execute(text("SELECT id FROM contractors WHERE name = :name"), {"name": name})
        row = result.fetchone()
    return row[0] if row else None

def get_contractor_name(contractor_id):
    if not contractor_id:
        return None
    engine = get_sqlalchemy_engine()
    with engine.begin() as conn:
        result = conn.execute(text("SELECT name FROM contractors WHERE id = :contractor_id"), {"contractor_id": contractor_id})
        row = result.fetchone()
    return row[0] if row else None
# -------------------------------------------------------

# ------------------- INCIDENT REPORTS ------------------
def clean_data(data: dict):
    """Convert empty strings to None"""
    return {k: (None if v == "" else v) for k, v in data.items()}

def save_incident_report(data, uploaded_by="Unknown"):
    """Save incident report into DB"""
    data = clean_data(data)
    contractor_id = get_active_contractor()
    engine = get_sqlalchemy_engine()

    # Prepare data for insertion
    insert_data = {
        "incident_date": data.get("incident_date"),
        "incident_time": str(data.get("incident_time")) if data.get("incident_time") else None,
        "caller": data.get("caller"),
        "phone_number": data.get("phone_number"),
        "location": data.get("location"),
        "bound": data.get("bound"),
        "chainage": data.get("chainage"),
        "num_vehicles": data.get("num_vehicles"),
        "vehicle_type": data.get("vehicle_type"),
        "vehicle_condition": data.get("vehicle_condition"),
        "num_injured": data.get("num_injured"),
        "cond_injured": data.get("cond_injured"),
        "injured_part": data.get("injured_part"),
        "fire_hazard": data.get("fire_hazard"),
        "oil_leakage": data.get("oil_leakage"),
        "chemical_leakage": data.get("chemical_leakage"),
        "damage_road_furniture": data.get("damage_road_furniture"),
        "response_time": data.get("response_time"),
        "clearing_time": data.get("clearing_time"),
        "department_contact": data.get("department_contact"),
        "description": data.get("description"),
        "patrol_car": data.get("patrol_car"),
        "incident_type": data.get("incident_type"),
        "uploaded_by": uploaded_by,
        "contractor_id": contractor_id
    }

    if USE_SQLITE:
        # SQLite version
        insert_data["created_at"] = datetime.now()

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO incident_reports (
                    incident_date, incident_time, caller, phone_number,
                    location, bound, chainage, num_vehicles, vehicle_type,
                    vehicle_condition, num_injured, cond_injured, injured_part,
                    fire_hazard, oil_leakage, chemical_leakage, damage_road_furniture,
                    response_time, clearing_time, department_contact,
                    description, patrol_car, incident_type, created_at,
                    uploaded_by, contractor_id
                ) VALUES (
                    :incident_date, :incident_time, :caller, :phone_number,
                    :location, :bound, :chainage, :num_vehicles, :vehicle_type,
                    :vehicle_condition, :num_injured, :cond_injured, :injured_part,
                    :fire_hazard, :oil_leakage, :chemical_leakage, :damage_road_furniture,
                    :response_time, :clearing_time, :department_contact,
                    :description, :patrol_car, :incident_type, :created_at,
                    :uploaded_by, :contractor_id
                )
            """), insert_data)

            # Get the last inserted row id for SQLite
            result = conn.execute(text("SELECT last_insert_rowid()"))
            row = result.fetchone()
            report_id = row[0] if row else None
            
            if not report_id or report_id <= 0:
                raise Exception("Failed to get valid report ID after insert")
    else:
        # PostgreSQL version
        with engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO incident_reports (
                    incident_date, incident_time, caller, phone_number,
                    location, bound, chainage, num_vehicles, vehicle_type,
                    vehicle_condition, num_injured, cond_injured, injured_part,
                    fire_hazard, oil_leakage, chemical_leakage, damage_road_furniture,
                    response_time, clearing_time, department_contact,
                    description, patrol_car, incident_type, created_at,
                    uploaded_by, contractor_id
                ) VALUES (
                    :incident_date, :incident_time, :caller, :phone_number,
                    :location, :bound, :chainage, :num_vehicles, :vehicle_type,
                    :vehicle_condition, :num_injured, :cond_injured, :injured_part,
                    :fire_hazard, :oil_leakage, :chemical_leakage, :damage_road_furniture,
                    :response_time, :clearing_time, :department_contact,
                    :description, :patrol_car, :incident_type, NOW(),
                    :uploaded_by, :contractor_id
                )
                RETURNING id
            """), insert_data)

            row = result.fetchone()
            report_id = row[0] if row else None
            
            if not report_id or report_id <= 0:
                raise Exception("Failed to get valid report ID after insert")

    return report_id

def save_incident_image(incident_id, image_bytes, image_name, conn=None):
    """Save image as raw bytes to ensure proper storage and retrieval
    
    Args:
        incident_id: The incident report ID
        image_bytes: Raw image bytes
        image_name: Name of the image file
        conn: Optional database connection (for transaction support)
    """
    # Ensure image_bytes is proper bytes type
    if isinstance(image_bytes, memoryview):
        image_bytes = bytes(image_bytes)
    elif not isinstance(image_bytes, bytes):
        image_bytes = bytes(image_bytes)

    # Critical: Ensure we save as raw bytes, not encoded strings
    # Convert to raw bytes and ensure no string conversion happens
    raw_bytes = bytes(image_bytes)

    print(f"DEBUG: Saving image {image_name} for incident {incident_id}: {len(raw_bytes)} bytes as {type(raw_bytes)}")

    if conn is not None:
        # Use provided connection (part of larger transaction)
        conn.execute(text("""
            INSERT INTO incident_images (incident_id, image_data, image_name)
            VALUES (:incident_id, :image_data, :image_name)
        """), {
            "incident_id": incident_id,
            "image_data": raw_bytes,  # Always raw bytes
            "image_name": image_name
        })
    else:
        # Create own transaction
        engine = get_sqlalchemy_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO incident_images (incident_id, image_data, image_name)
                VALUES (:incident_id, :image_data, :image_name)
            """), {
                "incident_id": incident_id,
                "image_data": raw_bytes,  # Always raw bytes
                "image_name": image_name
            })

    print(f"DEBUG: Successfully saved image {image_name} for incident {incident_id}")

def save_incident_with_images(data, uploaded_by, image_files=None):
    """Save incident report and images in a single atomic transaction
    
    This ensures that either both the incident and all images are saved,
    or nothing is saved (preventing orphaned records).
    
    Args:
        data: Dictionary containing incident report data
        uploaded_by: Username of the person uploading
        image_files: List of image files (file objects or tuples of (bytes, name))
        
    Returns:
        report_id: The ID of the saved incident report
        
    Raises:
        Exception: If saving fails for any reason
    """
    engine = get_sqlalchemy_engine()
    contractor_id = get_active_contractor()
    
    # Prepare data for insertion
    insert_data = {
        "incident_date": data.get("incident_date"),
        "incident_time": str(data.get("incident_time")) if data.get("incident_time") else None,
        "caller": data.get("caller"),
        "phone_number": data.get("phone_number"),
        "location": data.get("location"),
        "bound": data.get("bound"),
        "chainage": data.get("chainage"),
        "num_vehicles": data.get("num_vehicles"),
        "vehicle_type": data.get("vehicle_type"),
        "vehicle_condition": data.get("vehicle_condition"),
        "num_injured": data.get("num_injured"),
        "cond_injured": data.get("cond_injured"),
        "injured_part": data.get("injured_part"),
        "fire_hazard": data.get("fire_hazard"),
        "oil_leakage": data.get("oil_leakage"),
        "chemical_leakage": data.get("chemical_leakage"),
        "damage_road_furniture": data.get("damage_road_furniture"),
        "response_time": data.get("response_time"),
        "clearing_time": data.get("clearing_time"),
        "department_contact": data.get("department_contact"),
        "description": data.get("description"),
        "patrol_car": data.get("patrol_car"),
        "incident_type": data.get("incident_type"),
        "uploaded_by": uploaded_by,
        "contractor_id": contractor_id
    }
    
    # Single transaction for both incident and images
    with engine.begin() as conn:
        if USE_SQLITE:
            # SQLite version
            insert_data["created_at"] = datetime.now()
            
            conn.execute(text("""
                INSERT INTO incident_reports (
                    incident_date, incident_time, caller, phone_number,
                    location, bound, chainage, num_vehicles, vehicle_type,
                    vehicle_condition, num_injured, cond_injured, injured_part,
                    fire_hazard, oil_leakage, chemical_leakage, damage_road_furniture,
                    response_time, clearing_time, department_contact,
                    description, patrol_car, incident_type, created_at,
                    uploaded_by, contractor_id
                ) VALUES (
                    :incident_date, :incident_time, :caller, :phone_number,
                    :location, :bound, :chainage, :num_vehicles, :vehicle_type,
                    :vehicle_condition, :num_injured, :cond_injured, :injured_part,
                    :fire_hazard, :oil_leakage, :chemical_leakage, :damage_road_furniture,
                    :response_time, :clearing_time, :department_contact,
                    :description, :patrol_car, :incident_type, :created_at,
                    :uploaded_by, :contractor_id
                )
            """), insert_data)
            
            # Get the last inserted row id for SQLite
            result = conn.execute(text("SELECT last_insert_rowid()"))
            row = result.fetchone()
            report_id = row[0] if row else None
        else:
            # PostgreSQL version
            result = conn.execute(text("""
                INSERT INTO incident_reports (
                    incident_date, incident_time, caller, phone_number,
                    location, bound, chainage, num_vehicles, vehicle_type,
                    vehicle_condition, num_injured, cond_injured, injured_part,
                    fire_hazard, oil_leakage, chemical_leakage, damage_road_furniture,
                    response_time, clearing_time, department_contact,
                    description, patrol_car, incident_type, created_at,
                    uploaded_by, contractor_id
                ) VALUES (
                    :incident_date, :incident_time, :caller, :phone_number,
                    :location, :bound, :chainage, :num_vehicles, :vehicle_type,
                    :vehicle_condition, :num_injured, :cond_injured, :injured_part,
                    :fire_hazard, :oil_leakage, :chemical_leakage, :damage_road_furniture,
                    :response_time, :clearing_time, :department_contact,
                    :description, :patrol_car, :incident_type, NOW(),
                    :uploaded_by, :contractor_id
                )
                RETURNING id
            """), insert_data)
            
            row = result.fetchone()
            report_id = row[0] if row else None
        
        if not report_id or report_id <= 0:
            raise Exception("Failed to get valid report ID after insert")
        
        # Save images in the same transaction
        if image_files:
            for img_file in image_files:
                # Handle different input formats
                if hasattr(img_file, 'read'):
                    # File-like object
                    file_bytes = img_file.read()
                    file_name = getattr(img_file, 'name', 'image.jpg')
                elif isinstance(img_file, tuple) and len(img_file) == 2:
                    # Tuple of (bytes, name)
                    file_bytes, file_name = img_file
                else:
                    # Assume it's raw bytes
                    file_bytes = img_file
                    file_name = 'image.jpg'
                
                # Ensure proper bytes type
                if isinstance(file_bytes, memoryview):
                    file_bytes = bytes(file_bytes)
                elif not isinstance(file_bytes, bytes):
                    file_bytes = bytes(file_bytes)
                
                raw_bytes = bytes(file_bytes)
                
                print(f"DEBUG: Saving image {file_name} for incident {report_id}: {len(raw_bytes)} bytes")
                
                # Save image in same transaction
                conn.execute(text("""
                    INSERT INTO incident_images (incident_id, image_data, image_name)
                    VALUES (:incident_id, :image_data, :image_name)
                """), {
                    "incident_id": report_id,
                    "image_data": raw_bytes,
                    "image_name": file_name
                })
                
                print(f"DEBUG: Successfully saved image {file_name} for incident {report_id}")
    
    return report_id

def get_recent_incident_reports(limit=20):
    engine = get_sqlalchemy_engine()
    contractor_id = get_active_contractor()

    base_query = """
        SELECT ir.*, c.name AS contractor_name
        FROM incident_reports ir
        JOIN contractors c ON ir.contractor_id = c.id
    """
    params = {"limit": limit}

    if contractor_id:
        base_query += " WHERE ir.contractor_id = :contractor_id"
        params["contractor_id"] = contractor_id

    base_query += " ORDER BY ir.created_at DESC LIMIT :limit"

    # Use SQLAlchemy engine directly for pandas compatibility
    df = pd.read_sql_query(text(base_query), engine, params=params)

    return df

def get_incident_images(report_id, only_meta=False):
    """Retrieve images ensuring they are returned as proper bytes"""
    engine = get_sqlalchemy_engine()
    with engine.begin() as conn:
        if only_meta:
            query = text("""
                SELECT id, image_name
                FROM incident_images
                WHERE incident_id = :incident_id
            """)
            rows = conn.execute(query, {"incident_id": report_id}).mappings().all()
            return rows
        else:
            query = text("""
                SELECT id, image_name, image_data
                FROM incident_images
                WHERE incident_id = :incident_id
            """)
            result = conn.execute(query, {"incident_id": report_id}).mappings().all()

            # Process rows to ensure image_data is always proper bytes
            processed_rows = []
            for row in result:
                row_dict = dict(row)
                image_data = row_dict["image_data"]

                print(f"DEBUG: Retrieved image data type: {type(image_data)}, length: {len(image_data) if image_data else 0}")

                # Ensure image_data is proper bytes for image display
                if image_data is not None:
                    if isinstance(image_data, memoryview):
                        # PostgreSQL returns BLOB as memoryview
                        image_bytes = bytes(image_data)
                        print(f"DEBUG: Converted memoryview to bytes: {len(image_bytes)} bytes")
                    elif isinstance(image_data, bytes):
                        # Already bytes - this should be the normal case
                        image_bytes = image_data
                        print(f"DEBUG: Image data already bytes: {len(image_bytes)} bytes")
                    elif isinstance(image_data, str):
                        # This indicates data was stored as text - major issue
                        print(f"ERROR: Image data retrieved as string! This indicates improper storage. Length: {len(image_data)}")
                        print(f"First 50 chars: {image_data[:50]}")

                        # Try to decode as hex (most common issue)
                        import binascii
                        try:
                            if all(c in '0123456789abcdefABCDEF' for c in image_data.strip()):
                                image_bytes = binascii.unhexlify(image_data.strip())
                                print(f"SUCCESS: Recovered hex-encoded image: {len(image_bytes)} bytes")
                            else:
                                # Try base64
                                import base64
                                image_bytes = base64.b64decode(image_data)
                                print(f"SUCCESS: Recovered base64-encoded image: {len(image_bytes)} bytes")
                        except Exception as e:
                            print(f"FAILED: Could not decode string data: {e}")
                            # Last resort: encode as latin-1
                            image_bytes = image_data.encode('latin-1')
                            print(f"FALLBACK: Encoded as latin-1: {len(image_bytes)} bytes")
                    else:
                        # Convert other types to bytes
                        try:
                            image_bytes = bytes(image_data)
                            print(f"DEBUG: Converted other type to bytes: {len(image_bytes)} bytes")
                        except TypeError:
                            image_bytes = str(image_data).encode('latin-1')
                            print(f"DEBUG: Converted via string to bytes: {len(image_bytes)} bytes")

                    row_dict["image_data"] = image_bytes
                else:
                    print("WARNING: Image data is None")

                processed_rows.append(row_dict)
            return processed_rows
# -------------------------------------------------------

# ------------------- IDLE REPORTS ---------------------
def save_idle_report(idle_df, uploaded_by):
    """Save multiple idle records using bulk insert"""
    if idle_df.empty:
        return
    contractor_id = get_active_contractor()
    idle_df = idle_df.copy()
    idle_df.columns = [c.lower() for c in idle_df.columns]
    idle_df['uploaded_by'] = uploaded_by
    idle_df['contractor_id'] = contractor_id
    idle_df['uploaded_at'] = datetime.now()

    # Only keep columns that exist in the database table
    valid_columns = ['vehicle', 'idle_start', 'idle_end', 'idle_duration_min',
                     'location_address', 'latitude', 'longitude', 'description',
                     'uploaded_by', 'uploaded_at', 'contractor_id']
    idle_df = idle_df[[col for col in valid_columns if col in idle_df.columns]]

    engine = get_sqlalchemy_engine()
    try:
        idle_df.to_sql('idle_reports', engine, if_exists='append', index=False)
    except Exception as e:
        print("❌ Error saving idle report:", e)
        traceback.print_exc()

def get_idle_reports(limit=10000):
    """Fetch idle reports"""
    contractor_id = get_active_contractor()
    engine = get_sqlalchemy_engine()

    query = """
        SELECT id, vehicle, idle_start, idle_end, idle_duration_min,
               location_address, latitude, longitude,
               uploaded_by, uploaded_at, contractor_id
        FROM idle_reports
    """
    params = {"limit": limit}

    if contractor_id:
        query += " WHERE contractor_id = :contractor_id"
        params["contractor_id"] = contractor_id

    query += " ORDER BY uploaded_at DESC LIMIT :limit"

    df = pd.read_sql_query(text(query), engine, params=params)
    return df
# -------------------------------------------------------
