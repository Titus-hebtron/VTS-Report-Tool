import psycopg2
import bcrypt

# --- DATABASE CONFIG ---
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Hebtron123"
# ------------------------

def reset_all_passwords(new_password="Pass@12345"):
    # Hash the new password
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    cur = conn.cursor()

    # Update all users
    cur.execute("UPDATE users SET password_hash = %s", (hashed,))
    conn.commit()

    cur.close()
    conn.close()
    print(f"All user passwords reset to: {new_password}")

if __name__ == "__main__":
    reset_all_passwords()
