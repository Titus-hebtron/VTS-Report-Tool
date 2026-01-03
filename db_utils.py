# db_utils.py - Cleaned SQLite/PostgreSQL version
from sqlalchemy import create_engine, text
import bcrypt
import pandas as pd
import streamlit as st
from datetime import datetime
import os
import sqlite3
import traceback

# ------------------- SQLITE DATETIME ADAPTER -------------------
def adapt_datetime(dt):
    return dt.isoformat()
sqlite3.register_adapter(datetime, adapt_datetime)

# ------------------- DATABASE CONFIG -------------------
DATABASE_URL = os.getenv("DATABASE_URL")
USE_SQLITE = True

if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.strip()
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if DATABASE_URL.startswith("postgresql://"):
        USE_SQLITE = False

# ------------------- ENGINE CREATION (ONLY ONCE) -------------------
def create_db_engine():
    global USE_SQLITE
    if USE_SQLITE:
        print("✅ Using SQLite database: vts_database.db")
        return create_engine(
            "sqlite:///vts_database.db",
            connect_args={"check_same_thread": False}
        )
    
    # PostgreSQL engine
    print(f"📊 Connecting to PostgreSQL database...")
    
    # Check if sslmode is already in URL
    has_sslmode_in_url = '?sslmode=' in DATABASE_URL or '&sslmode=' in DATABASE_URL
    
    connect_args = {
        "connect_timeout": 30,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
    
    # Only add sslmode if not already in URL
    if not has_sslmode_in_url:
        connect_args["sslmode"] = "require"
    
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=7,
            pool_timeout=30,
            pool_recycle=3600,
            connect_args=connect_args
        )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        print("✅ PostgreSQL connected successfully")
        return engine
        
    except Exception as e:
        print(f"⚠️  PostgreSQL connection failed: {e}")
        print("🔄 Falling back to SQLite for local operation")
        # Fall back to SQLite if PostgreSQL fails
        USE_SQLITE = True
        return create_engine(
            "sqlite:///vts_database.db",
            connect_args={"check_same_thread": False}
        )

engine = create_db_engine()

# ------------------- HELPER FUNCTIONS -------------------
def get_sqlalchemy_engine():
    """Get the SQLAlchemy engine instance"""
    return engine

def get_connection():
    """Get a raw database connection"""
    return engine.raw_connection()

