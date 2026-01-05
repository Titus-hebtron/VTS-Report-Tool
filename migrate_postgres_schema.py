"""
PostgreSQL Schema Migration Script
Fixes auto-increment columns and binary data storage for incident reports.

This script:
1. Adds auto-increment sequences to id columns
2. Fixes image_data column to use bytea instead of text
"""

from db_utils import get_sqlalchemy_engine
from sqlalchemy import text

def _is_sqlite():
    """Check if using SQLite database"""
    engine = get_sqlalchemy_engine()
    return engine.dialect.name == "sqlite"

def migrate_postgres_schema():
    """Migrate PostgreSQL schema to fix auto-increment and binary storage"""
    
    if _is_sqlite():
        print("Database is SQLite - no migration needed")
        return
    
    print("Starting PostgreSQL schema migration...")
    engine = get_sqlalchemy_engine()
    
    try:
        with engine.begin() as conn:
            # Fix incident_reports.id column
            print("\n1. Fixing incident_reports.id auto-increment...")
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS incident_reports_id_seq"))
            result = conn.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM incident_reports"))
            next_id = result.fetchone()[0]
            conn.execute(text(f"ALTER SEQUENCE incident_reports_id_seq RESTART WITH {next_id}"))
            conn.execute(text("ALTER TABLE incident_reports ALTER COLUMN id SET DEFAULT nextval('incident_reports_id_seq')"))
            conn.execute(text("ALTER SEQUENCE incident_reports_id_seq OWNED BY incident_reports.id"))
            print("   ✅ incident_reports.id fixed")
            
            # Fix incident_images.id column
            print("\n2. Fixing incident_images.id auto-increment...")
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS incident_images_id_seq"))
            result = conn.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM incident_images"))
            next_id = result.fetchone()[0]
            conn.execute(text(f"ALTER SEQUENCE incident_images_id_seq RESTART WITH {next_id}"))
            conn.execute(text("ALTER TABLE incident_images ALTER COLUMN id SET DEFAULT nextval('incident_images_id_seq')"))
            conn.execute(text("ALTER SEQUENCE incident_images_id_seq OWNED BY incident_images.id"))
            print("   ✅ incident_images.id fixed")
            
            # Fix incident_images.image_data column
            print("\n3. Fixing incident_images.image_data to use bytea...")
            # Check current type
            result = conn.execute(text("""
                SELECT data_type FROM information_schema.columns 
                WHERE table_name = 'incident_images' AND column_name = 'image_data'
            """))
            current_type = result.fetchone()[0]
            
            if current_type != 'bytea':
                print(f"   Current type: {current_type}, converting to bytea...")
                conn.execute(text("""
                    ALTER TABLE incident_images 
                    ALTER COLUMN image_data TYPE bytea 
                    USING image_data::bytea
                """))
                print("   ✅ incident_images.image_data converted to bytea")
            else:
                print("   ✅ incident_images.image_data already bytea")
            
        print("\n✅ Migration completed successfully!")
        print("\nNOTE: If you had existing images stored as text, they may need to be re-uploaded.")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate_postgres_schema()