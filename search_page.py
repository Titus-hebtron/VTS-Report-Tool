def search_page():
    import streamlit as st
    import pandas as pd
    from db_utils import get_sqlalchemy_engine

    st.header("🔍 Search & View Data")

    search_options = ["Accidents", "Incidents", "Breaks", "Pickups"]
    selected_option = st.selectbox("Select data to view", search_options)

    start_date = st.date_input("Start date")
    end_date = st.date_input("End date")
    vehicle = st.text_input("Vehicle (optional)")

    if st.button("Search"):
        engine = get_sqlalchemy_engine()
        if selected_option == "Accidents":
            query = "SELECT * FROM incident_reports WHERE incident_date BETWEEN %s AND %s AND incident_type = %s"
            params = (start_date, end_date, "Accident")
            if vehicle:
                query += " AND patrol_car = %s"
                params += (vehicle,)
            df = pd.read_sql_query(query, engine, params=params)
        elif selected_option == "Incidents":
            query = "SELECT * FROM incident_reports WHERE incident_date BETWEEN %s AND %s AND incident_type = %s"
            params = (start_date, end_date, "Incident")
            if vehicle:
                query += " AND patrol_car = %s"
                params += (vehicle,)
            df = pd.read_sql_query(query, engine, params=params)
        elif selected_option == "Breaks":
            query = "SELECT * FROM breaks WHERE break_date BETWEEN %s AND %s"
            params = (start_date, end_date)
            if vehicle:
                query += " AND vehicle = %s"
                params += (vehicle,)
            df = pd.read_sql_query(query, engine, params=params)
        elif selected_option == "Pickups":
            query = "SELECT * FROM pickups WHERE pickup_start::date BETWEEN %s AND %s"
            params = (start_date, end_date)
            if vehicle:
                query += " AND vehicle = %s"
                params += (vehicle,)
            df = pd.read_sql_query(query, engine, params=params)
        else:
            df = pd.DataFrame()

        if not df.empty:
            st.dataframe(df)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Results as CSV",
                data=csv,
                file_name=f"{selected_option.lower()}_results.csv",
                mime="text/csv"
            )
        else:
            st.info("No data found for your search.")