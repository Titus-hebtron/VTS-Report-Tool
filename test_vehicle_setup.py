#!/usr/bin/env python3
"""Quick test to verify vehicle setup"""
import sys
sys.stdout.reconfigure(line_buffering=True)

print("Testing vehicle setup...", flush=True)

try:
    from db_utils import get_sqlalchemy_engine, USE_SQLITE
    from sqlalchemy import text
    
    print(f"Database type: {'SQLite' if USE_SQLITE else 'PostgreSQL'}", flush=True)
    
    engine = get_sqlalchemy_engine()
    print("Database connection successful!", flush=True)
    
    with engine.begin() as conn:
        # Check current vehicles
        result = conn.execute(text("SELECT COUNT(*) FROM vehicles"))
        count = result.fetchone()[0]
        print(f"Current vehicles in database: {count}", flush=True)
        
        # Show vehicles by contractor
        result = conn.execute(text("""
            SELECT contractor, COUNT(*) as count
            FROM vehicles
            GROUP BY contractor
            ORDER BY contractor
        """))
        
        print("\nVehicles by contractor:", flush=True)
        for contractor, cnt in result.fetchall():
            print(f"  {contractor}: {cnt}", flush=True)
    
    print("\n✅ Test completed successfully!", flush=True)
    
except Exception as e:
    print(f"❌ Error: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)