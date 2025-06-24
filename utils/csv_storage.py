import pandas as pd
import os
import hashlib
from datetime import datetime, date
from typing import List, Dict, Optional, Any
import json

# Data file paths
USERS_CSV = "data/users.csv"
FOOD_ITEMS_CSV = "data/food_items.csv"
DATA_DIR = "data"

def ensure_data_directory():
    """Ensure data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == password_hash

def init_csv_storage():
    """Initialize CSV files with proper headers"""
    try:
        ensure_data_directory()
        
        # Initialize users CSV
        if not os.path.exists(USERS_CSV):
            users_df = pd.DataFrame(columns=[
                'id', 'email', 'name', 'password_hash', 'money_saved', 'created_at'
            ])
            users_df.to_csv(USERS_CSV, index=False)
        
        # Initialize food items CSV
        if not os.path.exists(FOOD_ITEMS_CSV):
            food_items_df = pd.DataFrame(columns=[
                'id', 'user_email', 'name', 'category', 'purchase_date', 
                'expiry_date', 'quantity', 'opened', 'added_method'
            ])
            food_items_df.to_csv(FOOD_ITEMS_CSV, index=False)
        
        return True
    except Exception as e:
        print(f"Error initializing CSV storage: {e}")
        return False

def load_users() -> pd.DataFrame:
    """Load users from CSV"""
    ensure_data_directory()
    if os.path.exists(USERS_CSV):
        return pd.read_csv(USERS_CSV)
    return pd.DataFrame(columns=['id', 'email', 'name', 'password_hash', 'money_saved', 'created_at'])

def save_users(users_df: pd.DataFrame):
    """Save users to CSV"""
    ensure_data_directory()
    users_df.to_csv(USERS_CSV, index=False)

def load_food_items() -> pd.DataFrame:
    """Load food items from CSV"""
    ensure_data_directory()
    if os.path.exists(FOOD_ITEMS_CSV):
        df = pd.read_csv(FOOD_ITEMS_CSV)
        # Convert boolean column if it exists
        if 'opened' in df.columns:
            df['opened'] = df['opened'].astype(bool)
        return df
    return pd.DataFrame(columns=[
        'id', 'user_email', 'name', 'category', 'purchase_date', 
        'expiry_date', 'quantity', 'opened', 'added_method'
    ])

def save_food_items(food_items_df: pd.DataFrame):
    """Save food items to CSV"""
    ensure_data_directory()
    food_items_df.to_csv(FOOD_ITEMS_CSV, index=False)

def get_next_user_id() -> int:
    """Get next available user ID"""
    users_df = load_users()
    if users_df.empty:
        return 1
    return users_df['id'].max() + 1

def get_next_food_item_id() -> int:
    """Get next available food item ID"""
    food_items_df = load_food_items()
    if food_items_df.empty:
        return 1
    return food_items_df['id'].max() + 1

def create_user(name: str, email: str, password: str) -> bool:
    """Create a new user"""
    try:
        users_df = load_users()
        
        # Check if user already exists
        if not users_df.empty and email in users_df['email'].values:
            return False
        
        new_user = {
            'id': get_next_user_id(),
            'email': email.lower(),
            'name': name,
            'password_hash': hash_password(password),
            'money_saved': 0.0,
            'created_at': datetime.now().isoformat()
        }
        
        users_df = pd.concat([users_df, pd.DataFrame([new_user])], ignore_index=True)
        save_users(users_df)
        return True
    except Exception:
        return False

def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """Authenticate user login"""
    try:
        users_df = load_users()
        user_row = users_df[users_df['email'] == email.lower()]
        
        if user_row.empty:
            return None
        
        user = user_row.iloc[0]
        if verify_password(password, user['password_hash']):
            return {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'money_saved': user['money_saved']
            }
        return None
    except Exception:
        return None

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email"""
    try:
        users_df = load_users()
        user_row = users_df[users_df['email'] == email.lower()]
        
        if user_row.empty:
            return None
        
        user = user_row.iloc[0]
        return {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'money_saved': user['money_saved']
        }
    except Exception:
        return None

