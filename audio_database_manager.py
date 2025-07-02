"""
Updated Audio Database Manager with Enhanced File Handling
Supports both file paths and file-like objects for CSV upload functionality
"""

import pandas as pd
import re
from typing import Dict, List, Optional, Set, Tuple, Union, Any  # Added Any here
from dataclasses import dataclass
from pathlib import Path
import logging
import io

@dataclass
class AudioRecord:
    """Represents a single audio file record"""
    company: str
    folder: str
    file_name: str
    audio_id: str  # Extracted from file_name (e.g., "1001" from "1001.ulaw")
    transcript: str
    full_path: str  # e.g., "callflow:1001" or "type:1001"

class AudioDatabaseManager:
    """
    Enhanced Audio Database Manager that supports file uploads
    Handles loading, indexing, and searching the audio transcription database
    """
    
    def __init__(self, csv_source: Union[str, io.StringIO, pd.DataFrame] = None):
        self.audio_records: List[AudioRecord] = []
        self.transcript_index: Dict[str, List[AudioRecord]] = {}
        self.company_index: Dict[str, Dict[str, List[AudioRecord]]] = {}
        self.folder_index: Dict[str, List[AudioRecord]] = {}
        self.logger = logging.getLogger(__name__)
        
        if csv_source is not None:
            self.load_database(csv_source)
    
    def load_database(self, csv_source: Union[str, io.StringIO, pd.DataFrame]) -> None:
        """
        Load and index the audio database from various sources
        
        Args:
            csv_source: Can be file path, StringIO object, or DataFrame
        """
        try:
            self.logger.info(f"Loading audio database from {type(csv_source)}")
            
            # Handle different input types
            if isinstance(csv_source, pd.DataFrame):
                df = csv_source
            elif isinstance(csv_source, (str, Path)):
                df = pd.read_csv(csv_source)
            elif hasattr(csv_source, 'read'):
                # File-like object (StringIO, uploaded file, etc.)
                df = pd.read_csv(csv_source)
            else:
                raise ValueError(f"Unsupported csv_source type: {type(csv_source)}")
            
            # Validate required columns
            required_cols = ['Company', 'Folder', 'File Name', 'Transcript']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Clear existing data
            self.audio_records = []
            self.transcript_index = {}
            self.company_index = {}
            self.folder_index = {}
            
            # Process each record
            processed_count = 0
            for _, row in df.iterrows():
                try:
                    audio_record = self._create_audio_record(row)
                    if audio_record:
                        self.audio_records.append(audio_record)
                        processed_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to process row: {row.to_dict()}, Error: {e}")
            
            # Build indexes for fast searching
            self._build_indexes()
            self.logger.info(f"Loaded {processed_count} audio records from {len(df)} rows")
            
        except Exception as e:
            self.logger.error(f"Failed to load database: {e}")
            raise
    
    def load_from_uploaded_file(self, uploaded_file) -> None:
        """
        Convenience method to load from Streamlit uploaded file
        
        Args:
            uploaded_file: Streamlit UploadedFile object
        """
        try:
            # Convert uploaded file to StringIO
            content = uploaded_file.getvalue().decode('utf-8')
            csv_io = io.StringIO(content)
            self.load_database(csv_io)
        except Exception as e:
            self.logger.error(f"Failed to load from uploaded file: {e}")
            raise
    
    def _create_audio_record(self, row: pd.Series) -> Optional[AudioRecord]:
        """Create AudioRecord from CSV row"""
        try:
            company = str(row['Company']).strip().lower()
            folder = str(row['Folder']).strip()
            file_name = str(row['File Name']).strip()
            transcript = str(row['Transcript']).strip()
            
            # Skip invalid records
            if not all([company, folder, file_name, transcript]) or transcript.lower() in ['nan', 'none', '']:
                return None
            
            # Extract audio ID from filename (e.g., "1001.ulaw" -> "1001")
            audio_id = re.search(r'(\d+)', file_name)
            if not audio_id:
                self.logger.warning(f"Could not extract audio ID from filename: {file_name}")
                return None
            
            audio_id = audio_id.group(1)
            
            # Create full path (e.g., "callflow:1001", "type:1001")
            full_path = f"{folder}:{audio_id}"
            
            return AudioRecord(
                company=company,
                folder=folder,
                file_name=file_name,
                audio_id=audio_id,
                transcript=transcript,
                full_path=full_path
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create audio record: {e}")
            return None
    
    def _build_indexes(self) -> None:
        """Build search indexes for efficient lookups"""
        for record in self.audio_records:
            # Index by normalized transcript
            normalized = self._normalize_text(record.transcript)
            
            # Add to transcript index
            if normalized not in self.transcript_index:
                self.transcript_index[normalized] = []
            self.transcript_index[normalized].append(record)
            
            # Add to company index
            if record.company not in self.company_index:
                self.company_index[record.company] = {}
            if normalized not in self.company_index[record.company]:
                self.company_index[record.company][normalized] = []
            self.company_index[record.company][normalized].append(record)
            
            # Add to folder index
            if record.folder not in self.folder_index:
                self.folder_index[record.folder] = []
            self.folder_index[record.folder].append(record)
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching (lowercase, strip, remove extra spaces)"""
        return ' '.join(text.lower().strip().split())
    
    def find_exact_match(self, text: str, company: Optional[str] = None, folder: Optional[str] = None) -> Optional[AudioRecord]:
        """
        Find exact match for the given text
        
        Args:
            text: Text to search for
            company: Company context (None = search all)
            folder: Folder context (None = search all)
            
        Returns:
            AudioRecord if found, None otherwise
        """
        normalized = self._normalize_text(text)
        
        if company:
            # Search within specific company
            if company in self.company_index and normalized in self.company_index[company]:
                records = self.company_index[company][normalized]
                
                # Filter by folder if specified
                if folder:
                    records = [r for r in records if r.folder == folder]
                
                return records[0] if records else None
        else:
            # Search across all companies
            if normalized in self.transcript_index:
                records = self.transcript_index[normalized]
                
                # Filter by folder if specified
                if folder:
                    records = [r for r in records if r.folder == folder]
                
                return records[0] if records else None
        
        return None
    
    def find_by_prefix(self, prefix: str, company: Optional[str] = None, folder: Optional[str] = None) -> List[AudioRecord]:
        """Find all records that start with the given prefix"""
        normalized_prefix = self._normalize_text(prefix)
        results = []
        
        # Determine which records to search
        search_records = []
        if company and company in self.company_index:
            for transcript_records in self.company_index[company].values():
                search_records.extend(transcript_records)
        else:
            search_records = self.audio_records
        
        # Filter by prefix and folder
        for record in search_records:
            normalized_transcript = self._normalize_text(record.transcript)
            if normalized_transcript.startswith(normalized_prefix):
                if not folder or record.folder == folder:
                    results.append(record)
        
        return results
    
    def find_by_substring(self, substring: str, company: Optional[str] = None, folder: Optional[str] = None) -> List[AudioRecord]:
        """Find all records containing the substring"""
        normalized_substring = self._normalize_text(substring)
        results = []
        
        # Determine which records to search
        search_records = []
        if company and company in self.company_index:
            for transcript_records in self.company_index[company].values():
                search_records.extend(transcript_records)
        else:
            search_records = self.audio_records
        
        # Filter by substring and folder
        seen = set()  # Avoid duplicates
        for record in search_records:
            if record.full_path not in seen:
                normalized_transcript = self._normalize_text(record.transcript)
                if normalized_substring in normalized_transcript:
                    if not folder or record.folder == folder:
                        results.append(record)
                        seen.add(record.full_path)
        
        return results
    
    def get_companies(self) -> List[str]:
        """Get list of all companies in the database"""
        return sorted(list(self.company_index.keys()))
    
    def get_folders(self) -> List[str]:
        """Get list of all folders in the database"""
        return sorted(list(self.folder_index.keys()))
    
    def stats(self) -> Dict[str, int]:
        """Get database statistics"""
        return {
            'total_records': len(self.audio_records),
            'unique_transcripts': len(self.transcript_index),
            'companies': len(self.company_index),
            'folders': len(self.folder_index)
        }
    
    def validate_database(self) -> Dict[str, Any]:  # Any is now imported!
        """Validate database integrity and return report"""
        issues = []
        warnings = []
        
        # Check for duplicates
        seen_paths = {}
        for record in self.audio_records:
            if record.full_path in seen_paths:
                issues.append(f"Duplicate path found: {record.full_path} in companies: {seen_paths[record.full_path]}, {record.company}")
            else:
                seen_paths[record.full_path] = record.company
        
        # Check for empty transcripts
        empty_count = sum(1 for r in self.audio_records if not r.transcript)
        if empty_count > 0:
            warnings.append(f"{empty_count} records have empty transcripts")
        
        # Check for common folders
        expected_folders = ['callflow', 'type', 'reason', 'location', 'names', 'digits']
        missing_folders = [f for f in expected_folders if f not in self.folder_index]
        if missing_folders:
            warnings.append(f"Missing expected folders: {missing_folders}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'stats': self.stats()
        }

# Example usage for testing
if __name__ == "__main__":
    # Test with sample data
    test_data = pd.DataFrame([
        {"Company": "aep", "Folder": "callflow", "File Name": "1191.ulaw", "Transcript": "This is an"},
        {"Company": "aep", "Folder": "callflow", "File Name": "1274.ulaw", "Transcript": "callout from"},
        {"Company": "aep", "Folder": "type", "File Name": "1001.ulaw", "Transcript": "electric"},
    ])
    
    manager = AudioDatabaseManager(test_data)
    print(manager.stats())
    print(manager.validate_database())