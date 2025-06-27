import streamlit as st

st.set_page_config(
    page_title="ExpiryGenie - Landing",
    page_icon="🧞‍♂️",
    layout="wide"
)

def main():
    # Hero Section
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0;">🧞‍♂️🍽️ ExpiryGenie</h1>
        <h2 style="color: #87CEEB; font-size: 1.5rem; font-weight: 300;">Track food easily. Store smart. Waste never.</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Features Section
    st.markdown("## ✨ Why Choose ExpiryGenie?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🎯 Smart Tracking
        - **Manual Entry**: Quick and easy food logging
        - **Voice Input**: "I bought chicken and milk today"
        - **Smart Scanning**: OCR for receipts and barcodes
        - **AI Recognition**: Automatic food identification
        """)
    
    with col2:
        st.markdown("""
        ### 📅 Visual Management
        - **Color-Coded Calendar**: Green, Yellow, Red system
        - **Expiry Alerts**: 2-3 days advance notification
        - **Category Organization**: Grocery, Pantry, Frozen
        - **Family Sync**: Share with roommates & family
        """)
    
    with col3:
        st.markdown("""
        ### 💡 Smart Features
        - **Duplicate Warnings**: Avoid buying what you have
        - **Recipe Suggestions**: Use expiring ingredients
        - **Money Tracking**: See your savings grow
        - **Gamification**: Badges and achievements
        """)
    
    # How It Works Section
    st.markdown("---")
    st.markdown("## 🚀 How It Works")
    
    step_col1, step_col2, step_col3, step_col4 = st.columns(4)
    
    with step_col1:
        st.markdown("""
        **Step 1: Add Food** 📝
        
        Choose your preferred method:
        - Type it in manually
        - Say it out loud
        - Scan receipt/barcode
        - Take a photo
        """)
    
    with step_col2:
        st.markdown("""
        **Step 2: AI Processing** 🤖
        
        ExpiryGenie automatically:
        - Identifies food items
        - Predicts expiry dates
        - Categorizes by type
        - Learns your habits
        """)
    
    with step_col3:
        st.markdown("""
        **Step 3: Track & Alert** 📱
        
        Get notified when:
        - Items expire soon
        - You're buying duplicates
        - Recipes are suggested
        - Achievements unlocked
        """)
    
    with step_col4:
        st.markdown("""
        **Step 4: Save Money** 💰
        
        Watch your savings grow:
        - Reduced food waste
        - Better meal planning
        - Smart shopping habits
        - Family coordination
        """)
    
    # Testimonials Section
    st.markdown("---")
    st.markdown("## 💬 What Our Users Say")
    
    testimonial_col1, testimonial_col2, testimonial_col3 = st.columns(3)
    
    with testimonial_col1:
        st.markdown("""
        > "ExpiryGenie saved me $200 last month! The photo input is so convenient when I'm unpacking groceries."
        
        **- Sarah M., Working Mom**
        ⭐⭐⭐⭐⭐
        """)
    
    with testimonial_col2:
        st.markdown("""
        > "Perfect for our family of 5. Everyone can update the fridge inventory, and we never waste food anymore."
        
        **- David K., Family of 5**
        ⭐⭐⭐⭐⭐
        """)
    
    with testimonial_col3:
        st.markdown("""
        > "The OCR scanning is incredible! Just snap a photo of my receipt and everything gets added automatically."
        
        **- Maria L., Busy Professional**
        ⭐⭐⭐⭐⭐
        """)
    
    # Stats Section
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Happy Users", "5000+")
    with col2:
        st.metric("Food Items Tracked", "1000+")
    with col3:
        st.metric("Money Saved", "$50+")
    with col4:
        st.metric("Waste Reduced", "100 Tons")
    
    # Call to Action
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h3>Ready to start your food-saving journey? 🌟</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Join ExpiryGenie Now", type="primary", use_container_width=True):
            st.switch_page("pages/2_🔐_Auth.py")
    
    # Features Preview
    st.markdown("---")
    st.markdown("## 📱 App Preview")
    
    preview_col1, preview_col2 = st.columns(2)
    
    with preview_col1:
        st.markdown("### 🎤 Voice Input Demo")
        st.info("Try saying: 'I bought 2 pounds of chicken, a gallon of milk, and some bananas today'")
        st.markdown("ExpiryGenie will automatically extract and categorize these items!")
    
    with preview_col2:
        st.markdown("### 📸 Image Recognition Demo")
        st.info("Upload a photo of your groceries or receipt, and watch the magic happen!")
        st.markdown("Our AI can identify multiple food items and their likely expiry dates.")

if __name__ == "__main__":
    main()
