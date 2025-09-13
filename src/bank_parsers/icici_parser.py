import logging
import re
from typing import List
import pdfplumber
from .base_parser import BaseParser
from models import Transaction

logger = logging.getLogger(__name__)

class ICICIParser(BaseParser):
    def __init__(self):
        super().__init__("ICICI")
    
    def parse_pdf(self, pdf: pdfplumber.PDF) -> List[Transaction]:
        transactions = []
        
        try:
            for page_num, page in enumerate(pdf.pages):
                # Note: Don't skip first page entirely as some ICICI statements
                # have transactions on the first page (e.g. December 2024 format)
                
                # Parse tables first
                tables = page.extract_tables()

                # Handle case where headers and data might be in separate tables
                combined_tables = self._combine_adjacent_transaction_tables(tables)

                for table in combined_tables:
                    if self._is_transaction_table(table):
                        page_transactions = self._parse_transaction_table(table)
                        transactions.extend(page_transactions)
                
                # Always try text parsing as fallback for ICICI statements
                # Some ICICI statements have transactions in both table and text formats
                text_transactions = self._parse_text_format(page)

                # Combine transactions, only removing truly identical duplicates
                combined_transactions = transactions + text_transactions
                unique_transactions = []
                seen_transactions = set()

                for txn in combined_transactions:
                    # Only deduplicate if transactions are completely identical
                    txn_key = f"{txn.date}|{txn.amount}|{txn.description.strip()}"
                    if txn_key not in seen_transactions:
                        unique_transactions.append(txn)
                        seen_transactions.add(txn_key)

                transactions = unique_transactions
                    
            logger.info(f"ICICI parser extracted {len(transactions)} transactions")
            return [t for t in transactions if self.validate_transaction(t)]
            
        except Exception as e:
            logger.error(f"ICICI parser failed: {str(e)}")
            return []
    
    def _is_transaction_table(self, table: List[List[str]]) -> bool:
        """Check if table contains ICICI transaction data"""
        if not table or len(table) < 1:
            return False

        # Look for ICICI-specific headers
        # Handle multi-line headers by normalizing whitespace and newlines
        headers_text = ' '.join([cell.lower().replace('\n', ' ').replace('\r', ' ') if cell else "" for cell in table[0]])

        # ICICI specific headers: Date, SerNo., Transaction Details, Reward Points, Amount
        icici_indicators = [
            'transaction details',
            'reward points',
            'serno',
            'intl. # amount',  # Updated to match "Intl.#\namount"
            'amount (in'
        ]

        return any(indicator in headers_text for indicator in icici_indicators)

    def _combine_adjacent_transaction_tables(self, tables: List[List[List[str]]]) -> List[List[List[str]]]:
        """Combine adjacent tables that might be split transaction tables"""
        if not tables:
            return tables

        combined_tables = []
        i = 0

        while i < len(tables):
            current_table = tables[i]

            # Check if current table has transaction headers but minimal data
            if (self._is_transaction_table(current_table) and len(current_table) <= 2):

                # Look for transaction data in subsequent tables (skip empty tables)
                data_table_found = False
                for j in range(i + 1, len(tables)):
                    candidate_table = tables[j]

                    # Skip empty or minimal tables
                    if not candidate_table or all(not row or all(not cell or not cell.strip() for cell in row) for row in candidate_table):
                        continue

                    # Check if this table has transaction-like data
                    if self._looks_like_transaction_data(candidate_table):
                        # Combine tables: headers from current + data from candidate
                        combined_table = current_table + candidate_table
                        combined_tables.append(combined_table)
                        data_table_found = True
                        # Skip all tables up to and including the data table
                        i = j + 1
                        break
                    else:
                        # If we hit a non-transaction table, stop looking
                        break

                if not data_table_found:
                    combined_tables.append(current_table)
                    i += 1
            else:
                combined_tables.append(current_table)
                i += 1

        return combined_tables

    def _looks_like_transaction_data(self, table: List[List[str]]) -> bool:
        """Check if table rows look like transaction data (date, serial, amount patterns)"""
        if not table:
            return False

        for row in table:
            if row and len(row) >= 3:
                # Check first column for date pattern
                first_col = row[0] if row[0] else ""
                if self._is_valid_date(first_col):
                    return True

        return False

    def _parse_transaction_table(self, table: List[List[str]]) -> List[Transaction]:
        """Parse ICICI transaction table with format: Date | SerNo. | Transaction Details | Reward Points | Intl.# | Amount"""
        transactions = []
        
        try:
            # Skip header row and process data rows
            for row in table[1:]:
                if len(row) < 4:  # Need at least date, details, and amount
                    continue
                
                # Extract data from row
                date_str = row[0] if len(row) > 0 else ""
                ser_no = row[1] if len(row) > 1 else ""
                description = row[2] if len(row) > 2 else ""
                amount_str = row[-1] if len(row) > 0 else ""  # Amount is typically last column
                
                # Validate date format (DD/MM/YYYY)
                if not self._is_valid_date(date_str):
                    continue
                
                # Skip if no description or amount
                if not description or not amount_str:
                    continue
                
                # Parse amount
                amount = self._parse_amount(amount_str)
                if amount == 0:
                    continue
                
                # Create transaction
                transaction = Transaction(
                    date=self.normalize_date(date_str, "DD/MM/YYYY"),
                    bank="ICICI",
                    txn_id=ser_no or f"ICICI_{date_str}_{len(transactions)}",
                    description=self.clean_description(description),
                    amount=amount
                )
                
                if self.validate_transaction(transaction):
                    transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Failed to parse ICICI transaction table: {str(e)}")
            
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
                # Look for transaction pattern: DD/MM/YYYY SERNUM Description Amount
                match = re.match(r'^(\d{1,2}/\d{1,2}/\d{4})\s+(\d+)\s+(.+?)\s+([\d,]+\.?\d*(?:\s*CR)?)$', line.strip())
                
                if match:
                    date_str = match.group(1)
                    ser_no = match.group(2)
                    description = match.group(3)
                    amount_str = match.group(4)
                    
                    amount = self._parse_amount(amount_str)
                    if amount == 0:
                        continue
                    
                    transaction = Transaction(
                        date=self.normalize_date(date_str, "DD/MM/YYYY"),
                        bank="ICICI",
                        txn_id=ser_no,
                        description=self.clean_description(description),
                        amount=amount
                    )
                    
                    if self.validate_transaction(transaction):
                        transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Failed to parse ICICI text format: {str(e)}")
            
        return transactions
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if string matches DD/MM/YYYY format"""
        if not date_str:
            return False
        return bool(re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str.strip()))
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount from ICICI format (numbers with optional CR for credit)"""
        if not amount_str:
            return 0.0
        
        try:
            # Clean the amount string
            amount_clean = amount_str.strip()
            
            # Check if it's a credit (CR suffix)
            is_credit = amount_clean.upper().endswith('CR')
            if is_credit:
                amount_clean = amount_clean[:-2].strip()  # Remove CR suffix
            
            # Remove commas and convert to float
            amount_clean = re.sub(r'[,`₹]', '', amount_clean)
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