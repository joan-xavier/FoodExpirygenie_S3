from datetime import datetime, timedelta
import streamlit as st

# Food categories
FOOD_CATEGORIES = [
    "Grocery",
    "Cooked Food", 
    "Pantry",
    "Frozen",
    "Dairy",
    "Meat & Poultry",
    "Fruits",
    "Vegetables",
    "Beverages",
    "Snacks",
    "Condiments",
    "Bakery"
]

# Default shelf life data (in days)
DEFAULT_SHELF_LIFE = {
    # Dairy
    'milk': 7,
    'cheese': 14,
    'yogurt': 10,
    'butter': 30,
    'cream': 5,
    
    # Meat & Poultry
    'chicken': 3,
    'beef': 5,
    'pork': 4,
    'fish': 2,
    'ground beef': 2,
    'ground chicken': 2,
    
    # Fruits
    'apple': 14,
    'banana': 7,
    'orange': 10,
    'grapes': 7,
    'strawberry': 5,
    'blueberry': 10,
    
    # Vegetables
    'lettuce': 7,
    'tomato': 7,
    'carrot': 21,
    'potato': 30,
    'onion': 30,
    'broccoli': 7,
    
    # Pantry
    'bread': 7,
    'rice': 365,
    'pasta': 730,
    'cereal': 365,
    'flour': 365,
    
    # Beverages
    'juice': 7,
    'soda': 90,
    'beer': 120,
    'wine': 1825,
}

def get_food_categories():
    """Return list of food categories"""
    return FOOD_CATEGORIES

def add_food_item(name, category, purchase_date, expiry_date=None, quantity="1 unit", opened=False, method="manual"):
    """Add a food item to the inventory"""
    
    # Calculate expiry date if not provided
    if not expiry_date:
        expiry_date = calculate_expiry_date(name, purchase_date, opened)
    
    food_item = {
        'id': len(st.session_state.food_items),
        'name': name,
        'category': category,
        'purchase_date': purchase_date.strftime('%Y-%m-%d') if hasattr(purchase_date, 'strftime') else purchase_date,
        'expiry_date': expiry_date.strftime('%Y-%m-%d') if hasattr(expiry_date, 'strftime') else expiry_date,
        'quantity': quantity,
        'opened': opened,
        'added_method': method,
        'added_at': datetime.now().isoformat()
    }
    
    st.session_state.food_items.append(food_item)
    return food_item

