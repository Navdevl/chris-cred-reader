# Credit Card PDF Statement Processing System

Automatically process credit card PDF statements from Google Drive and populate transaction data into Google Sheets.

## Features

- **Automated PDF Processing**: Monitors Google Drive folder for credit card statements
- **Multi-Bank Support**: Supports Axis and ICICI bank statements (HDFC, SBI coming soon)
- **Password Protection**: Handles password-protected PDFs using filename convention
- **Duplicate Prevention**: Prevents duplicate transactions using hash-based detection
- **Google Sheets Integration**: Automatically populates transactions in a single spreadsheet
- **File Management**: Moves processed files to organized subfolders
- **Robust Error Handling**: Comprehensive logging and retry mechanisms

## Quick Start

### 1. Prerequisites
- Python 3.9+
- Google Cloud Project with Drive and Sheets APIs enabled
- Google service account credentials

### 2. Installation
```bash
git clone <repository-url>
cd chris-cred-reader
pip install -r requirements.txt
```

### 3. Configuration
1. Follow the detailed setup in `instructions.md`
2. Copy `.env.example` to `.env` and update values:
```bash
cp .env.example .env
```

### 4. Run Application
```bash
python src/main.py
```

## File Structure

```
chris-cred-reader/
├── requirements.md          # Detailed project specifications
├── instructions.md          # Google API setup guide
├── src/
│   ├── main.py             # Application entry point
│   ├── config.py           # Configuration management
│   ├── models.py           # Data models
│   ├── pdf_processor.py    # PDF processing engine
│   ├── google_drive_client.py    # Google Drive integration
│   ├── google_sheets_client.py   # Google Sheets integration
│   └── bank_parsers/       # Bank-specific PDF parsers
│       ├── base_parser.py
│       ├── axis_parser.py
│       ├── hdfc_parser.py
│       ├── sbi_parser.py
│       └── icici_parser.py
├── tests/                  # Unit tests
├── Dockerfile             # Docker configuration
├── fly.toml               # Fly.io deployment config
└── requirements.txt       # Python dependencies
```

## PDF Filename Convention

Credit card PDF files must follow this naming pattern:
```
<bank_name>-<password>-<identifier>.pdf
```

**Examples:**
- `axis-mypass123-jan2024.pdf`
- `hdfc-secretword-statement.pdf` 
- `sbi-password123-dec2023.pdf`
- `icici-mykey456-quarterly.pdf`

**Supported Bank Names:**
- `axis` - Axis Bank
- `hdfc` - HDFC Bank  
- `sbi` - State Bank of India
- `icici` - ICICI Bank

## Google Sheets Format

The application creates a single sheet with these columns:
- **Date**: Transaction date (YYYY-MM-DD)
- **Bank**: Bank name
- **Txn ID**: Transaction reference ID
- **Description**: Transaction description
- **Amount**: Amount (positive=credit, negative=debit)
- **Category**: Manual categorization field
- **Processed Date**: When the transaction was processed

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | `/path/to/service-account.json` |
| `GOOGLE_DRIVE_FOLDER_ID` | Google Drive folder ID to monitor | `1BxiMVs0XRA5nFMdKvBdBZjg...` |
| `GOOGLE_SHEET_ID` | Google Sheets spreadsheet ID | `1BxiMVs0XRA5nFMdKvBdBZjg...` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `POLL_INTERVAL_MINUTES` | How often to check for new files | `15` |

## Deployment

### Local Development
```bash
python src/main.py
```

### Fly.io Deployment
1. Install fly CLI: https://fly.io/docs/getting-started/installing-flyctl/
2. Login: `fly auth login`
3. Deploy: `fly deploy`

Set environment variables:
```bash
fly secrets set GOOGLE_APPLICATION_CREDENTIALS="$(cat service-account.json)"
fly secrets set GOOGLE_DRIVE_FOLDER_ID="your_folder_id"
fly secrets set GOOGLE_SHEET_ID="your_sheet_id"
```

## Monitoring and Logs

### View Application Logs
```bash
# Local
tail -f app.log

# Fly.io  
fly logs
```

### Processing Metrics
The application logs:
- Files processed per cycle
- Transactions extracted
- Duplicate detections
- Error messages and stack traces

## Troubleshooting

### Common Issues

**"Permission denied" on Google APIs:**
- Verify service account has access to Drive folder and Sheet
- Check that APIs are enabled in Google Cloud Console

**"File not found" errors:**
- Verify `GOOGLE_DRIVE_FOLDER_ID` and `GOOGLE_SHEET_ID` are correct
- Check folder/sheet sharing permissions

**PDF processing failures:**
- Verify filename follows convention: `<bank>-<password>-<id>.pdf`
- Check that PDF password is correct
- Ensure bank name is supported (axis/hdfc/sbi/icici)

**No transactions extracted:**
- Bank statement format may have changed
- Check logs for parser-specific errors
- Consider updating bank parser logic

### Debug Mode
Set `LOG_LEVEL=DEBUG` for verbose logging:
```bash
export LOG_LEVEL=DEBUG
python src/main.py
```

## Architecture

### Processing Flow
1. **Monitor** → Poll Google Drive folder every 15 minutes
2. **Download** → Get new PDF files matching naming convention  
3. **Parse** → Extract password from filename, process PDF
4. **Extract** → Use bank-specific parser to get transactions
5. **Validate** → Check for duplicates in Google Sheet
6. **Insert** → Batch insert new transactions
7. **Archive** → Move processed file to "processed" subfolder

### Error Handling
- **Retry Logic**: 3 attempts for API failures
- **Graceful Degradation**: Continue processing other files on individual failures
- **Comprehensive Logging**: Track all operations and errors

## Contributing

1. Follow existing code patterns and conventions
2. Add tests for new bank parsers
3. Update documentation for new features
4. Test thoroughly before deployment

## Security Notes

- Service account credentials stored as environment variables
- PDF passwords visible in filenames (consider secure alternatives)
- All API communication over HTTPS
- No sensitive data cached locally

## License

MIT License