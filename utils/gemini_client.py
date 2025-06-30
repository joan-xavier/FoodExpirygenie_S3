import os
import json
import logging
from datetime import datetime
import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Gemini model
def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2-flash")

def process_voice_input(voice_text):
    """Process voice input using Gemini AI to extract food items"""
    try:
        model = get_gemini_model()

        system_prompt = f"""
        You are a food inventory assistant. Extract food items from the user's voice input.
        Provide:
        - name
        - quantity
        - category
        - purchase_date (YYYY-MM-DD)
        - expiry_date (YYYY-MM-DD)
        Return a JSON array. Today's date: {datetime.now().strftime('%Y-%m-%d')}
        """

        response = model.generate_content(
            [
                {"role": "user", "parts": [{"text": voice_text}]}
            ],
            generation_config={"response_mime_type": "application/json"},
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
    """Process image input using Gemini AI to extract food items"""
    try:
        model = get_gemini_model()
        image_file.seek(0)
        image_bytes = image_file.read()
        image_file.seek(0)

        if image_type == "receipt":
            prompt = "Extract food items from this receipt image. Return as JSON."
        elif image_type == "barcode":
            prompt = "Analyze this barcode and return food product info in JSON."
        else:  # food_photo
            prompt = "Analyze this food photo and return visible food items in JSON."

        mime_type = image_file.type if hasattr(image_file, 'type') and image_file.type else "image/jpeg"

        response = model.generate_content(
            [
                {"inline_data": {"mime_type": mime_type, "data": image_bytes}},
                {"text": prompt}
            ],
            generation_config={"response_mime_type": "application/json"}
        )

        if response.text:
            extracted_items = json.loads(response.text)
            return extracted_items if isinstance(extracted_items, list) else []
        return []
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return []

def get_recipe_suggestions(expiring_items):
    """Suggest recipes using expiring items"""
    if not expiring_items:
        return []
    try:
        model = get_gemini_model()
        items_text = ", ".join([item['name'] for item in expiring_items])

        prompt = f"""
        Suggest 3 quick recipes using: {items_text}.
        Return a JSON array of recipes with name, ingredients, prep_time, instructions, and difficulty.
        """

        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        if response.text:
            recipes = json.loads(response.text)
            return recipes if isinstance(recipes, list) else []
        return []
    except Exception as e:
        st.error(f"Error getting recipe suggestions: {str(e)}")
        return []

def analyze_food_waste_patterns(food_items):
    """Analyze food waste trends"""
    try:
        model = get_gemini_model()
        today = datetime.now().date()
        items_data = [
            {
                'name': item['name'],
                'category': item['category'],
                'days_until_expiry': (datetime.strptime(item['expiry_date'], '%Y-%m-%d').date() - today).days,
                'quantity': item['quantity'],
                'added_method': item['added_method']
            }
            for item in food_items
        ]

        prompt = f"""
        Analyze this data for waste patterns:
        {json.dumps(items_data, indent=2)}
        Return JSON object with: patterns, tips, risk_categories, and recommendations.
        """

        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        if response.text:
            analysis = json.loads(response.text)
            return analysis
        return {}
    except Exception as e:
        st.error(f"Error analyzing waste patterns: {str(e)}")
        return {}

def generate_shopping_list(current_items):
    """Suggest shopping list based on what's missing"""
    try:
        model = get_gemini_model()
        current_text = json.dumps(current_items, indent=2)

        prompt = f"""
        Based on this inventory:
        {current_text}
        Suggest new items. Return JSON array with: item, category, priority, reason.
        """

        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        if response.text:
            shopping_list = json.loads(response.text)
            return shopping_list if isinstance(shopping_list, list) else []
        return []
    except Exception as e:
        st.error(f"Error generating shopping list: {str(e)}")
        return []

def detect_duplicate_purchases(new_items, existing_items):
    """Detect duplicates between new and current food items"""
    try:
        model = get_gemini_model()
        prompt = f"""
        New items:
        {json.dumps(new_items, indent=2)}
        Existing inventory:
        {json.dumps(existing_items, indent=2)}
        Identify duplicates. Return JSON with duplicates and recommendations.
        """

        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        if response.text:
            analysis = json.loads(response.text)
            return analysis
        return {'duplicates': [], 'recommendations': []}
    except Exception as e:
        st.error(f"Error detecting duplicates: {str(e)}")
        return {'duplicates': [], 'recommendations': []}
