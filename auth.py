import streamlit as st
import psycopg2
import bcrypt
from db_utils import get_sqlalchemy_engine

def login():
    st.header("🔑 Login Page")

    contractor = st.text_input("Contractor (e.g. Wizpro, Paschal, RE Office)")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        engine = get_sqlalchemy_engine()
        conn = engine.raw_connection()
        cur = conn.cursor()

        cur.execute("SELECT id, password_hash, role FROM users WHERE contractor=%s AND username=%s",
                    (contractor, username))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
            st.session_state["logged_in"] = True
            st.session_state["role"] = user[2]
            st.session_state["contractor"] = contractor
            st.success(f"✅ Logged in as {username} ({user[2]})")
        else:
            st.error("❌ Invalid login credentials")
