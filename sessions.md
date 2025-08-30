# Credit Card PDF Statement Processing System - Development Sessions

## Project Overview
**Goal**: Automatically process credit card PDF statements from Google Drive and populate transactions in Google Sheets.

**Supported Banks**: Axis, HDFC, SBI, ICICI
**Tech Stack**: Python 3.9+, pdfplumber, Google APIs, fly.io deployment

## Session Summary

### ✅ COMPLETED (Session 1)
1. **Project Structure Setup**
   - Created comprehensive `requirements.md` with detailed specifications
   - Set up complete project directory structure with `src/`, `bank_parsers/`, `tests/`
   - Created `requirements.txt` with all dependencies
   - Set up `.gitignore`, `.env.example`, configuration files

2. **Core Implementation**
   - **Configuration**: `src/config.py` - Environment variables, logging setup
   - **Data Models**: `src/models.py` - Transaction, ProcessedFile, ProcessingResult classes
   - **Google Drive Client**: `src/google_drive_client.py` - File monitoring, download, archive
   - **Google Sheets Client**: `src/google_sheets_client.py` - Transaction insertion, duplicate detection
   - **PDF Processor**: `src/pdf_processor.py` - Main processing engine
   - **Main Application**: `src/main.py` - Orchestration and scheduling

3. **Bank-Specific Parsers**
   - **Base Parser**: `src/bank_parsers/base_parser.py` - Common utilities
   - **Axis Parser**: `src/bank_parsers/axis_parser.py` - DD/MM/YYYY format
   - **HDFC Parser**: `src/bank_parsers/hdfc_parser.py` - DD MMM YYYY format
   - **SBI Parser**: `src/bank_parsers/sbi_parser.py` - DD/MM/YY format, Dr/Cr indicators
   - **ICICI Parser**: `src/bank_parsers/icici_parser.py` - DD/MM/YYYY format

4. **Deployment Configuration**
   - **Docker**: `Dockerfile` for containerization
   - **Fly.io**: `fly.toml` with resource constraints (512MB, 1 CPU)
   - **Environment**: Production-ready configuration

5. **Documentation**
   - **Setup Guide**: `instructions.md` - Step-by-step Google API setup
   - **README**: Complete usage and deployment instructions
   - **Requirements**: Detailed technical specifications

## 🔧 CURRENT ISSUES TO FIX

### 1. Import Dependencies Issue
**Problem**: `models.py` tries to import `config` but `dotenv` not available in test environment
**Solution**: Fix circular imports and dependency loading

### 2. Virtual Environment Setup
**Need**: Set up proper Python virtual environment for development and testing

### 3. Sample PDF Testing
**Available**: Axis bank sample PDFs in samples folder
**Need**: Test actual PDF parsing with real bank statements

## 📋 NEXT STEPS (Session 2)

### Priority 1: Environment Setup
1. Create virtual environment: `python3 -m venv venv`
2. Install dependencies: `pip install -r requirements.txt`
3. Fix import issues in `models.py` (remove config import)

### Priority 2: PDF Testing
1. Locate and examine Axis bank sample PDFs
2. Create test script for PDF parsing
3. Validate Axis parser against real statements
4. Adjust parser logic based on actual PDF format

### Priority 3: Integration Testing
1. Test Google Drive client (requires credentials)
2. Test Google Sheets client (requires credentials)  
3. End-to-end workflow testing
4. Error handling validation

## 🔍 KEY FILES TO KNOW

### Core Logic
- `src/main.py` - Entry point, scheduling, orchestration
- `src/pdf_processor.py` - PDF processing engine
- `src/models.py` - Data structures (Transaction, ProcessedFile)

### API Clients  
- `src/google_drive_client.py` - Drive file operations
- `src/google_sheets_client.py` - Sheets data operations

### Bank Parsers
- `src/bank_parsers/axis_parser.py` - Axis bank statement parsing
- `src/bank_parsers/base_parser.py` - Common parsing utilities

### Configuration
- `src/config.py` - Environment variables, logging
- `.env.example` - Environment template
- `requirements.txt` - Python dependencies

### Deployment
- `Dockerfile` - Container configuration
- `fly.toml` - Fly.io deployment settings

## 💡 ARCHITECTURAL DECISIONS

### PDF Processing Strategy
- **pdfplumber** for password-protected PDF handling
- **Bank-specific parsers** for different statement formats
- **Table extraction** + **text parsing** fallback approach

### Google APIs Integration
- **Service account authentication** for automated access
- **Batch operations** for efficiency
- **Retry logic** for reliability

### Data Flow
1. Poll Google Drive folder every 15 minutes
2. Download new PDFs with valid filename format
3. Extract transactions using bank-specific parsers
4. Check for duplicates in existing sheet data
5. Batch insert new transactions
6. Move processed files to archive folder

### Duplicate Prevention
- **Hash-based**: MD5 of (date + bank + txn_id + description + amount)
- **Pre-insertion check**: Query existing sheet data before inserting

## 🚨 KNOWN LIMITATIONS

1. **PDF Password Security**: Passwords visible in filenames
2. **Memory Usage**: No streaming for large PDFs
3. **Error Recovery**: Limited retry logic for individual files
4. **Bank Format Changes**: Parsers may break if statement formats change

## 📝 FILENAME CONVENTION
```
<bank_name>-<password>-<identifier>.pdf
Examples:
- axis-mypass123-jan2024.pdf  
- hdfc-secret456-statement.pdf
```

## 🎯 SUCCESS CRITERIA
- [ ] Successfully parse Axis sample PDFs
- [ ] Extract accurate transaction data
- [ ] Prevent duplicate insertions
- [ ] Handle errors gracefully
- [ ] Deploy to fly.io successfully