import streamlit as st
import hashlib
import json
import os
# S3 storage handles password hashing internally
from utils.s3_storage import create_user, authenticate_user, get_user_by_email, hash_password, verify_password

st.set_page_config(
    page_title="ExpiryGenie - Authentication",
    page_icon="🔐",
    layout="centered"
)

def main():
    st.markdown("# 🔐 Authentication")
    
    # Initialize session state variables
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'food_items' not in st.session_state:
        st.session_state.food_items = []
    if 'money_saved' not in st.session_state:
        st.session_state.money_saved = 0.0
    
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
                else:
                    user_data = authenticate_user(email, password)
                    
                    if user_data:
                        st.session_state.logged_in = True
                        st.session_state.current_user = email
                        st.session_state.food_items = []
                        st.session_state.money_saved = float(user_data.get('money_saved', 0.0))
                        st.success("✅ Login successful!")
                        st.balloons()
                        st.switch_page("pages/3_📱_Dashboard.py")
                    else:
                        st.error("❌ Invalid email or password")
        
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
                else:
                    # Create new user in database
                    success = create_user(name, email, password)
                    
                    if success:
                        # Auto login
                        st.session_state.logged_in = True
                        st.session_state.current_user = email
                        st.session_state.food_items = []
                        st.session_state.money_saved = 0.0
                        
                        st.success("🎉 Account created successfully!")
                        st.balloons()
                        st.switch_page("pages/3_📱_Dashboard.py")
                    else:
                        st.error("❌ Failed to create account. Email might already exist.")
    
    # Reset Password Tab
    with tab3:
        st.markdown("### Reset Your Password 🔄")
        
        with st.form("reset_form"):
            reset_email = st.text_input("📧 Email", placeholder="Enter your registered email")
            reset_submit = st.form_submit_button("📧 Send Reset Link", type="primary", use_container_width=True)
            
            if reset_submit:
                if not reset_email:
                    st.error("❌ Please enter your email")
                else:
                    user = get_user_by_email(reset_email)
                    if user:
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
