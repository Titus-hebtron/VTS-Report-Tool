from db_utils import get_connection

def list_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, name FROM users;")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users

# List and print users
users = list_users()
for user in users:
    print(user)