def calculate_expiry_date(food_name, purchase_date, opened=False):
    """Calculate expiry date based on food type and purchase date"""
    
    food_name_lower = food_name.lower()
    
    # Find matching food in shelf life data
    shelf_life_days = 7  # default
    for food, days in DEFAULT_SHELF_LIFE.items():
        if food in food_name_lower:
            shelf_life_days = days
            break
    
    # Reduce shelf life if opened/cooked
    if opened:
        if shelf_life_days > 7:
            shelf_life_days = min(7, shelf_life_days // 3)
        else:
            shelf_life_days = max(1, shelf_life_days // 2)
    
    # Convert purchase_date to date object if it's a string
    if isinstance(purchase_date, str):
        purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d').date()
    elif hasattr(purchase_date, 'date'):
        purchase_date = purchase_date.date()
    
    expiry_date = purchase_date + timedelta(days=shelf_life_days)
    return expiry_date

def get_expiry_status(expiry_date):
    """Get expiry status (Safe, Expiring Soon, Expired)"""
    
    today = datetime.now().date()
    
    if isinstance(expiry_date, str):
        expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
    
    days_until_expiry = (expiry_date - today).days
    
    if days_until_expiry < 0:
        return "Expired", "🔴"
    elif days_until_expiry <= 3:
        return "Expiring Soon", "🟡"
    else:
        return "Safe", "🟢"

def filter_food_items(items, category=None, status=None):
    """Filter food items by category and/or status"""
    
    filtered_items = items.copy()
    
    if category and category != "All":
        filtered_items = [item for item in filtered_items if item['category'] == category]
    
    if status and status != "All":
        filtered_by_status = []
        for item in filtered_items:
            item_status, _ = get_expiry_status(item['expiry_date'])
            if item_status == status:
                filtered_by_status.append(item)
        filtered_items = filtered_by_status
    
    return filtered_items

def sort_food_items(items, sort_by="expiry_date", ascending=True):
    """Sort food items by specified field"""
    
    if sort_by == "expiry_date":
        items.sort(key=lambda x: datetime.strptime(x['expiry_date'], '%Y-%m-%d'), reverse=not ascending)
    elif sort_by == "purchase_date":
        items.sort(key=lambda x: datetime.strptime(x['purchase_date'], '%Y-%m-%d'), reverse=not ascending)
    elif sort_by == "name":
        items.sort(key=lambda x: x['name'].lower(), reverse=not ascending)
    elif sort_by == "category":
        items.sort(key=lambda x: x['category'], reverse=not ascending)
    
    return items

def get_items_expiring_soon(items, days=3):
    """Get items expiring within specified days"""
    
    today = datetime.now().date()
    expiring_items = []
    
    for item in items:
        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
        days_until_expiry = (expiry_date - today).days
        
        if 0 <= days_until_expiry <= days:
            expiring_items.append(item)
    
    return expiring_items

def get_expired_items(items):
    """Get expired items"""
    
    today = datetime.now().date()
    expired_items = []
    
    for item in items:
        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
        
        if expiry_date < today:
            expired_items.append(item)
    
    return expired_items

def remove_food_item(item_id):
    """Remove food item by ID"""
    
    st.session_state.food_items = [
        item for item in st.session_state.food_items 
        if item['id'] != item_id
    ]

def update_food_item(item_id, updates):
    """Update food item with new data"""
    
    for i, item in enumerate(st.session_state.food_items):
        if item['id'] == item_id:
            st.session_state.food_items[i].update(updates)
            break

def get_food_suggestions(partial_name):
    """Get food name suggestions based on partial input"""
    
    common_foods = [
        'Milk', 'Bread', 'Eggs', 'Chicken', 'Beef', 'Fish', 'Cheese', 'Yogurt',
        'Apple', 'Banana', 'Orange', 'Tomato', 'Lettuce', 'Carrot', 'Potato',
        'Rice', 'Pasta', 'Cereal', 'Juice', 'Butter', 'Onion', 'Broccoli',
        'Ground Beef', 'Chicken Breast', 'Salmon', 'Strawberry', 'Blueberry',
        'Bell Pepper', 'Cucumber', 'Spinach', 'Mushroom', 'Garlic'
    ]
    
    partial_lower = partial_name.lower()
    suggestions = [food for food in common_foods if partial_lower in food.lower()]
    
    return suggestions[:5]  # Return top 5 suggestions

def categorize_food_automatically(food_name):
    """Automatically categorize food based on name"""
    
    food_name_lower = food_name.lower()
    
    # Define category keywords
    category_keywords = {
        'Dairy': ['milk', 'cheese', 'yogurt', 'butter', 'cream'],
        'Meat & Poultry': ['chicken', 'beef', 'pork', 'fish', 'turkey', 'lamb', 'ground'],
        'Fruits': ['apple', 'banana', 'orange', 'grape', 'strawberry', 'blueberry', 'mango'],
        'Vegetables': ['tomato', 'lettuce', 'carrot', 'potato', 'onion', 'broccoli', 'pepper'],
        'Pantry': ['rice', 'pasta', 'cereal', 'flour', 'sugar', 'salt', 'oil'],
        'Beverages': ['juice', 'soda', 'beer', 'wine', 'water', 'coffee', 'tea'],
        'Bakery': ['bread', 'bagel', 'muffin', 'cake', 'cookie', 'pie'],
        'Frozen': ['frozen', 'ice cream', 'popsicle'],
        'Condiments': ['sauce', 'dressing', 'ketchup', 'mustard', 'mayo']
    }
    
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in food_name_lower:
                return category
    
    return 'Grocery'  # Default category
