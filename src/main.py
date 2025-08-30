import logging
import time
import schedule
from typing import List
from config import Config
from models import ProcessedFile, ProcessingResult
from google_drive_client import GoogleDriveClient
from google_sheets_client import GoogleSheetsClient
from pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

class CreditCardProcessor:
    def __init__(self):
        self.drive_client = GoogleDriveClient()
        self.sheets_client = GoogleSheetsClient()
        self.pdf_processor = PDFProcessor()
        
    def run_processing_cycle(self) -> None:
        try:
            logger.info("Starting processing cycle")
            
            if not self.sheets_client.verify_sheet_access():
                logger.error("Cannot access Google Sheet - aborting cycle")
                return
            
            if not self.sheets_client.ensure_headers_exist():
                logger.error("Failed to ensure headers exist - aborting cycle")
                return
            
            pdf_files = self.drive_client.get_pdf_files()
            
            if not pdf_files:
                logger.info("No PDF files found to process")
                return
                
            processed_files = []
            
            for pdf_file in pdf_files:
                if self.drive_client.file_exists_in_processed(pdf_file.filename):
                    logger.info(f"File {pdf_file.filename} already processed, skipping")
                    continue
                
                result = self._process_single_file(pdf_file)
                processed_files.append(result)
                
                if result.success and result.transactions:
                    success = self.sheets_client.batch_insert_transactions(result.transactions)
                    
                    if success:
                        moved = self.drive_client.move_to_processed_folder(
                            pdf_file.file_id, 
                            pdf_file.filename
                        )
                        
                        if moved:
                            logger.info(f"Successfully processed {pdf_file.filename}")
                        else:
                            logger.warning(f"Processed {pdf_file.filename} but failed to move to processed folder")
                    else:
                        logger.error(f"Failed to insert transactions for {pdf_file.filename}")
                else:
                    logger.error(f"Failed to process {pdf_file.filename}: {result.error_message}")
            
            total_transactions = sum(len(r.transactions) for r in processed_files if r.success)
            successful_files = sum(1 for r in processed_files if r.success)
            
            logger.info(f"Processing cycle complete: {successful_files}/{len(processed_files)} files processed, {total_transactions} transactions extracted")
            
        except Exception as e:
            logger.error(f"Processing cycle failed: {str(e)}")
    
    def _process_single_file(self, pdf_file: ProcessedFile) -> ProcessingResult:
        try:
            logger.info(f"Processing file: {pdf_file.filename}")
            
            file_buffer = self.drive_client.download_file(pdf_file.file_id)
            
            result = self.pdf_processor.process_pdf(file_buffer, pdf_file)
            
            if result.success:
                logger.info(f"Extracted {len(result.transactions)} transactions from {pdf_file.filename}")
            else:
                logger.error(f"Failed to process {pdf_file.filename}: {result.error_message}")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process file {pdf_file.filename}: {str(e)}"
            logger.error(error_msg)
            return ProcessingResult(
                file=pdf_file,
                transactions=[],
                success=False,
                error_message=error_msg
            )

def main():
    try:
        Config.setup_logging()
        logger.info("Credit Card PDF Processor starting...")
        
        if not Config.validate_config():
            logger.error("Configuration validation failed")
            exit(1)
        
        processor = CreditCardProcessor()
        
        schedule.every(Config.POLL_INTERVAL_MINUTES).minutes.do(processor.run_processing_cycle)
        
        logger.info(f"Scheduled to run every {Config.POLL_INTERVAL_MINUTES} minutes")
        
        processor.run_processing_cycle()
        
        while True:
            schedule.run_pending()
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application failed: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()