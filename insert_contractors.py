import psycopg2
import bcrypt

# --- DATABASE CONFIG ---
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Hebtron123"
# ------------------------

def insert_contractors(create_logins: bool = False):
    """Insert contractors into the database.
    
    Args:
        create_logins: If True, also create contractor-role login accounts for each contractor.
                      Default username: contractor_<name>.lower(), password: Pass@12345
    """
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    cur = conn.cursor()

    contractors = ["Wizpro", "Paschal", "RE Office"]
    contractor_ids = {}
    
    # Insert contractors and get their IDs
    for name in contractors:
        cur.execute(
            "INSERT INTO contractors (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id",
            (name,)
        )
        result = cur.fetchone()
        if result:
            contractor_ids[name] = result[0]
        else:
            # If contractor already exists, fetch its ID
            cur.execute("SELECT id FROM contractors WHERE name=%s", (name,))
            contractor_ids[name] = cur.fetchone()[0]

    # Optionally create login accounts for each contractor
    if create_logins:
        for name, cid in contractor_ids.items():
            username = f"contractor_{name.lower().replace(' ', '_')}"
            password = "Pass@12345"
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            
            try:
                cur.execute(
                    """INSERT INTO users (username, password_hash, role, contractor_id)
                       VALUES (%s, %s, %s, %s) ON CONFLICT (username) DO NOTHING""",
                    (username, password_hash, "contractor", cid)
                )
                print(f"Created login for contractor '{name}': username='{username}', password='Pass@12345'")
            except Exception as e:
                print(f"Warning: Could not create login for '{name}': {e}")

    conn.commit()
    cur.close()
    conn.close()
    print("Contractors inserted.")

if __name__ == "__main__":
    import sys
    create_logins = "--create-logins" in sys.argv
    insert_contractors(create_logins=create_logins)