# ------------------- DATABASE INITIALIZATION -------------------
def init_database():
    """Initialize database tables if they don't exist"""
    print("Checking database initialization...")

    try:
        with engine.begin() as conn:
            # Check if users table exists
            if USE_SQLITE:
                result = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                )
            else:
                result = conn.execute(
                    text("SELECT table_name FROM information_schema.tables "
                         "WHERE table_name='users' AND table_schema='public'")
                )
            table_exists = result.fetchone() is not None

            if not table_exists:
                print("Creating database tables...")
                with open("schema.sql", "r") as f:
                    sql = f.read()

                if USE_SQLITE:
                    cursor = conn.connection.cursor()
                    cursor.executescript(sql)
                    cursor.close()
                else:
                    # PostgreSQL - split statements by semicolon
                    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.startswith("--")]
                    for stmt in statements:
                        conn.execute(text(stmt))
                print("Tables created successfully!")

                # Add default users
                default_users = [
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

                for username, pwd, name, cid, role in default_users:
                    hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
                    if USE_SQLITE:
                        conn.execute(
                            text("""INSERT OR IGNORE INTO users
                                (username, password_hash, role, contractor_id)
                                VALUES (:username, :password_hash, :role, :contractor_id)
                            """),
                            {"username": username, "password_hash": hashed, "role": role, "contractor_id": cid}
                        )
                    else:
                        conn.execute(
                            text("""INSERT INTO users
                                (username, password_hash, role, contractor_id)
                                VALUES (:username, :password_hash, :role, :contractor_id)
                                ON CONFLICT (username) DO NOTHING
                            """),
                            {"username": username, "password_hash": hashed, "role": role, "contractor_id": cid}
                        )
                print("Default users added!")
            else:
                print("Database tables already exist")

        print("✅ Database initialization completed successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise

# ------------------- USER MANAGEMENT -------------------
def add_user(username, plain_password, role="contractor", contractor_id=None):
    hashed = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()
    with engine.begin() as conn:
        if USE_SQLITE:
            conn.execute(
                text("""INSERT OR IGNORE INTO users
                        (username, password_hash, role, contractor_id)
                        VALUES (:username, :password_hash, :role, :contractor_id)
                """),
                {"username": username, "password_hash": hashed, "role": role, "contractor_id": contractor_id}
            )
        else:
            conn.execute(
                text("""INSERT INTO users
                        (username, password_hash, role, contractor_id)
                        VALUES (:username, :password_hash, :role, :contractor_id)
                        ON CONFLICT (username) DO NOTHING
                """),
                {"username": username, "password_hash": hashed, "role": role, "contractor_id": contractor_id}
            )

def get_user(username, contractor_id=None):
    query = """SELECT id, username, password_hash AS password, role, contractor_id
               FROM users WHERE username=:username"""
    params = {"username": username}
    if contractor_id:
        query += " AND contractor_id=:contractor_id"
        params["contractor_id"] = contractor_id
    with engine.begin() as conn:
        row = conn.execute(text(query), params).fetchone()
    return dict(row) if row else None

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

# ------------------- ACTIVE CONTRACTOR -------------------
def get_active_contractor():
    if st.session_state.get("role") == "re_admin":
        return st.session_state.get("active_contractor")
    return st.session_state.get("contractor_id")

def get_contractor_id(name):
    with engine.begin() as conn:
        row = conn.execute(text("SELECT id FROM contractors WHERE name=:name"), {"name": name}).fetchone()
    return row[0] if row else None

def get_contractor_name(contractor_id):
    if not contractor_id:
        return None
    with engine.begin() as conn:
        row = conn.execute(text("SELECT name FROM contractors WHERE id=:contractor_id"),
                           {"contractor_id": contractor_id}).fetchone()
    return row[0] if row else None

# ------------------- INCIDENT REPORTS -------------------
def clean_data(data: dict):
    return {k: (None if v == "" else v) for k, v in data.items()}

def save_incident_report(data, uploaded_by="Unknown"):
    data = clean_data(data)
    contractor_id = get_active_contractor()
    insert_data = {**data, "uploaded_by": uploaded_by, "contractor_id": contractor_id}

    with engine.begin() as conn:
        if USE_SQLITE:
            insert_data["created_at"] = datetime.now()
            conn.execute(
                text("""INSERT INTO incident_reports (
                        incident_date, incident_time, caller, phone_number,
                        location, bound, chainage, num_vehicles, vehicle_type,
                        vehicle_condition, num_injured, cond_injured, injured_part,
                        fire_hazard, oil_leakage, chemical_leakage, damage_road_furniture,
                        response_time, clearing_time, department_contact,
                        description, patrol_car, incident_type, created_at,
                        uploaded_by, contractor_id)
                    VALUES (
                        :incident_date, :incident_time, :caller, :phone_number,
                        :location, :bound, :chainage, :num_vehicles, :vehicle_type,
                        :vehicle_condition, :num_injured, :cond_injured, :injured_part,
                        :fire_hazard, :oil_leakage, :chemical_leakage, :damage_road_furniture,
                        :response_time, :clearing_time, :department_contact,
                        :description, :patrol_car, :incident_type, :created_at,
                        :uploaded_by, :contractor_id)
                """), insert_data)
            report_id = conn.execute(text("SELECT last_insert_rowid()")).fetchone()[0]
        else:
            result = conn.execute(
                text("""INSERT INTO incident_reports (
                        incident_date, incident_time, caller, phone_number,
                        location, bound, chainage, num_vehicles, vehicle_type,
                        vehicle_condition, num_injured, cond_injured, injured_part,
                        fire_hazard, oil_leakage, chemical_leakage, damage_road_furniture,
                        response_time, clearing_time, department_contact,
                        description, patrol_car, incident_type, created_at,
                        uploaded_by, contractor_id)
                    VALUES (
                        :incident_date, :incident_time, :caller, :phone_number,
                        :location, :bound, :chainage, :num_vehicles, :vehicle_type,
                        :vehicle_condition, :num_injured, :cond_injured, :injured_part,
                        :fire_hazard, :oil_leakage, :chemical_leakage, :damage_road_furniture,
                        :response_time, :clearing_time, :department_contact,
                        :description, :patrol_car, :incident_type, NOW(),
                        :uploaded_by, :contractor_id)
                    RETURNING id
                """), insert_data)
            report_id = result.fetchone()[0]

    return report_id

def save_incident_image(incident_id, image_bytes, image_name, conn=None):
    if isinstance(image_bytes, memoryview):
        image_bytes = bytes(image_bytes)
    elif not isinstance(image_bytes, bytes):
        image_bytes = bytes(image_bytes)

    if conn:
        conn.execute(
            text("INSERT INTO incident_images (incident_id, image_data, image_name) VALUES "
                 "(:incident_id, :image_data, :image_name)"),
            {"incident_id": incident_id, "image_data": image_bytes, "image_name": image_name}
        )
    else:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO incident_images (incident_id, image_data, image_name) VALUES "
                     "(:incident_id, :image_data, :image_name)"),
                {"incident_id": incident_id, "image_data": image_bytes, "image_name": image_name}
            )

