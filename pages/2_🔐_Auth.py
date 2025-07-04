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
    # Apply theme from session state
    current_theme = st.session_state.get('app_theme', 'Light')
    if current_theme == "Elegant":
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #FFB6C1 0%, #FFC0CB 50%, #FFE4E1 100%);
            color: #1f2937;
        }
        .stSelectbox, .stTextInput, .stTextArea {
            background-color: rgba(255, 255, 255, 0.9);
            color: #1f2937;
            border: 2px solid #FFB6C1;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(255, 182, 193, 0.2);
        }
        .stSelectbox:focus, .stTextInput:focus, .stTextArea:focus {
            border-color: #FF69B4;
            box-shadow: 0 0 0 3px rgba(255, 182, 193, 0.3);
        }
        .stButton > button {
            background: linear-gradient(135deg, #FFB6C1 0%, #FF69B4 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(255, 182, 193, 0.4);
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #FF69B4 0%, #FFB6C1 100%);
            box-shadow: 0 6px 20px rgba(255, 182, 193, 0.5);
            transform: translateY(-2px);
        }
        .stTabs [data-baseweb="tab-list"] {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 182, 193, 0.1) 100%);
            border-radius: 12px;
            border: 2px solid #FFB6C1;
        }
        .stTabs [data-baseweb="tab"] {
            color: #1f2937;
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #FFB6C1 0%, #FF69B4 100%);
            color: white;
            border-radius: 8px;
        }
        .stAlert {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 182, 193, 0.05) 100%);
            border: 2px solid #FFB6C1;
            border-radius: 12px;
        }
        .stInfo {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 182, 193, 0.05) 100%);
            border: 2px solid #FFB6C1;
            border-radius: 12px;
        }
        .stSuccess {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 182, 193, 0.05) 100%);
            border: 2px solid #10b981;
            border-radius: 12px;
        }
        .stWarning {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 182, 193, 0.05) 100%);
            border: 2px solid #f59e0b;
            border-radius: 12px;
        }
        .stError {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 182, 193, 0.05) 100%);
            border: 2px solid #ef4444;
            border-radius: 12px;
        }
        </style>
        """, unsafe_allow_html=True)
    
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
    
    # Check if user is already logged in
    if st.session_state.logged_in and st.session_state.current_user:
        # Show logout interface
        st.success(f"✅ Welcome back, {st.session_state.current_user}!")
        st.markdown("### You are currently logged in")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🏠 Go to Dashboard", type="primary", use_container_width=True):
                st.switch_page("pages/3_📱_Dashboard.py")
        
        with col2:
            if st.button("📊 View Statistics", use_container_width=True):
                st.switch_page("pages/5_📊_Stats.py")
        
        with col3:
            if st.button("🚪 Logout", type="secondary", use_container_width=True):
                # Clear all session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("👋 Logged out successfully!")
                st.rerun()
        
        st.markdown("---")
        st.info("💡 You can also use the sidebar navigation to move between pages.")
        
    else:
        # Show login/signup interface
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

if __name__ == "__main__":
    main()
