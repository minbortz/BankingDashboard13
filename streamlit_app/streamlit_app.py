import streamlit as st
import hashlib
import time 
from section import dashboardver2_1
from datetime import datetime
from section.utils.helper import insert_user, insert_admin, get_admin_by_username, get_user_by_username

st.set_page_config(page_title='Dashboard', layout='wide')

# Dummy admin key
VALID_ADMIN_KEY = "13102002"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def signup(user_type, user_id, username, password, email, admin_key=None):
    timestamp = datetime.now()
    hashed_password = hash_password(password)

    try:
        if user_type == "User":
            role = "User"
            insert_user(user_id, username, hashed_password, email, timestamp, role)
            return True, "User signed up and stored in database."

        elif user_type == "Admin":
            if not admin_key or admin_key.strip() != VALID_ADMIN_KEY:
                return False, "Invalid Admin Key."
            role = "Admin"
            insert_admin(user_id, username, hashed_password, email, timestamp, role)
            return True, "Admin signed up and stored in database."
    except Exception as e:
        return False, f"Database error: {str(e)}"


def login(username, password):
    if not username and not password:
        return False, "Please enter username and password."
    if not username:
        return False, "Please enter username."
    if not password:
        return False, "Please enter password."
    
    hashed_pw = hash_password(password)

    user = get_user_by_username(username)
    if user and user.get('password') == hashed_pw:
        st.session_state.user_role = "user" 
        return True, f"Welcome, {username} (User)!"

    admin = get_admin_by_username(username)
    if admin and admin.get('password') == hashed_pw:
        st.session_state.user_role = "admin"  
        return True, f"Welcome, {username} (Admin)!"

    return False, "Invalid username or password."


def main():
    if 'login_success' in st.session_state and st.session_state.login_success:
        dashboardver2_1.show_dashboard()
        return

    st.title("🔐 Login")

    page = st.radio("Select Action", ["Login", "Signup"])

    if page == "Signup":
        st.subheader("📝 Signup Form")

        if "signup_success" not in st.session_state:
            st.session_state.signup_success = False

        if st.session_state.signup_success:
            st.success("User signed up and stored in database.")
            st.session_state.signup_success = False
            st.stop()

        # Move the user_type selection outside the form so it updates immediately
        user_type = st.selectbox("Choose User Type", ["User", "Admin"])
        
        with st.form("signup_form"):
            user_id = st.text_input("User ID")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            email = st.text_input("Email")
            
            # This will now show immediately when Admin is selected
            admin_key = st.text_input("Admin Key", type="password") if user_type == "Admin" else None

            submitted = st.form_submit_button("Signup")
            if submitted:
                if not all([user_id, username, password, email]):
                    st.error("Please fill in all required fields.")
                elif user_type == "Admin" and not admin_key:
                    st.error("Please enter admin key.")
                else:
                    success, message = signup(
                        user_type, 
                        user_id, 
                        username, 
                        password, 
                        email, 
                        admin_key if user_type == "Admin" else None
                    )
                    if success:
                        st.session_state.signup_success = True
                        st.rerun()
                    else:
                        st.error(message)

    elif page == "Login":
        st.subheader("🔑 Login Form")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                success, message = login(username, password)
                if success:
                    st.success("Login successful! Redirecting to dashboard...")
                    st.session_state.login_success = True
                    st.session_state.username = username
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(message)

if __name__ == "__main__":
    main()