def get_incident_images(report_id, only_meta=False):
    with engine.begin() as conn:
        if only_meta:
            rows = conn.execute(
                text("SELECT id, image_name FROM incident_images WHERE incident_id=:incident_id"),
                {"incident_id": report_id}
            ).mappings().all()
        else:
            rows = conn.execute(
                text("SELECT id, image_name, image_data FROM incident_images WHERE incident_id=:incident_id"),
                {"incident_id": report_id}
            ).mappings().all()
            # Ensure proper bytes
            processed_rows = []
            for r in rows:
                row_dict = dict(r)
                if row_dict.get("image_data") is not None:
                    row_dict["image_data"] = bytes(row_dict["image_data"])
                processed_rows.append(row_dict)
            return processed_rows
    return rows

def get_recent_incident_reports(limit=20):
    """Fetch recent incident reports with contractor information"""
    contractor_id = get_active_contractor()
    
    query = """
        SELECT ir.*, c.name AS contractor_name
        FROM incident_reports ir
        JOIN contractors c ON ir.contractor_id = c.id
    """
    params = {"limit": limit}
    
    if contractor_id:
        query += " WHERE ir.contractor_id = :contractor_id"
        params["contractor_id"] = contractor_id
    
    query += " ORDER BY ir.created_at DESC LIMIT :limit"
    
    df = pd.read_sql_query(text(query), engine, params=params)
    return df

def save_incident_with_images(data, uploaded_by="Unknown", image_files=None):
    """Save an incident and associated images in a single operation.

    `image_files` may be a list of dicts like {"name": ..., "data": ...}
    or a list of (name, bytes) tuples.
    """
    # First save the incident
    report_id = save_incident_report(data, uploaded_by=uploaded_by)

    # Then save images (if any)
    if image_files:
        try:
            with engine.begin() as conn:
                for img in image_files:
                    img_name = None
                    img_bytes = None
                    if isinstance(img, dict):
                        img_name = img.get("name") or img.get("filename") or img.get("image_name")
                        img_bytes = img.get("data") or img.get("image_data") or img.get("bytes")
                    elif isinstance(img, (list, tuple)) and len(img) >= 2:
                        img_name, img_bytes = img[0], img[1]
                    else:
                        # Unsupported format; skip
                        continue

                    if img_bytes is None:
                        continue

                    # Normalize/compress image before saving
                    try:
                        norm_bytes = _normalize_image(img_bytes)
                    except Exception:
                        norm_bytes = img_bytes

                    conn.execute(
                        text("INSERT INTO incident_images (incident_id, image_data, image_name) VALUES (:incident_id, :image_data, :image_name)"),
                        {"incident_id": report_id, "image_data": norm_bytes, "image_name": img_name or "image.jpg"}
                    )
        except Exception as e:
            print(f"Error saving incident images: {e}")
            traceback.print_exc()

    return report_id

# ------------------- IDLE REPORTS -------------------
def save_idle_report(idle_df, uploaded_by):
    if idle_df.empty:
        return
    contractor_id = get_active_contractor()
    idle_df = idle_df.copy()
    idle_df.columns = [c.lower() for c in idle_df.columns]
    idle_df["uploaded_by"] = uploaded_by
    idle_df["contractor_id"] = contractor_id
    idle_df["uploaded_at"] = datetime.now()

    valid_columns = ['vehicle', 'idle_start', 'idle_end', 'idle_duration_min',
                     'location_address', 'latitude', 'longitude', 'description',
                     'uploaded_by', 'uploaded_at', 'contractor_id']
    idle_df = idle_df[[c for c in valid_columns if c in idle_df.columns]]

    try:
        idle_df.to_sql("idle_reports", engine, if_exists="append", index=False)
    except Exception as e:
        print("❌ Error saving idle report:", e)
        traceback.print_exc()

def get_idle_reports(limit=10000):
    contractor_id = get_active_contractor()
    query = "SELECT * FROM idle_reports"
    params = {}
    if contractor_id:
        query += " WHERE contractor_id=:contractor_id"
        params["contractor_id"] = contractor_id
    query += " ORDER BY uploaded_at DESC LIMIT :limit"
    params["limit"] = limit
    df = pd.read_sql_query(text(query), engine, params=params)
    return df
