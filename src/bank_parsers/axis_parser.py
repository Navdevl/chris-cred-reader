import logging
import re
from typing import List
import pdfplumber
from .base_parser import BaseParser
from models import Transaction

logger = logging.getLogger(__name__)

class AxisParser(BaseParser):
    def __init__(self):
        super().__init__("Axis")
    
    def parse_pdf(self, pdf: pdfplumber.PDF) -> List[Transaction]:
        transactions = []
        
        try:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                
                for table in tables:
                    if self._is_transaction_table(table):
                        page_transactions = self._parse_transaction_table(table)
                        transactions.extend(page_transactions)
                        
                if not tables:
                    text_transactions = self._parse_text_format(page)
                    transactions.extend(text_transactions)
                    
            logger.info(f"Axis parser extracted {len(transactions)} transactions")
            return [t for t in transactions if self.validate_transaction(t)]
            
        except Exception as e:
            logger.error(f"Axis parser failed: {str(e)}")
            return []
    
    def _is_transaction_table(self, table: List[List[str]]) -> bool:
        if not table or len(table) < 2:
            return False
            
        headers = [cell.lower() if cell else "" for cell in table[0]]
        header_text = ' '.join(headers)
        
        # Check for transaction table indicators
        transaction_indicators = [
            'date', 'transaction details', 'transaction', 'amount', 
            'merchant category', 'description', 'particulars'
        ]
        return any(indicator in header_text for indicator in transaction_indicators)
    
    def _parse_transaction_table(self, table: List[List[str]]) -> List[Transaction]:
        transactions = []
        
        try:
            # Find the actual header row - might not be row 0
            header_row_idx = self._find_header_row(table)
            if header_row_idx == -1:
                logger.warning("Could not find header row in transaction table")
                return transactions
            
            headers = [cell.lower().strip() if cell else "" for cell in table[header_row_idx]]
            
            date_col = self._find_column_index(headers, ['date', 'transaction date', 'txn date'])
            desc_col = self._find_column_index(headers, ['transaction details', 'description', 'particulars', 'details'])
            amount_col = self._find_column_index(headers, ['amount', 'debit', 'credit', 'txn amount'])
            ref_col = self._find_column_index(headers, ['reference', 'ref no', 'transaction id', 'txn id'])
            
            logger.info(f"Found columns - Date: {date_col}, Desc: {desc_col}, Amount: {amount_col}, Ref: {ref_col}")
            
            # Process data rows starting after the header row
            for row_idx in range(header_row_idx + 1, len(table)):
                row = table[row_idx]
                if len(row) <= max(date_col, desc_col, amount_col) if date_col >= 0 and desc_col >= 0 and amount_col >= 0 else 0:
                    continue
                    
                if date_col >= 0 and desc_col >= 0 and amount_col >= 0:
                    date_str = row[date_col] if date_col < len(row) else ""
                    description = row[desc_col] if desc_col < len(row) else ""
                    amount_str = row[amount_col] if amount_col < len(row) else ""
                    ref_no = row[ref_col] if ref_col >= 0 and ref_col < len(row) else ""
                    
                    if date_str and description and amount_str:
                        try:
                            transaction = Transaction(
                                date=self.normalize_date(date_str, "DD/MM/YYYY"),
                                bank="Axis",
                                txn_id=ref_no or f"AXIS_{date_str}_{len(transactions)}",
                                description=self.clean_description(description),
                                amount=self.normalize_amount(amount_str)
                            )
                            
                            if self.validate_transaction(transaction):
                                transactions.append(transaction)
                                
                        except Exception as e:
                            logger.warning(f"Failed to parse row {row}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to parse Axis transaction table: {str(e)}")
            
        return transactions
    
    def _parse_text_format(self, page) -> List[Transaction]:
        transactions = []
        
        try:
            text = page.extract_text()
            if not text:
                return transactions
            
            date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'
            amount_pattern = r'(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)\s*(?:Dr|Cr)?'
            
            lines = text.split('\n')
            
            for line in lines:
                date_match = re.search(date_pattern, line)
                amount_match = re.search(amount_pattern, line)
                
                if date_match and amount_match:
                    date_str = date_match.group(1)
                    amount_str = amount_match.group(0)
                    
                    description = line.strip()
                    description = re.sub(date_pattern, '', description)
                    description = re.sub(amount_pattern, '', description)
                    description = self.clean_description(description)
                    
                    if description:
                        transaction = Transaction(
                            date=self.normalize_date(date_str, "DD/MM/YYYY"),
                            bank="Axis",
                            txn_id=f"AXIS_TEXT_{date_str}_{len(transactions)}",
                            description=description,
                            amount=self.normalize_amount(amount_str)
                        )
                        
                        if self.validate_transaction(transaction):
                            transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Failed to parse Axis text format: {str(e)}")
            
        return transactions
    
    def _find_column_index(self, headers: List[str], keywords: List[str]) -> int:
        for i, header in enumerate(headers):
            for keyword in keywords:
                if keyword in header:
                    return i
        return -1
    
    def _find_header_row(self, table: List[List[str]]) -> int:
        """Find the row that contains the actual column headers"""
        for i, row in enumerate(table):
            if not row:
                continue
            
            # Look for key header indicators
            row_text = ' '.join([cell.lower() if cell else "" for cell in row])
            
            if ('date' in row_text and 
                ('transaction details' in row_text or 'description' in row_text) and
                'amount' in row_text):
                return i
                
            # Also check for exact matches
            if any(cell and cell.lower() == 'date' for cell in row):
                return i
                
        return -1