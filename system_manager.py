#!/usr/bin/env python3
"""
System Manager Page for VTS Report Tool
Allows Resident Engineer (re_admin) to manage contractors, users, data, and backups
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import bcrypt
from db_utils import get_sqlalchemy_engine, get_connection, USE_SQLITE
from sqlalchemy import text
import traceback

def system_manager_page():
    """System manager page for resident engineer"""
    st.header("⚙️ System Manager")

    # Check if user has permission (only re_admin)
    user_role = st.session_state.get("role", "")
    if user_role != "re_admin":
        st.error("❌ Access denied. Only Resident Engineer can access system management.")
        return

    st.info("🔐 **Resident Engineer Access Only** - Manage users, contractors, data, and backups")

    # Create tabs for different management operations
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["👥 User Management", "🏢 Contractor Management", "🚗 Patrol Car Management", "🗑️ Data Management", "💾 Backup & Restore"])

    with tab1:
        user_management_section()

    with tab2:
        contractor_management_section()

    with tab3:
        patrol_car_management_section()

    with tab4:
        data_management_section()

    with tab5:
        backup_restore_section()


def user_management_section():
    """User management section"""
    st.subheader("👥 User Management")

    # Get all users
    try:
        engine = get_sqlalchemy_engine()
        query = """
            SELECT u.id, u.username, u.role, c.name as contractor_name, u.contractor_id, u.created_at
            FROM users u
            LEFT JOIN contractors c ON u.contractor_id = c.id
            ORDER BY u.created_at DESC
        """
        users_df = pd.read_sql_query(text(query), engine)

        # Display user statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Users", len(users_df))
        with col2:
            admin_count = len(users_df[users_df['role'].isin(['re_admin', 'admin'])])
            st.metric("Admins", admin_count)
        with col3:
            patrol_count = len(users_df[users_df['role'] == 'patrol'])
            st.metric("Patrol Officers", patrol_count)
        with col4:
            contractor_count = len(users_df[users_df['role'] == 'contractor'])
            st.metric("Contractors", contractor_count)

        st.markdown("---")

        # Add new user section
        with st.expander("➕ Add New User", expanded=False):
            add_user_form()

        st.markdown("---")

        # Search and filter
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("🔍 Search by username", key="user_search")
        with col2:
            role_filter = st.selectbox("Filter by role", ["All"] + list(users_df['role'].unique()), key="role_filter")

        # Apply filters
        filtered_df = users_df.copy()
        if search_term:
            filtered_df = filtered_df[filtered_df['username'].str.contains(search_term, case=False, na=False)]
        if role_filter != "All":
            filtered_df = filtered_df[filtered_df['role'] == role_filter]

        # Display users table
        st.subheader(f"📋 Users ({len(filtered_df)})")
        
        if len(filtered_df) > 0:
            # Display as interactive table
            for idx, user in filtered_df.iterrows():
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
                    
                    with col1:
                        st.write(f"**{user['username']}**")
                    with col2:
                        role_badge = {
                            're_admin': '🔴 RE Admin',
                            'admin': '🟠 Admin',
                            'control': '🟡 Control',
                            'patrol': '🟢 Patrol',
                            'contractor': '🔵 Contractor'
                        }
                        st.write(role_badge.get(user['role'], user['role']))
                    with col3:
                        st.write(user['contractor_name'] if user['contractor_name'] else 'N/A')
                    with col4:
                        created_date = pd.to_datetime(user['created_at']).strftime('%Y-%m-%d') if user['created_at'] else 'N/A'
                        st.write(created_date)
                    with col5:
                        col_edit, col_delete = st.columns(2)
                        with col_edit:
                            if st.button("✏️", key=f"edit_{user['id']}", help="Edit user"):
                                st.session_state[f"editing_user_{user['id']}"] = True
                        with col_delete:
                            # Prevent deleting self and last re_admin
                            current_username = st.session_state.get("username", "")
                            is_self = user['username'] == current_username
                            is_last_admin = user['role'] == 're_admin' and len(users_df[users_df['role'] == 're_admin']) == 1
                            
                            if not is_self and not is_last_admin:
                                if st.button("🗑️", key=f"delete_{user['id']}", help="Delete user"):
                                    st.session_state[f"confirm_delete_{user['id']}"] = True
                            else:
                                st.write("🔒")

                    # Edit form
                    if st.session_state.get(f"editing_user_{user['id']}", False):
                        with st.form(key=f"edit_form_{user['id']}"):
                            st.write(f"**Editing: {user['username']}**")
                            
                            # Get contractors for dropdown
                            contractors_df = pd.read_sql_query(text("SELECT id, name FROM contractors ORDER BY name"), engine)
                            contractor_options = {row['name']: row['id'] for _, row in contractors_df.iterrows()}
                            
                            new_role = st.selectbox("Role", ['re_admin', 'admin', 'control', 'patrol', 'contractor'], 
                                                   index=['re_admin', 'admin', 'control', 'patrol', 'contractor'].index(user['role']))
                            new_contractor = st.selectbox("Contractor", list(contractor_options.keys()),
                                                         index=list(contractor_options.values()).index(user['contractor_id']) if user['contractor_id'] in contractor_options.values() else 0)
                            new_password = st.text_input("New Password (leave blank to keep current)", type="password")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Save Changes"):
                                    update_user(user['id'], new_role, contractor_options[new_contractor], new_password)
                                    st.session_state[f"editing_user_{user['id']}"] = False
                                    st.rerun()
                            with col2:
                                if st.form_submit_button("❌ Cancel"):
                                    st.session_state[f"editing_user_{user['id']}"] = False
                                    st.rerun()

                    # Delete confirmation
                    if st.session_state.get(f"confirm_delete_{user['id']}", False):
                        st.warning(f"⚠️ Are you sure you want to delete user **{user['username']}**?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Yes, Delete", key=f"confirm_yes_{user['id']}"):
                                delete_user(user['id'], user['username'])
                                st.session_state[f"confirm_delete_{user['id']}"] = False
                                st.rerun()
                        with col2:
                            if st.button("❌ Cancel", key=f"confirm_no_{user['id']}"):
                                st.session_state[f"confirm_delete_{user['id']}"] = False
                                st.rerun()

                    st.markdown("---")
        else:
            st.info("No users found matching the filters.")

    except Exception as e:
        st.error(f"Error loading users: {e}")
        with st.expander("View Error Details"):
            st.code(traceback.format_exc())


def add_user_form():
    """Form to add a new user"""
    try:
        engine = get_sqlalchemy_engine()
        contractors_df = pd.read_sql_query(text("SELECT id, name FROM contractors ORDER BY name"), engine)
        contractor_options = {row['name']: row['id'] for _, row in contractors_df.iterrows()}

        with st.form("add_user_form"):
            st.write("**Create New User**")
            
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username*", key="new_username")
                new_password = st.text_input("Password*", type="password", key="new_password")
            with col2:
                new_role = st.selectbox("Role*", ['contractor', 'patrol', 'control', 'admin', 're_admin'], key="new_role")
                new_contractor = st.selectbox("Contractor*", list(contractor_options.keys()), key="new_contractor")

            if st.form_submit_button("➕ Add User"):
                if not new_username or not new_password:
                    st.error("Username and password are required!")
                else:
                    add_new_user(new_username, new_password, new_role, contractor_options[new_contractor])
                    st.success(f"✅ User '{new_username}' added successfully!")
                    st.rerun()

    except Exception as e:
        st.error(f"Error in add user form: {e}")


def add_new_user(username, password, role, contractor_id):
    """Add a new user to the database"""
    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        engine = get_sqlalchemy_engine()
        
        with engine.begin() as conn:
            if USE_SQLITE:
                conn.execute(text("""
                    INSERT INTO users (username, password_hash, role, contractor_id)
                    VALUES (:username, :password_hash, :role, :contractor_id)
                """), {
                    "username": username,
                    "password_hash": hashed,
                    "role": role,
                    "contractor_id": contractor_id
                })
            else:
                conn.execute(text("""
                    INSERT INTO users (username, password_hash, role, contractor_id)
                    VALUES (:username, :password_hash, :role, :contractor_id)
                    ON CONFLICT (username) DO NOTHING
                """), {
                    "username": username,
                    "password_hash": hashed,
                    "role": role,
                    "contractor_id": contractor_id
                })
        
        st.success(f"✅ User '{username}' created successfully!")
        
    except Exception as e:
        st.error(f"Error adding user: {e}")
        raise


def update_user(user_id, role, contractor_id, new_password=None):
    """Update user details"""
    try:
        engine = get_sqlalchemy_engine()
        
        with engine.begin() as conn:
            if new_password:
                hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                conn.execute(text("""
                    UPDATE users 
                    SET role = :role, contractor_id = :contractor_id, password_hash = :password_hash
                    WHERE id = :user_id
                """), {
                    "role": role,
                    "contractor_id": contractor_id,
                    "password_hash": hashed,
                    "user_id": user_id
                })
            else:
                conn.execute(text("""
                    UPDATE users 
                    SET role = :role, contractor_id = :contractor_id
                    WHERE id = :user_id
                """), {
                    "role": role,
                    "contractor_id": contractor_id,
                    "user_id": user_id
                })
        
        st.success("✅ User updated successfully!")
        
    except Exception as e:
        st.error(f"Error updating user: {e}")
        raise


def delete_user(user_id, username):
    """Delete a user from the database"""
    try:
        engine = get_sqlalchemy_engine()
        
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
        
        st.success(f"✅ User '{username}' deleted successfully!")
        
    except Exception as e:
        st.error(f"Error deleting user: {e}")
        raise


def contractor_management_section():
    """Contractor management section"""
    st.subheader("🏢 Contractor Management")

    try:
        engine = get_sqlalchemy_engine()
        
        # Get contractors with statistics
        query = """
            SELECT 
                c.id,
                c.name,
                c.created_at,
                COUNT(DISTINCT u.id) as user_count,
                COUNT(DISTINCT v.id) as vehicle_count,
                COUNT(DISTINCT ir.id) as report_count
            FROM contractors c
            LEFT JOIN users u ON c.id = u.contractor_id
            LEFT JOIN vehicles v ON c.name = v.contractor
            LEFT JOIN incident_reports ir ON c.id = ir.contractor_id
            GROUP BY c.id, c.name, c.created_at
            ORDER BY c.name
        """
        contractors_df = pd.read_sql_query(text(query), engine)

        # Display statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Contractors", len(contractors_df))
        with col2:
            st.metric("Total Users", contractors_df['user_count'].sum())
        with col3:
            st.metric("Total Reports", contractors_df['report_count'].sum())

        st.markdown("---")

        # Add new contractor section
        with st.expander("➕ Add New Contractor", expanded=False):
            with st.form("add_contractor_form"):
                new_contractor_name = st.text_input("Contractor Name*")
                
                if st.form_submit_button("➕ Add Contractor"):
                    if not new_contractor_name:
                        st.error("Contractor name is required!")
                    else:
                        add_new_contractor(new_contractor_name)
                        st.rerun()

        st.markdown("---")

        # Display contractors
        st.subheader(f"📋 Contractors ({len(contractors_df)})")
        
        for idx, contractor in contractors_df.iterrows():
            with st.container():
                col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 2, 2, 1])
                
                with col1:
                    st.write(f"**{contractor['name']}**")
                with col2:
                    st.write(f"👥 {contractor['user_count']} users")
                with col3:
                    st.write(f"🚗 {contractor['vehicle_count']} vehicles")
                with col4:
                    st.write(f"📄 {contractor['report_count']} reports")
                with col5:
                    created_date = pd.to_datetime(contractor['created_at']).strftime('%Y-%m-%d') if contractor['created_at'] else 'N/A'
                    st.write(created_date)
                with col6:
                    # Only allow deletion if no users/vehicles/reports
                    can_delete = contractor['user_count'] == 0 and contractor['vehicle_count'] == 0 and contractor['report_count'] == 0
                    
                    if can_delete:
                        if st.button("🗑️", key=f"delete_contractor_{contractor['id']}", help="Delete contractor"):
                            st.session_state[f"confirm_delete_contractor_{contractor['id']}"] = True
                    else:
                        st.write("🔒")

                # Delete confirmation
                if st.session_state.get(f"confirm_delete_contractor_{contractor['id']}", False):
                    st.warning(f"⚠️ Are you sure you want to delete contractor **{contractor['name']}**?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Yes, Delete", key=f"confirm_yes_contractor_{contractor['id']}"):
                            delete_contractor(contractor['id'], contractor['name'])
                            st.session_state[f"confirm_delete_contractor_{contractor['id']}"] = False
                            st.rerun()
                    with col2:
                        if st.button("❌ Cancel", key=f"confirm_no_contractor_{contractor['id']}"):
                            st.session_state[f"confirm_delete_contractor_{contractor['id']}"] = False
                            st.rerun()

                st.markdown("---")

    except Exception as e:
        st.error(f"Error loading contractors: {e}")
        with st.expander("View Error Details"):
            st.code(traceback.format_exc())


def add_new_contractor(name):
    """Add a new contractor to the database"""
    try:
        engine = get_sqlalchemy_engine()
        
        with engine.begin() as conn:
            if USE_SQLITE:
                conn.execute(text("INSERT INTO contractors (name) VALUES (:name)"), {"name": name})
            else:
                conn.execute(text("INSERT INTO contractors (name) VALUES (:name) ON CONFLICT DO NOTHING"), {"name": name})
        
        st.success(f"✅ Contractor '{name}' added successfully!")
        
    except Exception as e:
        st.error(f"Error adding contractor: {e}")
        raise


def delete_contractor(contractor_id, name):
    """Delete a contractor from the database"""
    try:
        engine = get_sqlalchemy_engine()

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM contractors WHERE id = :contractor_id"), {"contractor_id": contractor_id})

        st.success(f"✅ Contractor '{name}' deleted successfully!")

    except Exception as e:
        st.error(f"Error deleting contractor: {e}")
        raise


def patrol_car_management_section():
    """Patrol car management section"""
    st.subheader("🚗 Patrol Car Management")

    try:
        engine = get_sqlalchemy_engine()

        # Get vehicles with contractor info
        query = """
            SELECT v.id, v.plate_number, v.contractor, v.created_at,
                   COUNT(DISTINCT ir.id) as incident_count
            FROM vehicles v
            LEFT JOIN incident_reports ir ON v.plate_number = ir.patrol_car
            GROUP BY v.id, v.plate_number, v.contractor, v.created_at
            ORDER BY v.contractor, v.plate_number
        """
        vehicles_df = pd.read_sql_query(text(query), engine)

        # Display statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Patrol Cars", len(vehicles_df))
        with col2:
            st.metric("Active Contractors", vehicles_df['contractor'].nunique())
        with col3:
            st.metric("Total Incidents", vehicles_df['incident_count'].sum())

        st.markdown("---")

        # Add new patrol car section
        with st.expander("➕ Add New Patrol Car", expanded=False):
            with st.form("add_vehicle_form"):
                new_plate_number = st.text_input("Plate Number*", key="new_plate")
                contractors_df = pd.read_sql_query(text("SELECT name FROM contractors ORDER BY name"), engine)
                contractor_options = list(contractors_df['name'])
                new_contractor = st.selectbox("Contractor*", contractor_options, key="new_vehicle_contractor")

                if st.form_submit_button("➕ Add Patrol Car"):
                    if not new_plate_number:
                        st.error("Plate number is required!")
                    else:
                        add_new_vehicle(new_plate_number, new_contractor)
                        st.rerun()

        st.markdown("---")

        # Search and filter
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("🔍 Search by plate number", key="vehicle_search")
        with col2:
            contractor_filter = st.selectbox("Filter by contractor", ["All Contractors"] + list(vehicles_df['contractor'].unique()), key="vehicle_contractor_filter")

        # Apply filters
        filtered_df = vehicles_df.copy()
        if search_term:
            filtered_df = filtered_df[filtered_df['plate_number'].str.contains(search_term, case=False, na=False)]
        if contractor_filter != "All Contractors":
            filtered_df = filtered_df[filtered_df['contractor'] == contractor_filter]

        # Display vehicles
        st.subheader(f"🚗 Patrol Cars ({len(filtered_df)})")

        if len(filtered_df) > 0:
            for idx, vehicle in filtered_df.iterrows():
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])

                    with col1:
                        st.write(f"**{vehicle['plate_number']}**")
                    with col2:
                        st.write(f"🏢 {vehicle['contractor']}")
                    with col3:
                        st.write(f"📄 {vehicle['incident_count']} incidents")
                    with col4:
                        created_date = pd.to_datetime(vehicle['created_at']).strftime('%Y-%m-%d') if vehicle['created_at'] else 'N/A'
                        st.write(created_date)
                    with col5:
                        if st.button("🗑️", key=f"delete_vehicle_{vehicle['id']}", help="Delete patrol car"):
                            st.session_state[f"confirm_delete_vehicle_{vehicle['id']}"] = True

                # Delete confirmation
                if st.session_state.get(f"confirm_delete_vehicle_{vehicle['id']}", False):
                    st.warning(f"⚠️ Are you sure you want to delete patrol car **{vehicle['plate_number']}**?")
                    st.info("Note: This will not delete associated incident reports, but they will no longer be linked to this vehicle.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Yes, Delete", key=f"confirm_yes_vehicle_{vehicle['id']}"):
                            delete_vehicle(vehicle['id'], vehicle['plate_number'])
                            st.session_state[f"confirm_delete_vehicle_{vehicle['id']}"] = False
                            st.rerun()
                    with col2:
                        if st.button("❌ Cancel", key=f"confirm_no_vehicle_{vehicle['id']}"):
                            st.session_state[f"confirm_delete_vehicle_{vehicle['id']}"] = False
                            st.rerun()

                st.markdown("---")
        else:
            st.info("No patrol cars found matching the filters.")

    except Exception as e:
        st.error(f"Error loading patrol cars: {e}")
        with st.expander("View Error Details"):
            st.code(traceback.format_exc())


def add_new_vehicle(plate_number, contractor):
    """Add a new vehicle to the database"""
    try:
        engine = get_sqlalchemy_engine()

        with engine.begin() as conn:
            if USE_SQLITE:
                conn.execute(text("INSERT INTO vehicles (plate_number, contractor) VALUES (:plate_number, :contractor)"),
                           {"plate_number": plate_number, "contractor": contractor})
            else:
                conn.execute(text("INSERT INTO vehicles (plate_number, contractor) VALUES (:plate_number, :contractor) ON CONFLICT DO NOTHING"),
                           {"plate_number": plate_number, "contractor": contractor})

        st.success(f"✅ Patrol car '{plate_number}' added successfully!")

    except Exception as e:
        st.error(f"Error adding patrol car: {e}")
        raise


def delete_vehicle(vehicle_id, plate_number):
    """Delete a vehicle from the database"""
    try:
        engine = get_sqlalchemy_engine()

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM vehicles WHERE id = :vehicle_id"), {"vehicle_id": vehicle_id})

        st.success(f"✅ Patrol car '{plate_number}' deleted successfully!")

    except Exception as e:
        st.error(f"Error deleting patrol car: {e}")
        raise


def data_management_section():
    """Data management section for deleting records"""
    st.subheader("🗑️ Data Management")

    st.warning("⚠️ **Warning:** Deleting data is permanent and cannot be undone. Please ensure you have recent backups before proceeding.")

    try:
        engine = get_sqlalchemy_engine()

        # Get data statistics
        stats_query = """
            SELECT
                (SELECT COUNT(*) FROM incident_reports) as incident_count,
                (SELECT COUNT(*) FROM incident_images) as image_count,
                (SELECT COUNT(*) FROM idle_reports) as idle_count,
                (SELECT COUNT(*) FROM patrol_logs) as patrol_count,
                (SELECT COUNT(*) FROM breaks) as break_count,
                (SELECT COUNT(*) FROM pickups) as pickup_count,
                (SELECT COUNT(*) FROM vehicles) as vehicle_count
        """
        stats = pd.read_sql_query(text(stats_query), engine).iloc[0]

        # Database usage and space information
        st.subheader("💾 Database Usage & Storage")

        # Get database file size (SQLite only)
        db_size_mb = 0
        if USE_SQLITE:
            import os
            db_path = 'vts_database.db'
            if os.path.exists(db_path):
                db_size_mb = os.path.getsize(db_path) / (1024 * 1024)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Database Size", f"{db_size_mb:.2f} MB")
        with col2:
            # Estimate remaining space (rough estimate)
            estimated_remaining = max(0, 100 - db_size_mb)  # Assuming 100MB limit for demo
            st.metric("Est. Remaining Space", f"{estimated_remaining:.1f} MB")
        with col3:
            usage_percent = min(100, (db_size_mb / 100) * 100) if db_size_mb > 0 else 0
            st.metric("Usage", f"{usage_percent:.1f}%")

        if db_size_mb > 80:
            st.error("⚠️ Database size is getting large. Consider archiving old data or creating backups.")
        elif db_size_mb > 50:
            st.warning("⚠️ Database size is moderate. Monitor growth and plan for archiving.")

        st.markdown("---")

        # Display statistics
        st.subheader("📊 Database Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Incident Reports", stats['incident_count'])
            st.metric("Incident Images", stats['image_count'])
        with col2:
            st.metric("Idle Reports", stats['idle_count'])
            st.metric("Patrol Logs", stats['patrol_count'])
        with col3:
            st.metric("Breaks", stats['break_count'])
            st.metric("Pickups", stats['pickup_count'])
        with col4:
            st.metric("Vehicles", stats['vehicle_count'])

        st.markdown("---")

        # Delete operations
        st.subheader("🗑️ Delete Operations")

        # Secret key for deletion confirmation
        st.markdown("🔐 **Security:** All deletion operations require entering the secret key 'Hebtron' for confirmation.")

        # Get contractors for filtering
        contractors_df = pd.read_sql_query(text("SELECT id, name FROM contractors ORDER BY name"), engine)
        contractor_options = ["All Contractors"] + list(contractors_df['name'])

        # Incident Reports deletion
        with st.expander("🚨 Delete Incident Reports"):
            col1, col2 = st.columns(2)
            with col1:
                delete_contractor = st.selectbox("Filter by Contractor", contractor_options, key="delete_incident_contractor")
            with col2:
                delete_date_range = st.date_input("Date Range", value=[], key="delete_incident_date")

            # Secret key input for deletion
            secret_key = st.text_input("Enter Secret Key for Deletion", type="password", key="incident_delete_key")

            if st.button("🗑️ Delete Incident Reports", type="secondary"):
                if secret_key != "Hebtron":
                    st.error("❌ Incorrect secret key. Deletion not authorized.")
                else:
                    st.session_state['confirm_delete_incidents'] = True

            if st.session_state.get('confirm_delete_incidents', False):
                # Build query to show what will be deleted
                preview_query = "SELECT COUNT(*) as count FROM incident_reports WHERE 1=1"
                params = {}

                if delete_contractor != "All Contractors":
                    contractor_id = contractors_df[contractors_df['name'] == delete_contractor]['id'].iloc[0]
                    preview_query += " AND contractor_id = :contractor_id"
                    params['contractor_id'] = contractor_id

                if len(delete_date_range) == 2:
                    preview_query += " AND incident_date BETWEEN :start_date AND :end_date"
                    params['start_date'] = delete_date_range[0]
                    params['end_date'] = delete_date_range[1]

                count = pd.read_sql_query(text(preview_query), engine, params=params).iloc[0]['count']

                st.warning(f"⚠️ This will delete **{count}** incident reports and their associated images. Are you sure?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, Delete", key="confirm_delete_incidents_yes"):
                        delete_incident_reports(delete_contractor, delete_date_range, contractors_df)
                        st.session_state['confirm_delete_incidents'] = False
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", key="confirm_delete_incidents_no"):
                        st.session_state['confirm_delete_incidents'] = False
                        st.rerun()

        # Idle Reports deletion
        with st.expander("⏱️ Delete Idle Reports"):
            col1, col2 = st.columns(2)
            with col1:
                delete_idle_contractor = st.selectbox("Filter by Contractor", contractor_options, key="delete_idle_contractor")
            with col2:
                delete_idle_date_range = st.date_input("Date Range", value=[], key="delete_idle_date")

            # Secret key input for idle reports deletion
            idle_secret_key = st.text_input("Enter Secret Key for Deletion", type="password", key="idle_delete_key")

            if st.button("🗑️ Delete Idle Reports", type="secondary"):
                if idle_secret_key != "Hebtron":
                    st.error("❌ Incorrect secret key. Deletion not authorized.")
                else:
                    st.session_state['confirm_delete_idle'] = True

            if st.session_state.get('confirm_delete_idle', False):
                preview_query = "SELECT COUNT(*) as count FROM idle_reports WHERE 1=1"
                params = {}

                if delete_idle_contractor != "All Contractors":
                    contractor_id = contractors_df[contractors_df['name'] == delete_idle_contractor]['id'].iloc[0]
                    preview_query += " AND contractor_id = :contractor_id"
                    params['contractor_id'] = contractor_id

                if len(delete_idle_date_range) == 2:
                    preview_query += " AND DATE(uploaded_at) BETWEEN :start_date AND :end_date"
                    params['start_date'] = delete_idle_date_range[0]
                    params['end_date'] = delete_idle_date_range[1]

                count = pd.read_sql_query(text(preview_query), engine, params=params).iloc[0]['count']

                st.warning(f"⚠️ This will delete **{count}** idle reports. Are you sure?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, Delete", key="confirm_delete_idle_yes"):
                        delete_idle_reports(delete_idle_contractor, delete_idle_date_range, contractors_df)
                        st.session_state['confirm_delete_idle'] = False
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", key="confirm_delete_idle_no"):
                        st.session_state['confirm_delete_idle'] = False
                        st.rerun()

        # Patrol Logs deletion
        with st.expander("📍 Delete Patrol Logs"):
            delete_patrol_date_range = st.date_input("Date Range", value=[], key="delete_patrol_date")

            # Secret key input for patrol logs deletion
            patrol_secret_key = st.text_input("Enter Secret Key for Deletion", type="password", key="patrol_delete_key")

            if st.button("🗑️ Delete Patrol Logs", type="secondary"):
                if patrol_secret_key != "Hebtron":
                    st.error("❌ Incorrect secret key. Deletion not authorized.")
                else:
                    st.session_state['confirm_delete_patrol'] = True

            if st.session_state.get('confirm_delete_patrol', False):
                preview_query = "SELECT COUNT(*) as count FROM patrol_logs WHERE 1=1"
                params = {}

                if len(delete_patrol_date_range) == 2:
                    preview_query += " AND DATE(timestamp) BETWEEN :start_date AND :end_date"
                    params['start_date'] = delete_patrol_date_range[0]
                    params['end_date'] = delete_patrol_date_range[1]

                count = pd.read_sql_query(text(preview_query), engine, params=params).iloc[0]['count']

                st.warning(f"⚠️ This will delete **{count}** patrol logs. Are you sure?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, Delete", key="confirm_delete_patrol_yes"):
                        delete_patrol_logs(delete_patrol_date_range)
                        st.session_state['confirm_delete_patrol'] = False
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", key="confirm_delete_patrol_no"):
                        st.session_state['confirm_delete_patrol'] = False
                        st.rerun()

        # Breaks & Pickups deletion
        with st.expander("🚦 Delete Breaks & Pickups"):
            col1, col2 = st.columns(2)
            with col1:
                delete_breaks_contractor = st.selectbox("Filter by Contractor", contractor_options, key="delete_breaks_contractor")
            with col2:
                delete_breaks_date_range = st.date_input("Date Range", value=[], key="delete_breaks_date")

            # Secret key inputs for breaks and pickups deletion
            breaks_secret_key = st.text_input("Enter Secret Key for Deletion", type="password", key="breaks_delete_key")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Delete Breaks", type="secondary"):
                    if breaks_secret_key != "Hebtron":
                        st.error("❌ Incorrect secret key. Deletion not authorized.")
                    else:
                        st.session_state['confirm_delete_breaks'] = True
            with col2:
                if st.button("🗑️ Delete Pickups", type="secondary"):
                    if breaks_secret_key != "Hebtron":
                        st.error("❌ Incorrect secret key. Deletion not authorized.")
                    else:
                        st.session_state['confirm_delete_pickups'] = True

            if st.session_state.get('confirm_delete_breaks', False):
                preview_query = "SELECT COUNT(*) as count FROM breaks WHERE 1=1"
                params = {}

                if delete_breaks_contractor != "All Contractors":
                    contractor_id = contractors_df[contractors_df['name'] == delete_breaks_contractor]['id'].iloc[0]
                    preview_query += " AND contractor_id = :contractor_id"
                    params['contractor_id'] = contractor_id

                if len(delete_breaks_date_range) == 2:
                    preview_query += " AND break_date BETWEEN :start_date AND :end_date"
                    params['start_date'] = delete_breaks_date_range[0]
                    params['end_date'] = delete_breaks_date_range[1]

                count = pd.read_sql_query(text(preview_query), engine, params=params).iloc[0]['count']

                st.warning(f"⚠️ This will delete **{count}** break records. Are you sure?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, Delete Breaks", key="confirm_delete_breaks_yes"):
                        delete_breaks(delete_breaks_contractor, delete_breaks_date_range, contractors_df)
                        st.session_state['confirm_delete_breaks'] = False
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", key="confirm_delete_breaks_no"):
                        st.session_state['confirm_delete_breaks'] = False
                        st.rerun()

            if st.session_state.get('confirm_delete_pickups', False):
                preview_query = "SELECT COUNT(*) as count FROM pickups WHERE 1=1"
                params = {}

                if delete_breaks_contractor != "All Contractors":
                    contractor_id = contractors_df[contractors_df['name'] == delete_breaks_contractor]['id'].iloc[0]
                    preview_query += " AND contractor_id = :contractor_id"
                    params['contractor_id'] = contractor_id

                if len(delete_breaks_date_range) == 2:
                    preview_query += " AND pickup_date BETWEEN :start_date AND :end_date"
                    params['start_date'] = delete_breaks_date_range[0]
                    params['end_date'] = delete_breaks_date_range[1]

                count = pd.read_sql_query(text(preview_query), engine, params=params).iloc[0]['count']

                st.warning(f"⚠️ This will delete **{count}** pickup records. Are you sure?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, Delete Pickups", key="confirm_delete_pickups_yes"):
                        delete_pickups(delete_breaks_contractor, delete_breaks_date_range, contractors_df)
                        st.session_state['confirm_delete_pickups'] = False
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", key="confirm_delete_pickups_no"):
                        st.session_state['confirm_delete_pickups'] = False
                        st.rerun()

    except Exception as e:
        st.error(f"Error in data management: {e}")
        with st.expander("View Error Details"):
            st.code(traceback.format_exc())


def delete_incident_reports(contractor_filter, date_range, contractors_df):
    """Delete incident reports based on filters"""
    try:
        engine = get_sqlalchemy_engine()
        
        with engine.begin() as conn:
            # Build delete query
            delete_query = "DELETE FROM incident_reports WHERE 1=1"
            params = {}
            
            if contractor_filter != "All Contractors":
                contractor_id = contractors_df[contractors_df['name'] == contractor_filter]['id'].iloc[0]
                delete_query += " AND contractor_id = :contractor_id"
                params['contractor_id'] = contractor_id
            
            if len(date_range) == 2:
                delete_query += " AND incident_date BETWEEN :start_date AND :end_date"
                params['start_date'] = date_range[0]
                params['end_date'] = date_range[1]

            # Delete associated images first
            image_delete_query = delete_query.replace("DELETE FROM incident_reports", 
                                                     "DELETE FROM incident_images WHERE incident_id IN (SELECT id FROM incident_reports")
            image_delete_query += ")"
            
            conn.execute(text(image_delete_query), params)
            result = conn.execute(text(delete_query), params)
            
        st.success(f"✅ Deleted {result.rowcount} incident reports and their images!")
        
    except Exception as e:
        st.error(f"Error deleting incident reports: {e}")
        raise


def delete_idle_reports(contractor_filter, date_range, contractors_df):
    """Delete idle reports based on filters"""
    try:
        engine = get_sqlalchemy_engine()
        
        with engine.begin() as conn:
            delete_query = "DELETE FROM idle_reports WHERE 1=1"
            params = {}
            
            if contractor_filter != "All Contractors":
                contractor_id = contractors_df[contractors_df['name'] == contractor_filter]['id'].iloc[0]
                delete_query += " AND contractor_id = :contractor_id"
                params['contractor_id'] = contractor_id
            
            if len(date_range) == 2:
                delete_query += " AND DATE(uploaded_at) BETWEEN :start_date AND :end_date"
                params['start_date'] = date_range[0]
                params['end_date'] = date_range[1]

            result = conn.execute(text(delete_query), params)
            
        st.success(f"✅ Deleted {result.rowcount} idle reports!")
        
    except Exception as e:
        st.error(f"Error deleting idle reports: {e}")
        raise


def delete_patrol_logs(date_range):
    """Delete patrol logs based on date range"""
    try:
        engine = get_sqlalchemy_engine()
        
        with engine.begin() as conn:
            delete_query = "DELETE FROM patrol_logs WHERE 1=1"
            params = {}
            
            if len(date_range) == 2:
                delete_query += " AND DATE(timestamp) BETWEEN :start_date AND :end_date"
                params['start_date'] = date_range[0]
                params['end_date'] = date_range[1]

            result = conn.execute(text(delete_query), params)
            
        st.success(f"✅ Deleted {result.rowcount} patrol logs!")
        
    except Exception as e:
        st.error(f"Error deleting patrol logs: {e}")
        raise


def delete_breaks(contractor_filter, date_range, contractors_df):
    """Delete break records based on filters"""
    try:
        engine = get_sqlalchemy_engine()
        
        with engine.begin() as conn:
            delete_query = "DELETE FROM breaks WHERE 1=1"
            params = {}
            
            if contractor_filter != "All Contractors":
                contractor_id = contractors_df[contractors_df['name'] == contractor_filter]['id'].iloc[0]
                delete_query += " AND contractor_id = :contractor_id"
                params['contractor_id'] = contractor_id
            
            if len(date_range) == 2:
                delete_query += " AND break_date BETWEEN :start_date AND :end_date"
                params['start_date'] = date_range[0]
                params['end_date'] = date_range[1]

            result = conn.execute(text(delete_query), params)
            
        st.success(f"✅ Deleted {result.rowcount} break records!")
        
    except Exception as e:
        st.error(f"Error deleting breaks: {e}")
        raise


def delete_pickups(contractor_filter, date_range, contractors_df):
    """Delete pickup records based on filters"""
    try:
        engine = get_sqlalchemy_engine()
        
        with engine.begin() as conn:
            delete_query = "DELETE FROM pickups WHERE 1=1"
            params = {}
            
            if contractor_filter != "All Contractors":
                contractor_id = contractors_df[contractors_df['name'] == contractor_filter]['id'].iloc[0]
                delete_query += " AND contractor_id = :contractor_id"
                params['contractor_id'] = contractor_id
            
            if len(date_range) == 2:
                delete_query += " AND pickup_date BETWEEN :start_date AND :end_date"
                params['start_date'] = date_range[0]
                params['end_date'] = date_range[1]

            result = conn.execute(text(delete_query), params)
            
        st.success(f"✅ Deleted {result.rowcount} pickup records!")
        
    except Exception as e:
        st.error(f"Error deleting pickups: {e}")
        raise


def backup_restore_section():
    """Backup and restore section - integrates with existing backup_management.py"""
    st.subheader("💾 Backup & Restore")
    
    # Import and use existing backup management functionality
    try:
        from backup_management import backup_management_page
        
        st.info("📌 This section provides backup management and restore capabilities.")
        
        # Add restore functionality
        st.markdown("---")
        st.subheader("🔄 Restore from Backup")
        
        import os
        import glob
        
        backup_dir = "backups"
        
        if not os.path.exists(backup_dir):
            st.warning("No backup directory found. Please create backups first.")
        else:
            # Get database backups
            db_backups = sorted(glob.glob(os.path.join(backup_dir, "vts_database_backup_*.db")), reverse=True)
            
            if db_backups:
                st.warning("⚠️ **Warning:** Restoring from backup will replace the current database. A pre-restore backup will be created automatically.")
                
                selected_backup = st.selectbox(
                    "Select backup to restore:",
                    [os.path.basename(f) for f in db_backups],
                    key="restore_backup_select"
                )
                
                if selected_backup:
                    backup_path = os.path.join(backup_dir, selected_backup)
                    
                    # Show backup info
                    file_size = os.path.getsize(backup_path) / (1024 * 1024)
                    st.info(f"📊 Backup size: {file_size:.2f} MB")
                    
                    # Extract timestamp from filename
                    try:
                        timestamp_str = selected_backup.replace("vts_database_backup_", "").replace(".db", "")
                        backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        st.info(f"📅 Backup date: {backup_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    except:
                        pass
                    
                    if st.button("🔄 Restore Database", type="primary"):
                        st.session_state['confirm_restore'] = True
                    
                    if st.session_state.get('confirm_restore', False):
                        st.error("⚠️ **FINAL WARNING:** This will replace your current database. Are you absolutely sure?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Yes, Restore Now", key="confirm_restore_yes"):
                                restore_database_from_backup(backup_path)
                                st.session_state['confirm_restore'] = False
                        with col2:
                            if st.button("❌ Cancel", key="confirm_restore_no"):
                                st.session_state['confirm_restore'] = False
                                st.rerun()
            else:
                st.info("No database backups available for restore.")
        
        st.markdown("---")
        
        # Show existing backup management page
        backup_management_page()
        
    except ImportError:
        st.error("Backup management module not found. Please ensure backup_management.py exists.")
    except Exception as e:
        st.error(f"Error in backup/restore section: {e}")
        with st.expander("View Error Details"):
            st.code(traceback.format_exc())


def restore_database_from_backup(backup_path):
    """Restore database from a backup file"""
    try:
        import shutil
        import os
        
        # Determine database path
        db_path = 'vts_database.db' if USE_SQLITE else None
        
        if not db_path:
            st.error("Restore is only supported for SQLite databases currently.")
            return
        
        # Create pre-restore backup
        if os.path.exists(db_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pre_restore_backup = f'backups/pre_restore_backup_{timestamp}.db'
            os.makedirs('backups', exist_ok=True)
            shutil.copy2(db_path, pre_restore_backup)
            st.info(f"✅ Pre-restore backup created: {pre_restore_backup}")
        
        # Restore from backup
        shutil.copy2(backup_path, db_path)
        
        st.success("✅ Database restored successfully!")
        st.warning("⚠️ Please refresh the page to see the restored data.")
        
        if st.button("🔄 Refresh Page"):
            st.rerun()
        
    except Exception as e:
        st.error(f"Error restoring database: {e}")
        with st.expander("View Error Details"):
            st.code(traceback.format_exc())


if __name__ == "__main__":
    # For testing standalone
    st.set_page_config(page_title="System Manager", page_icon="⚙️", layout="wide")
    system_manager_page()