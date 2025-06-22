from section.utils.helper import engine1
import streamlit as st
from sqlalchemy import inspect, text
import pandas as pd

def _is_admin():
    """Check if current user is admin (modify with your auth logic)."""
    return st.session_state.get('user_role') == 'admin'  # Replace with your auth system

def _delete_table(table_name):
    """Dangerous: Delete a table from the database."""
    with engine1.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        conn.commit()

def _fetch_table_names():
    """Helper function to get table names."""
    inspector = inspect(engine1)
    return inspector.get_table_names()

def _display_tables(table_names):
    """Helper function to display tables with admin controls."""
    if not table_names:
        st.warning("No tables found in the database.")
        return

    st.success(f"Found {len(table_names)} tables.")
    
    for table in table_names:
        with st.expander(f"📄 {table}"):
            # Table content display
            try:
                df = pd.read_sql_table(table, con=engine1)
                st.dataframe(df)
                
                # ADMIN-ONLY CONTROLS
                if _is_admin():
                    st.markdown("---")
                    st.warning("🔐 Admin Actions")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"❌ Delete {table}", key=f"delete_{table}"):
                            _delete_table(table)
                            st.rerun()  # Refresh the page
                    
                    with col2:
                        if st.button(f"🔁 Refresh {table}", key=f"refresh_{table}"):
                            st.rerun()
                            
            except Exception as e:
                st.error(f"Error reading table {table}: {e}")

def database_page():
    """Displays the database page with admin controls."""
    st.title("🗃️ Database Tables")
    
    try:
        table_names = _fetch_table_names()
        
        # ADMIN-ONLY WARNING
        if _is_admin():
            st.warning("⚠️ ADMIN MODE: You have table management privileges", icon="⚠️")
        
        _display_tables(table_names)

    except Exception as e:
        st.error(f"Database error: {e}")
