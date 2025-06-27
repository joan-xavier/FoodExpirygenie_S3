"""
AWS S3 Storage utilities for ExpiryGenie
Handles user data and food inventory storage in S3 bucket
"""

import boto3
import json
import pandas as pd
import hashlib
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from botocore.exceptions import ClientError, NoCredentialsError
import io

class S3Storage:
    def __init__(self):
        """Initialize S3 client with credentials from environment"""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            self.bucket_name = os.getenv('S3_BUCKET_NAME', 'expirygenie-data')
        except Exception as e:
            print(f"Error initializing S3 client: {e}")
            self.s3_client = None

    def _ensure_bucket_exists(self):
        """Ensure the S3 bucket exists, create if not"""
        try:
            if self.s3_client:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                try:
                    if self.s3_client:
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    print(f"Created S3 bucket: {self.bucket_name}")
                except Exception as create_error:
                    print(f"Error creating bucket: {create_error}")
                    return False
        return True

    def _get_object_key(self, object_type: str, identifier: str = None) -> str:
        """Generate S3 object key for different data types"""
        if object_type == 'users':
            return 'data/users.json'
        elif object_type == 'food_items':
            return f'data/food_items/{identifier}.json'
        elif object_type == 'user_profile':
            return f'data/profiles/{identifier}.json'
        else:
            return f'data/{object_type}/{identifier or "default"}.json'

    def _upload_json(self, data: dict, key: str) -> bool:
        """Upload JSON data to S3"""
        try:
            if not self.s3_client:
                return False
            
            if not self._ensure_bucket_exists():
                return False
            
            json_data = json.dumps(data, indent=2, default=str)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json_data,
                ContentType='application/json'
            )
            return True
        except Exception as e:
            print(f"Error uploading to S3: {e}")
            return False

    def _download_json(self, key: str) -> Optional[dict]:
        """Download JSON data from S3"""
        try:
            if not self.s3_client:
                return None
                
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            print(f"Error downloading from S3: {e}")
            return None
        except Exception as e:
            print(f"Error parsing S3 data: {e}")
            return None

    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return hashlib.sha256(password.encode()).hexdigest() == password_hash

    def load_users(self) -> Dict:
        """Load users from S3"""
        users_data = self._download_json(self._get_object_key('users'))
        return users_data if users_data else {}

    def save_users(self, users_data: Dict) -> bool:
        """Save users to S3"""
        return self._upload_json(users_data, self._get_object_key('users'))

    def create_user(self, name: str, email: str, password: str) -> bool:
        """Create a new user"""
        try:
            users_data = self.load_users()
            
            # Check if user already exists
            if email in users_data:
                return False
            
            # Create new user
            users_data[email] = {
                'name': name,
                'email': email,
                'password_hash': self.hash_password(password),
                'money_saved': 0.0,
                'created_at': datetime.now().isoformat()
            }
            
            return self.save_users(users_data)
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user login"""
        try:
            users_data = self.load_users()
            
            if email in users_data:
                user_data = users_data[email]
                if self.verify_password(password, user_data['password_hash']):
                    return {
                        'name': user_data['name'],
                        'email': user_data['email'],
                        'money_saved': user_data.get('money_saved', 0.0)
                    }
            return None
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            users_data = self.load_users()
            if email in users_data:
                user_data = users_data[email]
                return {
                    'name': user_data['name'],
                    'email': user_data['email'],
                    'money_saved': user_data.get('money_saved', 0.0)
                }
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    def load_user_food_items(self, user_email: str) -> List[Dict]:
        """Load food items for a specific user from S3"""
        try:
            # Use email hash for file naming to avoid special characters
            user_hash = hashlib.md5(user_email.encode()).hexdigest()
            food_data = self._download_json(self._get_object_key('food_items', user_hash))
            
            if food_data and 'items' in food_data:
                return food_data['items']
            return []
        except Exception as e:
            print(f"Error loading food items: {e}")
            return []

    def save_user_food_items(self, user_email: str, food_items: List[Dict]) -> bool:
        """Save food items for a specific user to S3"""
        try:
            user_hash = hashlib.md5(user_email.encode()).hexdigest()
            food_data = {
                'user_email': user_email,
                'last_updated': datetime.now().isoformat(),
                'items': food_items
            }
            
            return self._upload_json(food_data, self._get_object_key('food_items', user_hash))
        except Exception as e:
            print(f"Error saving food items: {e}")
            return False

    def add_food_item(self, user_email: str, name: str, category: str, 
                      purchase_date: str, expiry_date: str, quantity: str = '1 unit', 
                      opened: bool = False, added_method: str = 'manual') -> bool:
        """Add food item to S3"""
        try:
            food_items = self.load_user_food_items(user_email)
            
            # Generate new ID
            new_id = max([item.get('id', 0) for item in food_items], default=0) + 1
            
            new_item = {
                'id': new_id,
                'name': name,
                'category': category,
                'purchase_date': purchase_date,
                'expiry_date': expiry_date,
                'quantity': quantity,
                'opened': opened,
                'added_method': added_method,
                'created_at': datetime.now().isoformat()
            }
            
            food_items.append(new_item)
            return self.save_user_food_items(user_email, food_items)
            
        except Exception as e:
            print(f"Error adding food item: {e}")
            return False

    def get_user_food_items(self, user_email: str) -> List[Dict]:
        """Get all food items for a user"""
        return self.load_user_food_items(user_email)

    def delete_food_item(self, item_id: int, user_email: str) -> bool:
        """Delete a food item"""
        try:
            food_items = self.load_user_food_items(user_email)
            
            # Find and remove item
            food_items = [item for item in food_items if item.get('id') != item_id]
            
            return self.save_user_food_items(user_email, food_items)
            
        except Exception as e:
            print(f"Error deleting food item: {e}")
            return False

    def update_food_item_details(self, item_id: int, user_email: str, name: str, quantity: str, opened: bool) -> bool:
        """Update name, quantity, and opened status for a food item"""
        try:
            food_items = self.load_user_food_items(user_email)
            
            for item in food_items:
                if item.get('id') == item_id:
                    item['name'] = name
                    item['quantity'] = quantity
                    item['opened'] = opened
                    item['updated_at'] = datetime.now().isoformat()
                    break
            
            return self.save_user_food_items(user_email, food_items)
            
        except Exception as e:
            print(f"Error updating food item: {e}")
            return False

    def update_food_item_date(self, item_id: int, user_email: str, date_type: str, new_date: date) -> bool:
        """Update purchase or expiry date for a food item"""
        try:
            food_items = self.load_user_food_items(user_email)
            
            for item in food_items:
                if item.get('id') == item_id:
                    if date_type in ['purchase_date', 'expiry_date']:
                        item[date_type] = new_date.strftime('%Y-%m-%d')
                        item['updated_at'] = datetime.now().isoformat()
                    break
            
            return self.save_user_food_items(user_email, food_items)
            
        except Exception as e:
            print(f"Error updating food item date: {e}")
            return False

    def update_user_money_saved(self, user_email: str, amount: float) -> bool:
        """Update user's money saved"""
        try:
            users_data = self.load_users()
            
            if user_email in users_data:
                users_data[user_email]['money_saved'] = users_data[user_email].get('money_saved', 0) + amount
                users_data[user_email]['updated_at'] = datetime.now().isoformat()
                return self.save_users(users_data)
            
            return False
        except Exception as e:
            print(f"Error updating money saved: {e}")
            return False

    def delete_expired_items(self, user_email: str) -> int:
        """Delete expired items for a user"""
        try:
            food_items = self.load_user_food_items(user_email)
            today = datetime.now().date()
            
            original_count = len(food_items)
            food_items = [
                item for item in food_items 
                if datetime.strptime(item['expiry_date'], '%Y-%m-%d').date() > today
            ]
            
            deleted_count = original_count - len(food_items)
            
            if deleted_count > 0:
                self.save_user_food_items(user_email, food_items)
            
            return deleted_count
            
        except Exception as e:
            print(f"Error deleting expired items: {e}")
            return 0

    def export_to_csv(self, user_email: str) -> Optional[str]:
        """Export user's food items to CSV format"""
        try:
            food_items = self.load_user_food_items(user_email)
            
            if not food_items:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(food_items)
            
            # Add calculated fields
            today = datetime.now().date()
            df['days_left'] = df['expiry_date'].apply(
                lambda x: (datetime.strptime(x, '%Y-%m-%d').date() - today).days
            )
            df['status'] = df['days_left'].apply(
                lambda x: 'Expired' if x < 0 else ('Expiring Soon' if x <= 3 else 'Safe')
            )
            
            # Convert to CSV
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            return csv_buffer.getvalue()
            
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return None

