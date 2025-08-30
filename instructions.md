# Google API Setup Instructions

This document provides step-by-step instructions for setting up Google Drive and Google Sheets API access for the Credit Card PDF Statement Processing System.

## Prerequisites
- Google account with access to Google Cloud Console
- Google Drive folder where PDF statements will be uploaded
- Google Sheets document where transactions will be recorded

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "New Project" or select existing project
3. Enter project name (e.g., "credit-card-processor")
4. Note down your **Project ID** - you'll need this later

## Step 2: Enable Required APIs

1. In Google Cloud Console, go to **APIs & Services > Library**
2. Search and enable the following APIs:
   - **Google Drive API**
   - **Google Sheets API**

## Step 3: Create Service Account

1. Go to **APIs & Services > Credentials**
2. Click **"+ Create Credentials" > Service Account**
3. Enter service account details:
   - **Name**: `credit-card-processor-sa`
   - **Description**: `Service account for credit card statement processing`
4. Click **"Create and Continue"**
5. Skip role assignment for now (click **"Continue"** then **"Done"**)

## Step 4: Generate Service Account Key

1. In **Credentials** page, find your service account
2. Click on the service account email
3. Go to **"Keys"** tab
4. Click **"Add Key" > "Create New Key"**
5. Select **JSON** format
6. Click **"Create"**
7. **IMPORTANT**: Download and securely store the JSON file
   - Rename it to `service-account.json`
   - Keep it secure - never commit to version control

## Step 5: Set Up Google Drive Access

### Get Folder ID
1. Open Google Drive in browser
2. Navigate to the folder where PDF statements will be uploaded
3. Copy the folder ID from URL:
   - URL format: `https://drive.google.com/drive/folders/[FOLDER_ID]`
   - Example: If URL is `https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvnJcu`
   - Then FOLDER_ID is: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvnJcu`

### Grant Access to Service Account
1. Right-click on the folder in Google Drive
2. Click **"Share"**
3. Add your service account email (found in the JSON file as `client_email`)
4. Set permission to **"Editor"**
5. Click **"Send"**

### Create Processed Subfolder
1. Inside your main folder, create a subfolder named **"processed"**
2. This is where successfully processed PDF files will be moved

## Step 6: Set Up Google Sheets Access

### Create or Prepare Spreadsheet
1. Create a new Google Sheets document or use existing one
2. Rename it to something like **"Credit Card Transactions"**
3. Copy the spreadsheet ID from URL:
   - URL format: `https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit`
   - Example: If URL is `https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvnJcu/edit`
   - Then SPREADSHEET_ID is: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvnJcu`

### Set Up Sheet Headers
1. In the first sheet, add these column headers in row 1:
   - A1: **Date**
   - B1: **Bank**
   - C1: **Txn ID**
   - D1: **Description**
   - E1: **Amount**
   - F1: **Category**
   - G1: **Processed Date**

### Grant Access to Service Account
1. Click **"Share"** button in Google Sheets
2. Add your service account email (from JSON file)
3. Set permission to **"Editor"**
4. Click **"Send"**

## Step 7: Environment Configuration

Create a `.env` file in your project root with the following variables:

```env
# Google API Configuration
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_from_step_5
GOOGLE_SHEET_ID=your_spreadsheet_id_from_step_6

# Application Configuration
LOG_LEVEL=INFO
POLL_INTERVAL_MINUTES=15
```

**Important Notes:**
- Place your `service-account.json` file in the project root directory
- Replace `your_folder_id_from_step_5` with the actual folder ID you copied
- Replace `your_spreadsheet_id_from_step_6` with the actual spreadsheet ID you copied
- The application will create a `processed/` subfolder automatically if it doesn't exist

## Step 8: Test PDF File Setup

### Filename Format
Your PDF files must follow this naming convention:
```
<bank_name>-<password>-<identifier>.pdf
```

**Examples:**
- `axis-mypassword123-jan2024.pdf`
- `hdfc-secretpass-statement.pdf`
- `sbi-pass123-dec2023.pdf`
- `icici-mypass-quarterly.pdf`

**Supported Bank Names:**
- `axis` (for Axis Bank)
- `hdfc` (for HDFC Bank)
- `sbi` (for SBI Bank)
- `icici` (for ICICI Bank)

### Test Upload
1. Upload a test PDF to your Google Drive folder
2. Ensure the filename follows the convention above
3. Check that the file appears in your folder

