import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from utils.food_data import add_food_item, get_food_categories, calculate_expiry_date
from utils.gemini_client import process_voice_input, process_image_input
from utils.voice_input import voice_to_text
from utils.image_processing import extract_text_from_image, process_food_image

st.set_page_config(
    page_title="ExpiryGenie - Dashboard",
    page_icon="📱",
    layout="wide"
)

def check_authentication():
    if not st.session_state.get('logged_in', False):
        st.error("🔒 Please login first to access the dashboard")
        st.stop()

def main():
    check_authentication()
    
    st.markdown("# 📱 ExpiryGenie Dashboard")
    st.markdown(f"Welcome back, **{st.session_state.current_user}**! 🎉")
    
    # Sidebar for input method selection
    st.sidebar.markdown("## 🎯 Add Food Items")
    input_method = st.sidebar.selectbox(
        "Choose Input Method:",
        ["📝 Manual Entry", "🎤 Voice Input", "📸 Image/OCR Scan"]
    )
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if input_method == "📝 Manual Entry":
            manual_entry_section()
        elif input_method == "🎤 Voice Input":
            voice_input_section()
        elif input_method == "📸 Image/OCR Scan":
            image_input_section()
    
    with col2:
        quick_stats_section()
    
    # Display current food items
    st.markdown("---")
    display_food_items()

