import logging
import re
from typing import List
import pdfplumber
from .base_parser import BaseParser
from models import Transaction

logger = logging.getLogger(__name__)

class HDFCParser(BaseParser):
    def __init__(self):
        super().__init__("HDFC")
    
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
                
                # If no tables found, try text parsing
                if not tables or not any(self._is_transaction_table(table) for table in tables):
                    text_transactions = self._parse_text_format(page)
                    transactions.extend(text_transactions)
                    
            logger.info(f"HDFC parser extracted {len(transactions)} transactions")
            return [t for t in transactions if self.validate_transaction(t)]
            
        except Exception as e:
            logger.error(f"HDFC parser failed: {str(e)}")
            return []
    
    def _is_transaction_table(self, table: List[List[str]]) -> bool:
        """Check if table contains HDFC transaction data"""
        if not table or len(table) < 2:
            return False
        
        # Look for HDFC-specific headers
        headers_text = ' '.join([cell.lower() if cell else "" for cell in table[0]])
        
        # HDFC specific headers: Date, Transaction Description, Amount
        hdfc_indicators = [
            'date transaction description amount',
            'transaction description',
            'amount (in rs',
            'date & time transaction description amount pi',
            'amount pi'
        ]
        
        # Check for transaction data patterns in the table content
        if any(indicator in headers_text for indicator in hdfc_indicators):
            return True
        
        # For 2025 format, check if table contains transaction-like data
        for row in table[1:3]:  # Check first few data rows
            if len(row) > 0 and row[0]:
                row_text = row[0].lower()
                # Look for date patterns and transaction indicators
                if ('2025|' in row_text or '2024|' in row_text) and ('c ' in row_text):
                    return True
        
        return False
    
    def _parse_transaction_table(self, table: List[List[str]]) -> List[Transaction]:
        """Parse HDFC transaction table - handles both 2024 and 2025 formats"""
        transactions = []
        
        try:
            # Skip header row and process data rows
            for row in table[1:]:
                if not row or not row[0]:  # Skip empty rows
                    continue
                
                # Check if this is a 2025 single-column format
                if len(row) == 1 and ('|' in row[0] and ('C ' in row[0] or '+ C ' in row[0])):
                    # Parse 2025 single-column format
                    single_col_transactions = self._parse_2025_single_column(row[0])
                    transactions.extend(single_col_transactions)
                    continue
                
                # Skip rows that are just names
                if len(row) == 1 and self._is_name_row(row):
                    continue
                
                # Handle standard multi-column format (2024)
                if len(row) >= 2:
                    # Extract transaction data
                    if len(row) >= 3:  # Standard format: Date | Description | Amount
                        date_str = row[0] if len(row) > 0 else ""
                        description = row[1] if len(row) > 1 else ""
                        amount_str = row[2] if len(row) > 2 else ""
                    elif len(row) == 2:  # Some tables might have only 2 columns
                        # Check if first column looks like a date
                        if self._is_valid_date(row[0]):
                            date_str = row[0]
                            description = row[1]
                            amount_str = ""  # Will try to extract from description
                        else:
                            continue
                    else:
                        continue
                    
                    # Validate date format 
                    if not self._is_valid_date(date_str):
                        continue
                    
                    # Skip if no description
                    if not description:
                        continue
                    
                    # Parse amount - could be in amount column or embedded in description
                    amount = self._parse_amount_from_row(amount_str, description)
                    if amount == 0:
                        continue
                    
                    # Generate transaction ID from reference numbers in description
                    txn_id = self._extract_reference_number(description) or f"HDFC_{date_str}_{len(transactions)}"
                    
                    # Create transaction
                    transaction = Transaction(
                        date=self.normalize_date(self._clean_date(date_str), "DD/MM/YYYY"),
                        bank="HDFC",
                        txn_id=txn_id,
                        description=self.clean_description(description),
                        amount=amount
                    )
                    
                    if self.validate_transaction(transaction):
                        transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Failed to parse HDFC transaction table: {str(e)}")
            
        return transactions
    
    def _parse_text_format(self, page) -> List[Transaction]:
        """Parse transactions from text when table extraction fails"""
        transactions = []
        
        try:
            text = page.extract_text()
            if not text:
                return transactions
            
            lines = text.split('\n')
            
            for line in lines:
                # Look for transaction pattern: DD/MM/YYYY Description Amount
                # Handle both 2024 format (DD/MM/YYYY) and 2025 format (DD/MM/YYYY| HH:MM)
                match = re.match(r'^(\d{1,2}/\d{1,2}/\d{4})(?:\|\s*\d{2}:\d{2})?\s+(.+?)\s+((?:C\s*)?[\d,]+\.?\d*(?:Cr|cr)?(?:\s*[+])?)', line.strip())
                
                if match:
                    date_str = match.group(1)
                    description = match.group(2)
                    amount_str = match.group(3)
                    
                    amount = self._parse_amount(amount_str)
                    if amount == 0:
                        continue
                    
                    txn_id = self._extract_reference_number(description) or f"HDFC_TEXT_{date_str}_{len(transactions)}"
                    
                    transaction = Transaction(
                        date=self.normalize_date(date_str, "DD/MM/YYYY"),
                        bank="HDFC",
                        txn_id=txn_id,
                        description=self.clean_description(description),
                        amount=amount
                    )
                    
                    if self.validate_transaction(transaction):
                        transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Failed to parse HDFC text format: {str(e)}")
            
        return transactions
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if string matches DD/MM/YYYY format (with optional time)"""
        if not date_str:
            return False
        # Handle both DD/MM/YYYY and DD/MM/YYYY| HH:MM formats
        return bool(re.match(r'^\d{1,2}/\d{1,2}/\d{4}(?:\|\s*\d{2}:\d{2})?', date_str.strip()))
    
    def _clean_date(self, date_str: str) -> str:
        """Remove time component from date string"""
        if '|' in date_str:
            return date_str.split('|')[0].strip()
        return date_str.strip()
    
    def _is_name_row(self, row: List[str]) -> bool:
        """Check if row contains just customer name"""
        if len(row) != 1:
            return False
        
        text = row[0].strip().upper()
        # Common patterns for name rows
        name_patterns = [
            r'^[A-Z\s]+$',  # All caps letters and spaces
            r'^V CHRISTOPHER RAJA$',
            r'^[A-Z][A-Z\s]+[A-Z]$'  # Starts and ends with capital letters
        ]
        
        return any(re.match(pattern, text) for pattern in name_patterns) and len(text.split()) <= 4
    
    def _parse_amount_from_row(self, amount_str: str, description: str) -> float:
        """Parse amount from amount column or description"""
        # Try amount column first
        if amount_str and amount_str.strip():
            amount = self._parse_amount(amount_str)
            if amount != 0:
                return amount
        
        # Try to find amount in description for single-column formats
        amount_match = re.search(r'((?:C\s*)?[\d,]+\.?\d*(?:Cr|cr)?(?:\s*[+])?)', description)
        if amount_match:
            return self._parse_amount(amount_match.group(1))
        
        return 0.0
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount from HDFC format - handles both 2024 and 2025 formats"""
        if not amount_str:
            return 0.0
        
        try:
            # Clean the amount string
            amount_clean = amount_str.strip()
            
            # Handle different credit indicators
            is_credit = False
            
            # 2024 format: uses "Cr" suffix
            if amount_clean.lower().endswith('cr'):
                is_credit = True
                amount_clean = amount_clean[:-2].strip()
            
            # 2025 format: uses "+ " prefix for credits
            if amount_clean.startswith('+'):
                is_credit = True
                amount_clean = amount_clean[1:].strip()
            
            # Remove "C " prefix used in 2025 format
            if amount_clean.startswith('C '):
                amount_clean = amount_clean[2:].strip()
            elif amount_clean.startswith('C'):
                amount_clean = amount_clean[1:].strip()
            
            # Remove commas and currency symbols
            amount_clean = re.sub(r'[,₹Rs\.](?=\d{3})', '', amount_clean)
            amount_clean = re.sub(r'[,₹Rs]', '', amount_clean)
            
            # Handle decimal
            if '.' in amount_clean:
                # Keep only the last decimal point
                parts = amount_clean.split('.')
                if len(parts) > 2:
                    amount_clean = '.'.join(parts[:-1]) + '.' + parts[-1]
            
            amount = float(amount_clean)
            
            # Apply expense tracking sign convention:
            # - Credits (refunds, payments received) = negative (reduces expense)
            # - Debits (purchases, fees) = positive (increases expense)
            if is_credit:
                return -abs(amount)  # Credits are negative
            else:
                return abs(amount)   # Debits are positive
            
        except (ValueError, AttributeError) as e:
            logger.debug(f"Could not parse amount '{amount_str}': {e}")
            return 0.0
    
    def _extract_reference_number(self, description: str) -> str:
        """Extract reference number from description"""
        # Look for Ref# pattern
        ref_match = re.search(r'Ref#\s*([0-9]+)', description)
        if ref_match:
            return ref_match.group(1)
        
        # Look for other number patterns
        num_match = re.search(r'\b(\d{8,})\b', description)
        if num_match:
            return num_match.group(1)
        
        return ""
    
    def _parse_2025_single_column(self, cell_content: str) -> List[Transaction]:
        """Parse 2025 single-column format where all data is in one cell"""
        transactions = []
        
        try:
            # Split by newlines to get individual transaction lines
            lines = cell_content.split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                
                # Skip name lines
                if self._is_name_line(line):
                    continue
                
                # Look for transaction pattern in 2025 format: DD/MM/YYYY| HH:MM Description Amount
                match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})\|\s*\d{2}:\d{2}\s+(.+?)\s+((?:\+\s*)?C\s*[\d,]+\.?\d*)', line)
                
                if match:
                    date_str = match.group(1)
                    description = match.group(2).strip()
                    amount_str = match.group(3).strip()
                    
                    # Parse amount
                    amount = self._parse_amount(amount_str)
                    if amount == 0:
                        continue
                    
                    # Extract transaction ID
                    txn_id = self._extract_reference_number(description) or f"HDFC_2025_{date_str}_{len(transactions)}"
                    
                    # Create transaction
                    transaction = Transaction(
                        date=self.normalize_date(date_str, "DD/MM/YYYY"),
                        bank="HDFC",
                        txn_id=txn_id,
                        description=self.clean_description(description),
                        amount=amount
                    )
                    
                    if self.validate_transaction(transaction):
                        transactions.append(transaction)
                        
        except Exception as e:
            logger.error(f"Failed to parse 2025 single column: {str(e)}")
            
        return transactions
    
    def _is_name_line(self, line: str) -> bool:
        """Check if line contains just customer name"""
        line = line.strip().upper()
        return line == "V CHRISTOPHER RAJA" or (len(line.split()) <= 4 and line.isalpha())