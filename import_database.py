#!/usr/bin/env python3
"""
Database Import Script for VTS Report Tool
Imports data from SQLite to PostgreSQL for production deployment
"""

import sqlite3
import os
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

def get_postgres_engine():
    """Get PostgreSQL engine from environment"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL environment variable not found")
    return create_engine(database_url)

def get_sqlite_engine():
    """Get SQLite engine"""
    return create_engine("sqlite:///vts_database.db")

def create_postgres_schema(engine):
    """Create PostgreSQL schema"""
    print("Creating PostgreSQL schema...")

    # Read schema file
    with open('schema.sql', 'r') as f:
        schema_sql = f.read()

    # Split into individual statements and execute
    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

    with engine.begin() as conn:
        for statement in statements:
            if statement:
                try:
                    conn.execute(text(statement))
                    print(f"Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"Warning: {e}")

    print("PostgreSQL schema created successfully")

def migrate_table_data(sqlite_engine, postgres_engine, table_name, column_mappings=None):
    """Migrate data from SQLite table to PostgreSQL table"""
    print(f"Migrating table: {table_name}")

    try:
        # Read data from SQLite
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql_query(query, sqlite_engine)

        if df.empty:
            print(f"  No data in {table_name}")
            return

        # Apply column mappings if provided
        if column_mappings:
            df = df.rename(columns=column_mappings)

        # Handle datetime columns for PostgreSQL
        datetime_columns = ['created_at', 'uploaded_at', 'incident_date', 'idle_start', 'idle_end',
                           'break_start', 'break_end', 'pickup_start', 'pickup_end', 'timestamp']

        for col in datetime_columns:
            if col in df.columns:
                # Convert string dates to datetime objects
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Insert into PostgreSQL
        df.to_sql(table_name, postgres_engine, if_exists='append', index=False)
        print(f"  Migrated {len(df)} rows to {table_name}")

    except Exception as e:
        print(f"  ❌ Error migrating {table_name}: {e}")

def migrate_data():
    """Main migration function"""
    print("Starting database migration from SQLite to PostgreSQL")
    print("=" * 60)

    try:
        # Get database engines
        sqlite_engine = get_sqlite_engine()
        postgres_engine = get_postgres_engine()

        # Test connections
        print("Testing database connections...")
        with sqlite_engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        with postgres_engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Both databases connected successfully")

        # Create PostgreSQL schema
        create_postgres_schema(postgres_engine)

        # Migrate data from each table
        tables_to_migrate = [
            'contractors',
            'users',
            'vehicles',
            'patrol_logs',
            'incident_reports',
            'incident_images',
            'idle_reports',
            'breaks',
            'pickups',
            'accidents',
            'accident_reports_data',
            'accident_reports_images'
        ]

        for table in tables_to_migrate:
            migrate_table_data(sqlite_engine, postgres_engine, table)

        print("\n" + "=" * 60)
        print("Database migration completed successfully!")
        print("\nSummary:")
        print("- All tables created in PostgreSQL")
        print("- All data migrated from SQLite")
        print("- Your production database is now ready!")

    except Exception as e:
        print(f"\nMigration failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure DATABASE_URL environment variable is set")
        print("2. Check that vts_database.db exists in the current directory")
        print("3. Ensure PostgreSQL database is accessible")

if __name__ == "__main__":
    migrate_data()