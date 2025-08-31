# Docker Deployment Guide

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Google service account JSON file (`service-account.json`)
- Environment configuration file (`.env`)

### Directory Structure
```
chris-cred-reader/
├── docker-compose.yml
├── Dockerfile
├── service-account.json     # Your Google service account key
├── .env                     # Your environment variables
├── logs/                    # Created automatically for persistent logs
└── src/                     # Source code
```

### 1. Set Up Environment Files

**Create `.env` file:**
```env
# Google API Configuration
GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
GOOGLE_SHEET_ID=your_sheet_id_here

# Application Configuration
LOG_LEVEL=INFO
POLL_INTERVAL_MINUTES=15
MAX_RETRIES=3
BATCH_SIZE=100
```

**Place your `service-account.json`** in the project root directory.

### 2. Deploy with Docker Compose

```bash
# Build and start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### 3. Alternative: Manual Docker Commands

```bash
# Build the image
docker build -t credit-card-processor .

# Run the container
docker run -d \
  --name credit-card-processor \
  --restart unless-stopped \
  -v $(pwd)/service-account.json:/app/service-account.json:ro \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/logs:/app/logs \
  credit-card-processor
```

## Production Deployment

### Security Features
- ✅ Non-root user execution
- ✅ Read-only mounted credentials
- ✅ Minimal base image (python:3.9-slim)
- ✅ Health checks enabled
- ✅ Isolated container network

### Volume Mounts Explained

| Local Path | Container Path | Purpose | Mode |
|------------|----------------|---------|------|
| `./service-account.json` | `/app/service-account.json` | Google service account credentials | Read-only |
| `./.env` | `/app/.env` | Environment variables | Read-only |
| `./logs/` | `/app/logs` | Application logs | Read-write |

### Health Monitoring

```bash
# Check container health
docker ps

# View detailed health status
docker inspect credit-card-processor | grep -A5 "Health"

# View application logs
docker-compose logs -f credit-card-processor
```

## Log Management

### With Docker Compose (Recommended)
Logs are automatically stored in `./logs/app.log` and persisted across container restarts.

### Optional: Log Viewer Service
Enable the logs service for a web-based log viewer:

```bash
# Start with log viewer
docker-compose --profile logs up -d

# Access log viewer at http://localhost:8080
```

## Troubleshooting

### Common Issues

**1. Permission Denied Errors**
```bash
# Fix file permissions
chmod 600 service-account.json
chmod 644 .env
```

**2. Container Won't Start**
```bash
# Check logs
docker-compose logs credit-card-processor

# Verify files exist
ls -la service-account.json .env
```

**3. Google API Access Issues**
```bash
# Test API access from container
docker-compose exec credit-card-processor python -c "
import os
from google.oauth2 import service_account

creds = service_account.Credentials.from_service_account_file(
    os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
)
print('✅ Credentials loaded successfully')
print(f'Service account: {creds.service_account_email}')
"
```

### Health Check Commands

```bash
# Manual health check
docker-compose exec credit-card-processor python -c "
import os
print('✅ Service account exists:', os.path.exists('/app/service-account.json'))
print('✅ Environment file exists:', os.path.exists('/app/.env'))
"

# Test Google API connectivity
docker-compose exec credit-card-processor python test_google_apis.py
```

## Monitoring and Maintenance

### Resource Usage
```bash
# Monitor resource usage
docker stats credit-card-processor

# View container processes
docker-compose top
```

### Log Rotation
The application creates daily log files. Set up log rotation:

```bash
# Add to crontab for log cleanup
0 2 * * * find $(pwd)/logs -name "*.log" -mtime +30 -delete
```

### Updates
```bash
# Update application
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | `/app/service-account.json` | Path to service account JSON |
| `GOOGLE_DRIVE_FOLDER_ID` | Required | Google Drive folder ID |
| `GOOGLE_SHEET_ID` | Required | Google Sheets spreadsheet ID |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `POLL_INTERVAL_MINUTES` | `15` | How often to check for new files |
| `MAX_RETRIES` | `3` | Max retry attempts for failed operations |
| `BATCH_SIZE` | `100` | Batch size for sheet operations |

## Error Handling

### Failed File Processing
When files fail to process, the system automatically:

1. **Moves failed files** to a `failed/` subfolder in your Google Drive
2. **Logs errors** to `failed/errors.csv` with format: `date,filename,reason`
3. **Prevents reprocessing** of files already in failed folder
4. **Continues processing** other files without interruption

### Error Types Handled
- PDF parsing failures
- Password authentication errors  
- Google Sheets insertion failures
- Network connectivity issues
- File permission problems

### Error CSV Format
```csv
date,filename,reason
2025-08-31 09:53:32,axis-pass123-jan2024.pdf,"Password authentication failed"
2025-08-31 10:15:45,hdfc-secret-feb2024.pdf,"Failed to insert transactions into Google Sheets"
```

## Security Considerations

### File Permissions
- `service-account.json`: 600 (read-write for owner only)
- `.env`: 644 (read for owner, read-only for group/others)
- Never commit these files to version control

### Network Security
- Container runs with minimal network access
- Only required Google API endpoints are accessed
- No exposed ports by default (uncomment in docker-compose.yml if needed)

### Production Checklist
- [ ] Service account has minimal required permissions
- [ ] Credentials files are properly secured
- [ ] Log rotation is configured
- [ ] Container restart policy is set
- [ ] Health monitoring is enabled
- [ ] Backups of configuration are secured
- [ ] Failed folder permissions are configured
- [ ] Error logging is working properly

## Support

For issues:
1. Check application logs: `docker-compose logs -f`
2. Verify environment configuration
3. Test Google API connectivity
4. Review security permissions

The application includes comprehensive logging and health checks to help diagnose issues quickly.