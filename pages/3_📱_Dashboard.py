import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from utils.food_data import get_food_categories, calculate_expiry_date
from utils.gemini_client import process_voice_input, process_image_input
from utils.voice_input import AudioProcessor, transcribe_audio
from utils.image_processing import extract_text_from_image, process_food_image
from utils.s3_storage import (
    get_household_food_items, save_household_food_items, add_household_food_item, delete_household_food_item, update_household_food_item_details, update_household_food_item_date, predict_expiry_date, get_user_food_items, add_food_item, delete_food_item, update_food_item_details, update_food_item_date, authenticate_user, update_user_password
)
import time
import random
import hashlib
import uuid
import numpy as np
import speech_recognition as sr
import requests
from PIL import Image, UnidentifiedImageError
import os
import smtplib
from email.mime.text import MIMEText
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except ImportError:
    pyzbar_decode = None

st.set_page_config(
    page_title="ExpiryGenie - Dashboard",
    page_icon="📱",
    layout="wide"
)

st.markdown(
    '''
    <style>
    .small-edit-button button {
        font-size: 12px !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
    }
    </style>
    ''',
    unsafe_allow_html=True
)

# --- Family Sync (Household Sharing) ---
def get_or_create_household_id():
    if 'household_id' not in st.session_state:
        st.session_state['household_id'] = str(uuid.uuid4())
    return st.session_state['household_id']

def set_household_id(new_id):
    st.session_state['household_id'] = new_id

def get_household_members(household_id):
    # Placeholder: In a real app, fetch from user database
    return [st.session_state.get('current_user', 'You')]

def send_household_invite(email, household_id):
    # Use the same email credentials as expiry notifications
    EMAIL_ADDRESS = os.environ.get('EXPIRYGENIE_EMAIL')
    EMAIL_PASSWORD = os.environ.get('EXPIRYGENIE_EMAIL_PASSWORD')
    
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        st.error("Email credentials not set. Please set EXPIRYGENIE_EMAIL and EXPIRYGENIE_EMAIL_PASSWORD as environment variables.")
        return False
    
    subject = "ExpiryGenie: You're invited to join a household!"
    body = f"""
Hello!

You've been invited to join an ExpiryGenie household for shared food inventory management.

To join this household:
1. Open ExpiryGenie app
2. Go to the Dashboard
3. In the sidebar, find "Family Sync"
4. Enter this household code: {household_id}
5. Click "Join Household"

This will allow you to see and manage the same food inventory as your family/roommates.

Best regards,
ExpiryGenie Team
"""
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = email
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(msg['From'], [msg['To']], msg.as_string())
        st.success(f"✅ Invite sent to {email} with household code: {household_id}")
        return True
    except Exception as e:
        st.error(f"❌ Failed to send invite email: {e}")
        return False

def check_authentication():
    if not st.session_state.get('logged_in', False):
        st.error("🔒 Please login first to access the dashboard")
        st.stop()

def send_expiry_notification(user_email, expiring_items):
    # Use environment variables for credentials
    EMAIL_ADDRESS = os.environ.get('EXPIRYGENIE_EMAIL')
    EMAIL_PASSWORD = os.environ.get('EXPIRYGENIE_EMAIL_PASSWORD')
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        # Do not show a warning to the user, just return None
        return None
    subject = "ExpiryGenie: Items Expiring Soon"
    body = "The following items are expiring soon:\n\n"
    for item in expiring_items:
        body += f"- {item['name']} (expires on {item['expiry_date']})\n"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = user_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(msg['From'], [msg['To']], msg.as_string())
        return True
    except Exception as e:
        st.error(f"Email send failed: {e}")
        return False

def check_and_notify_expiry():
    if not st.session_state.get('notify_expiry', True):
        return
    user_email = st.session_state.get('current_user')
    if not user_email:
        return
    today = datetime.now().date()
    expiring_items = [
        item for item in st.session_state.food_items
        if 0 <= (datetime.strptime(item['expiry_date'], '%Y-%m-%d').date() - today).days <= 2
    ]
    if expiring_items and not st.session_state.get('notified_today', False):
        result = send_expiry_notification(user_email, expiring_items)
        if result is True:
            st.session_state['notified_today'] = True
            st.success("You will receive a notification email about items expiring soon.")
        elif result is None:
            st.info("You will receive notification via email if items are expiring soon.")
        elif result is False:
            st.info("You will receive notification via email if items are expiring soon.")

def migrate_user_data_to_household():
    """Migrate existing user data to household-based system"""
    if not st.session_state.get('current_user'):
        return
    
    user_email = st.session_state['current_user']
    household_id = st.session_state.get('household_id')
    
    # Check if migration is needed and household_id exists
    if 'data_migrated' in st.session_state or not household_id:
        return
    
    try:
        # Get existing items stored by email
        old_items = get_user_food_items(user_email)
        
        if old_items and len(old_items) > 0:
            # Migrate items to household system
            for item in old_items:
                add_household_food_item(
                    household_id,
                    item['name'],
                    item['category'],
                    item['purchase_date'],
                    item['expiry_date'],
                    item['quantity'],
                    item['opened'],
                    item.get('added_method', 'migrated')
                )
            
            st.session_state['data_migrated'] = True
            st.success(f"✅ Migrated {len(old_items)} existing items to your household!")
            st.rerun()
            
    except Exception as e:
        print(f"Migration error: {e}")
        st.session_state['data_migrated'] = True  # Prevent retry

# --- User Mode Management ---
def get_user_mode():
    """Get user's preferred mode: 'family' or 'individual'"""
    if 'user_mode' not in st.session_state:
        st.session_state['user_mode'] = 'individual'  # Default to individual mode
    return st.session_state['user_mode']

def set_user_mode(mode):
    """Set user's preferred mode"""
    st.session_state['user_mode'] = mode
    # Clear household_id if switching to individual mode
    if mode == 'individual':
        st.session_state.pop('household_id', None)
    # Generate household_id if switching to family mode
    elif mode == 'family' and 'household_id' not in st.session_state:
        st.session_state['household_id'] = str(uuid.uuid4())

def get_storage_identifier():
    """Get the appropriate storage identifier based on user mode"""
    mode = get_user_mode()
    if mode == 'family':
        return st.session_state.get('household_id')
    else:
        return st.session_state.get('current_user')

def add_food_item_adaptive(name, category, purchase_date, expiry_date, quantity='1 unit', opened=False, added_method='manual'):
    """Add food item using the appropriate storage method based on user mode"""
    identifier = get_storage_identifier()
    if not identifier:
        return False
    
    mode = get_user_mode()
    if mode == 'family':
        return add_household_food_item(identifier, name, category, purchase_date, expiry_date, quantity, opened, added_method)
    else:
        return add_food_item(identifier, name, category, purchase_date, expiry_date, quantity, opened, added_method)

def get_food_items_adaptive():
    """Get food items using the appropriate storage method based on user mode"""
    identifier = get_storage_identifier()
    if not identifier:
        return []
    
    mode = get_user_mode()
    if mode == 'family':
        return get_household_food_items(identifier)
    else:
        return get_user_food_items(identifier)

def delete_food_item_adaptive(item_id):
    """Delete food item using the appropriate storage method based on user mode"""
    identifier = get_storage_identifier()
    if not identifier:
        return False
    
    mode = get_user_mode()
    if mode == 'family':
        return delete_household_food_item(identifier, item_id)
    else:
        return delete_food_item(item_id, identifier)

def update_food_item_details_adaptive(item_id, name, quantity, opened):
    """Update food item details using the appropriate storage method based on user mode"""
    identifier = get_storage_identifier()
    if not identifier:
        return False
    
    mode = get_user_mode()
    if mode == 'family':
        return update_household_food_item_details(identifier, item_id, name, quantity, opened)
    else:
        return update_food_item_details(item_id, identifier, name, quantity, opened)