# Initialize global S3 storage instance
s3_storage = S3Storage()

# Convenience functions for backward compatibility
def hash_password(password: str) -> str:
    return s3_storage.hash_password(password)

def verify_password(password: str, password_hash: str) -> bool:
    return s3_storage.verify_password(password, password_hash)

def create_user(name: str, email: str, password: str) -> bool:
    return s3_storage.create_user(name, email, password)

def authenticate_user(email: str, password: str) -> Optional[Dict]:
    return s3_storage.authenticate_user(email, password)

def get_user_by_email(email: str) -> Optional[Dict]:
    return s3_storage.get_user_by_email(email)

def add_food_item(user_email: str, name: str, category: str, purchase_date: str, 
                  expiry_date: str, quantity: str = '1 unit', opened: bool = False, 
                  added_method: str = 'manual') -> bool:
    return s3_storage.add_food_item(user_email, name, category, purchase_date, 
                                    expiry_date, quantity, opened, added_method)

def get_user_food_items(user_email: str) -> List[Dict]:
    return s3_storage.get_user_food_items(user_email)

def delete_food_item(item_id: int, user_email: str) -> bool:
    return s3_storage.delete_food_item(item_id, user_email)

def update_food_item_details(item_id: int, user_email: str, name: str, quantity: str, opened: bool) -> bool:
    return s3_storage.update_food_item_details(item_id, user_email, name, quantity, opened)

