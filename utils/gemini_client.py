import os
import json
from datetime import datetime
import google.generativeai as genai
import streamlit as st

#  Gemini model setup
def get_gemini_model(model_name="gemini-2.5-flash"):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

#  Process voice input
def process_voice_input(voice_text):
    try:
        model = get_gemini_model()

        system_prompt = f"""
        Extract food items from user voice input. For each item, return:
        - name
        - quantity
        - category
        - purchase_date: today
        - expiry_date: based on shelf life
        Respond as JSON array.
        Current date: {datetime.now().strftime('%Y-%m-%d')}
        """

        response = model.generate_content(
            contents=[
                {"role": "user", "parts": [{"text": voice_text}]}
            ],
            generation_config={"response_mime_type": "application/json"},
            system_instruction=system_prompt
        )

        if response.text:
            items = json.loads(response.text)
            return items if isinstance(items, list) else []
        return []
    except Exception as e:
        st.error(f"Error processing voice input: {str(e)}")
        return []

#  Process image input
def process_image_input(image_file, image_type):
    try:
        model = get_gemini_model()

        image_file.seek(0)
        image_bytes = image_file.read()
        image_file.seek(0)

        mime_type = image_file.type if hasattr(image_file, 'type') and image_file.type else "image/jpeg"

        if image_type == "receipt":
            prompt = "Extract food items from this receipt. Return JSON array."
        elif image_type == "barcode":
            prompt = "Identify the food product in this barcode. Return JSON array."
        else:
            prompt = "Identify all visible food items in this photo. Return JSON array."

        response = model.generate_content(
            contents=[
                {"inline_data": {"mime_type": mime_type, "data": image_bytes}},
                {"text": prompt}
            ],
            generation_config={"response_mime_type": "application/json"}
        )

        if response.text:
            items = json.loads(response.text)
            return items if isinstance(items, list) else []
        return []
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return []

#  Suggest recipes
def get_recipe_suggestions(expiring_items):
    if not expiring_items:
        return []
    try:
        model = get_gemini_model()
        items_text = ", ".join([item['name'] for item in expiring_items])
        prompt = f"""
        Suggest 3-5 recipes using: {items_text}.
        For each recipe, return:
        - name, ingredients, prep_time, instructions, difficulty.
        Format as JSON array.
        """
        response = model.generate_content(
            contents=prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        if response.text:
            recipes = json.loads(response.text)
            return recipes if isinstance(recipes, list) else []
        return []
    except Exception as e:
        st.error(f"Error getting recipe suggestions: {str(e)}")
        return []

#  Waste pattern analysis
def analyze_food_waste_patterns(food_items):
    try:
        model = get_gemini_model()
        today = datetime.now().date()
        items_data = []
        for item in food_items:
            expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
            days_left = (expiry_date - today).days
            items_data.append({
                'name': item['name'],
                'category': item['category'],
                'days_until_expiry': days_left,
                'quantity': item['quantity'],
                'added_method': item['added_method']
            })
        prompt = f"""
        Analyze this food inventory for waste patterns:
        {json.dumps(items_data, indent=2)}
        Return JSON object with:
        - patterns, risk_categories, tips, recommendations.
        """
        response = model.generate_content(
            contents=prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        if response.text:
            return json.loads(response.text)
        return {}
    except Exception as e:
        st.error(f"Error analyzing waste patterns: {str(e)}")
        return {}

#  Generate shopping list
def generate_shopping_list(current_items, preferences=None):
    try:
        model = get_gemini_model()
        inventory = json.dumps([
            {'name': item['name'], 'category': item['category'], 'expiry_date': item['expiry_date']}
            for item in current_items
        ], indent=2)
        prompt = f"""
        Based on this inventory:
        {inventory}
        Generate a smart shopping list. Return JSON array with:
        - item, category, priority (High/Medium/Low), reason.
        """
        response = model.generate_content(
            contents=prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        if response.text:
            items = json.loads(response.text)
            return items if isinstance(items, list) else []
        return []
    except Exception as e:
        st.error(f"Error generating shopping list: {str(e)}")
        return []

#  Detect duplicates
def detect_duplicate_purchases(new_items, existing_items):
    try:
        model = get_gemini_model()
        new_text = json.dumps(new_items, indent=2)
        existing_text = json.dumps(existing_items, indent=2)
        prompt = f"""
        Check for duplicate items.
        New:
        {new_text}
        Existing:
        {existing_text}
        Return JSON with:
        - duplicates, recommendations.
        """
        response = model.generate_content(
            contents=prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        if response.text:
            return json.loads(response.text)
        return {'duplicates': [], 'recommendations': []}
    except Exception as e:
        st.error(f"Error detecting duplicates: {str(e)}")
        return {'duplicates': [], 'recommendations': []}
