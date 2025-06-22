import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import Counter

st.set_page_config(
    page_title="ExpiryGenie - Statistics",
    page_icon="📊",
    layout="wide"
)

def check_authentication():
    if not st.session_state.get('logged_in', False):
        st.error("🔒 Please login first to access statistics")
        st.stop()

def main():
    check_authentication()
    
    st.markdown("# 📊 ExpiryGenie Statistics")
    st.markdown(f"### Data insights for **{st.session_state.current_user}**")
    
    if not st.session_state.food_items:
        st.info("📝 No data available yet. Add some food items to see statistics!")
        if st.button("➕ Go to Dashboard"):
            st.switch_page("pages/3_📱_Dashboard.py")
        return
    
    # Main metrics
    display_main_metrics()
    
    # Charts section
    col1, col2 = st.columns(2)
    
    with col1:
        display_expiry_status_chart()
        display_category_breakdown()
    
    with col2:
        display_timeline_chart()
        display_money_saved_chart()
    
    # Additional insights
    st.markdown("---")
    display_insights_and_recommendations()

def display_main_metrics():
    """Display main KPI metrics"""
    
    today = datetime.now().date()
    items = st.session_state.food_items
    
    # Calculate metrics
    total_items = len(items)
    safe_count = 0
    warning_count = 0
    expired_count = 0
    total_value = 0
    
    for item in items:
        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
        days_until_expiry = (expiry_date - today).days
        
        # Estimate value (simplified)
        estimated_value = estimate_food_value(item['name'], item['quantity'])
        total_value += estimated_value
        
        if days_until_expiry < 0:
            expired_count += 1
        elif days_until_expiry <= 3:
            warning_count += 1
        else:
            safe_count += 1
    
    # Display metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="📦 Total Items",
            value=total_items,
            help="Total number of food items in your inventory"
        )
    
    with col2:
        st.metric(
            label="🟢 Safe Items",
            value=safe_count,
            delta=f"{(safe_count/total_items*100):.1f}%" if total_items > 0 else "0%",
            help="Items with more than 3 days until expiry"
        )
    
    with col3:
        st.metric(
            label="🟡 Expiring Soon",
            value=warning_count,
            delta=f"{(warning_count/total_items*100):.1f}%" if total_items > 0 else "0%",
            delta_color="inverse",
            help="Items expiring within 1-3 days"
        )
    
    with col4:
        st.metric(
            label="🔴 Expired",
            value=expired_count,
            delta=f"{(expired_count/total_items*100):.1f}%" if total_items > 0 else "0%",
            delta_color="inverse",
            help="Items past their expiry date"
        )
    
    with col5:
        st.metric(
            label="💰 Money Saved",
            value=f"${st.session_state.money_saved:.2f}",
            delta=f"${total_value:.2f} inventory value",
            help="Total money saved from avoiding food waste"
        )

