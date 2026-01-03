#!/usr/bin/env python3
"""
Validate environment variables for deployment
Run this on Render to check if DATABASE_URL is properly configured
"""

import os
import sys

print("=" * 60)
print("Environment Variables Validation")
print("=" * 60)

# Check DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

print("\n1. DATABASE_URL Check:")
if DATABASE_URL is None:
    print("   ❌ DATABASE_URL is not set")
    print("   → Please set DATABASE_URL in Render environment variables")
    sys.exit(1)
elif not DATABASE_URL.strip():
    print("   ❌ DATABASE_URL is set but empty")
    print("   → Please provide a valid PostgreSQL connection string")
    sys.exit(1)
elif not DATABASE_URL.startswith(('postgresql://', 'postgres://')):
    print(f"   ❌ DATABASE_URL doesn't start with postgresql:// or postgres://")
    print(f"   → Current value starts with: {DATABASE_URL[:30]}...")
    print("   → Expected format: postgresql://user:pass@host:5432/database")
    sys.exit(1)
else:
    # Extract host for display (hide credentials)
    try:
        host_part = DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else 'unknown'
        print(f"   ✅ DATABASE_URL is properly formatted")
        print(f"   → Host: {host_part}")
    except:
        print(f"   ⚠️  DATABASE_URL format is unusual but starting with correct prefix")
        print(f"   → Starts with: {DATABASE_URL[:30]}...")

# Test connection
print("\n2. Testing Database Connection:")
try:
    from sqlalchemy import create_engine, text
    
    connect_args = {
        "sslmode": "prefer",
        "connect_timeout": 30,
    }
    
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        echo=False
    )
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"   ✅ Connection successful!")
        print(f"   → PostgreSQL version: {version[:50]}...")
        
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    print(f"\n   Troubleshooting tips:")
    print(f"   1. Check if DATABASE_URL is correct in Render dashboard")
    print(f"   2. Ensure database is not paused (free tier)")
    print(f"   3. Check if SSL is properly configured")
    print(f"   4. Verify network connectivity")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ All checks passed! Environment is properly configured.")
print("=" * 60)