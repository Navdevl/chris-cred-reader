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
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_from_step_5
GOOGLE_SHEET_ID=your_spreadsheet_id_from_step_6

# Application Configuration
LOG_LEVEL=INFO
POLL_INTERVAL_MINUTES=15
```

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

## Next Steps

Once setup is complete:
1. Install the application dependencies: `pip install -r requirements.txt`
2. Run the application: `python src/main.py`
3. Upload a test PDF file to verify processing
4. Check Google Sheets for extracted transactions

## API Quotas and Limits

**Google Drive API:**
- 1,000 requests per 100 seconds per user
- 20,000 requests per 100 seconds

**Google Sheets API:**
- 300 requests per minute per project
- 100 requests per 100 seconds per user

These limits are generous for this application's expected usage patterns.