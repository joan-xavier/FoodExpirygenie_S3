# ExpiryGenie AWS S3 Setup Instructions

## Environment Variables Setup

### Method 1: Replit Secrets (Recommended)
1. Go to your Replit project
2. Click on "Secrets" tab in the left sidebar
3. Add the following secrets:

```
AWS_ACCESS_KEY_ID = your_aws_access_key
AWS_SECRET_ACCESS_KEY = your_aws_secret_key
AWS_REGION = us-east-1
S3_BUCKET_NAME = expirygenie-data
GEMINI_API_KEY = your_gemini_api_key
```

### Method 2: .env File (Local Development)
1. Copy `.env.example` to `.env`
2. Fill in your AWS credentials in the `.env` file
3. The app will automatically load these variables

## Getting AWS Credentials

### Step 1: Create AWS Account
1. Go to [AWS Console](https://aws.amazon.com/console/)
2. Sign up for an AWS account if you don't have one

### Step 2: Create IAM User
1. Go to AWS Console > IAM > Users
2. Click "Create user"
3. Enter username (e.g., "expirygenie-user")
4. Select "Programmatic access"

### Step 3: Set Permissions
1. Attach policies directly
2. Search and select "AmazonS3FullAccess"
3. Complete user creation

### Step 4: Get Access Keys
1. After user creation, click "Create access key"
2. Choose "Application running outside AWS"
3. Copy the Access Key ID and Secret Access Key
4. Store them securely

## S3 Bucket Configuration

The app will automatically:
- Create the S3 bucket if it doesn't exist
- Set up proper folder structure for user data
- Handle file uploads and downloads

## Data Structure in S3

```
your-bucket-name/
├── data/
│   ├── users.json                 # User accounts
│   └── food_items/
│       ├── user1_hash.json        # User 1's food items
│       └── user2_hash.json        # User 2's food items
```

## Security Notes

- Never commit your AWS credentials to version control
- Use IAM roles with minimal permissions
- Consider using AWS STS for temporary credentials
- Enable S3 bucket versioning for data protection

## Troubleshooting

### Common Issues:
1. **Access Denied**: Check IAM permissions
2. **Bucket Not Found**: Verify bucket name and region
3. **Connection Failed**: Check AWS credentials format

### Testing Connection:
The app will show connection status on the dashboard. If there are issues, check the Streamlit logs for detailed error messages.