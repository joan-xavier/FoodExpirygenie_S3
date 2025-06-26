ExpiryGenie - Food Expiry Tracking Application
==============================================

A comprehensive Streamlit-based web application for tracking food expiry dates and reducing food waste.

FEATURES
--------
- Multi-method food input: Manual entry, Voice input, Image/OCR scanning
- AI-powered food recognition using Google Gemini
- Smart expiry date prediction
- Calendar visualization with color-coded expiry dates
- Statistics dashboard with analytics
- CSV export functionality
- User authentication system

PREREQUISITES
-------------
Before running ExpiryGenie locally, ensure you have:

1. Python 3.11 or higher installed
2. pip package manager
3. Tesseract OCR engine installed on your system
4. Audio system for voice input (microphone access)
5. Google Gemini API key

SYSTEM DEPENDENCIES
-------------------
Install these system dependencies first:

For Ubuntu/Debian:
    sudo apt update
    sudo apt install tesseract-ocr
    sudo apt install portaudio19-dev
    sudo apt install libgl1-mesa-glx libglib2.0-0

For macOS:
    brew install tesseract
    brew install portaudio

For Windows:
    Download and install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
    Add Tesseract to your system PATH

INSTALLATION STEPS
------------------

1. Clone or download the project files to your local directory

2. Navigate to the project directory:
    cd /path/to/expirygenie

3. Create a virtual environment (recommended):
    python -m venv expiry_env
    
    # Activate the virtual environment:
    # On Windows:
    expiry_env\Scripts\activate
    # On macOS/Linux:
    source expiry_env/bin/activate

4. Install Python dependencies:
    pip install -r requirements.txt

5. Set up environment variables:
    Create a .env file in the project root with:
    GEMINI_API_KEY=your_google_gemini_api_key_here
    
    OR set environment variable directly:
    # Windows:
    set GEMINI_API_KEY=your_api_key_here
    # macOS/Linux:
    export GEMINI_API_KEY=your_api_key_here

6. Create the necessary directories:
    mkdir data
    
    The application will create CSV files automatically in the data directory.

GETTING GOOGLE GEMINI API KEY
-----------------------------
1. Go to Google AI Studio: https://aistudio.google.com/
2. Create a new project or select existing one
3. Generate an API key
4. Copy the API key and add it to your environment variables

RUNNING THE APPLICATION
-----------------------

1. Ensure you're in the project directory and virtual environment is activated

2. Start the Streamlit application:
    streamlit run app.py

3. The application will open in your default web browser at:
    http://localhost:8501

4. Create a new user account or login with existing credentials

5. Start adding food items using any of the available methods:
    - Manual entry in Dashboard
    - Voice input with speech recognition
    - Image upload for receipt/barcode/food photo scanning

USAGE GUIDE
-----------

Landing Page:
    - Introduction to ExpiryGenie features
    - Navigation to authentication

Authentication:
    - Sign up for new account
    - Login with existing credentials
    - Password reset functionality

Dashboard:
    - Add food items manually
    - Voice input for natural language food entry
    - Image upload for receipt scanning, barcode scanning, food photo recognition
    - View, edit, and delete food items
    - Download inventory as CSV

Calendar:
    - Color-coded visual timeline of expiry dates
    - Monthly, weekly, and daily views
    - Filter by categories
    - Interactive date selection

Statistics:
    - Analytics dashboard with charts
    - Food waste tracking
    - Money saved calculations
    - AI-powered insights and recommendations

DATA STORAGE
------------
ExpiryGenie uses SQLite for serverless data storage:
- data/expirygenie.db: SQLite database file containing all user and food data
- CSV export functionality available for downloading inventory data

No database server setup required - SQLite is file-based and serverless.

TROUBLESHOOTING
---------------

Common Issues:

1. "ModuleNotFoundError" for packages:
    - Ensure all dependencies are installed: pip install -r requirements.txt
    - Check if virtual environment is activated

2. Tesseract OCR errors:
    - Verify Tesseract is installed and in system PATH
    - Test with: tesseract --version

3. Audio/microphone issues:
    - Check microphone permissions in your browser
    - Ensure portaudio is properly installed

4. API errors:
    - Verify GEMINI_API_KEY is set correctly
    - Check API key validity at Google AI Studio

5. Streamlit port conflicts:
    - Use different port: streamlit run app.py --server.port 8502

6. Permission errors with CSV files:
    - Ensure write permissions in the data directory
    - Check if CSV files are not open in other applications

CONFIGURATION
-------------
The application runs on port 8501 by default. To change this:
    streamlit run app.py --server.port YOUR_PORT

For production deployment, additional configuration may be required.

SUPPORT
-------
For issues and questions:
1. Check the troubleshooting section above
2. Verify all prerequisites are installed
3. Ensure API keys are properly configured
4. Check file permissions for data directory

NOTES
-----
- Voice input requires microphone access permission
- Image processing works best with clear, well-lit photos
- The application automatically creates data backups in CSV format
- All user data is stored locally - no external database required

Happy food tracking with ExpiryGenie!