def display_expiry_status_chart():
    """Display pie chart of expiry status"""
    
    st.markdown("#### 🥧 Expiry Status Breakdown")
    
    today = datetime.now().date()
    status_counts = {"Safe": 0, "Expiring Soon": 0, "Expired": 0}
    
    for item in st.session_state.food_items:
        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
        days_until_expiry = (expiry_date - today).days
        
        if days_until_expiry < 0:
            status_counts["Expired"] += 1
        elif days_until_expiry <= 3:
            status_counts["Expiring Soon"] += 1
        else:
            status_counts["Safe"] += 1
    
    # Create pie chart
    fig = px.pie(
        values=list(status_counts.values()),
        names=list(status_counts.keys()),
        color_discrete_map={
            "Safe": "#2E8B57",
            "Expiring Soon": "#FFD700", 
            "Expired": "#DC143C"
        },
        title="Food Expiry Status Distribution"
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

def display_category_breakdown():
    """Display bar chart of categories"""
    
    st.markdown("#### 📊 Category Breakdown")
    
    categories = [item['category'] for item in st.session_state.food_items]
    category_counts = Counter(categories)
    
    fig = px.bar(
        x=list(category_counts.keys()),
        y=list(category_counts.values()),
        title="Items by Category",
        labels={'x': 'Category', 'y': 'Number of Items'},
        color=list(category_counts.values()),
        color_continuous_scale='viridis'
    )
    
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def display_timeline_chart():
    """Display timeline of expiry dates"""
    
    st.markdown("#### 📅 Expiry Timeline")
    
    # Prepare data
    items_data = []
    today = datetime.now().date()
    
    for item in st.session_state.food_items:
        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
        days_until_expiry = (expiry_date - today).days
        
        if days_until_expiry < 0:
            status = "Expired"
        elif days_until_expiry <= 3:
            status = "Expiring Soon"
        else:
            status = "Safe"
        
        items_data.append({
            'name': item['name'],
            'expiry_date': expiry_date,
            'status': status,
            'category': item['category']
        })
    
    # Sort by expiry date
    items_data.sort(key=lambda x: x['expiry_date'])
    
    # Create timeline chart
    fig = px.scatter(
        x=[item['expiry_date'] for item in items_data],
        y=[item['name'] for item in items_data],
        color=[item['status'] for item in items_data],
        hover_data=[item['category'] for item in items_data],
        color_discrete_map={
            "Safe": "#2E8B57",
            "Expiring Soon": "#FFD700",
            "Expired": "#DC143C"
        },
        title="Food Expiry Timeline"
    )
    
    # Add vertical line for today
    fig.add_vline(x=today, line_dash="dash", line_color="blue", 
                  annotation_text="Today")
    
    st.plotly_chart(fig, use_container_width=True)

def display_money_saved_chart():
    """Display money saved over time"""
    
    st.markdown("#### 💰 Money Saved Tracking")
    
    # Simulate money saved data (in real app, this would be tracked over time)
    dates = []
    savings = []
    
    # Generate sample data for demonstration
    start_date = datetime.now().date() - timedelta(days=30)
    current_savings = 0
    
    for i in range(31):
        date = start_date + timedelta(days=i)
        # Simulate saving money by avoiding waste
        if i > 0 and len(st.session_state.food_items) > 0:
            # Estimate daily savings based on items prevented from expiring
            daily_saving = min(5.0, len(st.session_state.food_items) * 0.5)
            current_savings += daily_saving * (i / 30)  # Gradual increase
        
        dates.append(date)
        savings.append(current_savings)
    
    # Create line chart
    fig = px.line(
        x=dates,
        y=savings,
        title="Cumulative Money Saved",
        labels={'x': 'Date', 'y': 'Money Saved ($)'}
    )
    
    fig.update_traces(line_color='#2E8B57', line_width=3)
    fig.update_layout(hovermode='x')
    
    st.plotly_chart(fig, use_container_width=True)

def display_insights_and_recommendations():
    """Display AI-powered insights and recommendations"""
    
    st.markdown("### 🧠 Smart Insights & Recommendations")
    
    today = datetime.now().date()
    
    # Analyze data for insights
    insights = []
    recommendations = []
    
    # Category analysis
    categories = [item['category'] for item in st.session_state.food_items]
    category_counts = Counter(categories)
    most_common_category = category_counts.most_common(1)[0] if category_counts else None
    
    if most_common_category:
        insights.append(f"📊 Your most tracked category is **{most_common_category[0]}** with {most_common_category[1]} items")
    
    # Expiry analysis
    expiring_soon = []
    expired = []
    
    for item in st.session_state.food_items:
        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
        days_until_expiry = (expiry_date - today).days
        
        if days_until_expiry < 0:
            expired.append(item)
        elif days_until_expiry <= 3:
            expiring_soon.append(item)
    
    if expiring_soon:
        insights.append(f"⚠️ You have **{len(expiring_soon)}** items expiring in the next 3 days")
        recommendations.append("🍳 Consider cooking meals using these expiring ingredients")
    
    if expired:
        insights.append(f"🗑️ You have **{len(expired)}** expired items that should be removed")
        recommendations.append("🧹 Clean out expired items to maintain food safety")
    
    # Money saving insights
    total_value = sum(estimate_food_value(item['name'], item['quantity']) for item in st.session_state.food_items)
    if total_value > 0:
        insights.append(f"💰 Your current inventory is worth approximately **${total_value:.2f}**")
    
    # Usage pattern analysis
    added_methods = [item['added_method'] for item in st.session_state.food_items]
    method_counts = Counter(added_methods)
    most_used_method = method_counts.most_common(1)[0] if method_counts else None
    
    if most_used_method:
        insights.append(f"📱 Your favorite input method is **{most_used_method[0]}** ({most_used_method[1]} times)")
    
    # Display insights
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💡 Key Insights")
        if insights:
            for insight in insights:
                st.markdown(f"• {insight}")
        else:
            st.info("Add more food items to get personalized insights!")
    
    with col2:
        st.markdown("#### 🎯 Recommendations")
        if recommendations:
            for recommendation in recommendations:
                st.markdown(f"• {recommendation}")
        
        # Always show general recommendations
        st.markdown("• 📅 Check your calendar daily for expiring items")
        st.markdown("• 🛒 Plan meals around items expiring soon")
        st.markdown("• 📱 Use voice input for quick grocery additions")
    
    # Achievement badges
    st.markdown("---")
    st.markdown("#### 🏆 Achievements")
    
    badges = []
    
    # Item count badges
    total_items = len(st.session_state.food_items)
    if total_items >= 50:
        badges.append("🏆 Inventory Master (50+ items tracked)")
    elif total_items >= 20:
        badges.append("📦 Organized Tracker (20+ items tracked)")
    elif total_items >= 5:
        badges.append("🌱 Getting Started (5+ items tracked)")
    
    # Money saved badges
    money_saved = st.session_state.money_saved
    if money_saved >= 100:
        badges.append("💰 Money Saver Pro ($100+ saved)")
    elif money_saved >= 50:
        badges.append("💵 Thrifty Tracker ($50+ saved)")
    elif money_saved >= 10:
        badges.append("🪙 Penny Pincher ($10+ saved)")
    
    # Category diversity badge
    unique_categories = len(set(item['category'] for item in st.session_state.food_items))
    if unique_categories >= 5:
        badges.append("🌈 Category Champion (5+ categories)")
    
    # Method diversity badge
    unique_methods = len(set(item['added_method'] for item in st.session_state.food_items))
    if unique_methods >= 3:
        badges.append("🎯 Multi-Method Master (All input methods used)")
    
    if badges:
        cols = st.columns(min(3, len(badges)))
        for i, badge in enumerate(badges):
            cols[i % 3].success(badge)
    else:
        st.info("🎮 Keep tracking food to unlock achievements!")

def estimate_food_value(name, quantity):
    """Estimate the monetary value of a food item"""
    
    # Simple estimation based on common food prices
    price_estimates = {
        'milk': 3.50,
        'bread': 2.50,
        'chicken': 8.00,
        'beef': 12.00,
        'fish': 10.00,
        'eggs': 3.00,
        'cheese': 5.00,
        'apple': 1.50,
        'banana': 1.00,
        'rice': 2.00,
        'pasta': 1.50,
        'yogurt': 4.00,
    }
    
    # Default value if not found
    base_value = 3.00
    
    # Try to match food name with price estimates
    name_lower = name.lower()
    for food, price in price_estimates.items():
        if food in name_lower:
            base_value = price
            break
    
    # Adjust for quantity (simplified)
    quantity_lower = quantity.lower()
    if 'lb' in quantity_lower or 'pound' in quantity_lower:
        multiplier = 1.0
    elif 'gallon' in quantity_lower:
        multiplier = 1.0
    elif 'dozen' in quantity_lower:
        multiplier = 1.0
    else:
        # Try to extract number
        import re
        numbers = re.findall(r'\d+', quantity)
        if numbers:
            multiplier = float(numbers[0])
        else:
            multiplier = 1.0
    
    return base_value * min(multiplier, 5.0)  # Cap at 5x to avoid extreme values

if __name__ == "__main__":
    main()
