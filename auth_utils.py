# auth_utils.py - User authentication and contractor management utilities
import bcrypt
import streamlit as st
from sqlalchemy import text
from db_utils import get_sqlalchemy_engine

engine = get_sqlalchemy_engine()


def add_user(username, plain_password, role="contractor", contractor_id=None):
    """Add a new user to the database."""
    hashed = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO users
                    (username, password_hash, role, contractor_id)
                    VALUES (:username, :password_hash, :role, :contractor_id)
                    ON CONFLICT (username) DO NOTHING
            """),
            {"username": username, "password_hash": hashed, "role": role, "contractor_id": contractor_id}
        )


def get_user(username, contractor_id=None):
    """Retrieve a user by username (and optionally contractor_id)."""
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
    """Verify a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_active_contractor():
    """Get the active contractor ID from session state."""
    if st.session_state.get("role") == "re_admin":
        return st.session_state.get("active_contractor")
    return st.session_state.get("contractor_id")


def get_contractor_id(name):
    """Get contractor ID by name."""
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM contractors WHERE name=:name"),
            {"name": name}
        ).fetchone()
    return row[0] if row else None


def get_contractor_name(contractor_id):
    """Get contractor name by ID."""
    if not contractor_id:
        return None
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT name FROM contractors WHERE id=:contractor_id"),
            {"contractor_id": contractor_id}
        ).fetchone()
    return row[0] if row else None