def manual_entry_section():
    st.markdown("### 📝 Manual Food Entry")
    
    with st.form("manual_food_entry"):
        col1, col2 = st.columns(2)
        
        with col1:
            food_name = st.text_input("🍎 Food Item Name", placeholder="e.g., Milk, Bananas, Chicken")
            purchase_date = st.date_input("📅 Purchase Date", value=datetime.now().date())
            category = st.selectbox("📂 Category", get_food_categories())
        
        with col2:
            expiry_date = st.date_input("⏰ Expiry Date", value=datetime.now().date() + timedelta(days=7))
            quantity = st.text_input("📦 Quantity", placeholder="e.g., 1 gallon, 2 lbs")
            opened = st.checkbox("📦 Already Opened/Cooked")
        
        submit_manual = st.form_submit_button("➕ Add Food Item", type="primary")
        
        if submit_manual:
            if food_name:
                # Adjust expiry date if opened
                final_expiry = expiry_date
                if opened:
                    # Reduce shelf life for opened items
                    days_diff = (expiry_date - purchase_date).days
                    reduced_days = max(1, days_diff // 3)  # Reduce to 1/3 of original
                    final_expiry = purchase_date + timedelta(days=reduced_days)
                
                food_item = {
                    'name': food_name,
                    'category': category,
                    'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                    'expiry_date': final_expiry.strftime('%Y-%m-%d'),
                    'quantity': quantity or "1 unit",
                    'opened': opened,
                    'added_method': 'manual',
                    'id': len(st.session_state.food_items)
                }
                
                st.session_state.food_items.append(food_item)
                save_food_items()
                st.success(f"✅ Added {food_name} to your inventory!")
                st.rerun()
            else:
                st.error("❌ Please enter a food item name")

def voice_input_section():
    st.markdown("### 🎤 Voice Input")
    st.info("💡 Try saying: 'I bought chicken, milk, and bananas today' or 'Add 2 pounds of ground beef expiring next Friday'")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        voice_text = st.text_area(
            "🗣️ Voice Input (or type here)",
            placeholder="Speak or type what you bought...",
            help="You can either use voice input or type your food items here"
        )
    
    with col2:
        st.markdown("#### 🎙️ Voice Controls")
        if st.button("🔴 Start Recording", use_container_width=True):
            try:
                # This would be the voice recording functionality
                voice_result = voice_to_text()
                if voice_result:
                    voice_text = voice_result
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Voice recording failed: {str(e)}")
        
        if st.button("⏹️ Stop & Process", use_container_width=True):
            if voice_text:
                process_voice_text(voice_text)
    
    if voice_text and st.button("🔄 Process Voice Input", type="primary"):
        process_voice_text(voice_text)

def process_voice_text(voice_text):
    with st.spinner("🤖 Processing your voice input with AI..."):
        try:
            extracted_items = process_voice_input(voice_text)
            
            if extracted_items:
                st.success(f"✅ Found {len(extracted_items)} food items!")
                
                # Display extracted items for confirmation
                st.markdown("#### 🔍 Confirm Extracted Items:")
                
                confirmed_items = []
                for i, item in enumerate(extracted_items):
                    with st.expander(f"📦 {item.get('name', 'Unknown Item')}", expanded=True):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            name = st.text_input("Name", value=item.get('name', ''), key=f"voice_name_{i}")
                            category = st.selectbox("Category", get_food_categories(), 
                                                  index=get_food_categories().index(item.get('category', 'Grocery')), 
                                                  key=f"voice_cat_{i}")
                        
                        with col2:
                            purchase_date = st.date_input("Purchase Date", 
                                                        value=datetime.strptime(item.get('purchase_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
                                                        key=f"voice_pdate_{i}")
                            quantity = st.text_input("Quantity", value=item.get('quantity', '1 unit'), key=f"voice_qty_{i}")
                        
                        with col3:
                            expiry_date = st.date_input("Expiry Date", 
                                                      value=datetime.strptime(item.get('expiry_date', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
                                                      key=f"voice_edate_{i}")
                            include = st.checkbox("Include this item", value=True, key=f"voice_include_{i}")
                        
                        if include:
                            confirmed_items.append({
                                'name': name,
                                'category': category,
                                'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                                'expiry_date': expiry_date.strftime('%Y-%m-%d'),
                                'quantity': quantity,
                                'opened': False,
                                'added_method': 'voice',
                                'id': len(st.session_state.food_items) + len(confirmed_items)
                            })
                
                if st.button("✅ Confirm and Add All Items", type="primary"):
                    st.session_state.food_items.extend(confirmed_items)
                    save_food_items()
                    st.success(f"🎉 Added {len(confirmed_items)} items to your inventory!")
                    st.rerun()
            else:
                st.warning("⚠️ No food items found in your input. Try being more specific!")
                
        except Exception as e:
            st.error(f"❌ Error processing voice input: {str(e)}")

def image_input_section():
    st.markdown("### 📸 Image/OCR Scanning")
    
    tab1, tab2, tab3 = st.tabs(["🧾 Receipt/Bill", "🏷️ Barcode", "📷 Food Photo"])
    
    with tab1:
        st.markdown("#### 📄 Upload Receipt or Bill")
        receipt_image = st.file_uploader(
            "Choose receipt image...",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a clear image of your grocery receipt"
        )
        
        if receipt_image is not None:
            st.image(receipt_image, caption="Uploaded Receipt", use_container_width=True)
            
            if st.button("🔍 Extract Items from Receipt", type="primary"):
                process_receipt_image(receipt_image)
    
    with tab2:
        st.markdown("#### 📊 Barcode Scanning")
        barcode_image = st.file_uploader(
            "Choose barcode image...",
            type=['png', 'jpg', 'jpeg'],
            help="Upload an image of the product barcode"
        )
        
        if barcode_image is not None:
            st.image(barcode_image, caption="Uploaded Barcode", use_container_width=True)
            
            if st.button("🔍 Scan Barcode", type="primary"):
                process_barcode_image(barcode_image)
    
    with tab3:
        st.markdown("#### 🍎 Food Photo Recognition")
        food_image = st.file_uploader(
            "Choose food image...",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a photo of your food items"
        )
        
        if food_image is not None:
            st.image(food_image, caption="Uploaded Food Photo", use_container_width=True)
            
            if st.button("🔍 Identify Food Items", type="primary"):
                process_food_photo(food_image)

def process_receipt_image(image):
    with st.spinner("🤖 Extracting items from receipt..."):
        try:
            extracted_items = process_image_input(image, "receipt")
            display_extracted_items(extracted_items, "receipt")
        except Exception as e:
            st.error(f"❌ Error processing receipt: {str(e)}")

def process_barcode_image(image):
    with st.spinner("🤖 Scanning barcode..."):
        try:
            extracted_items = process_image_input(image, "barcode")
            display_extracted_items(extracted_items, "barcode")
        except Exception as e:
            st.error(f"❌ Error scanning barcode: {str(e)}")

def process_food_photo(image):
    with st.spinner("🤖 Identifying food items..."):
        try:
            extracted_items = process_image_input(image, "food_photo")
            display_extracted_items(extracted_items, "food_photo")
        except Exception as e:
            st.error(f"❌ Error identifying food items: {str(e)}")

def display_extracted_items(extracted_items, source_type):
    if extracted_items:
        st.success(f"✅ Found {len(extracted_items)} items!")
        
        # Display items for confirmation
        st.markdown(f"#### 🔍 Confirm Extracted Items from {source_type.title()}:")
        
        confirmed_items = []
        for i, item in enumerate(extracted_items):
            with st.expander(f"📦 {item.get('name', 'Unknown Item')}", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    name = st.text_input("Name", value=item.get('name', ''), key=f"{source_type}_name_{i}")
                    category = st.selectbox("Category", get_food_categories(),
                                          index=get_food_categories().index(item.get('category', 'Grocery')),
                                          key=f"{source_type}_cat_{i}")
                
                with col2:
                    purchase_date = st.date_input("Purchase Date",
                                                value=datetime.strptime(item.get('purchase_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
                                                key=f"{source_type}_pdate_{i}")
                    quantity = st.text_input("Quantity", value=item.get('quantity', '1 unit'), key=f"{source_type}_qty_{i}")
                
                with col3:
                    expiry_date = st.date_input("Expiry Date",
                                              value=datetime.strptime(item.get('expiry_date', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
                                              key=f"{source_type}_edate_{i}")
                    include = st.checkbox("Include this item", value=True, key=f"{source_type}_include_{i}")
                
                if include:
                    confirmed_items.append({
                        'name': name,
                        'category': category,
                        'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                        'expiry_date': expiry_date.strftime('%Y-%m-%d'),
                        'quantity': quantity,
                        'opened': False,
                        'added_method': source_type,
                        'id': len(st.session_state.food_items) + len(confirmed_items)
                    })
        
        if st.button(f"✅ Confirm and Add All Items ({source_type})", type="primary", key=f"confirm_{source_type}"):
            st.session_state.food_items.extend(confirmed_items)
            save_food_items()
            st.success(f"🎉 Added {len(confirmed_items)} items to your inventory!")
            st.rerun()
    else:
        st.warning("⚠️ No items found. Try a clearer image or different angle.")

def quick_stats_section():
    st.markdown("### 📊 Quick Stats")
    
    if st.session_state.food_items:
        today = datetime.now().date()
        
        # Calculate stats
        total_items = len(st.session_state.food_items)
        safe_count = 0
        warning_count = 0
        expired_count = 0
        
        for item in st.session_state.food_items:
            expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
            days_until_expiry = (expiry_date - today).days
            
            if days_until_expiry < 0:
                expired_count += 1
            elif days_until_expiry <= 3:
                warning_count += 1
            else:
                safe_count += 1
        
        st.metric("📦 Total Items", total_items)
        st.metric("🟢 Safe", safe_count)
        st.metric("🟡 Expiring Soon", warning_count)
        st.metric("🔴 Expired", expired_count)
        st.metric("💰 Money Saved", f"${st.session_state.money_saved:.2f}")
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        if st.button("🗑️ Remove Expired", use_container_width=True):
            original_count = len(st.session_state.food_items)
            st.session_state.food_items = [
                item for item in st.session_state.food_items
                if datetime.strptime(item['expiry_date'], '%Y-%m-%d').date() >= today
            ]
            removed_count = original_count - len(st.session_state.food_items)
            if removed_count > 0:
                save_food_items()
                st.success(f"🗑️ Removed {removed_count} expired items")
                st.rerun()
        
        if st.button("📅 Go to Calendar", use_container_width=True):
            st.switch_page("pages/4_📅_Calendar.py")
            
    else:
        st.info("📝 No food items yet. Add some using the methods on the left!")

def display_food_items():
    st.markdown("### 🍎 Your Food Inventory")
    
    if not st.session_state.food_items:
        st.info("📝 Your inventory is empty. Add some food items above!")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.food_items)
    
    # Add expiry status
    today = datetime.now().date()
    
    def get_status(expiry_date_str):
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        days_until_expiry = (expiry_date - today).days
        
        if days_until_expiry < 0:
            return "🔴 Expired"
        elif days_until_expiry <= 3:
            return "🟡 Expiring Soon"
        else:
            return "🟢 Safe"
    
    df['Status'] = df['expiry_date'].apply(get_status)
    
    # Sorting options
    col1, col2, col3 = st.columns(3)
    with col1:
        sort_by = st.selectbox("Sort by:", ["expiry_date", "name", "category", "purchase_date"])
    with col2:
        sort_order = st.selectbox("Order:", ["Ascending", "Descending"])
    with col3:
        filter_status = st.selectbox("Filter by status:", ["All", "🟢 Safe", "🟡 Expiring Soon", "🔴 Expired"])
    
    # Apply filters
    if filter_status != "All":
        df = df[df['Status'] == filter_status]
    
    # Apply sorting
    ascending = sort_order == "Ascending"
    df = df.sort_values(by=sort_by, ascending=ascending)
    
    # Display items
    for idx, item in df.iterrows():
        with st.expander(f"{item['Status']} {item['name']} - Expires: {item['expiry_date']}", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.write(f"**Category:** {item['category']}")
                st.write(f"**Quantity:** {item['quantity']}")
            
            with col2:
                st.write(f"**Purchase Date:** {item['purchase_date']}")
                st.write(f"**Expiry Date:** {item['expiry_date']}")
            
            with col3:
                st.write(f"**Added via:** {item['added_method']}")
                if item.get('opened'):
                    st.write("**Status:** Opened/Cooked")
            
            with col4:
                if st.button(f"🗑️ Delete", key=f"delete_{item['id']}"):
                    st.session_state.food_items = [
                        food for food in st.session_state.food_items 
                        if food['id'] != item['id']
                    ]
                    save_food_items()
                    st.success(f"Deleted {item['name']}")
                    st.rerun()

def save_food_items():
    """Save food items to user data"""
    if st.session_state.current_user:
        if st.session_state.current_user not in st.session_state.user_data:
            st.session_state.user_data[st.session_state.current_user] = {}
        
        st.session_state.user_data[st.session_state.current_user]['food_items'] = st.session_state.food_items
        st.session_state.user_data[st.session_state.current_user]['money_saved'] = st.session_state.money_saved
        
        # Save to file
        with open('user_data.json', 'w') as f:
            json.dump(st.session_state.user_data, f)

if __name__ == "__main__":
    main()
