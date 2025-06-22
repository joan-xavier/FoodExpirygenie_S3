import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import json
import os

# Configure page settings
st.set_page_config(
    page_title="ExpiryGenie 🧞‍♂️",
    page_icon="🧞‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'food_items' not in st.session_state:
    st.session_state.food_items = []
if 'money_saved' not in st.session_state:
    st.session_state.money_saved = 0.0

# Load user data if exists
def load_user_data():
    if os.path.exists('user_data.json'):
        try:
            with open('user_data.json', 'r') as f:
                st.session_state.user_data = json.load(f)
        except:
            st.session_state.user_data = {}

# Save user data
def save_user_data():
    with open('user_data.json', 'w') as f:
        json.dump(st.session_state.user_data, f)

# Load food items for current user
def load_food_items():
    if st.session_state.current_user and st.session_state.current_user in st.session_state.user_data:
        user_foods = st.session_state.user_data[st.session_state.current_user].get('food_items', [])
        st.session_state.food_items = user_foods

# Save food items for current user
def save_food_items():
    if st.session_state.current_user:
        if st.session_state.current_user not in st.session_state.user_data:
            st.session_state.user_data[st.session_state.current_user] = {}
        st.session_state.user_data[st.session_state.current_user]['food_items'] = st.session_state.food_items
        save_user_data()

# Initialize data
load_user_data()
if st.session_state.logged_in:
    load_food_items()

# Main app content
def main():
    st.markdown("# 🧞‍♂️ ExpiryGenie")
    st.markdown("### *Track food easily. Store smart. Waste never.*")
    
    if not st.session_state.logged_in:
        st.info("👈 Please visit the Landing page to get started, or go to Auth to sign in!")
        
        # Quick stats for demonstration
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Users Helped", "10,000+")
        with col2:
            st.metric("Food Waste Reduced", "50 tons")
        with col3:
            st.metric("Money Saved", "$2M+")
            
        st.markdown("---")
        st.markdown("### ✨ Key Features")
        
        feature_col1, feature_col2 = st.columns(2)
        
        with feature_col1:
            st.markdown("""
            **🎯 Smart Tracking**
            - Manual entry with intuitive forms
            - Voice input with AI processing
            - Image/barcode scanning with OCR
            
            **📅 Visual Calendar**
            - Color-coded expiry dates
            - Green (Safe), Yellow (Soon), Red (Expired)
            - Daily, weekly, monthly views
            """)
            
        with feature_col2:
            st.markdown("""
            **🤖 AI-Powered**
            - Gemini AI for food recognition
            - Smart categorization
            - Personalized recommendations
            
            **📊 Analytics**
            - Money saved tracking
            - Waste reduction metrics
            - Usage patterns
            """)
    else:
        st.success(f"Welcome back, {st.session_state.current_user}! 🎉")
        
        # Quick dashboard
        if st.session_state.food_items:
            today = datetime.now().date()
            
            # Calculate expiry status
            safe_count = 0
            warning_count = 0
            expired_count = 0
            
            for item in st.session_state.food_items:
                expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                days_until_expiry = (expiry_date - today).days
                
                if days_until_expiry < 0:
                    expired_count += 1
                elif days_until_expiry <= 3:
                    warning_count += 1
                else:
                    safe_count += 1
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🟢 Safe Items", safe_count)
            with col2:
                st.metric("🟡 Expiring Soon", warning_count)
            with col3:
                st.metric("🔴 Expired Items", expired_count)
            with col4:
                st.metric("💰 Money Saved", f"${st.session_state.money_saved:.2f}")
                
            if warning_count > 0 or expired_count > 0:
                st.warning(f"⚠️ You have {warning_count + expired_count} items that need attention!")
        else:
            st.info("🎯 Ready to start tracking your food? Visit the Dashboard to add your first items!")

if __name__ == "__main__":
    main()
