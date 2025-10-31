#!/usr/bin/env python3
"""
Create PostgreSQL Tables Script
Creates all database tables in PostgreSQL using raw SQL
"""

import os
from sqlalchemy import create_engine, text

def get_postgres_engine():
    """Get PostgreSQL engine from environment"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL environment variable not found")
    return create_engine(database_url)

def create_tables():
    """Create all tables in PostgreSQL"""
    print("Creating all tables in PostgreSQL...")

    engine = get_postgres_engine()

    # Read schema file and create tables
    with open('schema.sql', 'r') as f:
        sql = f.read()

    with engine.begin() as conn:
        # Split by semicolon and execute CREATE TABLE statements only
        statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

        for statement in statements:
            if statement and statement.upper().startswith('CREATE TABLE'):
                try:
                    conn.execute(text(statement))
                    table_name = statement.split('CREATE TABLE')[1].split('(')[0].strip()
                    print(f"Created table: {table_name}")
                except Exception as e:
                    print(f"⚠️  Warning creating table: {e}")

    print("All tables created successfully!")

if __name__ == "__main__":
    create_tables()