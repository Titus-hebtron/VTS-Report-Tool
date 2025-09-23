import psycopg2

# --- DATABASE CONFIG ---
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Hebtron123"
# ------------------------

def update_user_roles():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    cur = conn.cursor()

    # Update roles based on username
    role_updates = [
        ("re%", "re_admin"),
        ("admin", "admin"),
        ("control", "control"),
        ("patrol", "patrol"),
    ]

    for pattern, role in role_updates:
        if pattern in ["admin", "control", "patrol"]:
            cur.execute("UPDATE users SET role = %s WHERE username LIKE %s", (role, f"%{pattern}%"))
        else:
            cur.execute("UPDATE users SET role = %s WHERE username LIKE %s", (role, pattern))

    conn.commit()
    cur.close()
    conn.close()
    print("User roles updated.")

if __name__ == "__main__":
    update_user_roles()