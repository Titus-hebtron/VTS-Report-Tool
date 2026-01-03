#!/usr/bin/env python3
"""
Test database connection and initialization
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in environment variables")
    print("Please set DATABASE_URL in .env file or environment")
    exit(1)

print(f"🔍 Testing connection to database...")
print(f"Host: {DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else 'localhost'}")

try:
    # Configure connection with SSL for Render PostgreSQL
    connect_args = {
        "sslmode": "require",
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
    
    # Create engine with proper settings
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_size=2,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✅ Connection successful!")
        print(f"📊 PostgreSQL version: {version}")
        
        # Check if tables exist
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        if tables:
            print(f"\n📋 Existing tables ({len(tables)}):")
            for table in tables:
                print(f"   - {table}")
        else:
            print("\n📋 No tables found - database needs initialization")
            
        print("\n✅ Database connection test completed successfully!")
        
except Exception as e:
    print(f"\n❌ Connection failed: {e}")
    print(f"\nError type: {type(e).__name__}")
    
    if "SSL" in str(e).upper():
        print("\n💡 Hint: This appears to be an SSL-related error.")
        print("   Make sure your DATABASE_URL is correct and the database allows SSL connections.")
    elif "timeout" in str(e).lower():
        print("\n💡 Hint: Connection timeout - the database might be sleeping (free tier)")
        print("   or there might be network connectivity issues.")
    elif "authentication" in str(e).lower():
        print("\n💡 Hint: Authentication failed - check your username and password.")
    else:
        print("\n💡 Hint: Check your DATABASE_URL format and network connectivity.")
    
    exit(1)