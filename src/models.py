from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import hashlib
import logging

logger = logging.getLogger(__name__)

@dataclass
class Transaction:
    date: str
    bank: str
    txn_id: str
    description: str
    amount: float
    category: str = ""
    processed_date: Optional[str] = None
    
    def __post_init__(self):
        if self.processed_date is None:
            self.processed_date = datetime.now().isoformat()
    
    def to_sheet_row(self) -> List[str]:
        return [
            self.date,
            self.bank,
            self.txn_id,
            self.description,
            str(self.amount),
            self.category,
            self.processed_date
        ]
    
    def get_duplicate_hash(self) -> str:
        hash_string = f"{self.date}|{self.bank}|{self.txn_id}|{self.description}|{self.amount}"
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    @classmethod
    def get_sheet_headers(cls) -> List[str]:
        return [
            "Date",
            "Bank", 
            "Txn ID",
            "Description",
            "Amount",
            "Category",
            "Processed Date"
        ]

@dataclass
class ProcessedFile:
    filename: str
    bank: str
    password: str
    identifier: str
    file_id: str
    processed_at: datetime
    transaction_count: int
    status: str
    error_message: Optional[str] = None
    
    @classmethod
    def parse_filename(cls, filename: str) -> Optional['ProcessedFile']:
        try:
            name_without_ext = filename.replace('.pdf', '')
            parts = name_without_ext.split('-')
            
            if len(parts) < 3:
                logger.warning(f"Invalid filename format: {filename}")
                return None
                
            bank = parts[0].lower()
            password = parts[1]
            identifier = '-'.join(parts[2:])
            
            # Check bank support if config is available
            try:
                from config import Config
                if bank not in Config.SUPPORTED_BANKS:
                    logger.warning(f"Unsupported bank: {bank}")
                    return None
            except ImportError:
                # Allow all banks during testing
                supported_banks = ['axis', 'hdfc', 'sbi', 'icici', 'rbl']
                if bank not in supported_banks:
                    logger.warning(f"Unsupported bank: {bank}")
                    return None
                
            return cls(
                filename=filename,
                bank=bank,
                password=password,
                identifier=identifier,
                file_id="",
                processed_at=datetime.now(),
                transaction_count=0,
                status="pending"
            )
            
        except Exception as e:
            logger.error(f"Error parsing filename {filename}: {str(e)}")
            return None

@dataclass
class ProcessingResult:
    file: ProcessedFile
    transactions: List[Transaction]
    success: bool
    error_message: Optional[str] = None
    
    def __post_init__(self):
        self.file.transaction_count = len(self.transactions)
        self.file.status = "success" if self.success else "failed"
        if self.error_message:
            self.file.error_message = self.error_message