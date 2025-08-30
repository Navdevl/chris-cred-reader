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
                tables = page.extract_tables()
                
                for table in tables:
                    if self._is_transaction_table(table):
                        page_transactions = self._parse_transaction_table(table)
                        transactions.extend(page_transactions)
                
                if not tables:
                    text_transactions = self._parse_text_format(page)
                    transactions.extend(text_transactions)
                    
            logger.info(f"ICICI parser extracted {len(transactions)} transactions")
            return [t for t in transactions if self.validate_transaction(t)]
            
        except Exception as e:
            logger.error(f"ICICI parser failed: {str(e)}")
            return []
    
    def _is_transaction_table(self, table: List[List[str]]) -> bool:
        if not table or len(table) < 2:
            return False
            
        headers = [cell.lower() if cell else "" for cell in table[0]]
        
        required_headers = ['date', 'transaction', 'amount', 'balance']
        return any(req in ' '.join(headers) for req in required_headers)
    
    def _parse_transaction_table(self, table: List[List[str]]) -> List[Transaction]:
        transactions = []
        
        try:
            headers = [cell.lower().strip() if cell else "" for cell in table[0]]
            
            date_col = self._find_column_index(headers, ['transaction date', 'date', 'value date'])
            desc_col = self._find_column_index(headers, ['description', 'transaction details', 'particulars'])
            debit_col = self._find_column_index(headers, ['debit', 'debit amount', 'withdrawal amount'])
            credit_col = self._find_column_index(headers, ['credit', 'credit amount', 'deposit amount'])
            ref_col = self._find_column_index(headers, ['reference number', 'reference', 'serial number'])
            
            for row in table[1:]:
                if len(row) <= max([i for i in [date_col, desc_col, debit_col, credit_col] if i >= 0], default=0):
                    continue
                    
                if date_col >= 0 and desc_col >= 0:
                    date_str = row[date_col] if date_col < len(row) else ""
                    description = row[desc_col] if desc_col < len(row) else ""
                    debit_amount = row[debit_col] if debit_col >= 0 and debit_col < len(row) else ""
                    credit_amount = row[credit_col] if credit_col >= 0 and credit_col < len(row) else ""
                    ref_no = row[ref_col] if ref_col >= 0 and ref_col < len(row) else ""
                    
                    if date_str and description:
                        amount = 0.0
                        
                        if debit_amount and debit_amount.strip() and debit_amount.strip() != '-':
                            amount = -abs(self.normalize_amount(debit_amount))
                        elif credit_amount and credit_amount.strip() and credit_amount.strip() != '-':
                            amount = abs(self.normalize_amount(credit_amount))
                        
                        if amount != 0:
                            transaction = Transaction(
                                date=self.normalize_date(date_str, "DD/MM/YYYY"),
                                bank="ICICI",
                                txn_id=ref_no or f"ICICI_{date_str}_{len(transactions)}",
                                description=self.clean_description(description),
                                amount=amount
                            )
                            
                            if self.validate_transaction(transaction):
                                transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Failed to parse ICICI transaction table: {str(e)}")
            
        return transactions
    
    def _parse_text_format(self, page) -> List[Transaction]:
        transactions = []
        
        try:
            text = page.extract_text()
            if not text:
                return transactions
            
            date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b'
            
            lines = text.split('\n')
            
            for line in lines:
                date_match = re.search(date_pattern, line)
                
                if date_match:
                    date_str = date_match.group(1)
                    
                    debit_match = re.search(r'([\d,]+\.?\d*)\s*(?:Dr|Debit)', line, re.IGNORECASE)
                    credit_match = re.search(r'([\d,]+\.?\d*)\s*(?:Cr|Credit)', line, re.IGNORECASE)
                    
                    amount = 0.0
                    if debit_match:
                        amount = -abs(self.normalize_amount(debit_match.group(1)))
                    elif credit_match:
                        amount = abs(self.normalize_amount(credit_match.group(1)))
                    
                    if amount != 0:
                        description = line.strip()
                        description = re.sub(date_pattern, '', description)
                        description = re.sub(r'[\d,]+\.?\d*\s*(?:Dr|Cr|Debit|Credit)', '', description, flags=re.IGNORECASE)
                        description = self.clean_description(description)
                        
                        if description:
                            transaction = Transaction(
                                date=self.normalize_date(date_str, "DD/MM/YYYY"),
                                bank="ICICI",
                                txn_id=f"ICICI_TEXT_{date_str}_{len(transactions)}",
                                description=description,
                                amount=amount
                            )
                            
                            if self.validate_transaction(transaction):
                                transactions.append(transaction)
            
        except Exception as e:
            logger.error(f"Failed to parse ICICI text format: {str(e)}")
            
        return transactions
    
    def _find_column_index(self, headers: List[str], keywords: List[str]) -> int:
        for i, header in enumerate(headers):
            for keyword in keywords:
                if keyword in header:
                    return i
        return -1