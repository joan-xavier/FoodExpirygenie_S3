import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from utils.food_data import get_food_categories, calculate_expiry_date
from utils.gemini_client import process_voice_input, process_image_input
from utils.voice_input import voice_to_text
from utils.image_processing import extract_text_from_image, process_food_image
from utils.database import add_food_item, get_user_food_items, delete_food_item, delete_expired_items

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
    
    # Sidebar navigation and controls
    with st.sidebar:
        st.markdown("## 🧞‍♂️ ExpiryGenie")
        
        if st.button("🏠 Home", use_container_width=True):
            st.switch_page("pages/1_🏠_Landing.py")
            
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Logged out successfully!")
            st.switch_page("pages/1_🏠_Landing.py")
        
        st.markdown("## 🎯 Add Food Items")
        input_method = st.selectbox(
            "Choose Input Method:",
            ["📝 Manual Entry", "🎤 Voice Input", "📸 Image/OCR Scan"]
        )
    
    # Main content area - full width for input methods
    if input_method == "📝 Manual Entry":
        manual_entry_section()
    elif input_method == "🎤 Voice Input":
        voice_input_section()
    elif input_method == "📸 Image/OCR Scan":
        image_input_section()
    
    # Display current food items
    st.markdown("---")
    display_food_items()
    
    # Quick stats section moved below
    st.markdown("---")
    quick_stats_section()

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
                
                # Add to database
                success = add_food_item(
                    user_email=st.session_state.current_user,
                    name=food_name,
                    category=category,
                    purchase_date=purchase_date,
                    expiry_date=final_expiry,
                    quantity=quantity or "1 unit",
                    opened=opened,
                    added_method='manual'
                )
                
                if success:
                    st.success(f"✅ Added {food_name} to your inventory!")
                    # Refresh food items from database
                    refresh_food_items()
                    st.rerun()
                else:
                    st.error("❌ Failed to add food item")
            else:
                st.error("❌ Please enter a food item name")

def voice_input_section():
    st.markdown("### 🎤 Voice Input")
    st.info("💡 Try saying: 'I bought chicken, milk, and bananas today' or 'Add 2 pounds of ground beef expiring next Friday'")
    
    # Voice input text area
    voice_text = st.text_area(
        "🗣️ Voice Input (or type here)",
        placeholder="Speak or type what you bought...",
        help="You can either use voice input or type your food items here",
        height=100
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎙️ Start Voice Recording", use_container_width=True):
            st.info("🎤 Voice recording feature simulated - please type in the text area above")
    
    with col2:
        if st.button("🔄 Process Voice Input", type="primary", use_container_width=True):
            if voice_text.strip():
                process_voice_text(voice_text)
            else:
                st.warning("Please enter some text first")

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
                    success_count = 0
                    for item in confirmed_items:
                        success = add_food_item(
                            user_email=st.session_state.current_user,
                            name=item['name'],
                            category=item['category'],
                            purchase_date=item['purchase_date'],
                            expiry_date=item['expiry_date'],
                            quantity=item['quantity'],
                            opened=item['opened'],
                            added_method=item['added_method']
                        )
                        if success:
                            success_count += 1
                    
                    if success_count > 0:
                        st.success(f"🎉 Added {success_count} items to your inventory!")
                        refresh_food_items()
                        st.rerun()
                    else:
                        st.error("❌ Failed to add items")
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
            help="Upload a clear image of your grocery receipt",
            key="receipt_uploader"
        )
        
        if receipt_image is not None:
            try:
                st.image(receipt_image, caption="Uploaded Receipt", use_container_width=True)
                
                if st.button("🔍 Extract Items from Receipt", type="primary", key="process_receipt"):
                    process_receipt_image(receipt_image)
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")
        
        # Display previously extracted items if they exist
        session_key = "extracted_items_receipt"
        if session_key in st.session_state and st.session_state[session_key]:
            display_extracted_items(st.session_state[session_key], "receipt")
    
    with tab2:
        st.markdown("#### 📊 Barcode Scanning")
        barcode_image = st.file_uploader(
            "Choose barcode image...",
            type=['png', 'jpg', 'jpeg'],
            help="Upload an image of the product barcode",
            key="barcode_uploader"
        )
        
        if barcode_image is not None:
            try:
                st.image(barcode_image, caption="Uploaded Barcode", use_container_width=True)
                
                if st.button("🔍 Scan Barcode", type="primary", key="process_barcode"):
                    process_barcode_image(barcode_image)
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")
        
        # Display previously extracted items if they exist
        session_key = "extracted_items_barcode"
        if session_key in st.session_state and st.session_state[session_key]:
            display_extracted_items(st.session_state[session_key], "barcode")
    
    with tab3:
        st.markdown("#### 🍎 Food Photo Recognition")
        food_image = st.file_uploader(
            "Choose food image...",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a photo of your food items",
            key="food_uploader"
        )
        
        if food_image is not None:
            try:
                st.image(food_image, caption="Uploaded Food Photo", use_container_width=True)
                
                if st.button("🔍 Identify Food Items", type="primary", key="process_food"):
                    process_food_photo(food_image)
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")
        
        # Display previously extracted items if they exist
        session_key = "extracted_items_food_photo"
        if session_key in st.session_state and st.session_state[session_key]:
            display_extracted_items(st.session_state[session_key], "food_photo")

