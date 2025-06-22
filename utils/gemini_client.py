import os
import json
import logging
from datetime import datetime, timedelta
from google import genai
from google.genai import types
import streamlit as st

# Initialize Gemini client
def get_gemini_client():
    """Get Gemini client with properly formatted API key"""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")
    return genai.Client(api_key=api_key)

def process_voice_input(voice_text):
    """Process voice input using Gemini AI to extract food items"""
    
    try:
        # Get Gemini client
        client = get_gemini_client()
        
        system_prompt = """
        You are a food inventory assistant. Extract food items from the user's voice input.
        
        The user might say things like:
        - "I bought chicken, milk, and bananas today"
        - "Add 2 pounds of ground beef expiring next Friday"
        - "I have yogurt, bread, and some apples"
        
        Extract each food item and provide the following information:
        - name: The food item name
        - quantity: How much (e.g., "2 pounds", "1 gallon", "6 pack")
        - category: One of [Grocery, Cooked Food, Pantry, Frozen, Dairy, Meat & Poultry, Fruits, Vegetables, Beverages, Snacks, Condiments, Bakery]
        - purchase_date: Today's date unless otherwise specified (YYYY-MM-DD format)
        - expiry_date: Estimated expiry date based on typical shelf life (YYYY-MM-DD format)
        
        Return the result as a JSON array of objects. If no food items are found, return an empty array.
        
        Current date: {current_date}
        """.format(current_date=datetime.now().strftime('%Y-%m-%d'))
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(role="user", parts=[types.Part(text=voice_text)])
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json"
            )
        )
        
        if response.text:
            extracted_items = json.loads(response.text)
            return extracted_items if isinstance(extracted_items, list) else []
        
        return []
        
    except ValueError as e:
        st.error("Please check your Gemini API key configuration.")
        return []
    except Exception as e:
        st.error(f"Error processing voice input: {str(e)}")
        return []

def process_image_input(image_file, image_type):
    """Process image input using Gemini AI to extract food items"""
    
    try:
        # Get Gemini client
        client = get_gemini_client()
        
        # Reset file pointer to beginning
        image_file.seek(0)
        
        # Convert uploaded file to bytes
        image_bytes = image_file.read()
        
        # Reset file pointer for potential reuse
        image_file.seek(0)
        
        # Create appropriate prompt based on image type
        if image_type == "receipt":
            prompt = """
            Analyze this receipt/bill image and extract all food items.
            
            For each food item found, provide:
            - name: The food item name as it appears
            - quantity: The quantity purchased
            - category: Categorize as one of [Grocery, Dairy, Meat & Poultry, Fruits, Vegetables, Beverages, Snacks, Condiments, Bakery, Pantry, Frozen]
            - purchase_date: Today's date (YYYY-MM-DD format)
            - expiry_date: Estimated expiry date based on typical shelf life (YYYY-MM-DD format)
            
            Return as JSON array. If no food items found, return empty array.
            Current date: {current_date}
            """.format(current_date=datetime.now().strftime('%Y-%m-%d'))
            
        elif image_type == "barcode":
            prompt = """
            Analyze this barcode image and identify the food product.
            
            Provide:
            - name: The product name
            - quantity: Standard package size
            - category: Appropriate food category
            - purchase_date: Today's date (YYYY-MM-DD format)
            - expiry_date: Estimated expiry date (YYYY-MM-DD format)
            
            Return as JSON array with single item. If barcode cannot be read, return empty array.
            Current date: {current_date}
            """.format(current_date=datetime.now().strftime('%Y-%m-%d'))
            
        else:  # food_photo
            prompt = """
            Analyze this food photo and identify all visible food items.
            
            For each food item visible, provide:
            - name: The food item name
            - quantity: Estimated quantity visible (e.g., "1 piece", "bunch", "package")
            - category: Appropriate food category
            - purchase_date: Today's date (YYYY-MM-DD format)
            - expiry_date: Estimated expiry date based on appearance and type (YYYY-MM-DD format)
            
            Return as JSON array. If no food items found, return empty array.
            Current date: {current_date}
            """.format(current_date=datetime.now().strftime('%Y-%m-%d'))
        
        # Determine MIME type based on file content
        mime_type = "image/jpeg"
        if hasattr(image_file, 'type') and image_file.type:
            mime_type = image_file.type
        elif len(image_bytes) >= 4 and image_bytes[:4] == b'\x89PNG':
            mime_type = "image/png"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type
                ),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        if response.text:
            extracted_items = json.loads(response.text)
            return extracted_items if isinstance(extracted_items, list) else []
        
        return []
        
    except ValueError as e:
        st.error("Please check your Gemini API key configuration.")
        return []
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return []

