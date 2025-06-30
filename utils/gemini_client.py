import os
import json
import logging
from datetime import datetime, timedelta
import google.generativeai as genai
from google.generativeai import types
import streamlit as st

# ✅ Fixed: Initialize Gemini client properly using configure()
def get_gemini_client():
    """Configure Gemini API client with API key"""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")
    genai.configure(api_key=api_key)
    return genai  # Return the module as client-compatible

def process_voice_input(voice_text):
    try:
        client = get_gemini_client()

        system_prompt = """
        You are a food inventory assistant. Extract food items from the user's voice input.

        The user might say things like:
        - "I bought chicken, milk, and bananas today"
        - "Add 2 pounds of ground beef expiring next Friday"
        - "I have yogurt, bread, and some apples"

        Extract each food item and provide the following information:
        - name
        - quantity
        - category
        - purchase_date (YYYY-MM-DD)
        - expiry_date (YYYY-MM-DD)

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

    except ValueError:
        st.error("Please check your Gemini API key configuration.")
        return []
    except Exception as e:
        st.error(f"Error processing voice input: {str(e)}")
        return []

def process_image_input(image_file, image_type):
    try:
        client = get_gemini_client()
        image_file.seek(0)
        image_bytes = image_file.read()
        image_file.seek(0)

        if image_type == "receipt":
            prompt = """
            Analyze this receipt/bill image and extract all food items.
            Provide: name, quantity, category, purchase_date, expiry_date.
            Return as JSON array.
            Current date: {current_date}
            """.format(current_date=datetime.now().strftime('%Y-%m-%d'))
        elif image_type == "barcode":
            prompt = """
            Analyze this barcode image and identify the food product.
            Return as JSON array with name, quantity, category, purchase_date, expiry_date.
            Current date: {current_date}
            """.format(current_date=datetime.now().strftime('%Y-%m-%d'))
        else:
            prompt = """
            Analyze this food photo and identify visible food items.
            Return as JSON array with name, quantity, category, purchase_date, expiry_date.
            Current date: {current_date}
            """.format(current_date=datetime.now().strftime('%Y-%m-%d'))

        mime_type = "image/jpeg"
        if hasattr(image_file, 'type') and image_file.type:
            mime_type = image_file.type
        elif len(image_bytes) >= 4 and image_bytes[:4] == b'\x89PNG':
            mime_type = "image/png"

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )

        if response.text:
            extracted_items = json.loads(response.text)
            return extracted_items if isinstance(extracted_items, list) else []

        return []

    except ValueError:
        st.error("Please check your Gemini API key configuration.")
        return []
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return []

def get_recipe_suggestions(expiring_items):
    if not expiring_items:
        return []

    try:
        client = get_gemini_client()
        items_text = ", ".join([item['name'] for item in expiring_items])

        prompt = f"""
        Suggest 3-5 easy recipes using expiring items: {items_text}.
        Return JSON array with: name, ingredients, prep_time, instructions, difficulty.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
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
        client = get_gemini_client()
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
        Analyze this inventory for food waste risks:
        {json.dumps(items_data, indent=2)}
        Return JSON with: patterns, risk_categories, tips, recommendations.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )

        if response.text:
            return json.loads(response.text)

        return {}

    except Exception as e:
        st.error(f"Error analyzing waste patterns: {str(e)}")
        return {}

def generate_shopping_list(current_items, preferences=None):
    try:
        client = get_gemini_client()
        current_items_text = json.dumps([
            {'name': item['name'], 'category': item['category'], 'expiry_date': item['expiry_date']}
            for item in current_items
        ], indent=2)

        prompt = f"""
        Based on this inventory:
        {current_items_text}
        Generate a smart shopping list (JSON): item, category, priority, reason.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
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
        client = get_gemini_client()

        new_items_text = json.dumps(new_items, indent=2)
        existing_items_text = json.dumps(existing_items, indent=2)

        prompt = f"""
        Check for duplicate purchases between:
        New items: {new_items_text}
        Existing inventory: {existing_items_text}
        Return JSON with duplicates and recommendations.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )

        if response.text:
            analysis = json.loads(response.text)
            return analysis

        return {'duplicates': [], 'recommendations': []}

    except Exception as e:
        st.error(f"Error detecting duplicates: {str(e)}")
        return {'duplicates': [], 'recommendations': []}