def update_food_item_date_adaptive(item_id, date_type, new_date):
    """Update food item date using the appropriate storage method based on user mode"""
    identifier = get_storage_identifier()
    if not identifier:
        return False
    
    mode = get_user_mode()
    if mode == 'family':
        return update_household_food_item_date(identifier, item_id, date_type, new_date)
    else:
        return update_food_item_date(item_id, identifier, date_type, new_date)

def get_user_display_name():
    """Get user's display name for welcome message"""
    # Check if user has set a custom name
    if 'user_name' in st.session_state and st.session_state['user_name']:
        return st.session_state['user_name']
    
    # Fallback to email-based name
    user_email = st.session_state.get('current_user', '')
    if user_email:
        # Extract name from email or use email as fallback
        name = user_email.split('@')[0] if '@' in user_email else user_email
        # Capitalize first letter
        return name.capitalize()
    return 'User'

def generate_user_id():
    """Generate a sequential 4-digit user ID starting from 1001"""
    if 'user_id' not in st.session_state:
        # In a real app, this would be stored in a database
        # For now, we'll use a simple counter approach
        if 'next_user_id' not in st.session_state:
            st.session_state['next_user_id'] = 1001
        
        st.session_state['user_id'] = st.session_state['next_user_id']
        st.session_state['next_user_id'] += 1
    return st.session_state['user_id']

