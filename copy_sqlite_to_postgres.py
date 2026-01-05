"""
Copy non-binary tables from local SQLite `vts_database.db` to a target PostgreSQL database.
Skips image/blob tables (`incident_images`, `accident_reports_images`).
Usage: adjust TARGET_URL below and run: python copy_sqlite_to_postgres.py
"""
from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.exc import SQLAlchemyError
import os
import sys

# ---------- CONFIGURE TARGET URL (update if you want to pass via env) ----------
# Use the Postgres URL you provided
TARGET_URL = os.getenv("TARGET_PG_URL") or "postgresql://vts_database_oukh_user:w3itFbz09r4uERyXbTGC8tUZXIfIo7hL@dpg-d5cnsomuk2gs738bta40-a.singapore-postgres.render.com/vts_database_oukh"

# Ensure sslmode parameter present for psycopg2 if not specified
if "sslmode" not in TARGET_URL:
    if "?" in TARGET_URL:
        TARGET_URL = TARGET_URL + "&sslmode=require"
    else:
        TARGET_URL = TARGET_URL + "?sslmode=require"

SQLITE_URL = "sqlite:///vts_database.db"
SCHEMA_FILE = "schema.sql"
SKIP_TABLES = {"incident_images", "accident_reports_images"}

def _mask(url: str) -> str:
    if not url:
        return "(empty)"
    try:
        # hide password
        import urllib.parse as up
        p = up.urlparse(url)
        user = p.username or ""
        host = p.hostname or ""
        port = f":{p.port}" if p.port else ""
        path = p.path or ""
        if user:
            return f"{p.scheme}://{user}:****@{host}{port}{path}"
        return f"{p.scheme}://{host}{port}{path}"
    except Exception:
        return url

print("Target Postgres (masked):", _mask(TARGET_URL))
print("SQLite source:", SQLITE_URL)

# Create engines
try:
    sqlite_engine = create_engine(SQLITE_URL)
    pg_engine = create_engine(TARGET_URL, pool_pre_ping=True)
except Exception as e:
    print("Failed to create engines:", e)
    sys.exit(2)

# Test Postgres connectivity
try:
    with pg_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Connected to Postgres successfully")
except Exception as e:
    print("❌ Could not connect to Postgres:", e)
    sys.exit(3)

# Apply schema.sql to Postgres but skip contractor INSERTs (to avoid conflict without proper constraints)
if os.path.exists(SCHEMA_FILE):
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        raw_sql = f.read()
    # Split statements
    statements = [s.strip() for s in raw_sql.split(";") if s.strip()]
    filtered = []
    for s in statements:
        s_low = s.lower()
        if s_low.startswith("insert into contractors") or "on conflict do nothing" in s_low and "contractors" in s_low:
            print("Skipping contractor INSERT statement to avoid ON CONFLICT issues")
            continue
        filtered.append(s)
    if filtered:
        try:
            with pg_engine.begin() as conn:
                for stmt in filtered:
                    conn.execute(text(stmt))
            print("✅ Executed schema statements on Postgres (filtered)")
        except SQLAlchemyError as e:
            print("Error applying schema to Postgres:", e)
            sys.exit(4)
else:
    print(f"Schema file {SCHEMA_FILE} not found; aborting")
    sys.exit(5)

# Reflect tables from SQLite
s_meta = MetaData()
try:
    s_meta.reflect(bind=sqlite_engine)
except Exception as e:
    print("Failed to reflect SQLite metadata:", e)
    sys.exit(6)

p_meta = MetaData()
try:
    p_meta.reflect(bind=pg_engine)
except Exception as e:
    print("Failed to reflect Postgres metadata:", e)
    sys.exit(7)

from sqlalchemy import insert

# Copy tables one by one
for s_table in s_meta.sorted_tables:
    tname = s_table.name
    if tname in SKIP_TABLES:
        print(f"Skipping binary table: {tname}")
        continue
    if tname not in p_meta.tables:
        print(f"Table {tname} does not exist in Postgres after schema application; skipping")
        continue

    p_table = Table(tname, p_meta, autoload_with=pg_engine)
    print(f"Copying table: {tname}")

    # Read rows from sqlite
    try:
        with sqlite_engine.connect() as sconn:
            rows = sconn.execute(select(s_table)).fetchall()
    except Exception as e:
        print(f"  ❌ Failed to read from sqlite table {tname}:", e)
        continue

    if not rows:
        print(f"  (no rows to copy)")
        continue

    # Insert into Postgres in a transaction
    inserted = 0
    try:
        with pg_engine.begin() as pconn:
            for r in rows:
                # Convert Row to mapping/dict
                try:
                    data = dict(r._mapping)
                except Exception:
                    data = dict(r)
                # Normalize memoryview/bytes
                for k, v in list(data.items()):
                    if isinstance(v, memoryview):
                        data[k] = bytes(v)
                # Execute insert (do nothing on conflict by primary key)
                ins = insert(p_table).values(**data)
                try:
                    pconn.execute(ins)
                    inserted += 1
                except Exception as ie:
                    # On duplicate primary key or other errors, print and continue
                    print(f"    warning: failed to insert row into {tname}: {ie}")
                    continue
        print(f"  ✅ Inserted ~{inserted} rows into {tname}")
    except Exception as e:
        print(f"  ❌ Transaction failure while inserting into {tname}:", e)
        continue

print("Migration complete. Note: image tables were skipped.")
print("If you need images migrated, we can add a binary-safe path using psycopg2 and bytea inserts.")
