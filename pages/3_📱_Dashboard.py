import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from utils.food_data import get_food_categories, calculate_expiry_date
from utils.gemini_client import process_voice_input, process_image_input
from utils.voice_input import voice_to_text
from utils.image_processing import extract_text_from_image, process_food_image
from utils.csv_storage import add_food_item, get_user_food_items, delete_food_item, delete_expired_items, predict_expiry_date, update_food_item_date, update_food_item_details

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
    
    # Always load food items on page load
    if 'food_items' not in st.session_state or not st.session_state.food_items:
        refresh_food_items()
    
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
    st.markdown("### 🎤 Voice Input with Speech Recognition")
    st.info("💡 Try saying: 'I bought chicken, milk, and bananas today' or 'Add 2 pounds of ground beef expiring next Friday'")
    
    # Voice recording state
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    if 'voice_text' not in st.session_state:
        st.session_state.voice_text = ""
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎤 Record Voice", type="primary", use_container_width=True):
            with st.spinner("🎙️ Recording... Speak now!"):
                try:
                    from utils.voice_input import voice_to_text
                    recognized_text = voice_to_text()
                    if recognized_text and recognized_text.strip():
                        st.session_state.voice_text = recognized_text.strip()
                        st.success(f"Voice recognized: {recognized_text[:50]}...")
                        st.rerun()
                    else:
                        st.warning("Could not recognize speech. Please try again or type manually.")
                except Exception as e:
                    st.error(f"Voice recognition error: {str(e)}")
                    st.info("Voice recognition not available. Please type your input manually.")
    
    with col2:
        # Auto-enable when there's text
        has_text = bool(st.session_state.voice_text and st.session_state.voice_text.strip())
        if st.button("🤖 Extract Food Items", use_container_width=True, disabled=not has_text):
            if st.session_state.voice_text.strip():
                process_voice_text(st.session_state.voice_text)
    
    with col3:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.voice_text = ""
            st.session_state.recording = False
            st.rerun()
    
    # Voice input text area (editable)
    voice_text = st.text_area(
        "🗣️ Voice Recognition Result / Manual Input",
        value=st.session_state.voice_text,
        placeholder="Voice recognition will appear here, or type manually...",
        help="Speak using the microphone button above, or type directly",
        height=100,
        key="voice_input_area"
    )
    
    # Update session state
    if voice_text != st.session_state.voice_text:
        st.session_state.voice_text = voice_text

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
        with st.container():
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
                    with st.spinner("Processing receipt image..."):
                        extracted_items = process_receipt_image(receipt_image)
                        if extracted_items:
                            st.session_state.extracted_items_receipt = extracted_items
                            st.success(f"Found {len(extracted_items)} items!")
                            st.rerun()
                        else:
                            st.error("No items found in the receipt")
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")
    
    # Display extracted items only once, outside the image upload section
    if "extracted_items_receipt" in st.session_state and st.session_state.extracted_items_receipt:
        st.markdown("---")
        display_extracted_items(st.session_state.extracted_items_receipt, "receipt")
    
    with tab2:
        st.markdown("#### 📊 Barcode Scanning")
        
        # Create two columns for better layout
        upload_col, display_col = st.columns([1, 1])
        
        with upload_col:
            barcode_image = st.file_uploader(
                "Choose barcode image...",
                type=['png', 'jpg', 'jpeg'],
                help="Upload an image of the product barcode",
                key="barcode_uploader"
            )
        
            if barcode_image is not None:
                try:
                    if st.button("🔍 Scan Barcode", type="primary", key="process_barcode"):
                        with st.spinner("Processing barcode image..."):
                            extracted_items = process_barcode_image(barcode_image)
                            if extracted_items:
                                st.session_state.extracted_items_barcode = extracted_items
                                st.success(f"Found {len(extracted_items)} items!")
                                st.rerun()
                            else:
                                st.error("No items found from barcode")
                except Exception as e:
                    st.error(f"Error processing image: {str(e)}")
        
        with display_col:
            if barcode_image is not None:
                st.image(barcode_image, caption="Uploaded Barcode", use_container_width=True)
    
    # Display extracted items in full width below
    if "extracted_items_barcode" in st.session_state and st.session_state.extracted_items_barcode:
        st.markdown("---")
        st.markdown("### 📊 Extracted Items from Barcode")
        display_extracted_items(st.session_state.extracted_items_barcode, "barcode")
    
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
        st.markdown("---")
        
        # Add better container for scrolling with max height
        with st.container():
            # Add CSS for better scrolling
            st.markdown("""
            <style>
            .stExpander > div[data-testid="stExpanderDetails"] {
                max-height: 300px;
                overflow-y: auto;
            }
            </style>
            """, unsafe_allow_html=True)
            
            for i, item in enumerate(current_items):
                # Create unique key using timestamp and random number to avoid duplicates
                import time
                import random
                item_key = f"{source_type}_{i}_{int(time.time())}_{random.randint(1000, 9999)}_{item.get('name', 'item').replace(' ', '_')}"
                
                with st.expander(f"📦 {item.get('name', 'Unknown Item')}", expanded=False):
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
                                                key=f"{item_key}_pdate",
                                                help="Edit purchase date")
                    quantity = st.text_input("Quantity", 
                                           value=item.get('quantity', '1 unit'), 
                                           key=f"{item_key}_qty")
                
                with col3:
                    # Use AI prediction for extracted items too
                    current_expiry = datetime.strptime(item.get('expiry_date', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')), '%Y-%m-%d').date()
                    
                    # Show AI predicted expiry if available
                    if name and st.session_state.current_user:
                        ai_predicted = predict_expiry_date(st.session_state.current_user, name, purchase_date)
                        if ai_predicted:
                            st.info(f"AI suggests: {ai_predicted.strftime('%Y-%m-%d')}")
                    
                    expiry_date = st.date_input("Expiry Date",
                                              value=current_expiry,
                                              key=f"{item_key}_edate",
                                              help="Edit expiry date (AI prediction shown above)")
                    opened = st.checkbox("Already opened", 
                                       value=item.get('opened', False),
                                       key=f"{item_key}_opened")
                
                with col4:
                    include = st.checkbox("Include", 
                                        value=True, 
                                        key=f"{item_key}_include")
                    if st.button("🗑️ Remove", key=f"remove_{source_type}_{i}_{abs(hash(str(item) + str(i)))}", help="Remove this item"):
                        # Remove item from session state
                        if session_key in st.session_state and i < len(st.session_state[session_key]):
                            current_items = st.session_state[session_key].copy()
                            current_items.pop(i)
                            st.session_state[session_key] = current_items
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
        
        if confirmed_items and st.button(f"Confirm and Add All Items ({source_type})", type="primary", key=f"confirm_{source_type}_{abs(hash(str(confirmed_items) + source_type))}"):
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
    
    # Initialize food_items if not exists or if empty
    if 'food_items' not in st.session_state or not st.session_state.food_items:
        refresh_food_items()
    
    if not st.session_state.food_items:
        st.info("📝 Your inventory is empty. Add some food items above!")
        # Show debug info to help troubleshoot
        if st.session_state.get('current_user'):
            if st.button("🔄 Try Loading Items Again"):
                refresh_food_items()
                st.rerun()
        return
    
    # Create DataFrame for better display
    items_df = pd.DataFrame(st.session_state.food_items)
    today = datetime.now().date()
    
    # Add calculated fields
    def get_status(expiry_date_str):
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        days_until_expiry = (expiry_date - today).days
        if days_until_expiry < 0:
            return "🔴 Expired"
        elif days_until_expiry <= 3:
            return "🟡 Expiring Soon"
        else:
            return "🟢 Safe"
    
    def get_days_left(expiry_date_str):
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        return (expiry_date - today).days
    
    items_df['Status'] = items_df['expiry_date'].apply(get_status)
    items_df['Days_Left'] = items_df['expiry_date'].apply(get_days_left)
    items_df['expiry_date_obj'] = pd.to_datetime(items_df['expiry_date'])
    items_df['purchase_date_obj'] = pd.to_datetime(items_df['purchase_date'])
    
    # Enhanced filtering and sorting controls
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        view_type = st.selectbox("View:", [
            "All Items", "Latest Added", "Oldest Added", 
            "Expiring Soon", "Recently Added", "By Category"
        ])
    
    with col2:
        if view_type == "By Category":
            categories = ["All"] + list(items_df['category'].unique()) if len(items_df) > 0 else ["All"]
            category_filter = st.selectbox("Category:", categories)
        else:
            sort_by = st.selectbox("Sort by:", 
                ["expiry_date", "name", "category", "purchase_date", "Days_Left"])
    
    with col3:
        status_filter = st.selectbox("Status:", 
            ["All", "🟢 Safe", "🟡 Expiring Soon", "🔴 Expired"])
    
    with col4:
        opened_filter = st.selectbox("Package Status:", 
            ["All", "Opened", "Packed"])
    
    with col5:
        # Batch operations
        if st.button("🗑️ Delete Selected", type="secondary"):
            delete_selected_items()
    
    # Add CSV download functionality
    if len(items_df) > 0:
        # Prepare export data
        export_df = items_df.copy()
        export_df = export_df.drop(['expiry_date_obj', 'purchase_date_obj'], axis=1)
        export_df = export_df.rename(columns={
            'name': 'Food Name',
            'category': 'Category', 
            'purchase_date': 'Purchase Date',
            'expiry_date': 'Expiry Date',
            'quantity': 'Quantity',
            'opened': 'Opened',
            'added_method': 'Added Method',
            'Status': 'Current Status',
            'Days_Left': 'Days Until Expiry'
        })
        
        # Convert to CSV
        csv_data = export_df.to_csv(index=False)
        
        # Add download button
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"food_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Download your complete food inventory as CSV file"
        )
    
    # Apply filters
    filtered_df = items_df.copy()
    
    # View type filtering
    if view_type == "Latest Added":
        filtered_df = filtered_df.sort_values('purchase_date_obj', ascending=False)
    elif view_type == "Oldest Added":
        filtered_df = filtered_df.sort_values('purchase_date_obj', ascending=True)
    elif view_type == "Expiring Soon":
        filtered_df = filtered_df[filtered_df['Days_Left'] <= 7].sort_values('Days_Left')
    elif view_type == "Recently Added":
        cutoff_date = today - timedelta(days=7)
        filtered_df = filtered_df[filtered_df['purchase_date_obj'] >= pd.Timestamp(cutoff_date)]
    elif view_type == "By Category" and 'category_filter' in locals() and category_filter != "All":
        filtered_df = filtered_df[filtered_df['category'] == category_filter]
    elif view_type == "All Items" and 'sort_by' in locals():
        ascending = True
        filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending)
    
    # Status filtering
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
    
    # Package status filtering
    if opened_filter == "Opened":
        filtered_df = filtered_df[filtered_df['opened'] == True]
    elif opened_filter == "Packed":
        filtered_df = filtered_df[filtered_df['opened'] == False]
    
    # Selection state
    if 'selected_items' not in st.session_state:
        st.session_state.selected_items = set()
    
    # Display summary
    st.write(f"Showing {len(filtered_df)} of {len(items_df)} items")
    
    # Select all checkbox
    if len(filtered_df) > 0:
        select_all = st.checkbox("Select All Visible Items")
        if select_all:
            st.session_state.selected_items.update(filtered_df['id'].tolist())
    
    # Display items with enhanced editing
    for idx, item in filtered_df.iterrows():
        with st.container():
            # Selection and basic info row
            col1, col2, col3, col4, col5, col6 = st.columns([0.5, 2, 1.5, 1.5, 1, 0.5])
            
            with col1:
                selected = st.checkbox("Select", 
                    value=item['id'] in st.session_state.selected_items,
                    key=f"select_item_{item['id']}",
                    label_visibility="collapsed")
                if selected:
                    st.session_state.selected_items.add(item['id'])
                else:
                    st.session_state.selected_items.discard(item['id'])
            
            with col2:
                package_icon = "📦" if not item.get('opened', False) else "📂"
                st.markdown(f"**{package_icon} {item['name']}**")
                st.caption(f"{item['category']} • {item['quantity']}")
            
            with col3:
                st.write(f"**Purchase:** {item['purchase_date']}")
            
            with col4:
                st.write(f"**Expires:** {item['expiry_date']} ({item['Days_Left']} days)")
            
            with col5:
                st.markdown(f"**{item['Status']}**")
                days_left = item['Days_Left']
                if days_left >= 0:
                    st.caption(f"{days_left} days left")
                else:
                    st.caption(f"{abs(days_left)} days overdue")
            
            with col6:
                # Single edit button for comprehensive editing
                if st.button("✏️ Edit", key=f"edit_{item['id']}", help="Edit this item"):
                    st.session_state[f"editing_{item['id']}"] = True
                    st.rerun()
            
            # Complete edit interface when editing
            if st.session_state.get(f"editing_{item['id']}", False):
                st.markdown("##### ✏️ Edit Item")
                edit_col1, edit_col2 = st.columns(2)
                
                with edit_col1:
                    new_name = st.text_input("Food Name:", value=item['name'], key=f"new_name_{item['id']}")
                    new_quantity = st.text_input("Quantity:", value=item['quantity'], key=f"new_qty_{item['id']}")
                    new_opened = st.checkbox("Opened/Cooked", value=item.get('opened', False), key=f"new_opened_{item['id']}")
                
                with edit_col2:
                    new_purchase_date = st.date_input("Purchase Date:", 
                                                    value=datetime.strptime(item['purchase_date'], '%Y-%m-%d').date(),
                                                    key=f"new_pdate_{item['id']}")
                    new_expiry_date = st.date_input("Expiry Date:", 
                                                  value=datetime.strptime(item['expiry_date'], '%Y-%m-%d').date(),
                                                  key=f"new_edate_{item['id']}")
                
                button_col1, button_col2, button_col3 = st.columns(3)
                with button_col1:
                    if st.button("💾 Save Changes", key=f"save_{item['id']}", type="primary"):
                        success1 = update_food_item_details(item['id'], new_name, new_quantity, new_opened)
                        success2 = update_food_item_date(item['id'], 'purchase_date', new_purchase_date)
                        success3 = update_food_item_date(item['id'], 'expiry_date', new_expiry_date)
                        
                        if success1 and success2 and success3:
                            st.success("All changes saved!")
                        else:
                            st.error("Some changes failed")
                        
                        st.session_state[f"editing_{item['id']}"] = False
                        refresh_food_items()
                        st.rerun()
                
                with button_col2:
                    if st.button("❌ Cancel", key=f"cancel_{item['id']}"):
                        st.session_state[f"editing_{item['id']}"] = False
                        st.rerun()
                
                with button_col3:
                    if st.button("🗑️ Delete", key=f"delete_{item['id']}", help="Delete this item"):
                        if delete_food_item(item['id'], st.session_state.current_user):
                            st.success("Item deleted!")
                            st.session_state[f"editing_{item['id']}"] = False
                            refresh_food_items()
                            st.rerun()
                        else:
                            st.error("Failed to delete item")



