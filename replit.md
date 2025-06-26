# ExpiryGenie - Food Expiry Tracking Application

## Overview

ExpiryGenie is a Streamlit-based web application designed to help users track food expiry dates and reduce food waste. The app features a multi-page interface with user authentication, smart food tracking, calendar visualization, and statistics dashboard. Users can add food items through multiple methods including manual entry, voice input, and image/OCR scanning.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit (Python web framework)
- **Layout**: Multi-page application with sidebar navigation
- **UI Components**: 
  - Landing page with hero section and feature showcase
  - Authentication system with login/signup forms
  - Dashboard for food item management
  - Calendar view with color-coded expiry dates
  - Statistics page with data visualization
- **Styling**: Custom CSS with color-coded theme (Green=Safe, Yellow=Soon, Red=Expired)

### Backend Architecture
- **Language**: Python 3.11
- **Database**: SQLite for serverless data storage with CSV export capability
- **Session Management**: Streamlit session state for user data persistence
- **File Storage**: SQLite database file (data/expirygenie.db) with CSV export functionality

### Data Processing Components
- **OCR**: Tesseract for text extraction from images
- **Computer Vision**: OpenCV for image preprocessing
- **Speech Recognition**: SpeechRecognition library for voice input
- **AI Integration**: Google Gemini AI for natural language processing
- **Data Visualization**: Plotly for charts and calendar views

## Key Components

### Authentication System
- User registration and login functionality
- Password hashing using SHA-256
- Session-based authentication with Streamlit session state
- Database integration for user management

### Food Tracking System
- **Manual Entry**: Direct input with category selection and expiry date estimation
- **Voice Input**: Natural language processing to extract food items from speech
- **Image Processing**: OCR scanning of receipts and food labels
- **Smart Categorization**: Predefined food categories (Grocery, Dairy, Meat & Poultry, etc.)

### Data Storage Schema
- **Users Table**: id, email, name, password_hash, money_saved, created_at
- **Food Items Table**: id, user_email, name, category, purchase_date, expiry_date, quantity, opened, added_method
- **CSV Export**: All data can be exported to CSV format with calculated fields

### Calendar Visualization
- Color-coded calendar view showing expiry dates
- Multiple view modes: Daily, Weekly, Monthly
- Interactive date selection with item details

### Statistics Dashboard
- Data analytics and visualization
- User savings tracking
- Food waste prevention metrics

## Data Flow

1. **User Authentication**: Login → Session establishment → SQLite user verification
2. **Food Item Addition**: Input (Manual/Voice/Image) → AI Processing → SQLite storage
3. **Calendar View**: SQLite data retrieval → Date processing → Visual rendering
4. **Statistics**: Data aggregation from SQLite → Chart generation → Dashboard display
5. **CSV Export**: SQLite data → CSV format → Download functionality

## External Dependencies

### Core Libraries
- `streamlit>=1.46.0` - Web framework
- `pandas>=2.3.0` - Data manipulation and CSV storage
- `plotly>=6.1.2` - Data visualization

### AI and Processing
- `google-genai>=1.21.1` - Gemini AI integration
- `opencv-python>=4.11.0.86` - Image processing
- `pytesseract>=0.3.13` - OCR functionality
- `speechrecognition>=3.14.3` - Voice input processing
- `pyaudio>=0.2.14` - Audio recording

### Environment Requirements
- File system access for CSV storage
- Tesseract OCR engine
- Audio processing libraries (portaudio)
- OpenGL libraries for image processing

## Deployment Strategy

### Platform Configuration
- **Target**: Replit autoscale deployment
- **Runtime**: Python 3.11 with Nix package management
- **Port Configuration**: Internal port 5000, external port 80
- **Process**: Streamlit server with custom port configuration

### Environment Variables
- `GEMINI_API_KEY` - Google AI service authentication

### Resource Requirements
- File system storage for CSV files
- Audio processing capabilities
- Image processing libraries
- Network access for AI API calls

## Recent Changes

```
- June 24, 2025: Migrated database.py from PostgreSQL to SQLite for serverless deployment
- June 24, 2025: Added CSV export functionality directly in database utilities
- June 24, 2025: Enhanced SQLite schema with proper data types and constraints
- June 24, 2025: Added CSV download functionality for food inventory export
- June 24, 2025: Created requirements.txt file with all necessary dependencies
- June 24, 2025: Generated comprehensive README.txt with local setup instructions
- June 24, 2025: Fixed duplicate element issues in Calendar page
- June 24, 2025: Implemented comprehensive CSV storage utilities with pandas
- June 24, 2025: Updated all data access functions to use CSV backend
- June 24, 2025: Simplified deployment by removing database dependencies
- June 24, 2025: Implemented comprehensive inline editing for all food item properties
- June 24, 2025: Added advanced inventory filtering (Latest/Oldest/Expiring Soon/By Category)
- June 24, 2025: Enhanced voice input with real speech recognition capabilities
- June 24, 2025: Added AI-powered expiry date prediction using historical data
- June 24, 2025: Implemented batch selection and deletion functionality
- June 24, 2025: Added visual package status indicators (📦 packed, 📂 opened)
- June 24, 2025: Fixed UI layout issues for image upload sections
- June 24, 2025: Initial ExpiryGenie setup with multi-page Streamlit architecture
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```