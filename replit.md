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
- **Database**: AWS S3 for cloud data storage with JSON format
- **Session Management**: Streamlit session state for user data persistence
- **File Storage**: S3 bucket with structured JSON files for users and food items

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
- **S3 Structure**: 
  - `data/users.json` - All user accounts with email, name, password_hash, money_saved
  - `data/food_items/{user_hash}.json` - Individual user food inventories
- **CSV Export**: S3 data can be exported to CSV format with calculated fields

### Calendar Visualization
- Color-coded calendar view showing expiry dates
- Multiple view modes: Daily, Weekly, Monthly
- Interactive date selection with item details

### Statistics Dashboard
- Data analytics and visualization
- User savings tracking
- Food waste prevention metrics

## Data Flow

1. **User Authentication**: Login → Session establishment → S3 user verification
2. **Food Item Addition**: Input (Manual/Text/Image) → AI Processing → S3 JSON storage
3. **Calendar View**: S3 data retrieval → Date processing → Visual rendering
4. **Statistics**: Data aggregation from S3 → Chart generation → Dashboard display
5. **CSV Export**: S3 JSON data → CSV format → Download functionality

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
- `AWS_ACCESS_KEY_ID` - AWS access key for S3
- `AWS_SECRET_ACCESS_KEY` - AWS secret key for S3
- `AWS_REGION` - AWS region (e.g., us-east-1)
- `S3_BUCKET_NAME` - S3 bucket name for data storage

### Resource Requirements
- File system storage for CSV files
- Audio processing capabilities
- Image processing libraries
- Network access for AI API calls

## Recent Changes

```
- June 27, 2025: Migrated from SQLite/CSV to AWS S3 cloud storage for better scalability
- June 27, 2025: Removed unnecessary local storage files and cleaned up folder structure
- June 27, 2025: Created comprehensive S3 setup instructions and environment configuration
- June 26, 2025: Replaced voice input with text input for better reliability
- June 26, 2025: Moved 'Add food items' section below dashboard title for better visibility
- June 26, 2025: Improved image upload layout with side-by-side design and better scrolling
- June 26, 2025: Fixed duplicate element key errors in image processing sections
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