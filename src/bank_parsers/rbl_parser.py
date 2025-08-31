import logging
import re
from typing import List
import pdfplumber
from .base_parser import BaseParser
from models import Transaction

logger = logging.getLogger(__name__)

class RBLParser(BaseParser):
    def __init__(self):
        super().__init__("RBL")
    
    def parse_pdf(self, pdf: pdfplumber.PDF) -> List[Transaction]:
        transactions = []
        
        try:
            for page_num, page in enumerate(pdf.pages):
                # Parse tables first
                tables = page.extract_tables()
                for table in tables:
                    if self._is_transaction_table(table):
                        page_transactions = self._parse_transaction_table(table)
                        transactions.extend(page_transactions)
                
                # Parse text format (primary method for RBL)
                text_transactions = self._parse_text_format(page)
                transactions.extend(text_transactions)
                    
            logger.info(f"RBL parser extracted {len(transactions)} transactions")
            return [t for t in transactions if self.validate_transaction(t)]
            
        except Exception as e:
            logger.error(f"RBL parser failed: {str(e)}")
            return []
    
    def _is_transaction_table(self, table: List[List[str]]) -> bool:
        """Check if table contains RBL transaction data"""
        if not table or len(table) < 2:
            return False
        
        # Look for RBL-specific headers
        headers_text = ' '.join([cell.lower() if cell else "" for cell in table[0]])
        
        # RBL specific headers
        rbl_indicators = [
            'date description amount',
            'date description amount ₹',
            'transaction amount',
        ]
        
        # Check for transaction data patterns in the table content
        if any(indicator in headers_text for indicator in rbl_indicators):
            return True
        
        # Check if table contains transaction-like data
        for row in table[1:3]:  # Check first few data rows
            if len(row) > 0 and row[0]:
                row_text = row[0].lower()
                # Look for date patterns and transaction indicators
                if self._contains_date_pattern(row_text) and any(char.isdigit() for char in row_text):
                    return True
        
        return False
    
    def _parse_transaction_table(self, table: List[List[str]]) -> List[Transaction]:
        """Parse RBL transaction table"""
        transactions = []
        
        try:
            # Skip header row and process data rows
            for row in table[1:]:
                if not row or not row[0]:  # Skip empty rows
                    continue
                
                # RBL typically uses single-column format
                if len(row) >= 1:
                    line = row[0].strip()
                    
                    # Skip non-transaction lines
                    if not line or self._is_summary_line(line):
                        continue
                    
                    # Parse transaction from single line
                    transaction = self._parse_transaction_line(line)
                    if transaction:
                        transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Failed to parse RBL transaction table: {str(e)}")
            
        return transactions
    
    def _parse_text_format(self, page) -> List[Transaction]:
        """Parse transactions from text when table extraction fails or as primary method"""
        transactions = []
        
        try:
            text = page.extract_text()
            if not text:
                return transactions
            
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip headers and summary lines
                if self._is_header_line(line) or self._is_summary_line(line):
                    continue
                
                # Parse transaction from line
                transaction = self._parse_transaction_line(line)
                if transaction:
                    transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Failed to parse RBL text format: {str(e)}")
            
        return transactions
    
    def _parse_transaction_line(self, line: str) -> Transaction:
        """Parse a single transaction line in RBL format"""
        try:
            # Clean up encoded characters from 2024 format
            line = self._decode_rbl_text(line)
            
            # RBL format: DD MMM YYYY Description Amount
            # Example: "13 Jul 2025 MS OMR MALL DEVELOPER KANCHIPURAM IND 160.00"
            match = re.match(r'^(\d{1,2}\s+\w{3}\s+\d{4})\s+(.+?)\s+([\d,]+\.?\d*)$', line.strip())
            
            if match:
                date_str = match.group(1).strip()
                description = match.group(2).strip()
                amount_str = match.group(3).strip()
                
                # Parse amount
                amount = self._parse_amount(amount_str, description)
                if amount == 0:
                    return None
                
                # Generate transaction ID
                txn_id = self._generate_transaction_id(date_str, description)
                
                # Create transaction
                transaction = Transaction(
                    date=self.normalize_date(date_str, "DD MMM YYYY"),
                    bank="RBL",
                    txn_id=txn_id,
                    description=self.clean_description(description),
                    amount=amount
                )
                
                if self.validate_transaction(transaction):
                    return transaction
            
        except Exception as e:
            logger.debug(f"Could not parse RBL transaction line '{line}': {e}")
            
        return None
    
    def _decode_rbl_text(self, text: str) -> str:
        """Decode RBL encoded text from 2024 format"""
        if not text:
            return text
        
        # Handle common encoded patterns from RBL 2024 format
        # This is a simplified decoder - in practice, you might need more comprehensive handling
        
        # Remove encoded character patterns like (cid:XX)
        text = re.sub(r'\(cid:\d+\)', '', text)
        
        # Common character replacements
        replacements = {
            '(cid:68)(cid:114)(cid:69)(cid:65)(cid:77)': 'DREAM',
            # Add more as needed based on observed patterns
        }
        
        for encoded, decoded in replacements.items():
            text = text.replace(encoded, decoded)
        
        return text.strip()
    
    def _contains_date_pattern(self, text: str) -> bool:
        """Check if text contains RBL date pattern (DD MMM YYYY)"""
        if not text:
            return False
        
        # RBL uses DD MMM YYYY format
        return bool(re.search(r'\d{1,2}\s+\w{3}\s+\d{4}', text))
    
    def _is_header_line(self, line: str) -> bool:
        """Check if line is a header"""
        line_lower = line.lower()
        header_patterns = [
            'date description amount',
            'account summary',
            'card number',
            'total amount due',
            'min. amt. due',
            'payment due date',
            'available reward points',
            'statement period',
            'statement date'
        ]
        
        return any(pattern in line_lower for pattern in header_patterns)
    
    def _is_summary_line(self, line: str) -> bool:
        """Check if line is a summary/non-transaction line"""
        line_lower = line.lower()
        summary_patterns = [
            'total amount due',
            'min. amt. due',
            'payment due date',
            'card number',
            'available reward',
            'points to expire',
            'opening balance',
            'closing balance',
            'fuel surcharge',
            'bonus points',
            'membership fee',
            't&cs apply',
            'use code',
            'valid till',
            'rblfares',
            'opt for',
            'download',
            'pay utility'
        ]
        
        return any(pattern in line_lower for pattern in summary_patterns)
    
    def _parse_amount(self, amount_str: str, description: str) -> float:
        """Parse amount from RBL format"""
        if not amount_str:
            return 0.0
        
        try:
            # Clean the amount string
            amount_clean = amount_str.strip()
            
            # Remove commas and currency symbols
            amount_clean = re.sub(r'[,₹Rs]', '', amount_clean)
            
            amount = float(amount_clean)
            
            # Determine if this is a credit or debit based on description
            is_credit = self._is_credit_transaction(description)
            
            # Apply expense tracking sign convention:
            # - Credits (payments, refunds) = negative (reduces expense)
            # - Debits (purchases) = positive (increases expense)
            if is_credit:
                return -abs(amount)  # Credits are negative
            else:
                return abs(amount)   # Debits are positive
            
        except (ValueError, AttributeError) as e:
            logger.debug(f"Could not parse amount '{amount_str}': {e}")
            return 0.0
    
    def _is_credit_transaction(self, description: str) -> bool:
        """Determine if transaction is a credit based on description"""
        description_lower = description.lower()
        
        # Credit indicators
        credit_patterns = [
            'payment',
            'upi',
            'transfer',
            'credit',
            'refund',
            'reversal',
            'cashback',
            'reward',
            'adjustment'
        ]
        
        return any(pattern in description_lower for pattern in credit_patterns)
    
    def _generate_transaction_id(self, date_str: str, description: str) -> str:
        """Generate transaction ID for RBL transactions"""
        # Look for any reference numbers in description
        ref_match = re.search(r'\b(\d{6,})\b', description)
        if ref_match:
            return ref_match.group(1)
        
        # Use first few words of description as identifier
        words = description.split()[:3]
        identifier = '_'.join(words).upper()
        
        return f"RBL_{date_str.replace(' ', '_')}_{identifier}"[:50]  # Limit length