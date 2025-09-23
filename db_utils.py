# db_utils.py
import psycopg2
import psycopg2.extras
import bcrypt
import pandas as pd
import traceback
from sqlalchemy import create_engine, text
import streamlit as st
from datetime import datetime

# ------------------- DATABASE CONFIG -------------------
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Hebtron123"
# -------------------------------------------------------

# ------------------- CONNECTION HELPERS ----------------
def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def get_sqlalchemy_engine():
    db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(db_url)
# -------------------------------------------------------

# ------------------- USER MANAGEMENT -------------------
def add_user(username, plain_password, name, contractor_id=None, role="contractor"):
    """Add a new user with hashed password"""
    hashed = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()
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
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if contractor_id:
        cur.execute(
            """
            SELECT id, username, password_hash as password, role, contractor_id
            FROM users
            WHERE username = %s AND contractor_id = %s
            """,
            (username, contractor_id)
        )
    else:
        cur.execute(
            """
            SELECT id, username, password_hash as password, role, contractor_id
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

    row = cur.fetchone()
    cur.close()
    conn.close()
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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM contractors WHERE name = %s", (name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
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

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO incident_reports (
            incident_date, incident_time, caller, phone_number,
            location, bound, chainage, num_vehicles, vehicle_type,
            vehicle_condition, num_injured, cond_injured, injured_part,
            fire_hazard, oil_leakage, chemical_leakage, damage_road_furniture,
            response_time, clearing_time, department_contact,
            description, patrol_car, incident_type, created_at,
            uploaded_by, contractor_id
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, NOW(),
            %s, %s
        )
        RETURNING id
    """, (
        data.get("incident_date"),
        str(data.get("incident_time")) if data.get("incident_time") else None,
        data.get("caller"),
        data.get("phone_number"),
        data.get("location"),
        data.get("bound"),
        data.get("chainage"),
        data.get("num_vehicles"),
        data.get("vehicle_type"),
        data.get("vehicle_condition"),
        data.get("num_injured"),
        data.get("cond_injured"),
        data.get("injured_part"),
        data.get("fire_hazard"),
        data.get("oil_leakage"),
        data.get("chemical_leakage"),
        data.get("damage_road_furniture"),
        data.get("response_time"),
        data.get("clearing_time"),
        data.get("department_contact"),
        data.get("description"),
        data.get("patrol_car"),
        data.get("incident_type"),
        uploaded_by,
        contractor_id
    ))

    report_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return report_id

def save_incident_image(incident_id, image_bytes, image_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO incident_images (incident_id, image_data, image_name) VALUES (%s, %s, %s)",
        (incident_id, psycopg2.Binary(image_bytes), image_name)
    )
    conn.commit()
    cur.close()
    conn.close()

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
