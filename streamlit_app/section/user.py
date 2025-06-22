import streamlit as st
import pandas as pd
import hashlib
import time 
from section.utils.helper import engine2
from sqlalchemy import text

def user_page():
    st.title("👥 User Information")

    # Fetch users from the database
    with engine2.connect() as conn:
        df_users = pd.read_sql("SELECT * FROM user_information", conn)

    # Drop the password column before displaying
    if 'password' in df_users.columns:
        df_users = df_users.drop(columns=["password"])
    
    original_df = df_users.copy()

    if st.session_state.get("user_role") == "admin":
        st.success("You are logged in as Admin. You can edit or delete users.")

        edited_df = st.data_editor(
            df_users,
            column_config={"userID": st.column_config.NumberColumn("User ID")},  # Show editable userID
            num_rows="dynamic",
            use_container_width=True,
            key="user_editor"
        )

        # Handle adding a new user
        st.subheader("➕ Add New User")
        with st.form("add_user_form"):
            new_userID = st.text_input("User ID")
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")

            new_user_submitted = st.form_submit_button("Add New User")

            if new_user_submitted:
                if new_username and new_email and new_password:
                    try:
                        # Hash the password
                        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()

                        with engine2.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO user_information (userID, username, email, password, role)
                                VALUES (:userID, :username, :email, :password, 'User')
                            """), {
                                "userID" : new_userID,
                                "username": new_username,
                                "email": new_email,
                                "password": hashed_password,
                            })
                        st.success("✅ New user added successfully.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding user: {e}")
                else:
                    st.warning("Please fill in all fields.")

        if not edited_df.equals(original_df):
            if st.button("💾 Save Changes"):
                try:
                    with engine2.begin() as conn:
                        for i in range(len(edited_df)):
                            row = edited_df.iloc[i]
                            original_userID = original_df.iloc[i]["userID"]  # original
                            conn.execute(text(""" 
                                UPDATE user_information
                                SET userID = :new_userID,
                                    username = :username,
                                    email = :email
                                WHERE userID = :original_userID
                            """), {
                                "new_userID": row["userID"],
                                "username": row["username"],
                                "email": row["email"],
                                "original_userID": original_userID
                            })
                    st.success("Changes saved successfully.")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving changes: {e}")

        # Delete row
        st.subheader("🗑️ Delete User")
        user_ids = df_users["userID"].tolist()
        selected_id = st.selectbox("Select a user ID to delete", user_ids)

        if st.button("Delete User"):
            try:
                with engine2.begin() as conn:
                    conn.execute(text("DELETE FROM user_information WHERE userID = :userID"), {"userID": selected_id})
                st.success(f"User with ID {selected_id} deleted.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete user: {e}")

    else:
        st.info("You are logged in as a user. View-only access.")
        st.dataframe(df_users, use_container_width=True)
