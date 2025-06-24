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
- **Database**: PostgreSQL 16 with psycopg2 connectivity
- **Session Management**: Streamlit session state for user data persistence
- **File Storage**: JSON-based fallback for user data (user_data.json)

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

### Database Schema
- **Users Table**: id, email, name, password_hash, money_saved, created_at
- **Food Items Table**: id, user_email, name, category, purchase_date, expiry_date, quantity, opened, added_method

### Calendar Visualization
- Color-coded calendar view showing expiry dates
- Multiple view modes: Daily, Weekly, Monthly
- Interactive date selection with item details

### Statistics Dashboard
- Data analytics and visualization
- User savings tracking
- Food waste prevention metrics

## Data Flow

1. **User Authentication**: Login → Session establishment → Database user verification
2. **Food Item Addition**: Input (Manual/Voice/Image) → AI Processing → Database storage
3. **Calendar View**: Database query → Date processing → Visual rendering
4. **Statistics**: Data aggregation → Chart generation → Dashboard display

## External Dependencies

### Core Libraries
- `streamlit>=1.46.0` - Web framework
- `pandas>=2.3.0` - Data manipulation
- `plotly>=6.1.2` - Data visualization
- `psycopg2-binary>=2.9.10` - PostgreSQL connectivity

### AI and Processing
- `google-genai>=1.21.1` - Gemini AI integration
- `opencv-python>=4.11.0.86` - Image processing
- `pytesseract>=0.3.13` - OCR functionality
- `speechrecognition>=3.14.3` - Voice input processing
- `pyaudio>=0.2.14` - Audio recording

### Environment Requirements
- PostgreSQL 16 database
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
- `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGPORT` - Database connection
- `GEMINI_API_KEY` - Google AI service authentication

### Resource Requirements
- PostgreSQL database instance
- Audio processing capabilities
- Image processing libraries
- Network access for AI API calls

## Recent Changes

```
- June 24, 2025: Implemented comprehensive inline editing for all food item properties
- June 24, 2025: Added advanced inventory filtering (Latest/Oldest/Expiring Soon/By Category)
- June 24, 2025: Enhanced voice input with real speech recognition capabilities
- June 24, 2025: Fixed PostgreSQL database query compatibility issues
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