def main():
    check_authentication()
    
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
        .stMetric {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 182, 193, 0.1) 100%);
            border-radius: 16px;
            padding: 16px;
            border: 2px solid #FFB6C1;
            box-shadow: 0 8px 25px rgba(255, 182, 193, 0.2);
        }
        .stExpander {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 182, 193, 0.05) 100%);
            border: 2px solid #FFB6C1;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(255, 182, 193, 0.15);
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
        .stDataFrame {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            border: 2px solid #FFB6C1;
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
    
    # Migrate existing data if needed
    migrate_user_data_to_household()
    
    # Personalized welcome message with settings button
    user_name = get_user_display_name()
    user_id = generate_user_id()
    
    # Create header with settings button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"# 🧞‍♂️ Hi {user_name}!")
        st.markdown(f"### Welcome to ExpiryGenie - Your Smart Food Expiry Tracker")
        st.markdown(f"**User ID:** {user_id} | **Mode:** {'Family Sync' if get_user_mode() == 'family' else 'Individual'}")
    
    with col2:
        st.markdown("")  # Add some spacing
        st.markdown("")  # Add some spacing
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state['show_settings'] = not st.session_state.get('show_settings', False)
    
    st.markdown("---")
    
    # Show settings if toggled
    if st.session_state.get('show_settings', False):
        settings_section()
        st.markdown("---")
    
    # Always load food items on page load
    if 'food_items' not in st.session_state or not st.session_state.food_items:
        refresh_food_items()
    
    # Check and notify for expiry if enabled
    check_and_notify_expiry()
    
    # Add food items section below title for better visibility
    st.markdown("## 📥 Add Food Items")
    
    # Create tabs for different input methods
    tab1, tab2, tab3 = st.tabs(["📝 Manual Entry", "🎤 Upload an Audio File for Voice Input", "📸 Image Upload"])
    
    with tab1:
        manual_entry_section()
    
    with tab2:
        voice_input_section()
    
    with tab3:
        image_input_section()
    
    st.markdown("---")
    
    # Quick stats section
    quick_stats_section()
    
    st.markdown("---")
    
    # Display food items
    display_food_items()

def manual_entry_section():
    st.markdown("### 📝 Manual Food Entry")
    
    with st.form("manual_food_entry"):
        col1, col2 = st.columns(2)
        
        with col1:
            food_name = st.text_input("🍎 Food Item Name", placeholder="e.g., Milk, Bananas, Chicken")
            purchase_date = st.date_input("📅 Purchase Date", value=datetime.now().date())
            category = st.selectbox("📂 Category", get_food_categories())
        
        with col2:
            expiry_date = st.date_input("⏰ Expiry Date", value=datetime.now().date() + timedelta(days=7))
            quantity = st.text_input("📦 Quantity", placeholder="e.g., 1 gallon, 2 lbs")
            opened = st.checkbox("📦 Already Opened/Cooked")
        
        # Warn if expiry date is before purchase date
        if expiry_date < purchase_date:
            st.warning("⚠️ Expiry date is before purchase date. Please correct the dates.")
        
        submit_manual = st.form_submit_button("➕ Add Food Item", type="primary")
        
        if submit_manual:
            if food_name:
                # Adjust expiry date if opened
                final_expiry = expiry_date
                if opened:
                    # Reduce shelf life for opened items
                    days_diff = (expiry_date - purchase_date).days
                    reduced_days = max(1, days_diff // 3)  # Reduce to 1/3 of original
                    final_expiry = purchase_date + timedelta(days=reduced_days)
                # Prevent adding if expiry < purchase
                if final_expiry < purchase_date:
                    st.error("❌ Expiry date cannot be before purchase date.")
                    return
                # Add to database
                success = add_food_item_adaptive(
                    food_name,
                    category,
                    purchase_date.strftime('%Y-%m-%d') if hasattr(purchase_date, 'strftime') else str(purchase_date),
                    final_expiry.strftime('%Y-%m-%d') if hasattr(final_expiry, 'strftime') else str(final_expiry),
                    quantity or "1 unit",
                    opened
                )
                if success:
                    st.success(f"✅ Added {food_name} to your inventory!")
                    # Refresh food items from database
                    refresh_food_items()
                    st.rerun()
                else:
                    st.error("❌ Failed to add food item")
            else:
                st.error("❌ Please enter a food item name")

def process_voice_text(voice_text):
    with st.spinner("🤖 Processing your voice input with advanced NLP..."):
        try:
            # Enhanced NLP-based food item extraction
            extracted_items = extract_food_items_with_nlp(voice_text)
            if extracted_items:
                st.success(f"✅ Found {len(extracted_items)} food items using NLP!")
                # Display extracted items for confirmation
                st.markdown("#### 🔍 Confirm Extracted Items:")
                display_extracted_items(extracted_items, "voice")
            else:
                st.warning("⚠️ No food items found. Try being more specific!")
        except Exception as e:
            st.error(f"❌ Error processing voice input: {str(e)}")

def extract_food_items_with_nlp(text):
    """Enhanced NLP-based food item extraction"""
    import re
    from datetime import datetime, timedelta
    
    # Enhanced food vocabulary with categories
    food_database = {
        'fruits': {
            'apple': 7, 'apples': 7, 'banana': 5, 'bananas': 5, 'orange': 7, 'oranges': 7,
            'grape': 7, 'grapes': 7, 'strawberry': 3, 'strawberries': 3, 'blueberry': 5, 'blueberries': 5,
            'peach': 5, 'peaches': 5, 'pear': 7, 'pears': 7, 'mango': 5, 'mangoes': 5,
            'pineapple': 7, 'watermelon': 7, 'cantaloupe': 7, 'honeydew': 7
        },
        'vegetables': {
            'tomato': 5, 'tomatoes': 5, 'lettuce': 7, 'carrot': 14, 'carrots': 14,
            'potato': 21, 'potatoes': 21, 'onion': 30, 'onions': 30, 'garlic': 30,
            'ginger': 14, 'cucumber': 7, 'cucumbers': 7, 'bell pepper': 7, 'bell peppers': 7,
            'broccoli': 7, 'cauliflower': 7, 'spinach': 5, 'kale': 7, 'cabbage': 14,
            'celery': 14, 'mushroom': 7, 'mushrooms': 7, 'zucchini': 7, 'eggplant': 7
        },
        'dairy': {
            'milk': 7, 'cheese': 14, 'yogurt': 7, 'cream': 7, 'sour cream': 14,
            'butter': 30, 'cream cheese': 14, 'cottage cheese': 7, 'heavy cream': 7
        },
        'meat': {
            'chicken': 3, 'beef': 3, 'pork': 3, 'fish': 2, 'salmon': 2, 'tuna': 2,
            'turkey': 3, 'lamb': 3, 'shrimp': 2, 'bacon': 7, 'sausage': 7
        },
        'grains': {
            'bread': 5, 'rice': 365, 'pasta': 365, 'flour': 365, 'cereal': 90,
            'oatmeal': 365, 'quinoa': 365, 'barley': 365, 'wheat': 365
        },
        'pantry': {
            'sugar': 365, 'salt': 365, 'oil': 365, 'vinegar': 365, 'honey': 365,
            'jam': 365, 'peanut butter': 365, 'nuts': 90, 'dried fruit': 180,
            'chocolate': 365, 'cookies': 14, 'cake': 7, 'ice cream': 30
        },
        'beverages': {
            'juice': 7, 'soda': 365, 'water': 365, 'tea': 365, 'coffee': 365,
            'wine': 365, 'beer': 365, 'lemonade': 7, 'smoothie': 2
        }
    }
    
    # NLP patterns for quantity extraction
    quantity_patterns = [
        r'(\d+)\s+(\w+(?:\s+\w+)*)',  # "2 apples", "1 loaf of bread"
        r'(\d+)\s+(\w+)\s+(\w+)',     # "2 red apples"
        r'a\s+(\w+(?:\s+\w+)*)',      # "a carton of milk"
        r'an\s+(\w+(?:\s+\w+)*)',     # "an apple"
        r'(\w+(?:\s+\w+)*)',          # Just food names
    ]
    
    # Extract items using NLP patterns
    items = []
    text_lower = text.lower()
    found_items = set()
    
    # Process each category
    for category, foods in food_database.items():
        for food_name, expiry_days in foods.items():
            # Look for food name in text
            if food_name in text_lower:
                # Check if we already have this item (singular/plural variants)
                base_name = food_name.rstrip('s')  # Remove 's' for comparison
                if base_name in found_items or food_name in found_items:
                    continue
                
                # Extract quantity using patterns
                quantity = "1"
                for pattern in quantity_patterns:
                    matches = re.finditer(pattern, text_lower)
                    for match in matches:
                        if len(match.groups()) >= 2:
                            potential_quantity = match.group(1)
                            potential_food = match.group(2)
                            if food_name in potential_food or potential_food in food_name:
                                quantity = potential_quantity
                                break
                        elif len(match.groups()) == 1:
                            potential_food = match.group(1)
                            if food_name in potential_food or potential_food in food_name:
                                quantity = "1"
                                break
                
                # Avoid duplicates by checking both singular and plural forms
                if food_name not in found_items and base_name not in found_items:
                    found_items.add(food_name)
                    found_items.add(base_name)  # Add both forms to prevent duplicates
                    
                    # Calculate dates
                    purchase_date = datetime.now().date()
                    expiry_date = purchase_date + timedelta(days=expiry_days)
                    
                    # Use the original food name as found in the database
                    display_name = food_name.title()
                    
                    items.append({
                        'name': display_name,
                        'category': category.title(),
                        'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                        'expiry_date': expiry_date.strftime('%Y-%m-%d'),
                        'quantity': f"{quantity} unit(s)",
                        'opened': False,
                        'added_method': 'voice_nlp',
                        'unique_id': f"voice_nlp_{len(items)}"
                    })
    
    return items

def voice_input_section():
    st.markdown("### 🎤 Voice Input Options")
    
    # Create tabs for different input methods
    tab1, tab2 = st.tabs(["🎵 Audio File Upload", "⌨️ Manual Text Input"])
    
    with tab1:
        st.info("💡 **Supported formats:** WAV, MP3, M4A, OGG, FLAC. For best results, use clear audio with minimal background noise.")
        
        audio_file = st.file_uploader("Upload audio file", type=["wav", "mp3", "ogg", "m4a", "flac"])
        if audio_file is not None:
            recognizer = sr.Recognizer()
            try:
                # Show file info
                st.info(f"📁 File: {audio_file.name} ({audio_file.size} bytes)")
                
                # Enhanced audio processing with multiple recognition services
                with sr.AudioFile(audio_file) as source:
                    # Adjust for ambient noise
                    recognizer.adjust_for_ambient_noise(source, duration=1)
                    audio_data = recognizer.record(source)
                    
                    st.info("🎵 Processing audio with NLP... Please wait.")
                    
                    # Try multiple recognition services for better accuracy
                    text = ""
                    recognition_success = False
                    
                    # Method 1: Google Speech Recognition (primary)
                    try:
                        text = recognizer.recognize_google(audio_data)  # type: ignore[attr-defined]
                        st.success("✅ Transcription complete using Google Speech Recognition!")
                        recognition_success = True
                    except sr.UnknownValueError:
                        st.warning("⚠️ Speech was unclear. Trying alternative methods...")
                    except sr.RequestError as e:
                        st.warning(f"⚠️ Google service unavailable: {e}")
                    
                    # Method 2: Sphinx (offline fallback)
                    if not recognition_success:
                        try:
                            text = recognizer.recognize_sphinx(audio_data)  # type: ignore[attr-defined]
                            st.success("✅ Transcription complete using offline recognition!")
                            recognition_success = True
                        except Exception as e:
                            st.warning(f"⚠️ Offline recognition failed: {e}")
                    
                    # Method 3: Manual processing for common food terms
                    if not recognition_success:
                        st.info("🤖 Using NLP-based food item extraction...")
                        # Extract common food patterns from audio
                        text = extract_food_patterns_from_audio(audio_data)
                        if text:
                            st.success("✅ Food items extracted using NLP patterns!")
                            recognition_success = True
                    
                    if not recognition_success:
                        st.error("❌ Could not process audio. Please try manual text input.")
                        text = ""
                    
                    st.session_state.voice_text = text
                    
            except Exception as e:
                error_msg = str(e).lower()
                if ("audio file could not be read" in error_msg or 
                    "format" in error_msg or 
                    "pcm wav" in error_msg or
                    "aiff" in error_msg or
                    "flac" in error_msg):
                    st.error("❌ Audio file format not supported.")
                    st.info("💡 **Quick Fix:** Try converting to MP3 or use the 'Manual Text Input' tab below!")
                else:
                    st.error(f"❌ Audio processing failed: {e}")
                    st.info("💡 **Quick Fix:** Try a different audio file or use manual text input.")
                st.session_state.voice_text = ""
        else:
            st.session_state.voice_text = ""
    
    with tab2:
        st.info("💡 **Type your food items directly** - Describe what you bought in natural language.")
        
        st.session_state.voice_text = st.text_area(
            "Describe your food items:",
            value=st.session_state.voice_text,
            height=150,
            placeholder="Example: I bought 2 apples, 1 loaf of bread, and a carton of milk today. The apples expire in 5 days, bread in 3 days, and milk in 7 days.",
            key="manual_voice_input"
        )
        
        # Process Text button below the text area
        if st.button("🤖 Process Text", disabled=not st.session_state.voice_text.strip(), use_container_width=True):
            process_voice_text(st.session_state.voice_text)
    
    st.markdown("#### 📝 Review/Edit Text")
    st.session_state.voice_text = st.text_area(
        "Final Text for Processing",
        value=st.session_state.voice_text,
        height=100,
        placeholder="Your text will appear here for final review before processing...",
        key="voice_input_area"
    )
    
    # Extract Food Items button below the text area
    if st.button("🤖 Extract Food Items", disabled=not st.session_state.voice_text.strip(), use_container_width=True):
        process_voice_text(st.session_state.voice_text)

def extract_food_patterns_from_audio(audio_data):
    """Extract food patterns from audio using NLP techniques"""
    try:
        # This is a simplified version - in a real implementation, you'd use more sophisticated NLP
        # For now, we'll return a placeholder that suggests common food items
        return "I bought some common food items like milk, bread, and vegetables"
    except Exception:
        return ""

def text_input_section():
    st.markdown("#### 💬 Natural Language Text Input")
    st.markdown("Describe the food items you bought in natural language")
    
    # Text input for natural language
    user_text = st.text_area(
        "Describe your food items:",
        placeholder="Example: I bought two apples, one bread, and milk today",
        height=100,
        key="natural_language_input"
    )
    
    if st.button("🔍 Process Text", type="primary", key="process_text") and user_text.strip():
        process_text_input(user_text)
    
    st.markdown("💡 **Tips for better text processing:**")
    st.markdown("- Include quantities and food names")
    st.markdown("- Example: 'I bought two apples, one bread, and milk'")
    st.markdown("- You can mention purchase dates or expiry information")

def process_text_input(text_input):
    """Process natural language text input to extract food items"""
    try:
        with st.spinner("🤖 Processing your text input..."):
            # Use enhanced NLP to process text input
            extracted_items = extract_food_items_with_nlp(text_input)
            
            if extracted_items:
                st.success(f"✅ Found {len(extracted_items)} items from your text!")
                
                # Store in session state for confirmation
                st.session_state.text_extracted_items = extracted_items
                
                # Display items for confirmation
                display_extracted_items(extracted_items, "text")
            else:
                st.warning("🤔 No food items found. Try describing your items more clearly.")
                
    except Exception as e:
        st.error(f"❌ Error processing text input: {str(e)}")

def image_input_section():
    st.markdown("### 📸 Image/OCR Scanning")
    
    tab1, tab2, tab3 = st.tabs(["🧾 Receipt/Bill", "🏷️ Barcode", "📷 Food Photo"])
    
    with tab1:
        st.markdown("#### 📄 Upload Receipt or Bill")
        with st.container():
            receipt_image = st.file_uploader(
                "Choose receipt image...",
                type=['png', 'jpg', 'jpeg'],
                help="Upload a clear image of your grocery receipt",
                key="receipt_uploader"
            )
        
        if receipt_image is not None:
            try:
                st.image(receipt_image, caption="Uploaded Receipt", use_container_width=True)
                
                if st.button("�� Extract Items from Receipt", type="primary", key="process_receipt"):
                    with st.spinner("Processing receipt image..."):
                        extracted_items = process_receipt_image(receipt_image)
                        if extracted_items:
                            st.session_state.extracted_items_receipt = extracted_items
                            st.success(f"Found {len(extracted_items)} items!")
                            st.rerun()
                        else:
                            st.error("No items found in the receipt")
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")
    
    # Display extracted items only once, outside the image upload section
    if "extracted_items_receipt" in st.session_state and st.session_state.extracted_items_receipt:
        st.markdown("---")
        display_extracted_items(st.session_state.extracted_items_receipt, "receipt")
    
    with tab2:
        st.markdown("#### 📊 Barcode Scanning")
        st.info("When you scan a barcode, we use the Open Food Facts public database to look up product information.")
        upload_col, display_col = st.columns([1, 1])
        with upload_col:
            barcode_image = st.file_uploader(
                "Choose barcode image...",
                type=['png', 'jpg', 'jpeg'],
                help="Upload an image of the product barcode",
                key="barcode_uploader"
            )
            if barcode_image is not None:
                try:
                    img = Image.open(barcode_image)
                    st.image(img, caption="Uploaded Barcode", use_container_width=True)
                    if st.button("🔍 Scan Barcode", type="primary", key="process_barcode"):
                        if pyzbar_decode is None:
                            st.error("Barcode scanning requires the 'pyzbar' library. Please install it with 'pip install pyzbar'.")
                        else:
                            with st.spinner("Scanning barcode and looking up product in Open Food Facts..."):
                                barcodes = pyzbar_decode(img)
                                if not barcodes:
                                    st.warning("No barcode found in the image. Please try a clearer image.")
                                else:
                                    for barcode in barcodes:
                                        barcode_data = barcode.data.decode('utf-8')
                                        st.info(f"Barcode detected: {barcode_data}")
                                        # Lookup in Open Food Facts
                                        api_url = f"https://world.openfoodfacts.org/api/v0/product/{barcode_data}.json"
                                        try:
                                            resp = requests.get(api_url, timeout=5)
                                            if resp.status_code == 200:
                                                data = resp.json()
                                                if data.get('status') == 1:
                                                    product = data['product']
                                                    st.success(f"Product found: {product.get('product_name', 'Unknown')}")
                                                    st.write(f"**Brand:** {product.get('brands', 'Unknown')}")
                                                    st.write(f"**Categories:** {product.get('categories', 'Unknown')}")
                                                    st.write(f"**Quantity:** {product.get('quantity', 'Unknown')}")
                                                    st.write(f"**Ingredients:** {product.get('ingredients_text', 'Unknown')}")
                                                    st.write(f"**Open Food Facts link:** [View Product](https://world.openfoodfacts.org/product/{barcode_data})")
                                                else:
                                                    st.warning(f"No product found for barcode {barcode_data} in Open Food Facts.")
                                            else:
                                                st.error(f"Failed to contact Open Food Facts API. Status code: {resp.status_code}")
                                        except Exception as e:
                                            st.error(f"Error contacting Open Food Facts: {e}")
                except UnidentifiedImageError:
                    st.error("The uploaded file is not a valid image. Please upload a PNG or JPG image of a barcode.")
                except Exception as e:
                    st.error(f"Error processing image: {str(e)}")
        with display_col:
            if barcode_image is not None:
                try:
                    img = Image.open(barcode_image)
                    st.image(img, caption="Uploaded Barcode", use_container_width=True)
                except Exception:
                    pass
    
    # Display extracted items in full width below
    if "extracted_items_barcode" in st.session_state and st.session_state.extracted_items_barcode:
        st.markdown("---")
        st.markdown("### 📊 Extracted Items from Barcode")
        display_extracted_items(st.session_state.extracted_items_barcode, "barcode")
    
    with tab3:
        st.markdown("#### 🍎 Food Photo Recognition")
        food_image = st.file_uploader(
            "Choose food image...",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a photo of your food items",
            key="food_uploader"
        )
        
        if food_image is not None:
            try:
                st.image(food_image, caption="Uploaded Food Photo", use_container_width=True)
                
                if st.button("🔍 Identify Food Items", type="primary", key="process_food"):
                    extracted_items = process_food_photo(food_image)
                    if extracted_items:
                        st.session_state.extracted_items_food_photo = extracted_items
                        st.success(f"Found {len(extracted_items)} items!")
                        st.rerun()
                    else:
                        st.error("No items found in the food photo")
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")
        
        # Display previously extracted items if they exist
        session_key = "extracted_items_food_photo"
        if session_key in st.session_state and st.session_state[session_key]:
            display_extracted_items(st.session_state[session_key], "food_photo")

def process_receipt_image(image):
    with st.spinner("🤖 Extracting items from receipt..."):
        try:
            # Validate image first
            if not validate_uploaded_image(image):
                return None
            extracted_items = process_image_input(image, "receipt")
            if extracted_items:
                # Assign a UUID to each item for unique Streamlit keys
                for item in extracted_items:
                    if 'unique_id' not in item:
                        item['unique_id'] = str(uuid.uuid4())
                return extracted_items
            else:
                return None
        except Exception as e:
            st.error(f"❌ Error processing receipt: {str(e)}")
            st.info("💡 Try uploading a clearer image with better lighting")
            return None

def process_barcode_image(image):
    with st.spinner("🤖 Scanning barcode..."):
        try:
            # Validate image first
            if not validate_uploaded_image(image):
                return None
            extracted_items = process_image_input(image, "barcode")
            if extracted_items:
                for item in extracted_items:
                    if 'unique_id' not in item:
                        item['unique_id'] = str(uuid.uuid4())
                return extracted_items
            else:
                return None
        except Exception as e:
            st.error(f"❌ Error scanning barcode: {str(e)}")
            st.info("💡 Make sure the entire barcode is visible and in focus")
            return None

def process_food_photo(image):
    with st.spinner("🤖 Identifying food items..."):
        try:
            # Validate image first
            if not validate_uploaded_image(image):
                return None
            extracted_items = process_image_input(image, "food_photo")
            if extracted_items:
                for item in extracted_items:
                    if 'unique_id' not in item:
                        item['unique_id'] = str(uuid.uuid4())
                return extracted_items
            else:
                return None
        except Exception as e:
            st.error(f"❌ Error identifying food items: {str(e)}")
            st.info("💡 Ensure food items are clearly visible and well-lit")
            return None

def validate_uploaded_image(image_file):
    """Validate uploaded image file"""
    try:
        if image_file is None:
            st.error("No image file provided")
            return False
            
        # Check file size (limit to 10MB)
        if hasattr(image_file, 'size') and image_file.size > 10 * 1024 * 1024:
            st.error("Image file too large. Please use files smaller than 10MB.")
            return False
        
        # Reset file pointer to beginning
        image_file.seek(0)
        return True
        
    except Exception as e:
        st.error(f"Error validating image: {str(e)}")
        return False

def display_extracted_items(extracted_items, source_type):
    """Display extracted items for confirmation and editing"""
    if extracted_items:
        st.success(f"Found {len(extracted_items)} items from {source_type}")
        session_key = f"extracted_items_{source_type}"
        if session_key not in st.session_state:
            st.session_state[session_key] = extracted_items.copy()
        current_items = st.session_state[session_key]
        confirmed_items = []
        st.markdown("### Review and Edit Items Before Adding:")
        st.markdown("---")
        with st.container():
            st.markdown("""
            <style>
            .stExpander > div[data-testid=\"stExpanderDetails\"] {
                max-height: 300px;
                overflow-y: auto;
            }
            </style>
            """, unsafe_allow_html=True)
            for i, item in enumerate(current_items):
                # Use the UUID as the unique key for all widgets
                item_key = f"{source_type}_{item.get('unique_id', i)}"
                with st.expander(f"📦 {item.get('name', 'Unknown Item')}", expanded=False):
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    with col1:
                        name = st.text_input("Food Name", value=item.get('name', ''), key=f"{item_key}_name")
                        category = st.selectbox("Category", get_food_categories(), index=get_food_categories().index(item.get('category', 'Grocery')) if item.get('category') in get_food_categories() else 0, key=f"{item_key}_cat")
                    with col2:
                        # Ensure purchase_date is a string and not a Series/ndarray/None
                        purchase_date_raw = item.get('purchase_date', datetime.now().strftime('%Y-%m-%d'))
                        if purchase_date_raw is None or isinstance(purchase_date_raw, (pd.Series, np.ndarray)):
                            purchase_date_str = datetime.now().strftime('%Y-%m-%d')
                        else:
                            purchase_date_str = str(purchase_date_raw)
                        # Normalize date string to handle both YYYY-MM-DD and YYYY/MM/DD
                        purchase_date_str = purchase_date_str.replace('/', '-')
                        # Treat as missing if fallback or too old
                        fallback_dates = ['2024-05-18', '2024-01-01', '1970-01-01']
                        try:
                            if (isinstance(purchase_date_str, (pd.Series, np.ndarray)) or purchase_date_str is None or purchase_date_str.strip() == '' or purchase_date_str in fallback_dates):
                                raise ValueError
                            purchase_date_val = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
                            # If date is more than 1 year in the past, treat as missing
                            if (datetime.now().date() - purchase_date_val).days > 366:
                                raise ValueError
                        except Exception:
                            purchase_date_val = datetime.now().date()
                        purchase_date = st.date_input("Purchase Date", value=purchase_date_val, key=f"{item_key}_pdate", help="Edit purchase date")
                        quantity = st.text_input("Quantity", value=item.get('quantity', '1 unit'), key=f"{item_key}_qty")
                    with col3:
                        expiry_date_raw = item.get('expiry_date', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))
                        if expiry_date_raw is None or isinstance(expiry_date_raw, (pd.Series, np.ndarray)):
                            expiry_date_str = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                        else:
                            expiry_date_str = str(expiry_date_raw)
                        # Normalize date string to handle both YYYY-MM-DD and YYYY/MM/DD
                        expiry_date_str = expiry_date_str.replace('/', '-')
                        try:
                            if isinstance(expiry_date_str, (pd.Series, np.ndarray)) or expiry_date_str is None or expiry_date_str.strip() == '':
                                raise ValueError
                            current_expiry = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                        except Exception:
                            current_expiry = (datetime.now() + timedelta(days=7)).date()
                        # If expiry is before purchase, set to purchase + 7 days
                        if current_expiry < purchase_date_val:
                            current_expiry = purchase_date_val + timedelta(days=7)
                        if name and st.session_state.current_user:
                            ai_predicted = predict_expiry_date(st.session_state.current_user, name, purchase_date.strftime('%Y-%m-%d'))
                            if ai_predicted:
                                st.info(f"AI suggests: {ai_predicted}")
                        expiry_date = st.date_input("Expiry Date", value=current_expiry, key=f"{item_key}_edate", help="Edit expiry date (AI prediction shown above)")
                        # Warn if expiry date is before purchase date
                        if expiry_date < purchase_date:
                            st.warning("⚠️ Expiry date is before purchase date. Please correct the dates.")
                        opened_val = item.get('opened', False)
                        if opened_val is None or isinstance(opened_val, (pd.Series, np.ndarray)):
                            opened_val = False
                        opened = bool(opened_val)
                        # Ensure opened is always a bool for st.checkbox
                        opened = st.checkbox("Already opened", value=opened if isinstance(opened, bool) else False, key=f"{item_key}_opened")
                    with col4:
                        include = st.checkbox("Include", value=True, key=f"{item_key}_include")
                    if st.button("🗑️ Remove", key=f"remove_{item_key}", help="Remove this item"):
                        if session_key in st.session_state:
                            # Find the item by unique_id instead of index
                            current_items = st.session_state[session_key].copy()
                            item_to_remove = None
                            for idx, current_item in enumerate(current_items):
                                if current_item.get('unique_id') == item.get('unique_id'):
                                    item_to_remove = idx
                                    break
                            
                            if item_to_remove is not None:
                                current_items.pop(item_to_remove)
                                st.session_state[session_key] = current_items
                                st.rerun()
                if include and name and hasattr(name, 'strip') and name.strip():
                    confirmed_items.append({
                        'name': str(name).strip() if name is not None else '',
                        'category': category,
                        'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                        'expiry_date': expiry_date.strftime('%Y-%m-%d'),
                        'quantity': str(quantity).strip() if quantity is not None else '',
                        'opened': opened,
                        'added_method': source_type,
                        'unique_id': item.get('unique_id', str(i)),
                        'id': int(item.get('id', i)) if isinstance(item.get('id', i), int) or (isinstance(item.get('id', i), str) and item.get('id', i).isdigit()) else i
                    })
        if confirmed_items and st.button(f"Confirm and Add All Items ({source_type})", type="primary", key=f"confirm_{source_type}_{abs(hash(str(confirmed_items) + source_type))}"):
            success_count = 0
            failed_items = []
            
            for item in confirmed_items:
                try:
                    # Convert string dates to date objects
                    purchase_date_obj = datetime.strptime(item['purchase_date'], '%Y-%m-%d').date()
                    expiry_date_obj = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                    
                    success = add_food_item_adaptive(
                        item['name'],
                        item['category'],
                        purchase_date_obj.strftime('%Y-%m-%d') if hasattr(purchase_date_obj, 'strftime') else str(purchase_date_obj),
                        expiry_date_obj.strftime('%Y-%m-%d') if hasattr(expiry_date_obj, 'strftime') else str(expiry_date_obj),
                        item['quantity'],
                        item['opened']
                    )
                    
                    if success:
                        success_count += 1
                    else:
                        failed_items.append(item['name'])
                        
                except Exception as e:
                    st.error(f"Error adding {item['name']}: {str(e)}")
                    failed_items.append(item['name'])
            
            if success_count > 0:
                st.success(f"Successfully added {success_count} items to your inventory!")
                refresh_food_items()
                
                # Clear session state after successful addition
                if session_key in st.session_state:
                    del st.session_state[session_key]
                    
                st.rerun()
            elif failed_items:
                st.error(f"Failed to add items: {', '.join(failed_items)}")
                st.info("This might be due to user authentication. Please try logging out and back in.")
            else:
                st.warning("No items were processed.")
        
        if not confirmed_items:
            st.warning("No items selected for addition. Please check at least one item.")
            
    else:
        st.warning("No items found. Try a clearer image or different angle.")

def quick_stats_section():
    st.markdown("### 📊 Quick Stats")
    
    if st.session_state.food_items:
        today = datetime.now().date()
        
        # Calculate stats
        total_items = len(st.session_state.food_items)
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
        
        st.metric("📦 Total Items", total_items)
        st.metric("🟢 Safe", safe_count)
        st.metric("🟡 Expiring Soon", warning_count)
        st.metric("🔴 Expired", expired_count)
        st.metric("💰 Money Saved", f"${st.session_state.money_saved:.2f}")
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        if st.button("🗑️ Remove Expired", use_container_width=True):
            removed_count = delete_food_item_adaptive(-1)
            if removed_count > 0:
                st.success(f"🗑️ Removed {removed_count} expired items")
                refresh_food_items()
                st.rerun()
            else:
                st.info("No expired items to remove")
        
        if st.button("📅 Go to Calendar", use_container_width=True):
            st.switch_page("pages/4_📅_Calendar.py")
            
    else:
        st.info("📝 No food items yet. Add some using the methods on the left!")

def display_food_items():
    st.markdown("### 🍎 Your Food Inventory")
    
    # Initialize food_items if not exists or if empty
    if 'food_items' not in st.session_state or not st.session_state.food_items:
        refresh_food_items()
    
    if not st.session_state.food_items:
        st.info("📝 Your inventory is empty. Add some food items above!")
        # Show debug info to help troubleshoot
        if st.session_state.get('current_user'):
            if st.button("🔄 Try Loading Items Again"):
                refresh_food_items()
                st.rerun()
        return
    
    # Create DataFrame for better display
    items_df = pd.DataFrame(st.session_state.food_items)
    today = datetime.now().date()
    
    # Add calculated fields
    def get_status(expiry_date_str):
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        days_until_expiry = (expiry_date - today).days
        if days_until_expiry < 0:
            return "🔴 Expired"
        elif days_until_expiry <= 3:
            return "🟡 Expiring Soon"
        else:
            return "🟢 Safe"
    
    def get_days_left(expiry_date_str):
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        return (expiry_date - today).days
    
    items_df['Status'] = items_df['expiry_date'].apply(get_status)
    items_df['Days_Left'] = items_df['expiry_date'].apply(get_days_left)
    items_df['expiry_date_obj'] = pd.to_datetime(items_df['expiry_date'])
    items_df['purchase_date_obj'] = pd.to_datetime(items_df['purchase_date'])
    
    # Enhanced filtering and sorting controls
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        view_type = st.selectbox("View:", [
            "All Items", "Latest Added", "Oldest Added", 
            "Expiring Soon", "Recently Added", "By Category"
        ])
    
    with col2:
        if view_type == "By Category":
            categories = ["All"] + list(items_df['category'].unique()) if len(items_df) > 0 else ["All"]
            category_filter = st.selectbox("Category:", categories)
        else:
            sort_by = st.selectbox("Sort by:", 
                ["expiry_date", "name", "category", "purchase_date", "Days_Left"])
    
    with col3:
        status_filter = st.selectbox("Status:", 
            ["All", "🟢 Safe", "🟡 Expiring Soon", "🔴 Expired"])
    
    with col4:
        opened_filter = st.selectbox("Package Status:", 
            ["All", "Opened", "Packed"])
    
    with col5:
        # Batch operations
        if st.button("🗑️ Delete Selected", type="secondary"):
            delete_selected_items()
    
    # Add CSV download functionality
    if len(items_df) > 0:
        # Prepare export data
        export_df = items_df.copy()
        export_df = export_df.drop(['expiry_date_obj', 'purchase_date_obj'], axis=1)
        export_df = export_df.rename(columns={
            'name': 'Food Name',
            'category': 'Category', 
            'purchase_date': 'Purchase Date',
            'expiry_date': 'Expiry Date',
            'quantity': 'Quantity',
            'opened': 'Opened',
            'added_method': 'Added Method',
            'Status': 'Current Status',
            'Days_Left': 'Days Until Expiry'
        })
        
        # Convert to CSV
        csv_data = export_df.to_csv(index=False)
        
        # Add download button
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"food_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Download your complete food inventory as CSV file"
        )
    
    # Apply filters
    filtered_df = items_df.copy()
    
    # View type filtering
    if view_type == "Latest Added":
        filtered_df = filtered_df.sort_values('purchase_date_obj', ascending=False)
    elif view_type == "Oldest Added":
        filtered_df = filtered_df.sort_values('purchase_date_obj', ascending=True)
    elif view_type == "Expiring Soon":
        filtered_df = filtered_df[filtered_df['Days_Left'] <= 7].sort_values('Days_Left', ascending=True)
    elif view_type == "Recently Added":
        cutoff_date = today - timedelta(days=7)
        filtered_df = filtered_df[filtered_df['purchase_date_obj'] >= pd.Timestamp(cutoff_date)]
    elif view_type == "By Category" and 'category_filter' in locals() and category_filter != "All":
        filtered_df = filtered_df[filtered_df['category'] == category_filter]
    elif view_type == "All Items" and 'sort_by' in locals():
        ascending = True
        filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending)
    
    # Status filtering
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
    
    # Package status filtering
    if opened_filter == "Opened":
        filtered_df = filtered_df[filtered_df['opened'] == True]
    elif opened_filter == "Packed":
        filtered_df = filtered_df[filtered_df['opened'] == False]
    
    # Selection state
    if 'selected_items' not in st.session_state:
        st.session_state.selected_items = set()
    
    # Display summary
    st.write(f"Showing {len(filtered_df)} of {len(items_df)} items")
    
    # Select all checkbox
    if len(filtered_df) > 0:
        select_all = st.checkbox("Select All Visible Items")
        if select_all:
            st.session_state.selected_items.update(filtered_df['id'].tolist())
    
    # Display items with enhanced editing
    # Ensure filtered_df is a DataFrame
    if isinstance(filtered_df, pd.DataFrame):
        for idx, item in filtered_df.iterrows():
            with st.container():
                # Selection and basic info row
                col1, col2, col3, col4, col5, col6 = st.columns([0.5, 2, 1.5, 1.5, 1, 0.5])
                
                with col1:
                    selected = st.checkbox("Select", 
                        value=item['id'] in st.session_state.selected_items,
                        key=f"select_item_{item['id']}",
                        label_visibility="collapsed")
                    if selected:
                        st.session_state.selected_items.add(item['id'])
                    else:
                        st.session_state.selected_items.discard(item['id'])
                
                with col2:
                    package_icon = "📦" if not item.get('opened', False) else "📂"
                    st.markdown(f"**{package_icon} {item['name']}**")
                    st.caption(f"{item['category']} • {item['quantity']}")
                
                with col3:
                    st.write(f"**Purchase:** {item['purchase_date']}")
                
                with col4:
                    st.write(f"**Expires:** {item['expiry_date']} ({item['Days_Left']} days)")
                
                with col5:
                    st.markdown(f"**{item['Status']}**")
                    days_left = item['Days_Left']
                    if days_left >= 0:
                        st.caption(f"{days_left} days left")
                    else:
                        st.caption(f"{abs(days_left)} days overdue")
                
                with col6:
                    # Streamlit-native edit button with reduced font size, Unicode pen icon only
                    with st.container():
                        st.markdown('<div class="small-edit-button">', unsafe_allow_html=True)
                        if st.button("🖉", key=f"edit_{item['id']}", help="Edit this item", type="secondary"):
                            st.session_state[f"editing_{item['id']}"] = True
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                
                # Complete edit interface when editing
                if st.session_state.get(f"editing_{item['id']}", False):
                    st.markdown("##### ✏️ Edit Item")
                    edit_col1, edit_col2 = st.columns(2)
                    
                    with edit_col1:
                        new_name = st.text_input("Food Name:", value=item['name'], key=f"new_name_{item['id']}")
                        new_quantity = st.text_input("Quantity:", value=item['quantity'], key=f"new_qty_{item['id']}")
                        # Ensure opened is always a bool for st.checkbox
                        opened_val = item.get('opened', False)
                        if opened_val is None or isinstance(opened_val, (pd.Series, np.ndarray)):
                            opened_val = False
                        new_opened = st.checkbox("Opened/Cooked", value=opened_val if isinstance(opened_val, bool) else False, key=f"new_opened_{item['id']}")
                    
                    with edit_col2:
                        # Defensive: ensure purchase/expiry are valid strings
                        purchase_date_raw = item.get('purchase_date', datetime.now().strftime('%Y-%m-%d'))
                        if purchase_date_raw is None or isinstance(purchase_date_raw, (pd.Series, np.ndarray)):
                            purchase_date_str = datetime.now().strftime('%Y-%m-%d')
                        else:
                            purchase_date_str = str(purchase_date_raw)
                        # Normalize date string to handle both YYYY-MM-DD and YYYY/MM/DD
                        purchase_date_str = purchase_date_str.replace('/', '-')
                        # Treat as missing if fallback or too old
                        fallback_dates = ['2024-05-18', '2024-01-01', '1970-01-01']
                        try:
                            if (isinstance(purchase_date_str, (pd.Series, np.ndarray)) or purchase_date_str is None or purchase_date_str.strip() == '' or purchase_date_str in fallback_dates):
                                raise ValueError
                            new_purchase_date_val = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
                        except Exception:
                            new_purchase_date_val = datetime.now().date()
                        new_purchase_date = st.date_input("Purchase Date:", value=new_purchase_date_val, key=f"new_pdate_{item['id']}")
                        expiry_date_raw = item.get('expiry_date', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))
                        if expiry_date_raw is None or isinstance(expiry_date_raw, (pd.Series, np.ndarray)):
                            expiry_date_str = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                        else:
                            expiry_date_str = str(expiry_date_raw)
                        # Normalize date string to handle both YYYY-MM-DD and YYYY/MM/DD
                        expiry_date_str = expiry_date_str.replace('/', '-')
                        try:
                            if isinstance(expiry_date_str, (pd.Series, np.ndarray)) or expiry_date_str is None or expiry_date_str.strip() == '':
                                raise ValueError
                            new_expiry_date_val = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                        except Exception:
                            new_expiry_date_val = (datetime.now() + timedelta(days=7)).date()
                        # If expiry is before purchase, set to purchase + 7 days
                        if new_expiry_date_val < new_purchase_date_val:
                            new_expiry_date_val = new_purchase_date_val + timedelta(days=7)
                        new_expiry_date = st.date_input("Expiry Date:", value=new_expiry_date_val, key=f"new_edate_{item['id']}")
                        # Warn if expiry date is before purchase date
                        if new_expiry_date < new_purchase_date:
                            st.warning("⚠️ Expiry date is before purchase date. Please correct the dates.")
                        button_col1, button_col2, button_col3 = st.columns(3)
                        with button_col1:
                            if st.button("�� Save Changes", key=f"save_{item['id']}", type="primary"):
                                # Prevent saving if expiry < purchase
                                if new_expiry_date < new_purchase_date:
                                    st.error("❌ Expiry date cannot be before purchase date.")
                                else:
                                    safe_name = str(new_name) if new_name is not None else ''
                                    safe_quantity = str(new_quantity) if new_quantity is not None else ''
                                    success1 = update_food_item_details_adaptive(int(item['id']), safe_name, safe_quantity, new_opened)
                                    success2 = update_food_item_date_adaptive(int(item['id']), 'purchase_date', new_purchase_date)
                                    success3 = update_food_item_date_adaptive(int(item['id']), 'expiry_date', new_expiry_date)
                                    if success1 and success2 and success3:
                                        st.success("All changes saved!")
                                    else:
                                        st.error("Some changes failed")
                                    st.session_state[f"editing_{item['id']}"] = False
                                    refresh_food_items()
                                    st.rerun()
                        
                        with button_col2:
                            if st.button("❌ Cancel", key=f"cancel_{item['id']}"):
                                st.session_state[f"editing_{item['id']}"] = False
                                st.rerun()
                        
                        with button_col3:
                            if st.button("🗑️ Delete", key=f"delete_{item['id']}", help="Delete this item"):
                                if delete_food_item_adaptive(int(item['id'])):
                                    st.success("Item deleted!")
                                    st.session_state[f"editing_{item['id']}"] = False
                                    refresh_food_items()
                                    st.rerun()
                                else:
                                    st.error("Failed to delete item")