def update_food_item_date(item_id: int, user_email: str, date_type: str, new_date: date) -> bool:
    return s3_storage.update_food_item_date(item_id, user_email, date_type, new_date)

def update_user_money_saved(user_email: str, amount: float) -> bool:
    return s3_storage.update_user_money_saved(user_email, amount)

def delete_expired_items(user_email: str) -> int:
    return s3_storage.delete_expired_items(user_email)

def predict_expiry_date(user_email: str, food_name: str, purchase_date: str) -> Optional[str]:
    """Predict expiry date based on historical data using ML"""
    try:
        food_items = get_user_food_items(user_email)
        
        # Filter items with same food name
        similar_items = [item for item in food_items if food_name.lower() in item['name'].lower()]
        
        if similar_items:
            # Calculate average shelf life
            total_days = 0
            count = 0
            
            for item in similar_items:
                try:
                    p_date = datetime.strptime(item['purchase_date'], '%Y-%m-%d').date()
                    e_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                    shelf_life = (e_date - p_date).days
                    total_days += shelf_life
                    count += 1
                except:
                    continue
            
            if count > 0:
                avg_shelf_life = total_days // count
                purchase_date_obj = datetime.strptime(purchase_date, '%Y-%m-%d').date()
                predicted_date = purchase_date_obj + timedelta(days=avg_shelf_life)
                return predicted_date.strftime('%Y-%m-%d')
        
        return None
    except Exception as e:
        print(f"Error predicting expiry date: {e}")
        return None

def get_default_expiry_prediction(food_name: str, purchase_date: date) -> str:
    """Get default expiry prediction based on food categories"""
    # Default shelf life for different food types (in days)
    food_shelf_life = {
        'milk': 7, 'bread': 5, 'eggs': 21, 'chicken': 3, 'fish': 2,
        'beef': 5, 'pork': 5, 'rice': 365, 'pasta': 730, 'flour': 365,
        'apple': 30, 'banana': 7, 'orange': 14, 'lettuce': 7, 'tomato': 7,
        'potato': 30, 'onion': 30, 'cheese': 21, 'yogurt': 14, 'butter': 30
    }
    
    # Find matching food type
    food_lower = food_name.lower()
    days_to_add = 7  # default
    
    for food_type, shelf_life in food_shelf_life.items():
        if food_type in food_lower:
            days_to_add = shelf_life
            break
    
    predicted_date = purchase_date + timedelta(days=days_to_add)
    return predicted_date.strftime('%Y-%m-%d')