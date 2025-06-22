import hashlib
import json
import os
import streamlit as st
from datetime import datetime

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash

def save_user_data():
    """Save user data to JSON file"""
    try:
        with open('user_data.json', 'w') as f:
            json.dump(st.session_state.user_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving user data: {str(e)}")
        return False

def load_user_data():
    """Load user data from JSON file"""
    try:
        if os.path.exists('user_data.json'):
            with open('user_data.json', 'r') as f:
                st.session_state.user_data = json.load(f)
        else:
            st.session_state.user_data = {}
        return True
    except Exception as e:
        st.error(f"Error loading user data: {str(e)}")
        st.session_state.user_data = {}
        return False

def create_user(name, email, password):
    """Create a new user account"""
    if email in st.session_state.user_data:
        return False, "User already exists"
    
    password_hash = hash_password(password)
    st.session_state.user_data[email] = {
        'name': name,
        'password_hash': password_hash,
        'food_items': [],
        'money_saved': 0.0,
        'created_at': str(datetime.now())
    }
    
    if save_user_data():
        return True, "User created successfully"
    else:
        return False, "Error creating user"

def authenticate_user(email, password):
    """Authenticate user login"""
    if email not in st.session_state.user_data:
        return False, "User not found"
    
    user_info = st.session_state.user_data[email]
    if verify_password(password, user_info['password_hash']):
        # Set session state
        st.session_state.logged_in = True
        st.session_state.current_user = email
        st.session_state.food_items = user_info.get('food_items', [])
        st.session_state.money_saved = user_info.get('money_saved', 0.0)
        return True, "Login successful"
    else:
        return False, "Invalid password"

def logout_user():
    """Logout current user"""
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.food_items = []
    st.session_state.money_saved = 0.0

def reset_password(email, new_password):
    """Reset user password (simplified version)"""
    if email not in st.session_state.user_data:
        return False, "User not found"
    
    password_hash = hash_password(new_password)
    st.session_state.user_data[email]['password_hash'] = password_hash
    
    if save_user_data():
        return True, "Password reset successfully"
    else:
        return False, "Error resetting password"