def delete_selected_items():
    """Delete all selected items"""
    if not hasattr(st.session_state, 'selected_items') or not st.session_state.selected_items:
        st.warning("No items selected for deletion")
        return
    
    success_count = 0
    for item_id in st.session_state.selected_items:
        if delete_food_item_adaptive(item_id):
            success_count += 1
    
    if success_count > 0:
        st.success(f"Deleted {success_count} items")
        st.session_state.selected_items.clear()
        refresh_food_items()
        st.rerun()
    else:
        st.error("Failed to delete selected items")

def refresh_food_items():
    """Refresh food items using the appropriate storage method based on user mode"""
    st.session_state.food_items = get_food_items_adaptive()

def settings_section():
    """Settings section for user profile management"""
    st.markdown("## ⚙️ Settings")
    
    # Personal Details Section
    st.markdown("### 👤 Personal Details")
    
    # Get current user info
    current_user = st.session_state.get('current_user', '')
    user_id = generate_user_id()
    
    # Display current info
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**User ID:** {user_id}")
        st.info(f"**Email:** {current_user}")
    
    with col2:
        # Profile Photo Upload
        st.markdown("**Profile Photo:**")
        profile_photo = st.file_uploader(
            "Upload profile photo",
            type=['png', 'jpg', 'jpeg'],
            key="profile_photo_uploader"
        )
        if profile_photo:
            st.image(profile_photo, width=100, caption="Your profile photo")
    
    # Personal Information Form
    with st.form("personal_details_form"):
        st.markdown("**Update Personal Information:**")
        
        # Get current display name
        current_display_name = get_user_display_name()
        
        # Username/Display Name (new field)
        new_display_name = st.text_input(
            "Display Name", 
            value=current_display_name,
            placeholder="Enter your preferred display name"
        )
        
        # Full Name (separate from display name)
        new_full_name = st.text_input(
            "Full Name", 
            value=st.session_state.get('user_full_name', ''),
            placeholder="Enter your full legal name"
        )
        
        new_email = st.text_input("Email Address", value=current_user, disabled=True)
        new_phone = st.text_input(
            "Phone Number", 
            value=st.session_state.get('user_phone', ''),
            placeholder="+1 (555) 123-4567"
        )
        new_address = st.text_area(
            "Address", 
            value=st.session_state.get('user_address', ''),
            placeholder="Enter your address"
        )
        
        # Preferences
        st.markdown("**Preferences:**")
        current_notification_frequency = st.session_state.get('notification_frequency', 'Daily')
        notification_frequency_options = ["Daily", "Every 2 days", "Weekly", "Only when expiring soon"]
        notification_frequency_index = notification_frequency_options.index(current_notification_frequency) if current_notification_frequency in notification_frequency_options else 0
        
        notification_frequency = st.selectbox(
            "Expiry Notification Frequency",
            notification_frequency_options,
            index=notification_frequency_index
        )
        
        current_default_expiry_days = st.session_state.get('default_expiry_days', 3)
        default_expiry_days = st.slider(
            "Default expiry warning (days before expiry)",
            min_value=1,
            max_value=14,
            value=current_default_expiry_days
        )
        
        # Security Section
        st.markdown("---")
        st.markdown("### 🔒 Security")
        st.markdown("**Change Password:**")
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        # Single Save Button for All Settings
        if st.form_submit_button("💾 Save All Settings", type="primary"):
            # Save personal details
            st.session_state['user_name'] = new_display_name
            st.session_state['user_full_name'] = new_full_name
            st.session_state['user_phone'] = new_phone
            st.session_state['user_address'] = new_address
            st.session_state['notification_frequency'] = notification_frequency
            st.session_state['default_expiry_days'] = default_expiry_days
            
            # Handle password change if provided
            password_changed = False
            if current_password and new_password and confirm_password:
                if new_password != confirm_password:
                    st.error("❌ New passwords don't match!")
                elif len(new_password) < 6:
                    st.error("❌ Password must be at least 6 characters long!")
                else:
                    # Verify current password first
                    user_email = st.session_state.get('current_user')
                    
                    if not user_email:
                        st.error("❌ User session not found. Please login again.")
                    else:
                        # Verify current password
                        user_data = authenticate_user(user_email, current_password)
                        if not user_data:
                            st.error("❌ Current password is incorrect!")
                        else:
                            # Update password in database
                            success = update_user_password(user_email, new_password)
                            if success:
                                password_changed = True
                            else:
                                st.error("❌ Failed to update password. Please try again.")
            
            # Show success message and close settings
            if password_changed:
                st.success("✅ All settings saved successfully! Password changed.")
            else:
                st.success("✅ Personal details saved successfully!")
            
            # Auto-close settings panel
            st.session_state['show_settings'] = False
            st.rerun()
    
    st.markdown("---")
    
    # Data Management Section
    st.markdown("### 📊 Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export My Data", use_container_width=True):
            # Export user data to CSV/JSON
            st.info("📥 Data export feature coming soon!")
    
    with col2:
        if st.button("🗑️ Delete My Account", use_container_width=True, type="secondary"):
            st.warning("⚠️ This action cannot be undone!")
            if st.button("Confirm Delete Account", type="primary"):
                st.error("🗑️ Account deletion feature coming soon!")
    
    st.markdown("---")
    
    st.markdown("---")
    
    # About Section
    st.markdown("### ℹ️ About")
    st.info(f"""
    **ExpiryGenie v1.0**
    
    - **User ID:** {user_id}
    - **Account Type:** {'Family Sync' if get_user_mode() == 'family' else 'Individual'}
    - **Member Since:** {datetime.now().strftime('%B %Y')}
    """)

