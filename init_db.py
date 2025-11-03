#!/usr/bin/env python3
"""
Initialize the SQLite database with schema
"""
from db_utils import get_sqlalchemy_engine
from sqlalchemy import text

def init_database():
    from db_utils import USE_SQLITE
    engine = get_sqlalchemy_engine()

    with open('schema.sql', 'r') as f:
        sql = f.read()

    # Use raw connection to execute multiple statements
    conn = engine.raw_connection()
    try:
        cursor = conn.cursor()
        if USE_SQLITE:
            cursor.executescript(sql)
        else:
            # PostgreSQL: split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
            for statement in statements:
                if statement:
                    cursor.execute(statement)
        conn.commit()
        print("Database initialized successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()