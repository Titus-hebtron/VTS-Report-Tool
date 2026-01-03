#!/usr/bin/env python3
"""
Test the actual Render database connection
"""
import os
from sqlalchemy import create_engine, text

# Your actual Render DATABASE_URL
DATABASE_URL = "postgresql://vts_database_gjwk_user:n4xw1WPj2nsL43ZNIEwS15SBwljyUW94@dpg-d41n30fdiees73ejr6gg-a.singapore-postgres.render.com:5432/vts_database_gjwk?sslmode=require"

print("🔍 Testing Render PostgreSQL connection...")
print(f"Host: dpg-d41n30fdiees73ejr6gg-a.singapore-postgres.render.com")
print(f"Database: vts_database_gjwk")
print(f"SSL: require (from URL)")

try:
    # Since sslmode is in URL, we don't need to add it to connect_args
    # But we can add other connection parameters
    connect_args = {
        "connect_timeout": 30,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
    
    print("\n📡 Creating engine with 30s timeout...")
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_size=3,
        max_overflow=7,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_timeout=30,
        echo=False
    )
    
    print("🔌 Connecting to database (this may take 30-60s if database is sleeping)...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"\n✅ Connection successful!")
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
            
        print("\n✅ All checks passed! Database is working correctly.")
        
except Exception as e:
    print(f"\n❌ Connection failed: {e}")
    print(f"\nError type: {type(e).__name__}")
    
    if "timeout" in str(e).lower():
        print("\n💡 The database is likely sleeping (Render free tier).")
        print("   Solutions:")
        print("   1. Wait 1-2 minutes and try again")
        print("   2. Upgrade to paid tier ($7/month) for always-on database")
        print("   3. Use SQLite for local development (automatic fallback)")
    elif "ssl" in str(e).lower():
        print("\n💡 SSL connection issue.")
        print("   The URL already has ?sslmode=require which should work.")
    else:
        print("\n💡 Check if:")
        print("   1. Database is running in Render dashboard")
        print("   2. Network connectivity is working")
        print("   3. Credentials are correct")
    
    exit(1)