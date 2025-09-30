# db_utils.py
import bcrypt
import pandas as pd
import traceback
from sqlalchemy import create_engine, text
import streamlit as st
from datetime import datetime
import os

# ------------------- DATABASE CONFIG -------------------
# Set to True for SQLite (works on Streamlit Cloud), False for PostgreSQL
USE_SQLITE = os.getenv("USE_SQLITE", "true").lower() == "true"

if USE_SQLITE:
    # SQLite configuration (file-based, works on Streamlit Cloud)
    DB_FILE = "vts_database.db"
else:
    # PostgreSQL configuration
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_NAME = "postgres"
    DB_USER = "postgres"
    DB_PASS = "Hebtron123"

    # Import psycopg2 only when needed
    import psycopg2
    import psycopg2.extras
# -------------------------------------------------------

# ------------------- CONNECTION HELPERS ----------------
def get_connection():
    if USE_SQLITE:
        # For SQLite, we'll use SQLAlchemy engine directly
        # This function returns None for SQLite since we use engine
        return None
    else:
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )

def get_sqlalchemy_engine():
    if USE_SQLITE:
        # SQLite engine with proper configuration for Streamlit
        db_url = f"sqlite:///{DB_FILE}"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        # Initialize database schema if using SQLite
        initialize_sqlite_database(engine)
        return engine
    else:
        db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        return create_engine(db_url)

def initialize_sqlite_database(engine):
    """Initialize SQLite database with schema if it doesn't exist"""
    try:
        # Check if tables exist by trying to query users table
        with engine.begin() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
            if not result.fetchone():
                # Tables don't exist, create them
                print("Initializing SQLite database...")

                # Read and execute schema.sql
                schema_path = "schema.sql"
                if os.path.exists(schema_path):
                    with open(schema_path, 'r') as f:
                        schema_sql = f.read()

                    # Split by semicolon and execute each statement
                    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

                    for statement in statements:
                        if statement:
                            try:
                                conn.execute(text(statement))
                            except Exception as e:
                                print(f"Warning: Could not execute statement: {statement[:50]}... Error: {e}")

                    print("✅ SQLite database initialized successfully!")
                else:
                    print("❌ schema.sql file not found!")
    except Exception as e:
        print(f"❌ Error initializing SQLite database: {e}")
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
                    :description, :patrol_car, :incident_type, :created_at,
                    :uploaded_by, :contractor_id
                )
            """), insert_data)

            # Get the last inserted row id for SQLite
            result = conn.execute(text("SELECT last_insert_rowid()"))
            report_id = result.fetchone()[0]
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

            report_id = result.fetchone()[0]

    return report_id

def save_incident_image(incident_id, image_bytes, image_name):
    engine = get_sqlalchemy_engine()

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO incident_images (incident_id, image_data, image_name)
            VALUES (:incident_id, :image_data, :image_name)
        """), {
            "incident_id": incident_id,
            "image_data": image_bytes,  # SQLite can handle bytes directly
            "image_name": image_name
        })

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

    df = pd.read_sql_query(text(base_query), engine, params=params)
    return df

def get_incident_images(report_id, only_meta=False):
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
            rows = conn.execute(query, {"incident_id": report_id}).mappings().all()
            return rows
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

    # Only keep columns that exist in the database table
    valid_columns = ['vehicle', 'idle_start', 'idle_end', 'idle_duration_min',
                     'location_address', 'latitude', 'longitude', 'description',
                     'uploaded_by', 'contractor_id']
    idle_df = idle_df[[col for col in valid_columns if col in idle_df.columns]]

    engine = get_sqlalchemy_engine()
    try:
        idle_df.to_sql('idle_reports', engine, if_exists='append', index=False)
    except Exception as e:
        print("❌ Error saving idle report:", e)
        traceback.print_exc()

def get_idle_reports(limit=100):
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
