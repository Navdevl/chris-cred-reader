# Credit Card PDF Statement Processing System

## Project Overview
A Python application that automatically processes credit card PDF statements from Google Drive and populates transaction data into Google Sheets.

## Core Requirements

### Primary Functionality
- Monitor a single Google Drive folder for credit card PDF statements
- Extract transaction data from password-protected PDFs
- Populate a single Google Sheet with all transactions
- Prevent duplicate entries
- Move processed files to a "processed" subfolder
- Support for 4 Indian banks: Axis, HDFC, SBI, ICICI

### Data Collection Specification
**Required transaction fields:**
- **Date**: Transaction date (standardized to YYYY-MM-DD format)
- **Bank**: Bank name (Axis/HDFC/SBI/ICICI)
- **Txn ID**: Transaction ID/Reference number
- **Description**: Transaction description/merchant name
- **Amount**: Transaction amount (positive for credits, negative for debits)
- **Category**: Manual categorization field (initially empty)

### File Processing Rules
**Filename Convention**: `<bank_name>-<password>-<identifier>.pdf`
- Examples: `axis-mypass123-jan2024.pdf`, `hdfc-secret456-statement.pdf`
- Password extracted from filename for PDF decryption
- Processed files moved to `processed/` subfolder within monitored folder

## Technical Architecture

### Tech Stack
- **Language**: Python 3.9+
- **PDF Processing**: `pdfplumber` (password support + table extraction)
- **Google APIs**: `google-api-python-client` + `google-auth`
- **Data Handling**: `pandas` for data manipulation
- **Scheduling**: Cron-based polling (15-minute intervals)
- **Deployment**: fly.io (free tier with $5 credit)
- **Authentication**: Google service account with environment variables

### System Components
1. **PDF Processor Engine**
   - Password extraction from filename
   - Bank-specific statement parsers
   - Transaction data extraction and validation

2. **Google Drive Integration**
   - File monitoring with API polling
   - File download and processing management
   - Processed file archiving

3. **Google Sheets Integration**
   - Single sheet with all transactions
   - Batch insertion for efficiency
   - Duplicate prevention logic

4. **Bank Statement Parsers**
   - Custom parser per bank (Axis, HDFC, SBI, ICICI)
   - Handle varying PDF layouts and formats
   - Extract standardized transaction data

## Google Sheet Design
**Sheet Name**: "Credit Card Transactions"
**Columns**:
- A: Date (YYYY-MM-DD)
- B: Bank (Axis/HDFC/SBI/ICICI)
- C: Txn ID
- D: Description
- E: Amount (INR)
- F: Category (manual entry)
- G: Processed Date (timestamp)

## Security & Configuration
**Environment Variables Required:**
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON
- `GOOGLE_DRIVE_FOLDER_ID`: Target folder ID for monitoring
- `GOOGLE_SHEET_ID`: Target spreadsheet ID
- `LOG_LEVEL`: Application logging level

**Security Considerations:**
- PDF passwords stored in filenames (temporary approach)
- Google service account with minimal required permissions
- No sensitive data logged or cached

## Deployment Specifications
**Platform**: fly.io
**Resources**: 1 shared-cpu VM (within $5 credit limit)
**Memory**: <512MB target for efficiency
**Storage**: Minimal (no local file retention)
**Networking**: HTTPS only for Google API calls

## Processing Flow
1. **Poll Google Drive folder** (every 15 minutes)
2. **Download new PDF files** with valid filename format
3. **Extract password** from filename
4. **Process PDF** with appropriate bank parser
5. **Validate and normalize** transaction data
6. **Check for duplicates** in Google Sheet
7. **Insert new transactions** in batch
8. **Move processed file** to processed subfolder
9. **Log results** and handle errors

## Error Handling Strategy
- **Retry logic** for API failures (3 attempts)
- **Graceful degradation** for individual file failures
- **Comprehensive logging** for debugging
- **Email alerts** for critical failures (future enhancement)

## Duplicate Prevention Logic
**Duplicate Criteria**: Same Date + Amount + Description + Bank + Txn ID
**Implementation**: Hash-based comparison with existing sheet data
**Conflict Resolution**: Log duplicates, skip insertion

## Performance Considerations
- **Memory efficiency**: Stream processing, no large file caching
- **API rate limits**: Batch operations, respect Google quotas
- **Processing time**: Parallel PDF processing where possible
- **Resource monitoring**: Log memory and processing time

## Future Enhancements (Post-MVP)
- Webhook-based Google Drive monitoring
- Machine learning for transaction categorization
- Multi-currency support
- Real-time dashboard
- Email notification system
- OCR fallback for complex PDFs

## Bank-Specific Requirements

### Axis Bank
- PDF Layout: Tabular format with clear column headers
- Date Format: DD/MM/YYYY or DD-MM-YYYY
- Amount Format: INR with comma separators
- Transaction ID: Reference number column

### HDFC Bank
- PDF Layout: Mixed text and table format
- Date Format: DD MMM YYYY (e.g., 15 Jan 2024)
- Amount Format: Positive/negative amounts
- Transaction ID: Transaction reference

### SBI Bank
- PDF Layout: Dense tabular format
- Date Format: DD/MM/YY
- Amount Format: Dr/Cr indicators
- Transaction ID: Transaction number

### ICICI Bank
- PDF Layout: Clean table with headers
- Date Format: DD/MM/YYYY
- Amount Format: Debit/Credit columns
- Transaction ID: Reference field
