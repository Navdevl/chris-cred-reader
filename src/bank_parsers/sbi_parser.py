import logging
import re
from typing import List
import pdfplumber
from .base_parser import BaseParser
from models import Transaction

logger = logging.getLogger(__name__)

class SBIParser(BaseParser):
    def __init__(self):
        super().__init__("SBI")
    
    def parse_pdf(self, pdf: pdfplumber.PDF) -> List[Transaction]:
        transactions = []
        
        try:
            for page_num, page in enumerate(pdf.pages):
                # Parse tables first (primary method for SBI)
                tables = page.extract_tables()
                for table in tables:
                    if self._is_transaction_table(table):
                        page_transactions = self._parse_transaction_table(table)
                        transactions.extend(page_transactions)
                
                # Parse text format as fallback
                if not any(self._is_transaction_table(table) for table in tables):
                    text_transactions = self._parse_text_format(page)
                    transactions.extend(text_transactions)
                    
            logger.info(f"SBI parser extracted {len(transactions)} transactions")
            return [t for t in transactions if self.validate_transaction(t)]
            
        except Exception as e:
            logger.error(f"SBI parser failed: {str(e)}")
            return []
    
    def _is_transaction_table(self, table: List[List[str]]) -> bool:
        """Check if table contains SBI transaction data"""
        if not table or len(table) < 2:
            return False
        
        # Look for SBI-specific table structure
        if len(table[0]) != 3:  # SBI uses 3-column format
            return False
        
        # Check for SBI headers
        headers = [cell.lower() if cell else "" for cell in table[0]]
        header_text = ' '.join(headers)
        
        sbi_indicators = [
            'date transaction details amount',
            'transaction details',
            'amount ( `',
            'amount (rs',
        ]
        
        if any(indicator in header_text for indicator in sbi_indicators):
            return True
        
        # Check if data row contains SBI-style multi-line format
        if len(table) > 1 and table[1]:
            for cell in table[1]:
                if cell and '\n' in cell:
                    # Check for date patterns in first column
                    if self._contains_sbi_date_pattern(cell):
                        return True
                    # Check for amount patterns with C/D in third column
                    if self._contains_sbi_amount_pattern(cell):
                        return True
        
        return False
    
    def _parse_transaction_table(self, table: List[List[str]]) -> List[Transaction]:
        """Parse SBI transaction table with 3-column multi-line format"""
        transactions = []
        
        try:
            # Skip header row and process data rows
            for row in table[1:]:
                if not row or len(row) != 3:  # SBI requires exactly 3 columns
                    continue
                
                dates_cell = row[0] if row[0] else ""
                descriptions_cell = row[1] if row[1] else ""
                amounts_cell = row[2] if row[2] else ""
                
                # Split multi-line cells
                dates = [d.strip() for d in dates_cell.split('\n') if d.strip()]
                descriptions = [d.strip() for d in descriptions_cell.split('\n') if d.strip()]
                amounts = [a.strip() for a in amounts_cell.split('\n') if a.strip()]
                
                # Skip if we don't have corresponding entries
                if not dates or not descriptions or not amounts:
                    continue
                
                # Process transactions - use minimum length to avoid mismatched data
                min_length = min(len(dates), len(descriptions), len(amounts))
                
                for i in range(min_length):
                    date_str = dates[i]
                    description = descriptions[i]
                    amount_str = amounts[i]
                    
                    # Skip invalid entries
                    if not self._is_valid_sbi_date(date_str) or not description or not amount_str:
                        continue
                    
                    # Skip header-like descriptions
                    if self._is_header_description(description):
                        continue
                    
                    # Parse transaction
                    transaction = self._create_sbi_transaction(date_str, description, amount_str)
                    if transaction:
                        transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Failed to parse SBI transaction table: {str(e)}")
            
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
                line = line.strip()
                if not line:
                    continue
                
                # Look for transaction pattern: DD MMM YY Description Amount C/D
                # Example: "28 Nov 24 FUEL SURCHARGE WAIVER EXCL TAX 5.04 C"
                match = re.match(r'^(\d{1,2}\s+\w{3}\s+\d{2})\s+(.+?)\s+([\d,]+\.?\d*)\s+([CD])$', line)
                
                if match:
                    date_str = match.group(1).strip()
                    description = match.group(2).strip()
                    amount_num = match.group(3).strip()
                    cd_indicator = match.group(4).strip()
                    
                    amount_str = f"{amount_num} {cd_indicator}"
                    
                    transaction = self._create_sbi_transaction(date_str, description, amount_str)
                    if transaction:
                        transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Failed to parse SBI text format: {str(e)}")
            
        return transactions
    
    def _create_sbi_transaction(self, date_str: str, description: str, amount_str: str) -> Transaction:
        """Create SBI transaction from parsed data"""
        try:
            # Parse amount
            amount = self._parse_sbi_amount(amount_str)
            if amount == 0:
                return None
            
            # Generate transaction ID
            txn_id = self._generate_sbi_transaction_id(date_str, description)
            
            # Create transaction
            transaction = Transaction(
                date=self.normalize_date(date_str, "DD MMM YY"),
                bank="SBI",
                txn_id=txn_id,
                description=self.clean_description(description),
                amount=amount
            )
            
            if self.validate_transaction(transaction):
                return transaction
            
        except Exception as e:
            logger.debug(f"Could not create SBI transaction from '{date_str}' '{description}' '{amount_str}': {e}")
            
        return None
    
    def _contains_sbi_date_pattern(self, text: str) -> bool:
        """Check if text contains SBI date pattern (DD MMM YY)"""
        if not text:
            return False
        
        # Look for SBI date pattern
        return bool(re.search(r'\d{1,2}\s+\w{3}\s+\d{2}', text))
    
    def _contains_sbi_amount_pattern(self, text: str) -> bool:
        """Check if text contains SBI amount pattern with C/D indicators"""
        if not text:
            return False
        
        # Look for amounts with C or D suffix
        return bool(re.search(r'[\d,]+\.?\d*\s+[CD]', text))
    
    def _is_valid_sbi_date(self, date_str: str) -> bool:
        """Check if string matches SBI date format (DD MMM YY)"""
        if not date_str:
            return False
        
        # SBI uses DD MMM YY format
        return bool(re.match(r'^\d{1,2}\s+\w{3}\s+\d{2}$', date_str.strip()))
    
    def _is_header_description(self, description: str) -> bool:
        """Check if description is a header line"""
        description_lower = description.lower()
        
        header_patterns = [
            'transactions for',
            'transaction details',
            'statement',
            'account summary',
            'previous balance',
            'available credit',
            'payment due date',
            'shop & smile',
            'important information'
        ]
        
        return any(pattern in description_lower for pattern in header_patterns)
    
    def _parse_sbi_amount(self, amount_str: str) -> float:
        """Parse amount from SBI format with C/D indicators"""
        if not amount_str:
            return 0.0
        
        try:
            # Clean and extract amount and indicator
            amount_str = amount_str.strip()
            
            # Extract C/D indicator
            is_credit = False
            
            if amount_str.endswith(' C'):
                is_credit = True
                amount_clean = amount_str[:-2].strip()
            elif amount_str.endswith(' D'):
                is_credit = False
                amount_clean = amount_str[:-2].strip()
            else:
                # Try to find C or D in the string
                if ' C' in amount_str:
                    is_credit = True
                    amount_clean = amount_str.replace(' C', '').strip()
                elif ' D' in amount_str:
                    is_credit = False
                    amount_clean = amount_str.replace(' D', '').strip()
                else:
                    amount_clean = amount_str
            
            # Remove commas and currency symbols
            amount_clean = re.sub(r'[,₹Rs`]', '', amount_clean)
            
            amount = float(amount_clean)
            
            # Apply expense tracking sign convention:
            # - Credits (payments, refunds, waivers) = negative (reduces expense)
            # - Debits (purchases) = positive (increases expense)
            if is_credit:
                return -abs(amount)  # Credits are negative
            else:
                return abs(amount)   # Debits are positive
            
        except (ValueError, AttributeError) as e:
            logger.debug(f"Could not parse SBI amount '{amount_str}': {e}")
            return 0.0
    
    def _generate_sbi_transaction_id(self, date_str: str, description: str) -> str:
        """Generate transaction ID for SBI transactions"""
        # Look for payment reference numbers
        payment_match = re.search(r'000DP\d+[A-Za-z0-9]+', description)
        if payment_match:
            return payment_match.group(0)
        
        # Look for other reference numbers
        ref_match = re.search(r'\b([A-Z0-9]{6,})\b', description)
        if ref_match:
            return ref_match.group(1)
        
        # Use first few words of description as identifier
        words = description.split()[:3]
        identifier = '_'.join(words).upper()
        
        # Remove special characters
        identifier = re.sub(r'[^A-Z0-9_]', '', identifier)
        
        return f"SBI_{date_str.replace(' ', '_')}_{identifier}"[:50]  # Limit length