## Security Best Practices

1. **Service Account Key Security**
   - Never commit `service-account.json` to version control
   - Add `*.json` to your `.gitignore` file
   - Store the file securely with restricted permissions

2. **Password Security**
   - PDF passwords in filenames are visible in Google Drive
   - Consider this a temporary MVP approach
   - Future versions should use secure password storage

3. **API Permissions**
   - Service account has minimal required permissions
   - Only accesses specified folder and spreadsheet
   - Cannot access other Google Drive content

## Troubleshooting

### Common Issues

**"Permission denied" errors:**
- Verify service account email is shared on folder/sheet
- Check that permissions are set to "Editor"
- Ensure APIs are enabled in Google Cloud Console

**"File not found" errors:**
- Double-check folder ID and spreadsheet ID
- Verify the IDs are copied correctly from URLs
- Ensure service account has access

**Authentication errors:**
- Verify `GOOGLE_APPLICATION_CREDENTIALS` path is correct
- Check that JSON file is valid and not corrupted
- Ensure service account key is properly generated

### Getting Help
- Check application logs for detailed error messages
- Verify all environment variables are set correctly
- Test API access using Google API Explorer

## Step 9: Testing Your Setup

### Test Google API Access
Before running the full application, test your Google API setup:

1. **Create a simple test script** (save as `test_google_apis.py`):
```python
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# Test credentials
try:
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
        scopes=['https://www.googleapis.com/auth/drive', 
                'https://www.googleapis.com/auth/spreadsheets']
    )
    print("✅ Credentials loaded successfully")
except Exception as e:
    print(f"❌ Credentials error: {e}")
    exit(1)

# Test Drive API
try:
    drive_service = build('drive', 'v3', credentials=credentials)
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    
    folder = drive_service.files().get(fileId=folder_id).execute()
    print(f"✅ Google Drive access working - Folder: '{folder['name']}'")
except Exception as e:
    print(f"❌ Google Drive error: {e}")

# Test Sheets API
try:
    sheets_service = build('sheets', 'v4', credentials=credentials)
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    sheet = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    print(f"✅ Google Sheets access working - Sheet: '{sheet['properties']['title']}'")
except Exception as e:
    print(f"❌ Google Sheets error: {e}")

print("\n🎉 All tests passed! Your Google API setup is working.")
```

2. **Run the test script:**
```bash
source venv/bin/activate  # if using virtual environment
python test_google_apis.py
```

3. **Expected output:**
```
✅ Credentials loaded successfully
✅ Google Drive access working - Folder: 'Credit Card Statements'
✅ Google Sheets access working - Sheet: 'Credit Card Transactions'

🎉 All tests passed! Your Google API setup is working.
```

### Test with Sample PDF
1. **Upload a test PDF** to your Google Drive folder using the correct naming format
2. **Run the application** once to test processing:
```bash
python src/main.py
```
3. **Check your Google Sheet** for extracted transactions
4. **Verify the PDF** was moved to the `processed/` subfolder

## Next Steps

Once setup is complete and tested:
1. Install the application dependencies: `pip install -r requirements.txt`
2. Test your setup using the instructions above
3. Run the application: `python src/main.py`
4. Upload PDF files to your Google Drive folder for automatic processing

## API Quotas and Limits

**Google Drive API:**
- 1,000 requests per 100 seconds per user
- 20,000 requests per 100 seconds

**Google Sheets API:**
- 300 requests per minute per project
- 100 requests per 100 seconds per user

These limits are generous for this application's expected usage patterns.

## Duplicate Transaction Handling

The system automatically prevents duplicate transactions using MD5 hash-based detection:

### How It Works
1. **Hash Generation**: Each transaction gets a unique hash based on:
   - Date
   - Bank name  
   - Transaction ID
   - Description
   - Amount

2. **Duplicate Check**: Before inserting new transactions:
   - System reads existing transactions from Google Sheets
   - Compares hash of new transactions with existing ones
   - Only inserts transactions that don't already exist

3. **File Processing**: 
   - If you accidentally upload the same PDF file again
   - The system will detect duplicate transactions and skip them
   - No duplicate entries will be created in your Google Sheet
   - Already processed files are moved to `processed/` folder to avoid reprocessing

### Benefits
- **Safe to re-run**: You can safely re-upload files or re-run the application
- **Accurate data**: No duplicate transactions in your expense tracking
- **Robust processing**: System handles interruptions gracefully