def process_receipt_image(image):
    with st.spinner("🤖 Extracting items from receipt..."):
        try:
            # Validate image first
            if not validate_uploaded_image(image):
                return
            
            extracted_items = process_image_input(image, "receipt")
            if extracted_items:
                display_extracted_items(extracted_items, "receipt")
            else:
                st.warning("No food items found in the receipt. Try a clearer image or different angle.")
        except Exception as e:
            st.error(f"❌ Error processing receipt: {str(e)}")
            st.info("💡 Try uploading a clearer image with better lighting")

def process_barcode_image(image):
    with st.spinner("🤖 Scanning barcode..."):
        try:
            # Validate image first
            if not validate_uploaded_image(image):
                return
                
            extracted_items = process_image_input(image, "barcode")
            if extracted_items:
                display_extracted_items(extracted_items, "barcode")
            else:
                st.warning("Could not read barcode. Ensure the barcode is clear and fully visible.")
        except Exception as e:
            st.error(f"❌ Error scanning barcode: {str(e)}")
            st.info("💡 Make sure the entire barcode is visible and in focus")

def process_food_photo(image):
    with st.spinner("🤖 Identifying food items..."):
        try:
            # Validate image first
            if not validate_uploaded_image(image):
                return
                
            extracted_items = process_image_input(image, "food_photo")
            if extracted_items:
                display_extracted_items(extracted_items, "food_photo")
            else:
                st.warning("No food items detected in the image. Try a clearer photo with better lighting.")
        except Exception as e:
            st.error(f"❌ Error identifying food items: {str(e)}")
            st.info("💡 Ensure food items are clearly visible and well-lit")

def validate_uploaded_image(image_file):
    """Validate uploaded image file"""
    try:
        if image_file is None:
            st.error("No image file provided")
            return False
            
        # Check file size (limit to 10MB)
        if hasattr(image_file, 'size') and image_file.size > 10 * 1024 * 1024:
            st.error("Image file too large. Please use files smaller than 10MB.")
            return False
        
        # Reset file pointer to beginning
        image_file.seek(0)
        return True
        
    except Exception as e:
        st.error(f"Error validating image: {str(e)}")
        return False

