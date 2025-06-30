import os
import json
import logging
from datetime import datetime, timedelta
import google.generativeai as genai
from google.generativeai import types
import streamlit as st

# ✅ Fixed: Initialize Gemini model properly
def get_gemini_model(model_name="gemini-2.5-flash"):
    """Get configured Gemini model"""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

def process_voice_input(voice_text):
    try:
        model = get_gemini_model()

        system_prompt = f"""
        You are a food inventory assistant. Extract food items from the user's voice input.

        Extract each food item and provide the following information:
        - name
        - quantity
        - category
        - purchase_date: today's date (YYYY-MM-DD)
        - expiry_date: based on typical shelf life (YYYY-MM-DD)

        Return result as a JSON array of objects.
        Current date: {datetime.now().strftime('%Y-%m-%d')}
        """

        response = model.generate_content(
            contents=[
                types.Content(role="user", parts=[types.Part(text=voice_text)])
            ],
            generation_config=types.GenerationConfig(
                response_mime_type="application/json"
            ),
            system_instruction=system_prompt
        )

        if response.text:
            extracted_items = json.loads(response.text)
            return extracted_items if isinstance(extracted_items, list) else []

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

        if image_type == "receipt":
            prompt = f"""
            Extract food items from this receipt. Return JSON array with:
            - name, quantity, category, purchase_date, expiry_date.
            Current date: {datetime.now().strftime('%Y-%m-%d')}
            """
        elif image_type == "barcode":
            prompt = f"""
            Identify product in this barcode. Return JSON with:
            - name, quantity, category, purchase_date, expiry_date.
            Current date: {datetime.now().strftime('%Y-%m-%d')}
            """
        else:
            prompt = f"""
            Identify food items in this photo. Return JSON array with:
            - name, quantity, category, purchase_date, expiry_date.
            Current date: {datetime.now().strftime('%Y-%m-%d')}
            """

        mime_type = image_file.type if hasattr(image_file, 'type') and image_file.type else "image/jpeg"

        response = model.generate_content(
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                types.Part(text=prompt)
            ],
            generation_config=types.GenerationConfig(response_mime_type="application/json")
        )

        if response.text:
            extracted_items = json.loads(response.text)
            return extracted_items if isinstance(extracted_items, list) else []

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
        Suggest 3-5 easy recipes using these expiring ingredients: {items_text}
        Return JSON array with: name, ingredients, prep_time, instructions, difficulty.
        """

        response = model.generate_content(
            contents=prompt,
            generation_config=types.GenerationConfig(response_mime_type="application/json")
        )

        if response.text:
            recipes = json.loads(response.text)
            return recipes if isinstance(recipes, list) else []

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
        Analyze food waste patterns from this data:
        {json.dumps(items_data, indent=2)}

        Return a JSON object with keys:
        - patterns
        - recommendations
        - risk_categories
        - tips
        """

        response = model.generate_content(
            contents=prompt,
            generation_config=types.GenerationConfig(response_mime_type="application/json")
        )

        if response.text:
            return json.loads(response.text)

        return {}

    except Exception as e:
        st.error(f"Error analyzing waste patterns: {str(e)}")
        return {}

def generate_shopping_list(current_items, preferences=None):
    try:
        model = get_gemini_model()
        current_items_text = json.dumps([
            {'name': item['name'], 'category': item['category'], 'expiry_date': item['expiry_date']}
            for item in current_items
        ], indent=2)

        prompt = f"""
        Given this inventory:
        {current_items_text}
        Generate a shopping list. Return JSON array with:
        - item
        - category
        - priority (High/Medium/Low)
        - reason
        """

        response = model.generate_content(
            contents=prompt,
            generation_config=types.GenerationConfig(response_mime_type="application/json")
        )

        if response.text:
            shopping_list = json.loads(response.text)
            return shopping_list if isinstance(shopping_list, list) else []

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
        Detect duplicates between new items and existing inventory.
        New:
        {new_text}
        Existing:
        {existing_text}

        Return JSON with:
        - duplicates
        - recommendations
        """

        response = model.generate_content(
            contents=prompt,
            generation_config=types.GenerationConfig(response_mime_type="application/json")
        )

        if response.text:
            return json.loads(response.text)

        return {'duplicates': [], 'recommendations': []}

    except Exception as e:
        st.error(f"Error detecting duplicates: {str(e)}")
        return {'duplicates': [], 'recommendations': []}
