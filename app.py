import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import json
import os
from utils.database import init_database, get_user_food_items

# Configure page settings
st.set_page_config(
    page_title="ExpiryGenie 🧞‍♂️",
    page_icon="🧞‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database on app start
if 'db_initialized' not in st.session_state:
    if init_database():
        st.session_state.db_initialized = True

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
    # Check if user is logged in and load their food items from database
    if st.session_state.logged_in and st.session_state.current_user:
        db_items = get_user_food_items(st.session_state.current_user)
        # Convert database items to session state format
        st.session_state.food_items = []
        for item in db_items:
            st.session_state.food_items.append({
                'id': item['id'],
                'name': item['name'],
                'category': item['category'],
                'purchase_date': item['purchase_date'].strftime('%Y-%m-%d'),
                'expiry_date': item['expiry_date'].strftime('%Y-%m-%d'),
                'quantity': item['quantity'],
                'opened': item['opened'],
                'added_method': item['added_method']
            })
    
    # Redirect to landing page by default
    if not st.session_state.logged_in:
        st.switch_page("pages/1_🏠_Landing.py")
    else:
        st.markdown("# 🧞‍♂️ ExpiryGenie Dashboard")
        st.markdown(f"Welcome back, **{st.session_state.current_user}**! 🎉")
        
        # Quick dashboard
        if st.session_state.food_items:
            today = datetime.now().date()
            
            # Calculate expiry status
            safe_count = 0
            warning_count = 0
            expired_count = 0
            
            for item in st.session_state.food_items:
                if isinstance(item['expiry_date'], str):
                    expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                else:
                    expiry_date = item['expiry_date']
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
                
            # Quick actions
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("➕ Add Food Items", type="primary"):
                    st.switch_page("pages/3_📱_Dashboard.py")
            with col2:
                if st.button("📅 View Calendar"):
                    st.switch_page("pages/4_📅_Calendar.py")
            with col3:
                if st.button("📊 View Statistics"):
                    st.switch_page("pages/5_📊_Stats.py")
        else:
            st.info("🎯 Ready to start tracking your food? Add your first items!")
            if st.button("➕ Add Food Items", type="primary"):
                st.switch_page("pages/3_📱_Dashboard.py")

if __name__ == "__main__":
    main()
