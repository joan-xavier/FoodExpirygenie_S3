import cv2
import numpy as np
from PIL import Image
import streamlit as st
import pytesseract
import io

def extract_text_from_image(image_file):
    """Extract text from image using OCR (Tesseract)"""
    
    try:
        # Convert uploaded file to PIL Image
        image = Image.open(image_file)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Use pytesseract to extract text
        extracted_text = pytesseract.image_to_string(image)
        
        return extracted_text.strip()
        
    except Exception as e:
        st.error(f"Error extracting text from image: {str(e)}")
        return ""

def preprocess_image_for_ocr(image):
    """Preprocess image to improve OCR accuracy"""
    
    try:
        # Convert PIL Image to OpenCV format
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # Apply noise reduction
        denoised = cv2.medianBlur(gray, 5)
        
        # Apply thresholding to get binary image
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Convert back to PIL Image
        processed_image = Image.fromarray(thresh)
        
        return processed_image
        
    except Exception as e:
        st.error(f"Error preprocessing image: {str(e)}")
        return image

def process_receipt_image(image_file):
    """Process receipt image to extract food items"""
    
    try:
        # Extract text using OCR
        text = extract_text_from_image(image_file)
        
        if not text:
            return []
        
        # Basic parsing for receipt items
        # In practice, this would use more sophisticated parsing
        lines = text.split('\n')
        potential_items = []
        
        # Common food-related keywords for filtering
        food_keywords = [
            'milk', 'bread', 'cheese', 'chicken', 'beef', 'fish', 'eggs',
            'apple', 'banana', 'tomato', 'lettuce', 'carrot', 'potato',
            'yogurt', 'butter', 'rice', 'pasta', 'cereal', 'juice'
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Skip empty lines and common receipt headers/footers
            if not line_lower or len(line_lower) < 3:
                continue
            
            # Skip lines that look like prices, dates, or receipt metadata
            if any(char in line_lower for char in ['$', 'total', 'tax', 'cash', 'card']):
                continue
            
            # Check if line contains food-related keywords
            for keyword in food_keywords:
                if keyword in line_lower:
                    potential_items.append({
                        'name': line.strip().title(),
                        'quantity': '1 unit',
                        'category': 'Grocery'
                    })
                    break
        
        return potential_items[:10]  # Limit to 10 items
        
    except Exception as e:
        st.error(f"Error processing receipt: {str(e)}")
        return []

def process_barcode_image(image_file):
    """Process barcode image to identify product"""
    
    try:
        # For this demo, we'll simulate barcode processing
        # In practice, you would use libraries like pyzbar or integrate with barcode APIs
        
        st.info("🔍 Barcode scanning would be implemented here")
        st.info("📱 This would typically use libraries like pyzbar or external APIs")
        
        # Return a simulated result
        return [{
            'name': 'Sample Product (from barcode)',
            'quantity': '1 unit',
            'category': 'Grocery'
        }]
        
    except Exception as e:
        st.error(f"Error processing barcode: {str(e)}")
        return []

def process_food_image(image_file):
    """Process food photo to identify items"""
    
    try:
        # This would typically use computer vision or AI services
        # For demo purposes, we'll provide a placeholder
        
        st.info("📷 Food image recognition would be implemented here")
        st.info("🤖 This would use computer vision models or AI services like Gemini Vision")
        
        # Return simulated results
        return [
            {
                'name': 'Food Item 1 (from photo)',
                'quantity': '1 piece',
                'category': 'Fruits'
            },
            {
                'name': 'Food Item 2 (from photo)', 
                'quantity': '1 bunch',
                'category': 'Vegetables'
            }
        ]
        
    except Exception as e:
        st.error(f"Error processing food image: {str(e)}")
        return []

def enhance_image_quality(image):
    """Enhance image quality for better processing"""
    
    try:
        # Convert to OpenCV format
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Enhance contrast and brightness
        alpha = 1.2  # Contrast control
        beta = 10    # Brightness control
        enhanced = cv2.convertScaleAbs(opencv_image, alpha=alpha, beta=beta)
        
        # Apply sharpening
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        # Convert back to PIL Image
        enhanced_image = Image.fromarray(cv2.cvtColor(sharpened, cv2.COLOR_BGR2RGB))
        
        return enhanced_image
        
    except Exception as e:
        st.error(f"Error enhancing image: {str(e)}")
        return image

def validate_image_file(image_file):
    """Validate uploaded image file"""
    
    try:
        # Check file size (limit to 10MB)
        if image_file.size > 10 * 1024 * 1024:
            st.error("❌ Image file too large. Please use files smaller than 10MB.")
            return False
        
        # Check file type
        valid_types = ['image/jpeg', 'image/jpg', 'image/png']
        if image_file.type not in valid_types:
            st.error("❌ Invalid file type. Please use JPEG or PNG images.")
            return False
        
        # Try to open image
        try:
            image = Image.open(image_file)
            image.verify()
            image_file.seek(0)  # Reset file pointer
            return True
        except Exception:
            st.error("❌ Invalid or corrupted image file.")
            return False
        
    except Exception as e:
        st.error(f"Error validating image: {str(e)}")
        return False

def get_image_processing_tips():
    """Get tips for better image processing results"""
    
    return [
        "📷 Use good lighting and avoid shadows",
        "🔍 Ensure text is clear and readable",
        "📐 Keep the camera steady and avoid blur",
        "📋 For receipts, lay them flat and capture the full document",
        "🏷️ For barcodes, ensure the entire barcode is visible",
        "🍎 For food photos, capture items clearly separated",
        "📱 Higher resolution images work better",
        "🖼️ JPEG and PNG formats are supported"
    ]

def display_image_processing_help():
    """Display help information for image processing"""
    
    st.markdown("#### 📸 Image Processing Tips")
    
    with st.expander("💡 Tips for Better Results", expanded=False):
        tips = get_image_processing_tips()
        for tip in tips:
            st.markdown(f"• {tip}")
    
    with st.expander("🔧 Supported Image Types", expanded=False):
        st.markdown("""
        **Supported formats:**
        • JPEG (.jpg, .jpeg)
        • PNG (.png)
        
        **Maximum file size:** 10MB
        
        **Recommended resolution:** 1080p or higher for best results
        """)
    
    with st.expander("📋 What Can Be Processed", expanded=False):
        st.markdown("""
        **Receipt/Bill Scanning:**
        • Grocery store receipts
        • Restaurant bills with itemized food
        • Online order confirmations (printed)
        
        **Barcode Scanning:**
        • Product barcodes (UPC, EAN)
        • QR codes with product information
        
        **Food Photo Recognition:**
        • Individual food items
        • Multiple items in one photo
        • Packaged foods with visible labels
        """)

def get_ocr_confidence_score(image_file):
    """Get OCR confidence score for extracted text"""
    
    try:
        image = Image.open(image_file)
        
        # Get detailed OCR data with confidence scores
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Calculate average confidence
        confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return avg_confidence
        
    except Exception as e:
        st.error(f"Error calculating OCR confidence: {str(e)}")
        return 0
