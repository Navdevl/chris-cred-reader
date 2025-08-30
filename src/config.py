import os
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
    GOOGLE_DRIVE_FOLDER_ID: str = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
    GOOGLE_SHEET_ID: str = os.getenv('GOOGLE_SHEET_ID', '')
    
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    POLL_INTERVAL_MINUTES: int = int(os.getenv('POLL_INTERVAL_MINUTES', '15'))
    
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '100'))
    
    SUPPORTED_BANKS = ['axis', 'hdfc', 'sbi', 'icici']
    PROCESSED_FOLDER_NAME = 'processed'
    
    GOOGLE_DRIVE_SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.metadata'
    ]
    
    GOOGLE_SHEETS_SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets'
    ]
    
    @classmethod
    def validate_config(cls) -> bool:
        required_vars = [
            'GOOGLE_APPLICATION_CREDENTIALS',
            'GOOGLE_DRIVE_FOLDER_ID', 
            'GOOGLE_SHEET_ID'
        ]
        
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            logging.error(f"Missing required environment variables: {missing_vars}")
            return False
            
        if not os.path.exists(cls.GOOGLE_APPLICATION_CREDENTIALS):
            logging.error(f"Google credentials file not found: {cls.GOOGLE_APPLICATION_CREDENTIALS}")
            return False
            
        return True
    
    @classmethod
    def setup_logging(cls) -> None:
        log_level = getattr(logging, cls.LOG_LEVEL.upper(), logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('app.log')
            ]
        )
        
        logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
        logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)