def delete_selected_items():
    """Delete all selected items"""
    if not hasattr(st.session_state, 'selected_items') or not st.session_state.selected_items:
        st.warning("No items selected for deletion")
        return
    
    success_count = 0
    for item_id in st.session_state.selected_items:
        if delete_food_item(item_id, st.session_state.current_user):
            success_count += 1
    
    if success_count > 0:
        st.success(f"Deleted {success_count} items")
        st.session_state.selected_items.clear()
        refresh_food_items()
        st.rerun()
    else:
        st.error("Failed to delete selected items")

def refresh_food_items():
    """Refresh food items from database"""
    if st.session_state.current_user:
        try:
            print(f"Refreshing food items for user: {st.session_state.current_user}")
            db_items = get_user_food_items(st.session_state.current_user)
            st.session_state.food_items = []
            for item in db_items:
                st.session_state.food_items.append({
                    'id': item['id'],
                    'name': item['name'],
                    'category': item['category'],
                    'purchase_date': item['purchase_date'].strftime('%Y-%m-%d') if hasattr(item['purchase_date'], 'strftime') else str(item['purchase_date']),
                    'expiry_date': item['expiry_date'].strftime('%Y-%m-%d') if hasattr(item['expiry_date'], 'strftime') else str(item['expiry_date']),
                    'quantity': item['quantity'],
                    'opened': item['opened'],
                    'added_method': item['added_method']
                })
            print(f"Successfully loaded {len(st.session_state.food_items)} items for user {st.session_state.current_user}")
        except Exception as e:
            print(f"Error loading food items: {str(e)}")
            st.session_state.food_items = []
    else:
        print("No current user found, setting empty food items")
        st.session_state.food_items = []

if __name__ == "__main__":
    main()