def display_extracted_items(extracted_items, source_type):
    """Display extracted items for confirmation and editing"""
    if extracted_items:
        st.success(f"Found {len(extracted_items)} items from {source_type}")
        
        # Store items in session state to prevent loss on rerun
        session_key = f"extracted_items_{source_type}"
        if session_key not in st.session_state:
            st.session_state[session_key] = extracted_items.copy()
        
        current_items = st.session_state[session_key]
        confirmed_items = []
        
        st.markdown("### Review and Edit Items Before Adding:")
        
        for i, item in enumerate(current_items):
            item_key = f"{source_type}_{i}_{item.get('name', 'item')}"
            
            with st.expander(f"📦 {item.get('name', 'Unknown Item')}", expanded=True):
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                
                with col1:
                    name = st.text_input("Food Name", 
                                       value=item.get('name', ''), 
                                       key=f"{item_key}_name")
                    category = st.selectbox("Category", 
                                          get_food_categories(),
                                          index=get_food_categories().index(item.get('category', 'Grocery')) if item.get('category') in get_food_categories() else 0,
                                          key=f"{item_key}_cat")
                
                with col2:
                    purchase_date = st.date_input("Purchase Date",
                                                value=datetime.strptime(item.get('purchase_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
                                                key=f"{item_key}_pdate")
                    quantity = st.text_input("Quantity", 
                                           value=item.get('quantity', '1 unit'), 
                                           key=f"{item_key}_qty")
                
                with col3:
                    expiry_date = st.date_input("Expiry Date",
                                              value=datetime.strptime(item.get('expiry_date', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
                                              key=f"{item_key}_edate")
                    opened = st.checkbox("Already opened", 
                                       value=item.get('opened', False),
                                       key=f"{item_key}_opened")
                
                with col4:
                    include = st.checkbox("Include", 
                                        value=True, 
                                        key=f"{item_key}_include")
                    if st.button("Remove", key=f"{item_key}_remove"):
                        st.session_state[session_key].pop(i)
                        st.rerun()
                
                if include and name.strip():
                    confirmed_items.append({
                        'name': name.strip(),
                        'category': category,
                        'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                        'expiry_date': expiry_date.strftime('%Y-%m-%d'),
                        'quantity': quantity.strip(),
                        'opened': opened,
                        'added_method': source_type
                    })
        
        if confirmed_items and st.button(f"Confirm and Add All Items ({source_type})", type="primary", key=f"confirm_{source_type}"):
            success_count = 0
            failed_items = []
            
            for item in confirmed_items:
                try:
                    # Convert string dates to date objects
                    purchase_date_obj = datetime.strptime(item['purchase_date'], '%Y-%m-%d').date()
                    expiry_date_obj = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                    
                    success = add_food_item(
                        user_email=st.session_state.current_user,
                        name=item['name'],
                        category=item['category'],
                        purchase_date=purchase_date_obj,
                        expiry_date=expiry_date_obj,
                        quantity=item['quantity'],
                        opened=item['opened'],
                        added_method=item['added_method']
                    )
                    
                    if success:
                        success_count += 1
                    else:
                        failed_items.append(item['name'])
                        
                except Exception as e:
                    st.error(f"Error adding {item['name']}: {str(e)}")
                    failed_items.append(item['name'])
            
            if success_count > 0:
                st.success(f"Successfully added {success_count} items to your inventory!")
                refresh_food_items()
                
                # Clear session state after successful addition
                if session_key in st.session_state:
                    del st.session_state[session_key]
                    
                st.rerun()
            elif failed_items:
                st.error(f"Failed to add items: {', '.join(failed_items)}")
                st.info("This might be due to user authentication. Please try logging out and back in.")
            else:
                st.warning("No items were processed.")
        
        if not confirmed_items:
            st.warning("No items selected for addition. Please check at least one item.")
            
    else:
        st.warning("No items found. Try a clearer image or different angle.")

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
            removed_count = delete_expired_items(st.session_state.current_user)
            if removed_count > 0:
                st.success(f"🗑️ Removed {removed_count} expired items")
                refresh_food_items()
                st.rerun()
            else:
                st.info("No expired items to remove")
        
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
    
    # Top controls row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sort_by = st.selectbox("Sort by:", ["expiry_date", "name", "category", "purchase_date"])
    with col2:
        sort_order = st.selectbox("Order:", ["Ascending", "Descending"])
    with col3:
        filter_status = st.selectbox("Filter by status:", ["All", "🟢 Safe", "🟡 Expiring Soon", "🔴 Expired"])
    with col4:
        # CSV Download button
        if st.button("📥 Download CSV", type="primary"):
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download Food Inventory",
                data=csv_data,
                file_name=f"food_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
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
                    success = delete_food_item(item['id'], st.session_state.current_user)
                    if success:
                        st.success(f"Deleted {item['name']}")
                        refresh_food_items()
                        st.rerun()
                    else:
                        st.error("Failed to delete item")

def refresh_food_items():
    """Refresh food items from database"""
    if st.session_state.current_user:
        db_items = get_user_food_items(st.session_state.current_user)
        st.session_state.food_items = []
        for item in db_items:
            st.session_state.food_items.append({
                'id': item['id'],
                'name': item['name'],
                'category': item['category'],
                'purchase_date': item['purchase_date'].strftime('%Y-%m-%d'),
                'expiry_date': item['expiry_date'].strftime('%Y-%m-%d'),
                'quantity': item['quantity'],
                'opened': item['opened'],
                'added_method': item['added_method']
            })

if __name__ == "__main__":
    main()
