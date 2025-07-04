import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import calendar
import numpy as np
from utils.s3_storage import get_user_food_items, get_household_food_items
import streamlit.components.v1 as components

st.set_page_config(
    page_title="ExpiryGenie - Calendar",
    page_icon="📅",
    layout="wide"
)

def check_authentication():
    if not st.session_state.get('logged_in', False):
        st.error("🔒 Please login first to access the calendar")
        st.stop()

def get_food_items_adaptive():
    """Get food items using the appropriate storage method based on user mode"""
    if 'user_mode' not in st.session_state:
        st.session_state['user_mode'] = 'individual'
    
    mode = st.session_state.get('user_mode', 'individual')
    if mode == 'family':
        household_id = st.session_state.get('household_id')
        if household_id:
            return get_household_food_items(household_id)
        else:
            return []
    else:
        return get_user_food_items(st.session_state.current_user)

def main():
    check_authentication()
    
    # Apply theme from session state
    current_theme = st.session_state.get('app_theme', 'Light')
    if current_theme == "Elegant":
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #FFB6C1 0%, #FFC0CB 50%, #FFE4E1 100%);
            color: #1f2937;
        }
        .stSelectbox, .stTextInput, .stTextArea {
            background-color: rgba(255, 255, 255, 0.9);
            color: #1f2937;
            border: 2px solid #FFB6C1;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(255, 182, 193, 0.2);
        }
        .stSelectbox:focus, .stTextInput:focus, .stTextArea:focus {
            border-color: #FF69B4;
            box-shadow: 0 0 0 3px rgba(255, 182, 193, 0.3);
        }
        .stButton > button {
            background: linear-gradient(135deg, #FFB6C1 0%, #FF69B4 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(255, 182, 193, 0.4);
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #FF69B4 0%, #FFB6C1 100%);
            box-shadow: 0 6px 20px rgba(255, 182, 193, 0.5);
            transform: translateY(-2px);
        }
        .stMetric {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 182, 193, 0.1) 100%);
            border-radius: 16px;
            padding: 16px;
            border: 2px solid #FFB6C1;
            box-shadow: 0 8px 25px rgba(255, 182, 193, 0.2);
        }
        .calendar-day {
            background: rgba(255, 255, 255, 0.9);
            border: 2px solid #FFB6C1;
            border-radius: 12px;
            padding: 8px;
            margin: 2px;
            min-height: 80px;
            transition: all 0.3s ease;
        }
        .calendar-day:hover {
            border-color: #FF69B4;
            box-shadow: 0 4px 15px rgba(255, 182, 193, 0.3);
            transform: translateY(-2px);
        }
        .dot-cluster {
            display: flex;
            flex-wrap: wrap;
            gap: 2px;
            margin-top: 4px;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin: 1px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .status-dot:hover {
            transform: scale(1.2);
        }
        .dot-safe { background-color: #10b981; }
        .dot-warning { background-color: #f59e0b; }
        .dot-expired { background-color: #ef4444; }
        </style>
        """, unsafe_allow_html=True)
    
    st.markdown("# 📅 ExpiryGenie Calendar")
    st.markdown("### 🎯 Interactive Day-Dot Calendar for Smart Food Management")
    
    # Load fresh data from database
    db_items = get_food_items_adaptive()
    food_items = []
    for item in db_items:
        food_items.append({
            'id': item['id'],
            'name': item['name'],
            'category': item['category'],
            'purchase_date': item['purchase_date'],
            'expiry_date': item['expiry_date'],
            'quantity': item['quantity'],
            'opened': item['opened'],
            'added_method': item['added_method']
        })
    
    if not food_items:
        st.info("📝 No food items to display. Add some items in the Dashboard first!")
        if st.button("➕ Go to Dashboard"):
            st.switch_page("pages/3_📱_Dashboard.py")
        return
    
    # Calendar controls
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        view_mode = st.selectbox("📊 View Mode:", ["Monthly Dot Calendar", "Weekly Timeline", "Daily Details"], key="cal_view_mode")
    with col2:
        selected_date = st.date_input("📅 Select Date:", value=datetime.now().date())
    with col3:
        show_categories = st.multiselect(
            "🏷️ Filter Categories:",
            options=list(set(item['category'] for item in food_items)),
            default=list(set(item['category'] for item in food_items))
        )
    with col4:
        show_insights = st.checkbox("🧠 Show AI Insights", value=True)
    
    # Filter items by categories
    filtered_items = [
        item for item in food_items 
        if item['category'] in show_categories
    ]
    
    # Quick stats
    display_quick_stats(filtered_items)
    
    if view_mode == "Monthly Dot Calendar":
        display_monthly_dot_calendar(selected_date, filtered_items, show_insights)
    elif view_mode == "Weekly Timeline":
        display_weekly_timeline(selected_date, filtered_items)
    else:
        display_daily_details(selected_date, filtered_items)

def display_quick_stats(items):
    """Display quick statistics about food items"""
    today = datetime.now().date()
    
    total_items = len(items)
    expired_count = 0
    expiring_soon_count = 0
    safe_count = 0
    cluster_warnings = 0
    
    # Count items by status
    for item in items:
        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
        days_until_expiry = (expiry_date - today).days
        
        if days_until_expiry < 0:
            expired_count += 1
        elif days_until_expiry <= 3:
            expiring_soon_count += 1
        else:
            safe_count += 1
    
    # Check for cluster warnings (multiple items expiring same day)
    expiry_dates = {}
    for item in items:
        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
        if expiry_date not in expiry_dates:
            expiry_dates[expiry_date] = []
        expiry_dates[expiry_date].append(item)
    
    for date, date_items in expiry_dates.items():
        if len(date_items) >= 3:  # 3 or more items on same day
            cluster_warnings += 1
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Total Items", total_items)
    with col2:
        st.metric("🟢 Safe", safe_count)
    with col3:
        st.metric("🟡 Expiring Soon", expiring_soon_count)
    with col4:
        st.metric("🔴 Expired", expired_count)
    
    # Show cluster warnings
    if cluster_warnings > 0:
        st.warning(f"⚠️ **Cluster Warning:** {cluster_warnings} days have 3+ items expiring. Plan meals accordingly!")

def display_monthly_dot_calendar(selected_date, items, show_insights):
    """Display interactive monthly calendar with dot visualization"""
    st.markdown(f"### 📅 {selected_date.strftime('%B %Y')} - Day-Dot Calendar")
    
    # Get calendar data
    year = selected_date.year
    month = selected_date.month
    
    # Create calendar matrix
    cal = calendar.monthcalendar(year, month)
    
    # Process items by date
    items_by_date = {}
    today = datetime.now().date()
    
    for item in items:
        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
        if expiry_date.year == year and expiry_date.month == month:
            day = expiry_date.day
            if day not in items_by_date:
                items_by_date[day] = []
            
            # Determine status
            days_until_expiry = (expiry_date - today).days
            if days_until_expiry < 0:
                status = "expired"
                status_emoji = "🔴"
            elif days_until_expiry <= 3:
                status = "warning"
                status_emoji = "🟡"
            else:
                status = "safe"
                status_emoji = "🟢"
            
            items_by_date[day].append({
                'id': item['id'],
                'name': item['name'],
                'status': status,
                'status_emoji': status_emoji,
                'category': item['category'],
                'quantity': item['quantity'],
                'days_until_expiry': days_until_expiry,
                'expiry_date': expiry_date
            })
    
    # Display calendar grid
    days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    # Header with elegant styling
    st.markdown("---")
    header_cols = st.columns(7)
    for i, day in enumerate(days_of_week):
        header_cols[i].markdown(f"<div style='text-align: center; font-weight: 600; padding: 6px; background-color: rgba(255, 182, 193, 0.15); border-radius: 6px; font-size: 13px; color: #374151;'>{day}</div>", unsafe_allow_html=True)
    
    # Calendar grid with elegant day boxes
    for week_idx, week in enumerate(cal):
        # Create a container for each week
        with st.container():
            # Calendar row
            cols = st.columns(7)
            for col_idx, day in enumerate(week):
                if day == 0:
                    cols[col_idx].write("")
                else:
                    # Create elegant day container
                    with cols[col_idx]:
                        # Elegant day box styling
                        day_style = "background-color: rgba(255, 255, 255, 0.8); border: 1px solid #FFB6C1; border-radius: 8px; padding: 6px; margin: 1px; min-height: 70px; box-shadow: 0 2px 4px rgba(255, 182, 193, 0.1);"
                        st.markdown(f"<div style='{day_style}'>", unsafe_allow_html=True)
                        
                        # Day number with elegant styling
                        st.markdown(f"<div style='text-align: center; font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #374151;'>{day}</div>", unsafe_allow_html=True)
                        
                        # Add interactive dots
                        if day in items_by_date:
                            day_items = items_by_date[day]
                            
                            # Group by status
                            safe_items = [item for item in day_items if item['status'] == 'safe']
                            warning_items = [item for item in day_items if item['status'] == 'warning']
                            expired_items = [item for item in day_items if item['status'] == 'expired']
                            
                            # Create elegant dot display
                            dot_html = '<div style="display: flex; flex-wrap: wrap; gap: 2px; justify-content: center; margin: 4px 0;">'
                            
                            # Add dots for each status with elegant styling
                            for item in safe_items:
                                dot_html += f'<div class="status-dot dot-safe" title="{item["name"]} - Safe ({item["days_until_expiry"]} days left)" style="width: 10px; height: 10px; border-radius: 50%; background-color: #10b981;"></div>'
                            for item in warning_items:
                                dot_html += f'<div class="status-dot dot-warning" title="{item["name"]} - Expiring Soon ({item["days_until_expiry"]} days left)" style="width: 10px; height: 10px; border-radius: 50%; background-color: #f59e0b;"></div>'
                            for item in expired_items:
                                dot_html += f'<div class="status-dot dot-expired" title="{item["name"]} - Expired ({abs(item["days_until_expiry"])} days overdue)" style="width: 10px; height: 10px; border-radius: 50%; background-color: #ef4444;"></div>'
                            
                            dot_html += '</div>'
                            st.markdown(dot_html, unsafe_allow_html=True)
                            
                            # Show item count with elegant styling
                            total_dots = len(day_items)
                            if total_dots > 0:
                                count_style = "text-align: center; font-size: 10px; color: #6b7280; margin: 2px 0; font-weight: 500;"
                                st.markdown(f"<div style='{count_style}'>{total_dots} item{'s' if total_dots > 1 else ''}</div>", unsafe_allow_html=True)
                            
                            # Elegant button for details
                            button_key = f"details_{day}_{week_idx}_{col_idx}"
                            if st.button(f"📋", key=button_key, help=f"View {total_dots} items for {day}", use_container_width=True):
                                # Toggle the details state
                                if f"show_details_{day}" not in st.session_state:
                                    st.session_state[f"show_details_{day}"] = True
                                else:
                                    st.session_state[f"show_details_{day}"] = not st.session_state[f"show_details_{day}"]
                            
                            # Elegant cluster warning
                            if len(day_items) >= 3:
                                warning_style = "background-color: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 4px; padding: 2px; margin: 2px 0; text-align: center; font-size: 9px; color: #92400e; font-weight: 500;"
                                st.markdown(f"<div style='{warning_style}'>⚠️ {len(day_items)}</div>", unsafe_allow_html=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
        
        # Display details for this week if any day is selected
        week_has_details = False
        for day in week:
            if day != 0 and f"show_details_{day}" in st.session_state and st.session_state[f"show_details_{day}"]:
                week_has_details = True
                break
        
        if week_has_details:
            # Create elegant details section with better spacing
            st.markdown("---")
            st.markdown("#### 📋 Day Details")
            
            # Create a single container that adjusts size based on content
            with st.container():
                # Track which days have details to show
                days_with_details = []
                for day in week:
                    if day != 0 and f"show_details_{day}" in st.session_state and st.session_state[f"show_details_{day}"]:
                        days_with_details.append(day)
                
                if days_with_details:
                    # Calculate dynamic height based on number of items
                    total_items = 0
                    for day in days_with_details:
                        if day in items_by_date:
                            total_items += len(items_by_date[day])
                    
                    # Dynamic height calculation (minimum 200px, add 60px per item)
                    dynamic_height = max(200, 200 + (total_items * 60))
                    
                    # Create responsive grid layout
                    if len(days_with_details) <= 3:
                        # Use 3 columns for 1-3 days
                        detail_cols = st.columns(3)
                        cols_per_day = 3
                    elif len(days_with_details) <= 4:
                        # Use 4 columns for 4 days
                        detail_cols = st.columns(4)
                        cols_per_day = 4
                    else:
                        # Use 5 columns for 5+ days
                        detail_cols = st.columns(5)
                        cols_per_day = 5
                    
                    # Distribute days across columns
                    for idx, day in enumerate(days_with_details):
                        col_idx = idx % cols_per_day
                        
                        with detail_cols[col_idx]:
                            if day in items_by_date:
                                day_items = items_by_date[day]
                                
                                # Group by status
                                safe_items = [item for item in day_items if item['status'] == 'safe']
                                warning_items = [item for item in day_items if item['status'] == 'warning']
                                expired_items = [item for item in day_items if item['status'] == 'expired']
                                
                                # Create clean list view for all items
                                all_items = []
                                
                                # Add expired items first (highest priority)
                                for item in expired_items:
                                    all_items.append({
                                        'name': item['name'],
                                        'category': item['category'],
                                        'status': 'expired',
                                        'days': abs(item['days_until_expiry']),
                                        'emoji': '🔴'
                                    })
                                
                                # Add warning items
                                for item in warning_items:
                                    all_items.append({
                                        'name': item['name'],
                                        'category': item['category'],
                                        'status': 'warning',
                                        'days': item['days_until_expiry'],
                                        'emoji': '🟡'
                                    })
                                
                                # Add safe items
                                for item in safe_items:
                                    all_items.append({
                                        'name': item['name'],
                                        'category': item['category'],
                                        'status': 'safe',
                                        'days': item['days_until_expiry'],
                                        'emoji': '🟢'
                                    })
                                
                                # Build all items HTML at once
                                items_html = ""
                                if all_items:
                                    for item in all_items:
                                        # Create item row with status-based styling and better spacing
                                        if item['status'] == 'expired':
                                            item_style = "background-color: rgba(239, 68, 68, 0.15); border-left: 4px solid #ef4444; padding: 12px; margin: 8px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(239, 68, 68, 0.1);"
                                            time_text = f"{item['days']} days overdue"
                                        elif item['status'] == 'warning':
                                            item_style = "background-color: rgba(245, 158, 11, 0.15); border-left: 4px solid #f59e0b; padding: 12px; margin: 8px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(245, 158, 11, 0.1);"
                                            time_text = f"{item['days']} days left"
                                        else:
                                            item_style = "background-color: rgba(16, 185, 129, 0.15); border-left: 4px solid #10b981; padding: 12px; margin: 8px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(16, 185, 129, 0.1);"
                                            time_text = f"{item['days']} days left"
                                        
                                        # Show full name with better formatting
                                        display_name = item['name']
                                        
                                        items_html += f"""
                                        <div style='{item_style}'>
                                            <div style='font-weight: 600; font-size: 14px; color: #1f2937; line-height: 1.4; margin-bottom: 4px;'>{item['emoji']} {display_name}</div>
                                            <div style='font-size: 12px; color: #6b7280; font-weight: 500;'>{item['category']} • {time_text}</div>
                                        </div>
                                        """
                                
                                # Build insights HTML
                                insights_html = ""
                                if show_insights and day_items:
                                    insights_html = "<div style='margin-top: 16px; padding-top: 12px; border-top: 2px solid #FFB6C1;'>"
                                    insights_html += "<div style='font-weight: 600; font-size: 14px; color: #FF69B4; margin-bottom: 8px;'>🧠 Smart Insights:</div>"
                                    
                                    total_items = len(day_items)
                                    if total_items >= 5:
                                        insights_html += "<div style='background-color: rgba(245, 158, 11, 0.1); padding: 8px; border-radius: 6px; margin: 4px 0; font-size: 12px; color: #f59e0b;'>⚠️ High Volume Day</div>"
                                    elif total_items >= 3:
                                        insights_html += "<div style='background-color: rgba(59, 130, 246, 0.1); padding: 8px; border-radius: 6px; margin: 4px 0; font-size: 12px; color: #3b82f6;'>🍳 Perfect for Meal Planning</div>"
                                    
                                    if len(expired_items) > 0:
                                        insights_html += "<div style='background-color: rgba(239, 68, 68, 0.1); padding: 8px; border-radius: 6px; margin: 4px 0; font-size: 12px; color: #ef4444;'>🚨 Action Required - Items Expired</div>"
                                    
                                    # Category insights
                                    categories = [item['category'] for item in day_items]
                                    unique_categories = set(categories)
                                    if len(unique_categories) >= 3:
                                        insights_html += "<div style='background-color: rgba(16, 185, 129, 0.1); padding: 8px; border-radius: 6px; margin: 4px 0; font-size: 12px; color: #10b981;'>🥗 Diverse Food Categories</div>"
                                    
                                    # Recipe suggestions
                                    if 'Dairy' in categories and 'Vegetables' in categories:
                                        insights_html += "<div style='background-color: rgba(16, 185, 129, 0.1); padding: 8px; border-radius: 6px; margin: 4px 0; font-size: 12px; color: #10b981;'>🥛🥬 Perfect for Pasta or Smoothies</div>"
                                    elif 'Meat' in categories and 'Vegetables' in categories:
                                        insights_html += "<div style='background-color: rgba(16, 185, 129, 0.1); padding: 8px; border-radius: 6px; margin: 4px 0; font-size: 12px; color: #10b981;'>🥩🥬 Great for Stir-fry or Stew</div>"
                                    
                                    insights_html += "</div>"
                                
                                # Create complete container with all content in one HTML block
                                complete_html = f"""
                                <div style="background-color: rgba(255, 255, 255, 0.95); border: 2px solid #FFB6C1; border-radius: 12px; padding: 16px; margin: 8px 4px; height: 400px; box-shadow: 0 4px 12px rgba(255, 182, 193, 0.2); display: flex; flex-direction: column;">
                                    <div style="text-align: center; font-weight: 700; font-size: 20px; margin-bottom: 12px; color: #FF69B4; padding: 8px; background: linear-gradient(135deg, rgba(255, 182, 193, 0.2) 0%, rgba(255, 105, 180, 0.1) 100%); border-radius: 8px; flex-shrink: 0;">{day}</div>
                                    <div style="flex: 1; overflow-y: auto; padding-right: 8px;">
                                        {items_html}
                                        {insights_html}
                                    </div>
                                </div>
                                """
                                
                                # Use st.components.html for better HTML rendering
                                components.html(complete_html, height=400, scrolling=True)
                                
                            else:
                                # Empty day container
                                empty_html = f"""
                                <div style="background-color: rgba(255, 255, 255, 0.95); border: 2px solid #FFB6C1; border-radius: 12px; padding: 16px; margin: 8px 4px; height: 400px; box-shadow: 0 4px 12px rgba(255, 182, 193, 0.2); display: flex; flex-direction: column;">
                                    <div style="text-align: center; font-weight: 700; font-size: 20px; margin-bottom: 12px; color: #FF69B4; padding: 8px; background: linear-gradient(135deg, rgba(255, 182, 193, 0.2) 0%, rgba(255, 105, 180, 0.1) 100%); border-radius: 8px; flex-shrink: 0;">{day}</div>
                                    <div style="flex: 1; display: flex; align-items: center; justify-content: center;">
                                        <div style="text-align: center; color: #6b7280; font-style: italic;">No items for this day</div>
                                    </div>
                                </div>
                                """
                                components.html(empty_html, height=400, scrolling=False)
                else:
                    # No days selected - show empty state
                    st.markdown("<div style='text-align: center; padding: 40px; color: #6b7280; font-style: italic; background: rgba(255, 255, 255, 0.5); border-radius: 12px; border: 2px dashed #FFB6C1;'>Click on any day above to view its food items</div>", unsafe_allow_html=True)

def display_weekly_timeline(selected_date, items):
    """Display weekly timeline view"""
    st.markdown(f"### 📅 Week of {selected_date.strftime('%B %d, %Y')}")
    
    # Get start of week (Monday)
    start_of_week = selected_date - timedelta(days=selected_date.weekday())
    
    # Create week dates
    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]
    
    # Create timeline data
    timeline_data = []
    today = datetime.now().date()
    
    for date in week_dates:
        day_items = []
        for item in items:
            expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
            if expiry_date == date:
                days_until_expiry = (expiry_date - today).days
                if days_until_expiry < 0:
                    status = "Expired"
                    color = "#ef4444"
                elif days_until_expiry <= 3:
                    status = "Expiring Soon"
                    color = "#f59e0b"
                else:
                    status = "Safe"
                    color = "#10b981"
                
                day_items.append({
                    'name': item['name'],
                    'status': status,
                    'color': color,
                    'category': item['category'],
                    'days_until_expiry': days_until_expiry
                })
        
        timeline_data.append({
            'date': date,
            'items': day_items
        })
    
    # Display timeline
    for day_data in timeline_data:
        date = day_data['date']
        day_items = day_data['items']
        
        with st.expander(f"{date.strftime('%A, %B %d')} - {len(day_items)} items", expanded=len(day_items) > 0):
            if day_items:
                for item in day_items:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.markdown(f"**{item['name']}** ({item['category']})")
                    with col2:
                        st.markdown(f"<span style='color: {item['color']}; font-weight: bold;'>{item['status']}</span>", unsafe_allow_html=True)
                    with col3:
                        if item['days_until_expiry'] < 0:
                            st.error(f"{abs(item['days_until_expiry'])} days overdue")
                        else:
                            st.info(f"{item['days_until_expiry']} days left")
            else:
                st.info("No items expiring on this date")

def display_daily_details(selected_date, items):
    """Display detailed daily view with AI insights"""
    st.markdown(f"### 📅 {selected_date.strftime('%A, %B %d, %Y')}")
    
    # Find items for selected date
    day_items = []
    today = datetime.now().date()
    
    for item in items:
        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
        if expiry_date == selected_date:
            days_until_expiry = (expiry_date - today).days
            if days_until_expiry < 0:
                status = "🔴 Expired"
                priority = "high"
            elif days_until_expiry <= 3:
                status = "🟡 Expiring Soon"
                priority = "medium"
            else:
                status = "🟢 Safe"
                priority = "low"
            
            day_items.append({
                'id': item['id'],
                'name': item['name'],
                'status': status,
                'priority': priority,
                'category': item['category'],
                'quantity': item['quantity'],
                'purchase_date': item['purchase_date'],
                'days_until_expiry': days_until_expiry
            })
    
    if day_items:
        st.markdown(f"#### 🎯 Items expiring on this date: {len(day_items)}")
        
        # Sort by priority
        day_items.sort(key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['priority']])
        
        for item in day_items:
            with st.expander(f"{item['status']} {item['name']}", expanded=item['priority'] in ['high', 'medium']):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write(f"**Category:** {item['category']}")
                    st.write(f"**Quantity:** {item['quantity']}")
                with col2:
                    st.write(f"**Purchase Date:** {item['purchase_date']}")
                    st.write(f"**Status:** {item['status']}")
                with col3:
                    if "Expired" in item['status']:
                        st.error("⚠️ This item has expired!")
                        st.button("🗑️ Mark as Used", key=f"used_{item['id']}")
                    elif "Soon" in item['status']:
                        st.warning("⏰ Use this item soon!")
                        st.button("✅ Mark as Used", key=f"used_{item['id']}")
                    else:
                        st.success("✅ Item is still fresh!")
                with col4:
                    st.button("✏️ Edit", key=f"edit_{item['id']}")
                    st.button("🗑️ Delete", key=f"delete_{item['id']}")
        
        # AI Insights
        if len(day_items) >= 3:
            st.markdown("---")
            st.markdown("#### 🧠 AI Insights")
            
            expired_items = [item for item in day_items if "Expired" in item['status']]
            expiring_items = [item for item in day_items if "Soon" in item['status']]
            
            if expired_items:
                st.error(f"⚠️ **Action Required:** {len(expired_items)} items have expired. Consider composting or safe disposal.")
            
            if expiring_items:
                st.warning(f"🍳 **Meal Planning Opportunity:** {len(expiring_items)} items expiring today. Perfect for a 'use-it-up' meal!")
                
                # Suggest recipes based on categories
                categories = [item['category'] for item in expiring_items]
                if 'Dairy' in categories:
                    st.info("🥛 **Recipe Suggestion:** Consider making a creamy pasta or smoothie with dairy items")
                if 'Vegetables' in categories:
                    st.info("🥬 **Recipe Suggestion:** Perfect for a stir-fry or soup with fresh vegetables")
                if 'Meat' in categories:
                    st.info("🥩 **Recipe Suggestion:** Great for a hearty stew or casserole with meat items")
    else:
        st.info("📝 No items expiring on this date.")
    
    # Show upcoming items
    st.markdown("---")
    st.markdown("#### 📋 Coming up in the next 7 days:")
    
    upcoming_items = []
    for i in range(1, 8):
        future_date = selected_date + timedelta(days=i)
        for item in items:
            expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
            if expiry_date == future_date:
                upcoming_items.append({
                    'name': item['name'],
                    'expiry_date': expiry_date,
                    'days_away': i,
                    'category': item['category']
                })
    
    if upcoming_items:
        for item in upcoming_items:
            if item['days_away'] <= 3:
                st.warning(f"🟡 **{item['name']}** expires in {item['days_away']} day(s) ({item['expiry_date']})")
            else:
                st.info(f"🟢 **{item['name']}** expires in {item['days_away']} day(s) ({item['expiry_date']})")
    else:
        st.success("🎉 No items expiring in the next 7 days!")

def show_day_details_enhanced(day, month, year, items, show_insights):
    """Show enhanced day details with AI insights"""
    st.markdown(f"#### 📅 Items for {month}/{day}/{year}")
    
    if not items:
        st.info("No items expiring on this date.")
        return
    
    # Group by status
    safe_items = [item for item in items if item['status'] == 'safe']
    warning_items = [item for item in items if item['status'] == 'warning']
    expired_items = [item for item in items if item['status'] == 'expired']
    
    # Display items by priority
    if expired_items:
        st.error(f"🔴 **Expired Items ({len(expired_items)})**")
        for item in expired_items:
            st.markdown(f"- {item['name']} ({item['category']}) - {abs(item['days_until_expiry'])} days overdue")
    
    if warning_items:
        st.warning(f"🟡 **Expiring Soon ({len(warning_items)})**")
        for item in warning_items:
            st.markdown(f"- {item['name']} ({item['category']}) - {item['days_until_expiry']} days left")
    
    if safe_items:
        st.success(f"🟢 **Safe Items ({len(safe_items)})**")
        for item in safe_items:
            st.markdown(f"- {item['name']} ({item['category']}) - {item['days_until_expiry']} days left")
    
    # AI Insights
    if show_insights and items:
        st.markdown("---")
        st.markdown("#### 🧠 Smart Insights")
        
        total_items = len(items)
        
        if total_items >= 5:
            st.warning("⚠️ **High Volume Day:** 5+ items expiring. Consider meal prep or sharing with neighbors.")
        
        if len(expired_items) > 0:
            st.error("🚨 **Immediate Action:** Expired items detected. Please dispose safely.")
        
        if len(warning_items) >= 3:
            st.warning("🍳 **Meal Planning:** Multiple items expiring soon. Perfect for a 'fridge clean-out' meal!")
        
        # Category-based insights
        categories = [item['category'] for item in items]
        unique_categories = set(categories)
        
        if len(unique_categories) >= 4:
            st.info("🥗 **Diverse Ingredients:** Items from 4+ categories. Great for a varied meal!")
        
        if 'Dairy' in categories and 'Vegetables' in categories:
            st.info("🥛🥬 **Recipe Match:** Dairy + Vegetables = Perfect for creamy pasta or smoothies!")
        
        if 'Meat' in categories and 'Vegetables' in categories:
            st.info("🥩🥬 **Recipe Match:** Meat + Vegetables = Ideal for stir-fry or stew!")

# Sidebar navigation
with st.sidebar:
    st.markdown("## 🧞‍♂️ ExpiryGenie")
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("pages/1_🏠_Landing.py")
    if st.button("📱 Dashboard", use_container_width=True):
        st.switch_page("pages/3_📱_Dashboard.py")
    if st.button("📊 Statistics", use_container_width=True):
        st.switch_page("pages/5_📊_Stats.py")
    # Show logout only if logged in
    if st.session_state.get('logged_in', False):
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Logged out successfully!")
            st.switch_page("pages/1_🏠_Landing.py")

if __name__ == "__main__":
    main()
