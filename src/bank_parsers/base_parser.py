import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
import pdfplumber
from models import Transaction

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    def __init__(self, bank_name: str):
        self.bank_name = bank_name
        
    @abstractmethod
    def parse_pdf(self, pdf: pdfplumber.PDF) -> List[Transaction]:
        pass
    
    def normalize_date(self, date_str: str, date_format: str) -> str:
        try:
            if date_format == "DD/MM/YYYY":
                dt = datetime.strptime(date_str, "%d/%m/%Y")
            elif date_format == "DD-MM-YYYY":
                dt = datetime.strptime(date_str, "%d-%m-%Y")
            elif date_format == "DD MMM YYYY":
                dt = datetime.strptime(date_str, "%d %b %Y")
            elif date_format == "DD/MM/YY":
                dt = datetime.strptime(date_str, "%d/%m/%y")
            else:
                logger.warning(f"Unknown date format: {date_format}")
                return date_str
                
            return dt.strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"Failed to parse date {date_str}: {str(e)}")
            return date_str
    
    def normalize_amount(self, amount_str: str) -> float:
        try:
            amount_str = amount_str.replace(',', '').replace('INR', '').strip()
            
            if 'Cr' in amount_str or 'Credit' in amount_str:
                amount_str = amount_str.replace('Cr', '').replace('Credit', '').strip()
                return abs(float(amount_str))
            elif 'Dr' in amount_str or 'Debit' in amount_str:
                amount_str = amount_str.replace('Dr', '').replace('Debit', '').strip()
                return -abs(float(amount_str))
            
            amount = float(amount_str)
            return amount
            
        except Exception as e:
            logger.error(f"Failed to parse amount {amount_str}: {str(e)}")
            return 0.0
    
    def clean_description(self, description: str) -> str:
        if not description:
            return ""
        
        description = description.strip()
        description = re.sub(r'\s+', ' ', description)
        description = description.replace('\n', ' ')
        
        return description
    
    def extract_transaction_id(self, text: str, pattern: Optional[str] = None) -> str:
        if not text:
            return ""
            
        if pattern:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return text.strip()
    
    def validate_transaction(self, transaction: Transaction) -> bool:
        if not transaction.date:
            logger.warning("Transaction missing date")
            return False
            
        if not transaction.description:
            logger.warning("Transaction missing description")
            return False
            
        if transaction.amount == 0:
            logger.warning("Transaction has zero amount")
            return False
            
        return True