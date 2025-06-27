import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import calendar
from utils.s3_storage import get_user_food_items

st.set_page_config(
    page_title="ExpiryGenie - Calendar",
    page_icon="📅",
    layout="wide"
)

def check_authentication():
    if not st.session_state.get('logged_in', False):
        st.error("🔒 Please login first to access the calendar")
        st.stop()

def main():
    check_authentication()
    
    st.markdown("# 📅 Expiry Calendar")
    st.markdown("### Color-coded visual timeline of your food expiry dates")
    
    # Load fresh data from database
    db_items = get_user_food_items(st.session_state.current_user)
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
    
    # Calendar view options
    col1, col2, col3 = st.columns(3)
    with col1:
        view_mode = st.selectbox("📊 View Mode:", ["Monthly", "Weekly", "Daily"], key="cal_view_mode_unique")
    with col2:
        selected_date = st.date_input("📅 Select Date:", value=datetime.now().date())
    with col3:
        show_categories = st.multiselect(
            "🏷️ Filter Categories:",
            options=list(set(item['category'] for item in food_items)),
            default=list(set(item['category'] for item in food_items))
        )
    
    # Filter items by categories
    filtered_items = [
        item for item in food_items 
        if item['category'] in show_categories
    ]
    
    if view_mode == "Monthly":
        display_monthly_calendar(selected_date, filtered_items)
    elif view_mode == "Weekly":
        display_weekly_calendar(selected_date, filtered_items)
    else:
        display_daily_calendar(selected_date, filtered_items)
    
    # Legend
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🟢 **Safe** - More than 3 days")
    with col2:
        st.markdown("🟡 **Expiring Soon** - 1-3 days")
    with col3:
        st.markdown("🔴 **Expired** - Past expiry date")

def display_monthly_calendar(selected_date, items):
    st.markdown(f"### 📅 {selected_date.strftime('%B %Y')} Calendar")
    
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
                status = "🔴"
            elif days_until_expiry <= 3:
                status = "🟡"
            else:
                status = "🟢"
            
            items_by_date[day].append({
                'name': item['name'],
                'status': status,
                'category': item['category']
            })
    
    # Display calendar
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Header
    cols = st.columns(7)
    for i, day in enumerate(days_of_week):
        cols[i].markdown(f"**{day[:3]}**")
    
    # Calendar grid
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                # Day number
                day_text = f"**{day}**"
                
                # Add items info
                if day in items_by_date:
                    items_info = items_by_date[day]
                    status_counts = {}
                    for item in items_info:
                        status = item['status']
                        status_counts[status] = status_counts.get(status, 0) + 1
                    
                    status_text = " ".join([f"{status}{count}" for status, count in status_counts.items()])
                    day_text += f"\n{status_text}"
                    
                    # Show item details on click
                    if cols[i].button(f"{day}", key=f"day_{day}"):
                        show_day_details(day, month, year, items_info)
                else:
                    cols[i].markdown(day_text)

def display_weekly_calendar(selected_date, items):
    st.markdown(f"### 📅 Week of {selected_date.strftime('%B %d, %Y')}")
    
    # Get start of week (Monday)
    start_of_week = selected_date - timedelta(days=selected_date.weekday())
    
    # Create week dates
    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]
    
    cols = st.columns(7)
    today = datetime.now().date()
    
    for i, date in enumerate(week_dates):
        with cols[i]:
            st.markdown(f"**{date.strftime('%a')}<br>{date.strftime('%m/%d')}**", unsafe_allow_html=True)
            
            # Find items for this date
            day_items = []
            for item in items:
                expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                if expiry_date == date:
                    days_until_expiry = (expiry_date - today).days
                    if days_until_expiry < 0:
                        status = "🔴"
                    elif days_until_expiry <= 3:
                        status = "🟡"
                    else:
                        status = "🟢"
                    
                    day_items.append({
                        'name': item['name'],
                        'status': status,
                        'category': item['category']
                    })
            
            # Display items
            for item in day_items[:3]:  # Show max 3 items
                st.markdown(f"{item['status']} {item['name'][:10]}...")
            
            if len(day_items) > 3:
                st.markdown(f"... +{len(day_items) - 3} more")

def display_daily_calendar(selected_date, items):
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
            elif days_until_expiry <= 3:
                status = "🟡 Expiring Soon"
            else:
                status = "🟢 Safe"
            
            day_items.append({
                'name': item['name'],
                'status': status,
                'category': item['category'],
                'quantity': item['quantity'],
                'purchase_date': item['purchase_date']
            })
    
    if day_items:
        st.markdown(f"#### Items expiring on this date: {len(day_items)}")
        
        for item in day_items:
            with st.expander(f"{item['status']} {item['name']}", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Category:** {item['category']}")
                    st.write(f"**Quantity:** {item['quantity']}")
                with col2:
                    st.write(f"**Purchase Date:** {item['purchase_date']}")
                    st.write(f"**Status:** {item['status']}")
                with col3:
                    if "Expired" in item['status']:
                        st.error("⚠️ This item has expired!")
                    elif "Soon" in item['status']:
                        st.warning("⏰ Use this item soon!")
                    else:
                        st.success("✅ Item is still fresh!")
    else:
        st.info("📝 No items expiring on this date.")
    
    # Show items expiring in the next 7 days
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

def show_day_details(day, month, year, items):
    st.markdown(f"#### Items expiring on {month}/{day}/{year}:")
    
    for item in items:
        st.markdown(f"{item['status']} **{item['name']}** ({item['category']})")

# Visualization section
def create_expiry_timeline(items):
    """Create a timeline visualization of expiry dates"""
    
    if not items:
        return None
    
    # Prepare data
    dates = []
    names = []
    categories = []
    statuses = []
    colors = []
    
    today = datetime.now().date()
    
    for item in items:
        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
        days_until_expiry = (expiry_date - today).days
        
        dates.append(expiry_date)
        names.append(item['name'])
        categories.append(item['category'])
        
        if days_until_expiry < 0:
            status = "Expired"
            color = "red"
        elif days_until_expiry <= 3:
            status = "Expiring Soon"
            color = "orange"
        else:
            status = "Safe"
            color = "green"
        
        statuses.append(status)
        colors.append(color)
    
    # Create scatter plot
    fig = px.scatter(
        x=dates,
        y=names,
        color=statuses,
        color_discrete_map={
            "Safe": "green",
            "Expiring Soon": "orange", 
            "Expired": "red"
        },
        title="Food Expiry Timeline",
        labels={'x': 'Expiry Date', 'y': 'Food Items'}
    )
    
    # Add vertical line for today
    fig.add_vline(x=today, line_dash="dash", line_color="blue", 
                  annotation_text="Today", annotation_position="top")
    
    return fig

# Sidebar navigation
with st.sidebar:
    st.markdown("## 🧞‍♂️ ExpiryGenie")
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("pages/1_🏠_Landing.py")
    if st.button("🚪 Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Logged out successfully!")
        st.switch_page("pages/1_🏠_Landing.py")

if __name__ == "__main__":
    main()
