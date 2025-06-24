import os
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
import json
from datetime import datetime

def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(
            host=os.environ.get('PGHOST'),
            database=os.environ.get('PGDATABASE'),
            user=os.environ.get('PGUSER'),
            password=os.environ.get('PGPASSWORD'),
            port=os.environ.get('PGPORT', 5432)
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return None

def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            # Create users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    money_saved DECIMAL(10,2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create food_items table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS food_items (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    purchase_date DATE NOT NULL,
                    expiry_date DATE NOT NULL,
                    quantity VARCHAR(100) DEFAULT '1 unit',
                    opened BOOLEAN DEFAULT FALSE,
                    added_method VARCHAR(50) DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def create_user(name, email, password_hash):
    """Create a new user"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
            """, (name, email, password_hash))
            conn.commit()
            return True, "User created successfully"
            
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "User already exists"
    except Exception as e:
        conn.rollback()
        return False, f"Error creating user: {str(e)}"
    finally:
        conn.close()

def authenticate_user(email, password_hash):
    """Authenticate user"""
    conn = get_db_connection()
    if not conn:
        return False, None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM users WHERE email = %s AND password_hash = %s
            """, (email, password_hash))
            user = cur.fetchone()
            
            if user:
                return True, dict(user)
            else:
                return False, None
                
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return False, None
    finally:
        conn.close()

def get_user_by_email(email):
    """Get user by email"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            return dict(user) if user else None
            
    except Exception as e:
        st.error(f"Error fetching user: {str(e)}")
        return None
    finally:
        conn.close()

def add_food_item(user_email, name, category, purchase_date, expiry_date, quantity='1 unit', opened=False, added_method='manual'):
    """Add food item to database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO food_items (user_email, name, category, purchase_date, expiry_date, quantity, opened, added_method)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_email, name, category, purchase_date, expiry_date, quantity, opened, added_method))
            conn.commit()
            return True
            
    except Exception as e:
        print(f"Database error adding food item: {str(e)}")  # Debug logging
        conn.rollback()
        return False
    finally:
        conn.close()

def get_user_food_items(user_email):
    """Get all food items for a user"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM food_items 
                WHERE user_email = %s 
                ORDER BY expiry_date ASC
            """, (user_email,))
            items = cur.fetchall()
            return [dict(item) for item in items]
            
    except Exception as e:
        st.error(f"Error fetching food items: {str(e)}")
        return []
    finally:
        conn.close()

def delete_food_item(item_id, user_email):
    """Delete a food item"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM food_items 
                WHERE id = %s AND user_email = %s
            """, (item_id, user_email))
            conn.commit()
            return cur.rowcount > 0
            
    except Exception as e:
        st.error(f"Error deleting food item: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_user_money_saved(user_email, amount):
    """Update user's money saved"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users 
                SET money_saved = %s 
                WHERE email = %s
            """, (amount, user_email))
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Error updating money saved: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_expired_items(user_email):
    """Delete expired items for a user"""
    conn = get_db_connection()
    if not conn:
        return 0
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM food_items 
                WHERE user_email = %s AND expiry_date < CURRENT_DATE
            """, (user_email,))
            conn.commit()
            return cur.rowcount
            
    except Exception as e:
        st.error(f"Error deleting expired items: {str(e)}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def predict_expiry_date(user_email, food_name, purchase_date):
    """Predict expiry date based on historical data using ML"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get historical data for similar food items
            cur.execute("""
                SELECT name, purchase_date, expiry_date,
                       (expiry_date - purchase_date) as shelf_life
                FROM food_items 
                WHERE user_email = %s 
                AND LOWER(name) LIKE %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_email, f"%{food_name.lower()}%"))
            
            historical_data = cur.fetchall()
            
            if historical_data:
                # Simple prediction: average shelf life from historical data
                shelf_lives = []
                for item in historical_data:
                    if item['shelf_life']:
                        # Handle both interval and integer types
                        if hasattr(item['shelf_life'], 'days'):
                            days = item['shelf_life'].days
                        else:
                            days = int(item['shelf_life'])
                        if days > 0:
                            shelf_lives.append(days)
                
                if shelf_lives:
                    from statistics import mean
                    from datetime import timedelta
                    avg_shelf_life = int(mean(shelf_lives))
                    predicted_expiry = purchase_date + timedelta(days=avg_shelf_life)
                    return predicted_expiry
            
            # Fallback: default shelf life based on food type
            return get_default_expiry_prediction(food_name, purchase_date)
            
    except Exception as e:
        print(f"Error predicting expiry date: {str(e)}")
        return None
    finally:
        conn.close()

def get_default_expiry_prediction(food_name, purchase_date):
    """Get default expiry prediction based on food categories"""
    from datetime import timedelta
    
    food_name_lower = food_name.lower()
    
    # Default shelf lives (in days) for different food categories
    shelf_life_map = {
        'milk': 7, 'cheese': 14, 'yogurt': 10, 'butter': 21,
        'chicken': 3, 'beef': 3, 'pork': 3, 'fish': 2, 'turkey': 3,
        'apple': 14, 'banana': 7, 'orange': 10, 'lettuce': 7, 'tomato': 7,
        'bread': 5, 'rice': 365, 'pasta': 365, 'cereal': 180,
        'frozen': 90, 'canned': 365
    }
    
    # Find matching category
    for keyword, days in shelf_life_map.items():
        if keyword in food_name_lower:
            return purchase_date + timedelta(days=days)
    
    # Default fallback
    return purchase_date + timedelta(days=7)

def update_food_item_details(item_id, name, quantity, opened):
    """Update name, quantity, and opened status for a food item"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE food_items 
                SET name = %s, quantity = %s, opened = %s 
                WHERE id = %s
            """, (name, quantity, opened, item_id))
            
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Error updating item details: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_food_item_date(item_id, date_type, new_date):
    """Update purchase or expiry date for a food item"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            if date_type == 'purchase_date':
                cur.execute("""
                    UPDATE food_items 
                    SET purchase_date = %s 
                    WHERE id = %s
                """, (new_date, item_id))
            elif date_type == 'expiry_date':
                cur.execute("""
                    UPDATE food_items 
                    SET expiry_date = %s 
                    WHERE id = %s
                """, (new_date, item_id))
            else:
                return False
            
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Error updating {date_type}: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()