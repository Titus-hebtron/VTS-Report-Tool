import psycopg2

# --- DATABASE CONFIG ---
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Hebtron123"
# ------------------------

def update_user_contractors():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    cur = conn.cursor()

    # Get contractor ids
    cur.execute("SELECT id, name FROM contractors")
    contractors = {name: id for id, name in cur.fetchall()}

    # Update users based on username
    updates = [
        ("wiz%", contractors["Wizpro"]),
        ("paschal%", contractors["Paschal"]),
        ("re%", contractors["RE Office"]),
        ("admin", contractors["RE Office"]),  # assuming admin is RE
    ]

    for pattern, cid in updates:
        if pattern == "admin":
            cur.execute("UPDATE users SET contractor_id = %s WHERE username = %s", (cid, pattern))
        else:
            cur.execute("UPDATE users SET contractor_id = %s WHERE username LIKE %s", (cid, pattern))

    conn.commit()
    cur.close()
    conn.close()
    print("User contractors updated.")

if __name__ == "__main__":
    update_user_contractors()