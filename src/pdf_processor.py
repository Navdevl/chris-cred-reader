import io
import logging
from typing import List, Optional
import pdfplumber
from models import Transaction, ProcessedFile, ProcessingResult

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.bank_parsers = self._load_bank_parsers()
    
    def _load_bank_parsers(self):
        from bank_parsers.axis_parser import AxisParser
        from bank_parsers.hdfc_parser import HDFCParser
        from bank_parsers.sbi_parser import SBIParser
        from bank_parsers.icici_parser import ICICIParser
        
        return {
            'axis': AxisParser(),
            'hdfc': HDFCParser(),
            'sbi': SBIParser(),
            'icici': ICICIParser()
        }
    
    def process_pdf(self, file_buffer: io.BytesIO, processed_file: ProcessedFile) -> ProcessingResult:
        try:
            logger.info(f"Processing PDF: {processed_file.filename}")
            
            file_buffer.seek(0)
            
            with pdfplumber.open(file_buffer, password=processed_file.password) as pdf:
                
                if processed_file.bank not in self.bank_parsers:
                    error_msg = f"No parser available for bank: {processed_file.bank}"
                    logger.error(error_msg)
                    return ProcessingResult(
                        file=processed_file,
                        transactions=[],
                        success=False,
                        error_message=error_msg
                    )
                
                parser = self.bank_parsers[processed_file.bank]
                transactions = parser.parse_pdf(pdf)
                
                logger.info(f"Extracted {len(transactions)} transactions from {processed_file.filename}")
                
                return ProcessingResult(
                    file=processed_file,
                    transactions=transactions,
                    success=True
                )
                
        except Exception as e:
            error_msg = f"Failed to process PDF {processed_file.filename}: {str(e)}"
            logger.error(error_msg)
            return ProcessingResult(
                file=processed_file,
                transactions=[],
                success=False,
                error_message=error_msg
            )
    
    def extract_text_content(self, pdf: pdfplumber.PDF) -> str:
        try:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
            return full_text
        except Exception as e:
            logger.error(f"Failed to extract text content: {str(e)}")
            return ""
    
    def extract_tables(self, pdf: pdfplumber.PDF) -> List[List[List[str]]]:
        try:
            all_tables = []
            for page_num, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                if page_tables:
                    logger.debug(f"Found {len(page_tables)} tables on page {page_num + 1}")
                    all_tables.extend(page_tables)
            return all_tables
        except Exception as e:
            logger.error(f"Failed to extract tables: {str(e)}")
            return []