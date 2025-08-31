import io
import csv
import logging
from datetime import datetime
from typing import List, Optional, Tuple
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from config import Config
from models import ProcessedFile

logger = logging.getLogger(__name__)

class GoogleDriveClient:
    def __init__(self):
        self.credentials = self._get_credentials()
        self.service = build('drive', 'v3', credentials=self.credentials)
        
    def _get_credentials(self) -> Credentials:
        try:
            credentials = Credentials.from_service_account_file(
                Config.GOOGLE_APPLICATION_CREDENTIALS,
                scopes=Config.GOOGLE_DRIVE_SCOPES
            )
            return credentials
        except Exception as e:
            logger.error(f"Failed to load Google Drive credentials: {str(e)}")
            raise
    
    def get_pdf_files(self) -> List[ProcessedFile]:
        try:
            query = f"'{Config.GOOGLE_DRIVE_FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="files(id, name, modifiedTime)"
            ).execute()
            
            files = results.get('files', [])
            processed_files = []
            
            for file in files:
                parsed_file = ProcessedFile.parse_filename(file['name'])
                if parsed_file:
                    parsed_file.file_id = file['id']
                    processed_files.append(parsed_file)
                else:
                    logger.warning(f"Skipping invalid filename: {file['name']}")
                    
            logger.info(f"Found {len(processed_files)} valid PDF files")
            return processed_files
            
        except Exception as e:
            logger.error(f"Failed to list Google Drive files: {str(e)}")
            raise
    
    def download_file(self, file_id: str) -> io.BytesIO:
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            
            while done is False:
                status, done = downloader.next_chunk()
                
            file_buffer.seek(0)
            logger.debug(f"Downloaded file {file_id}, size: {file_buffer.getbuffer().nbytes} bytes")
            return file_buffer
            
        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {str(e)}")
            raise
    
    def move_to_processed_folder(self, file_id: str, filename: str) -> bool:
        try:
            processed_folder_id = self._get_or_create_processed_folder()
            
            self.service.files().update(
                fileId=file_id,
                addParents=processed_folder_id,
                removeParents=Config.GOOGLE_DRIVE_FOLDER_ID,
                fields='id, parents'
            ).execute()
            
            logger.info(f"Moved {filename} to processed folder")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move file {filename}: {str(e)}")
            return False
    
    def _get_or_create_processed_folder(self) -> str:
        try:
            query = f"'{Config.GOOGLE_DRIVE_FOLDER_ID}' in parents and name='{Config.PROCESSED_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=1,
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                logger.debug(f"Found existing processed folder: {folders[0]['id']}")
                return folders[0]['id']
            
            folder_metadata = {
                'name': Config.PROCESSED_FOLDER_NAME,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [Config.GOOGLE_DRIVE_FOLDER_ID]
            }
            
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            logger.info(f"Created processed folder: {folder['id']}")
            return folder['id']
            
        except Exception as e:
            logger.error(f"Failed to get/create processed folder: {str(e)}")
            raise
    
    def file_exists_in_processed(self, filename: str) -> bool:
        try:
            processed_folder_id = self._get_or_create_processed_folder()
            
            query = f"'{processed_folder_id}' in parents and name='{filename}' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=1,
                fields="files(id)"
            ).execute()
            
            files = results.get('files', [])
            exists = len(files) > 0
            
            if exists:
                logger.debug(f"File {filename} already exists in processed folder")
                
            return exists
            
        except Exception as e:
            logger.error(f"Failed to check if file exists in processed folder: {str(e)}")
            return False
    
    def file_exists_in_failed(self, filename: str) -> bool:
        try:
            failed_folder_id = self._get_or_create_failed_folder()
            
            query = f"'{failed_folder_id}' in parents and name='{filename}' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=1,
                fields="files(id)"
            ).execute()
            
            files = results.get('files', [])
            exists = len(files) > 0
            
            if exists:
                logger.debug(f"File {filename} already exists in failed folder")
                
            return exists
            
        except Exception as e:
            logger.error(f"Failed to check if file exists in failed folder: {str(e)}")
            return False
    
    def move_to_failed_folder(self, file_id: str, filename: str, error_reason: str) -> bool:
        try:
            failed_folder_id = self._get_or_create_failed_folder()
            
            # Move file to failed folder
            self.service.files().update(
                fileId=file_id,
                addParents=failed_folder_id,
                removeParents=Config.GOOGLE_DRIVE_FOLDER_ID,
                fields='id, parents'
            ).execute()
            
            # Log error to CSV file in failed folder
            self._log_error_to_csv(failed_folder_id, filename, error_reason)
            
            logger.info(f"Moved {filename} to failed folder with reason: {error_reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move file {filename} to failed folder: {str(e)}")
            return False
    
    def _get_or_create_failed_folder(self) -> str:
        try:
            query = f"'{Config.GOOGLE_DRIVE_FOLDER_ID}' in parents and name='{Config.FAILED_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=1,
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                logger.debug(f"Found existing failed folder: {folders[0]['id']}")
                return folders[0]['id']
            
            folder_metadata = {
                'name': Config.FAILED_FOLDER_NAME,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [Config.GOOGLE_DRIVE_FOLDER_ID]
            }
            
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            logger.info(f"Created failed folder: {folder['id']}")
            return folder['id']
            
        except Exception as e:
            logger.error(f"Failed to get/create failed folder: {str(e)}")
            raise
    
    def _log_error_to_csv(self, failed_folder_id: str, filename: str, error_reason: str) -> None:
        try:
            # Check if errors.csv already exists in failed folder
            error_file_id = self._get_error_csv_file_id(failed_folder_id)
            
            if error_file_id:
                # Download existing CSV, append new error, and upload back
                existing_content = self._download_error_csv(error_file_id)
                updated_content = self._append_error_to_csv(existing_content, filename, error_reason)
                self._update_error_csv(error_file_id, updated_content)
            else:
                # Create new errors.csv file
                csv_content = self._create_new_error_csv(filename, error_reason)
                self._create_error_csv_file(failed_folder_id, csv_content)
                
            logger.debug(f"Logged error for {filename} to errors.csv")
            
        except Exception as e:
            logger.error(f"Failed to log error to CSV: {str(e)}")
    
    def _get_error_csv_file_id(self, failed_folder_id: str) -> Optional[str]:
        try:
            query = f"'{failed_folder_id}' in parents and name='{Config.ERROR_LOG_FILENAME}' and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=1,
                fields="files(id)"
            ).execute()
            
            files = results.get('files', [])
            return files[0]['id'] if files else None
            
        except Exception as e:
            logger.error(f"Failed to check for existing error CSV: {str(e)}")
            return None
    
    def _download_error_csv(self, file_id: str) -> str:
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            
            while done is False:
                status, done = downloader.next_chunk()
            
            file_buffer.seek(0)
            return file_buffer.read().decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to download error CSV: {str(e)}")
            return ""
    
    def _append_error_to_csv(self, existing_content: str, filename: str, error_reason: str) -> str:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_row = f"\n{current_time},{filename},\"{error_reason}\""
        return existing_content.rstrip() + new_row
    
    def _create_new_error_csv(self, filename: str, error_reason: str) -> str:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        csv_content = "Date,Filename,Reason\n"
        csv_content += f"{current_time},{filename},\"{error_reason}\""
        return csv_content
    
    def _update_error_csv(self, file_id: str, content: str) -> None:
        try:
            media = MediaIoBaseUpload(
                io.BytesIO(content.encode('utf-8')),
                mimetype='text/csv'
            )
            
            self.service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            
        except Exception as e:
            logger.error(f"Failed to update error CSV: {str(e)}")
            raise
    
    def _create_error_csv_file(self, failed_folder_id: str, content: str) -> None:
        try:
            file_metadata = {
                'name': Config.ERROR_LOG_FILENAME,
                'parents': [failed_folder_id],
                'mimeType': 'text/csv'
            }
            
            media = MediaIoBaseUpload(
                io.BytesIO(content.encode('utf-8')),
                mimetype='text/csv'
            )
            
            self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            logger.debug(f"Created new error CSV file in failed folder")
            
        except Exception as e:
            logger.error(f"Failed to create error CSV file: {str(e)}")
            raise