import psycopg2

# --- DATABASE CONFIG ---
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Hebtron123"
# ------------------------

def alter_role_constraint():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    cur = conn.cursor()

    # Drop the existing constraint
    cur.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS valid_role")

    # Add new constraint with re_admin
    cur.execute("""
        ALTER TABLE users ADD CONSTRAINT valid_role
        CHECK (role IN ('admin', 'control', 'patrol', 'contractor', 're_office', 're_admin'))
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Role constraint updated.")

if __name__ == "__main__":
    alter_role_constraint()