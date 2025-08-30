import io
import logging
from typing import List, Optional, Tuple
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
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