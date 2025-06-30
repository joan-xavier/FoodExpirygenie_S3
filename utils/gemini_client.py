import os
import json
from datetime import datetime
import google.generativeai as genai
import streamlit as st

#  Gemini model setup --
def get_gemini_model(model_name="gemini-2.5-flash"):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

#  Parse JSON safely from Gemini response
def safe_parse_json(response_text):
    try:
        result = json.loads(response_text)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return [result]
        else:
            return []
    except Exception as e:
        st.error(f"Error parsing Gemini response: {str(e)}")
        return []

def process_voice_input(voice_text):
    try:
        model = get_gemini_model()
        system_prompt = f"""
        You are a food inventory assistant. Extract food items from user voice input. 
        For each item, return:
        - name, quantity, category, purchase_date, expiry_date

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

        Respond as a JSON array. If no food items are found, return an empty array.
        Current date: {datetime.now().strftime('%Y-%m-%d')}
        """

        response = model.generate_content(
            contents=[{"role": "user", "parts": [{"text": voice_text}]}],
            generation_config={"response_mime_type": "application/json"},
            system_instruction=system_prompt
        )

        if response.text:
            return safe_parse_json(response.text)
        return []
    except Exception as e:
        st.error(f"Error processing voice input: {str(e)}")
        return []

def process_image_input(image_file, image_type):
    try:
        model = get_gemini_model()
        image_file.seek(0)
        image_bytes = image_file.read()
        image_file.seek(0)

        mime_type = image_file.type if hasattr(image_file, 'type') and image_file.type else "image/jpeg"

        if image_type == "receipt":
            prompt = """
            Analyze this receipt/bill image and extract all food items.

            For each food item found, provide:
            - name: The food item name as it appears
            - quantity: The quantity purchased
            - category: Categorize as one of [Grocery, Dairy, Meat & Poultry, Fruits, Vegetables, Beverages, Snacks, Condiments, Bakery, Pantry, Frozen]
            - purchase_date: Today's date (YYYY-MM-DD format)
            - expiry_date: Estimated expiry date based on typical shelf life (YYYY-MM-DD format)

            Return JSON array.
            """
        elif image_type == "barcode":
            prompt = """
            Identify the food product in this barcode. 
            Return JSON array. If no food items found, return empty array.
            """
        else:
            prompt = """
            Identify all visible food items in this photo.

            For each food item found, provide:
            - name: The food item name as it appears
            - quantity: The quantity purchased
            - category: Categorize as one of [Grocery, Dairy, Meat & Poultry, Fruits, Vegetables, Beverages, Snacks, Condiments, Bakery, Pantry, Frozen]
            - purchase_date: Today's date (YYYY-MM-DD format)
            - expiry_date: Estimated expiry date based on typical shelf life (YYYY-MM-DD format)

            Return JSON array.
            """

        response = model.generate_content(
            contents=[
                {"inline_data": {"mime_type": mime_type, "data": image_bytes}},
                {"text": prompt}
            ],
            generation_config={"response_mime_type": "application/json"}
        )

        if response.text:
            return safe_parse_json(response.text)
        return []
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return []

def get_recipe_suggestions(expiring_items):
    if not expiring_items:
        return []

    try:
        model = get_gemini_model()
        items_text = ", ".join([item['name'] for item in expiring_items])

        prompt = f"""
        Suggest 3–5 recipes using the following items: {items_text}.
        Each recipe should include:
        - name, ingredients, prep_time, instructions, difficulty
        Return as a JSON array.
        """

        response = model.generate_content(
            contents=prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        if response.text:
            return safe_parse_json(response.text)
        return []
    except Exception as e:
        st.error(f"Error getting recipe suggestions: {str(e)}")
        return []

def analyze_food_waste_patterns(food_items):
    try:
        model = get_gemini_model()
        today = datetime.now().date()
        items_data = []

        for item in food_items:
            try:
                expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                days_left = (expiry_date - today).days
                items_data.append({
                    'name': item['name'],
                    'category': item['category'],
                    'days_until_expiry': days_left,
                    'quantity': item['quantity'],
                    'added_method': item['added_method']
                })
            except Exception:
                continue

        prompt = f"""
        Analyze the following inventory for waste patterns:
        {json.dumps(items_data, indent=2)}
        Return JSON object with:
        - patterns, risk_categories, tips, recommendations
        """

        response = model.generate_content(
            contents=prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        if response.text:
            result = json.loads(response.text)
            return result if isinstance(result, dict) else {}
        return {}
    except Exception as e:
        st.error(f"Error analyzing waste patterns: {str(e)}")
        return {}

def generate_shopping_list(current_items, preferences=None):
    try:
        model = get_gemini_model()
        current_text = json.dumps([
            {'name': item['name'], 'category': item['category'], 'expiry_date': item['expiry_date']}
            for item in current_items
        ], indent=2)

        prompt = f"""
        Based on this inventory:
        {current_text}
        Generate a shopping list. Return JSON array with:
        - item, category, priority (High/Medium/Low), reason
        """

        response = model.generate_content(
            contents=prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        if response.text:
            return safe_parse_json(response.text)
        return []
    except Exception as e:
        st.error(f"Error generating shopping list: {str(e)}")
        return []

def detect_duplicate_purchases(new_items, existing_items):
    try:
        model = get_gemini_model()
        new_text = json.dumps(new_items, indent=2)
        existing_text = json.dumps(existing_items, indent=2)

        prompt = f"""
        Identify duplicates between new and existing items.
        New:
        {new_text}
        Existing:
        {existing_text}
        Return JSON object with:
        - duplicates, recommendations
        """

        response = model.generate_content(
            contents=prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        if response.text:
            result = json.loads(response.text)
            return result if isinstance(result, dict) else {'duplicates': [], 'recommendations': []}
        return {'duplicates': [], 'recommendations': []}
    except Exception as e:
        st.error(f"Error detecting duplicates: {str(e)}")
        return {'duplicates': [], 'recommendations': []}
