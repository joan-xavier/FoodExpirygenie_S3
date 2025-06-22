import streamlit as st
import hashlib
import json
import os
from utils.auth import hash_password, verify_password, save_user_data, load_user_data

st.set_page_config(
    page_title="ExpiryGenie - Authentication",
    page_icon="🔐",
    layout="centered"
)

def main():
    st.markdown("# 🔐 Authentication")
    
    # Load existing user data
    load_user_data()
    
    # Create tabs for different auth methods
    tab1, tab2, tab3 = st.tabs(["🔑 Login", "📝 Sign Up", "🔄 Reset Password"])
    
    # Login Tab
    with tab1:
        st.markdown("### Welcome Back! 👋")
        
        with st.form("login_form"):
            email = st.text_input("📧 Email", placeholder="your.email@example.com")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            login_submit = st.form_submit_button("🚀 Login", type="primary", use_container_width=True)
            
            if login_submit:
                if not email or not password:
                    st.error("❌ Please fill in all fields")
                elif email in st.session_state.user_data:
                    user_info = st.session_state.user_data[email]
                    if verify_password(password, user_info['password_hash']):
                        st.session_state.logged_in = True
                        st.session_state.current_user = email
                        # Load user's food items
                        st.session_state.food_items = user_info.get('food_items', [])
                        st.session_state.money_saved = user_info.get('money_saved', 0.0)
                        st.success("✅ Login successful!")
                        st.balloons()
                        st.switch_page("pages/3_📱_Dashboard.py")
                    else:
                        st.error("❌ Invalid password")
                else:
                    st.error("❌ User not found")
        
        # Google Sign In (placeholder)
        st.markdown("---")
        st.markdown("### Or continue with:")
        if st.button("🔍 Sign in with Google", use_container_width=True):
            st.info("🚧 Google Sign-in integration coming soon!")
    
    # Sign Up Tab
    with tab2:
        st.markdown("### Join the ExpiryGenie Family! 🎉")
        
        with st.form("signup_form"):
            name = st.text_input("👤 Full Name", placeholder="John Doe")
            email = st.text_input("📧 Email", placeholder="john.doe@example.com")
            password = st.text_input("🔒 Password", type="password", placeholder="Create a strong password")
            confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm your password")
            
            # Terms and conditions
            terms_accepted = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            
            signup_submit = st.form_submit_button("🎯 Create Account", type="primary", use_container_width=True)
            
            if signup_submit:
                if not all([name, email, password, confirm_password]):
                    st.error("❌ Please fill in all fields")
                elif password != confirm_password:
                    st.error("❌ Passwords do not match")
                elif len(password) < 6:
                    st.error("❌ Password must be at least 6 characters long")
                elif not terms_accepted:
                    st.error("❌ Please accept the terms and conditions")
                elif email in st.session_state.user_data:
                    st.error("❌ User already exists with this email")
                else:
                    # Create new user
                    password_hash = hash_password(password)
                    st.session_state.user_data[email] = {
                        'name': name,
                        'password_hash': password_hash,
                        'food_items': [],
                        'money_saved': 0.0,
                        'created_at': str(st.session_state.get('current_time', 'unknown'))
                    }
                    save_user_data()
                    
                    # Auto login
                    st.session_state.logged_in = True
                    st.session_state.current_user = email
                    st.session_state.food_items = []
                    st.session_state.money_saved = 0.0
                    
                    st.success("🎉 Account created successfully!")
                    st.balloons()
                    st.switch_page("pages/3_📱_Dashboard.py")
    
    # Reset Password Tab
    with tab3:
        st.markdown("### Reset Your Password 🔄")
        
        with st.form("reset_form"):
            reset_email = st.text_input("📧 Email", placeholder="Enter your registered email")
            reset_submit = st.form_submit_button("📧 Send Reset Link", type="primary", use_container_width=True)
            
            if reset_submit:
                if not reset_email:
                    st.error("❌ Please enter your email")
                elif reset_email in st.session_state.user_data:
                    st.success("✅ Password reset link sent to your email!")
                    st.info("🚧 Email functionality coming soon! For now, please contact support.")
                else:
                    st.error("❌ Email not found in our records")
    
    # Current Status
    if st.session_state.logged_in:
        st.markdown("---")
        st.success(f"✅ Currently logged in as: {st.session_state.current_user}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏠 Go to Dashboard", type="primary"):
                st.switch_page("pages/3_📱_Dashboard.py")
        with col2:
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.current_user = None
                st.session_state.food_items = []
                st.session_state.money_saved = 0.0
                st.success("👋 Logged out successfully!")
                st.rerun()

if __name__ == "__main__":
    main()
