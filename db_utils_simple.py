# db_utils.py - Simplified SQLite version
from sqlalchemy import create_engine

# Use SQLite instead of Postgres
engine = create_engine("sqlite:///vts_database.db", connect_args={"check_same_thread": False})

def get_connection():
    return engine.raw_connection()

def get_sqlalchemy_engine():
    return engine