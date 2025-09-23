import psycopg2

# --- DATABASE CONFIG ---
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Hebtron123"
# ------------------------

def insert_contractors():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    cur = conn.cursor()

    contractors = ["Wizpro", "Paschal", "RE Office"]
    for name in contractors:
        cur.execute("INSERT INTO contractors (name) VALUES (%s) ON CONFLICT DO NOTHING", (name,))

    conn.commit()
    cur.close()
    conn.close()
    print("Contractors inserted.")

if __name__ == "__main__":
    insert_contractors()