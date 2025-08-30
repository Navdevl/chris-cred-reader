import logging
from typing import List, Set
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from config import Config
from models import Transaction

logger = logging.getLogger(__name__)

class GoogleSheetsClient:
    def __init__(self):
        self.credentials = self._get_credentials()
        self.service = build('sheets', 'v4', credentials=self.credentials)
        self.sheet_range = "Credit Card Transactions"
        
    def _get_credentials(self) -> Credentials:
        try:
            credentials = Credentials.from_service_account_file(
                Config.GOOGLE_APPLICATION_CREDENTIALS,
                scopes=Config.GOOGLE_SHEETS_SCOPES
            )
            return credentials
        except Exception as e:
            logger.error(f"Failed to load Google Sheets credentials: {str(e)}")
            raise
    
    def ensure_headers_exist(self) -> bool:
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=Config.GOOGLE_SHEET_ID,
                range=f"{self.sheet_range}!A1:G1"
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                headers = Transaction.get_sheet_headers()
                self._write_headers(headers)
                logger.info("Added headers to spreadsheet")
                return True
            
            expected_headers = Transaction.get_sheet_headers()
            actual_headers = values[0] if values else []
            
            if actual_headers != expected_headers:
                logger.warning(f"Headers mismatch. Expected: {expected_headers}, Found: {actual_headers}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to check/create headers: {str(e)}")
            return False
    
    def _write_headers(self, headers: List[str]) -> None:
        try:
            body = {
                'values': [headers]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=Config.GOOGLE_SHEET_ID,
                range=f"{self.sheet_range}!A1:G1",
                valueInputOption='RAW',
                body=body
            ).execute()
            
        except Exception as e:
            logger.error(f"Failed to write headers: {str(e)}")
            raise
    
    def get_existing_transaction_hashes(self) -> Set[str]:
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=Config.GOOGLE_SHEET_ID,
                range=f"{self.sheet_range}!A:E"
            ).execute()
            
            values = result.get('values', [])
            
            if len(values) <= 1:
                return set()
            
            hashes = set()
            for row in values[1:]:
                if len(row) >= 5:
                    date, bank, txn_id, description, amount = row[0], row[1], row[2], row[3], row[4]
                    hash_string = f"{date}|{bank}|{txn_id}|{description}|{amount}"
                    import hashlib
                    hash_value = hashlib.md5(hash_string.encode()).hexdigest()
                    hashes.add(hash_value)
                    
            logger.debug(f"Found {len(hashes)} existing transaction hashes")
            return hashes
            
        except Exception as e:
            logger.error(f"Failed to get existing transactions: {str(e)}")
            return set()
    
    def batch_insert_transactions(self, transactions: List[Transaction]) -> bool:
        try:
            if not transactions:
                logger.info("No transactions to insert")
                return True
                
            existing_hashes = self.get_existing_transaction_hashes()
            
            new_transactions = [
                t for t in transactions 
                if t.get_duplicate_hash() not in existing_hashes
            ]
            
            if not new_transactions:
                logger.info("No new transactions to insert (all duplicates)")
                return True
                
            rows = [transaction.to_sheet_row() for transaction in new_transactions]
            
            body = {
                'values': rows
            }
            
            self.service.spreadsheets().values().append(
                spreadsheetId=Config.GOOGLE_SHEET_ID,
                range=f"{self.sheet_range}!A:G",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logger.info(f"Inserted {len(new_transactions)} new transactions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert transactions: {str(e)}")
            return False
    
    def verify_sheet_access(self) -> bool:
        try:
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=Config.GOOGLE_SHEET_ID
            ).execute()
            
            logger.info(f"Successfully connected to sheet: {sheet_metadata.get('properties', {}).get('title', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to access Google Sheet: {str(e)}")
            return False