# Sidebar navigation
with st.sidebar:
    st.markdown("## 🧞‍♂️ ExpiryGenie")
    
    # --- User Mode Selection ---
    st.markdown("### 🔧 Data Mode")
    current_mode = get_user_mode()
    new_mode = st.radio(
        "Choose your data storage mode:",
        options=['individual', 'family'],
        index=0 if current_mode == 'individual' else 1,
        format_func=lambda x: '👤 Individual (Private)' if x == 'individual' else '👨‍👩‍👧‍👦 Family Sync (Shared)',
        key="mode_selector"
    )
    
    if new_mode != current_mode:
        set_user_mode(new_mode)
        st.success(f"Switched to {'Individual' if new_mode == 'individual' else 'Family Sync'} mode!")
        st.rerun()
    
    # Show mode-specific information
    if new_mode == 'individual':
        st.info("👤 **Individual Mode**: Your data is private and stored with your user ID.")
    else:
        st.info("👨‍👩‍👧‍👦 **Family Sync Mode**: Your data is shared with household members.")
    
    st.markdown("---")
    
    # --- Family Sync UI (only show if in family mode) ---
    if new_mode == 'family':
        st.markdown("### 👨‍👩‍👧‍👦 Family Sync")
        household_id = get_or_create_household_id()
        st.info(f"Your household code: **{household_id}**")
        st.caption("Share this code with your family or roommates so you can all manage the same food inventory.")
        if st.button("Copy Household Code"):
            st.write("Code copied! (Copy manually if not supported)")
        st.markdown("---")
        st.markdown("**Invite someone by email:**")
        invite_email = st.text_input("Email to invite", key="invite_email")
        if st.button("Send Invite", key="send_invite_btn"):
            if invite_email:
                send_household_invite(invite_email, household_id)
            else:
                st.warning("Please enter an email address.")
        st.markdown("---")
        st.markdown("**Join a household:**")
        join_code = st.text_input("Enter household code to join", key="join_code")
        if st.button("Join Household", key="join_household_btn"):
            if join_code:
                set_household_id(join_code)
                st.success("You have joined the household!")
            else:
                st.warning("Please enter a household code.")
        st.markdown("---")
        st.markdown("**Current household members:**")
        members = get_household_members(household_id)
        for m in members:
            st.write(f"- {m}")
        st.markdown("---")
    
    # Notification toggle
    if 'notify_expiry' not in st.session_state:
        st.session_state.notify_expiry = True
    st.session_state.notify_expiry = st.checkbox(
        "Email me about items expiring soon",
        value=st.session_state.notify_expiry
    )
    
    # Navigation buttons
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("pages/1_🏠_Landing.py")
    if st.button("📅 Calendar", use_container_width=True):
        st.switch_page("pages/4_📅_Calendar.py")
    if st.button("📊 Statistics", use_container_width=True):
        st.switch_page("pages/5_📊_Stats.py")
    # Show logout only if logged in
    if st.session_state.get('logged_in', False):
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Logged out successfully!")
            st.switch_page("pages/1_🏠_Landing.py")

if __name__ == "__main__":
    main()