def get_recipe_suggestions(expiring_items):
    """Get recipe suggestions for expiring food items using Gemini AI"""
    
    if not expiring_items:
        return []
    
    try:
        client = get_gemini_client()
        items_text = ", ".join([item['name'] for item in expiring_items])
        
        prompt = f"""
        Suggest 3-5 quick and easy recipes that use these ingredients that are expiring soon: {items_text}
        
        For each recipe, provide:
        - name: Recipe name
        - ingredients: List of ingredients (highlight the expiring ones)
        - prep_time: Preparation time in minutes
        - instructions: Brief cooking instructions
        - difficulty: Easy/Medium/Hard
        
        Focus on simple recipes that help use expiring ingredients efficiently.
        Return as JSON array.
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        if response.text:
            recipes = json.loads(response.text)
            return recipes if isinstance(recipes, list) else []
        
        return []
        
    except Exception as e:
        st.error(f"Error getting recipe suggestions: {str(e)}")
        return []

def analyze_food_waste_patterns(food_items):
    """Analyze food waste patterns using Gemini AI"""
    
    try:
        client = get_gemini_client()
        # Prepare data for analysis
        items_data = []
        today = datetime.now().date()
        
        for item in food_items:
            expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
            days_until_expiry = (expiry_date - today).days
            
            items_data.append({
                'name': item['name'],
                'category': item['category'],
                'days_until_expiry': days_until_expiry,
                'quantity': item['quantity'],
                'added_method': item['added_method']
            })
        
        prompt = f"""
        Analyze this food inventory data and provide insights about potential waste patterns:
        {json.dumps(items_data, indent=2)}
        
        Provide analysis on:
        - Categories with most items expiring soon
        - Patterns in food types that expire frequently
        - Suggestions for better food management
        - Recommendations for purchase timing
        
        Return insights as JSON object with keys: patterns, recommendations, risk_categories, tips
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        if response.text:
            analysis = json.loads(response.text)
            return analysis
        
        return {}
        
    except Exception as e:
        st.error(f"Error analyzing waste patterns: {str(e)}")
        return {}

def generate_shopping_list(current_items, preferences=None):
    """Generate smart shopping list based on current inventory"""
    
    try:
        client = get_gemini_client()
        current_items_text = json.dumps([
            {'name': item['name'], 'category': item['category'], 'expiry_date': item['expiry_date']}
            for item in current_items
        ], indent=2)
        
        prompt = f"""
        Based on this current food inventory:
        {current_items_text}
        
        Generate a smart shopping list that:
        - Avoids items that are already well-stocked
        - Suggests complementary items for existing ingredients
        - Considers items that are running low or missing
        - Includes seasonal/fresh items
        
        Return as JSON array with objects containing:
        - item: Item name
        - category: Food category
        - priority: High/Medium/Low
        - reason: Why this item is suggested
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        if response.text:
            shopping_list = json.loads(response.text)
            return shopping_list if isinstance(shopping_list, list) else []
        
        return []
        
    except Exception as e:
        st.error(f"Error generating shopping list: {str(e)}")
        return []

def detect_duplicate_purchases(new_items, existing_items):
    """Detect potential duplicate purchases using AI"""
    
    try:
        client = get_gemini_client()
        existing_items_text = json.dumps([
            {'name': item['name'], 'category': item['category'], 'expiry_date': item['expiry_date']}
            for item in existing_items
        ], indent=2)
        
        new_items_text = json.dumps(new_items, indent=2)
        
        prompt = f"""
        Check if these new items might be duplicates of existing inventory:
        
        New items to add:
        {new_items_text}
        
        Existing inventory:
        {existing_items_text}
        
        Identify potential duplicates and provide warnings. Consider:
        - Same or similar item names
        - Items in same category that might overlap
        - Quantities that might be excessive
        
        Return JSON object with:
        - duplicates: Array of potential duplicate warnings
        - recommendations: Suggestions for the user
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        if response.text:
            analysis = json.loads(response.text)
            return analysis
        
        return {'duplicates': [], 'recommendations': []}
        
    except Exception as e:
        st.error(f"Error detecting duplicates: {str(e)}")
        return {'duplicates': [], 'recommendations': []}