def add_food_item(user_email: str, name: str, category: str, purchase_date: str, 
                  expiry_date: str, quantity: str = '1 unit', opened: bool = False, 
                  added_method: str = 'manual') -> bool:
    """Add food item to CSV"""
    try:
        food_items_df = load_food_items()
        
        new_item = {
            'id': get_next_food_item_id(),
            'user_email': user_email.lower(),
            'name': name,
            'category': category,
            'purchase_date': purchase_date,
            'expiry_date': expiry_date,
            'quantity': quantity,
            'opened': opened,
            'added_method': added_method
        }
        
        food_items_df = pd.concat([food_items_df, pd.DataFrame([new_item])], ignore_index=True)
        save_food_items(food_items_df)
        return True
    except Exception:
        return False

def get_user_food_items(user_email: str) -> List[Dict]:
    """Get all food items for a user"""
    try:
        food_items_df = load_food_items()
        user_items = food_items_df[food_items_df['user_email'] == user_email.lower()]
        return user_items.to_dict('records')
    except Exception:
        return []

def delete_food_item(item_id: int, user_email: str) -> bool:
    """Delete a food item"""
    try:
        food_items_df = load_food_items()
        initial_count = len(food_items_df)
        
        # Remove the item
        food_items_df = food_items_df[
            ~((food_items_df['id'] == item_id) & (food_items_df['user_email'] == user_email.lower()))
        ]
        
        if len(food_items_df) < initial_count:
            save_food_items(food_items_df)
            return True
        return False
    except Exception:
        return False

def update_food_item_details(item_id: int, name: str, quantity: str, opened: bool) -> bool:
    """Update name, quantity, and opened status for a food item"""
    try:
        food_items_df = load_food_items()
        mask = food_items_df['id'] == item_id
        
        if mask.any():
            food_items_df.loc[mask, 'name'] = str(name)
            food_items_df.loc[mask, 'quantity'] = str(quantity)
            food_items_df.loc[mask, 'opened'] = bool(opened)
            save_food_items(food_items_df)
            return True
        return False
    except Exception:
        return False

def update_food_item_date(item_id: int, date_type: str, new_date: date) -> bool:
    """Update purchase or expiry date for a food item"""
    try:
        food_items_df = load_food_items()
        mask = food_items_df['id'] == item_id
        
        if mask.any():
            date_str = new_date.strftime('%Y-%m-%d')
            if date_type in ['purchase', 'purchase_date']:
                food_items_df.loc[mask, 'purchase_date'] = date_str
            elif date_type in ['expiry', 'expiry_date']:
                food_items_df.loc[mask, 'expiry_date'] = date_str
            save_food_items(food_items_df)
            return True
        return False
    except Exception:
        return False

def update_user_money_saved(user_email: str, amount: float) -> bool:
    """Update user's money saved"""
    try:
        users_df = load_users()
        mask = users_df['email'] == user_email.lower()
        
        if mask.any():
            current_amount = users_df.loc[mask, 'money_saved'].iloc[0]
            users_df.loc[mask, 'money_saved'] = current_amount + amount
            save_users(users_df)
            return True
        return False
    except Exception:
        return False

def delete_expired_items(user_email: str) -> int:
    """Delete expired items for a user"""
    try:
        food_items_df = load_food_items()
        today = datetime.now().date()
        
        # Count expired items
        user_items = food_items_df[food_items_df['user_email'] == user_email.lower()]
        expired_mask = pd.to_datetime(user_items['expiry_date']).dt.date < today
        expired_count = expired_mask.sum()
        
        # Remove expired items
        food_items_df = food_items_df[
            ~((food_items_df['user_email'] == user_email.lower()) & 
              (pd.to_datetime(food_items_df['expiry_date']).dt.date < today))
        ]
        
        save_food_items(food_items_df)
        return expired_count
    except Exception:
        return 0

def predict_expiry_date(user_email: str, food_name: str, purchase_date: str) -> Optional[str]:
    """Predict expiry date based on historical data using ML"""
    try:
        from utils.food_data import get_default_expiry_prediction
        purchase_date_obj = datetime.strptime(purchase_date, '%Y-%m-%d').date()
        return get_default_expiry_prediction(food_name, purchase_date_obj)
    except Exception:
        return None

def get_default_expiry_prediction(food_name: str, purchase_date: date) -> str:
    """Get default expiry prediction based on food categories"""
    from utils.food_data import calculate_expiry_date
    return calculate_expiry_date(food_name, purchase_date)