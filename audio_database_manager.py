"""
Updated Audio Database Manager with Enhanced File Handling
Supports both file paths and file-like objects for CSV upload functionality
"""

import pandas as pd
import re
from typing import Dict, List, Optional, Set, Tuple, Union
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
            self.logger.error(f"Error creating audio record: {e}")
            return None
    
    def _build_indexes(self) -> None:
        """Build search indexes for efficient lookup"""
        self.transcript_index = {}
        self.company_index = {}
        self.folder_index = {}
        
        for record in self.audio_records:
            # Transcript index (exact match)
            transcript_key = self._normalize_text(record.transcript)
            if transcript_key not in self.transcript_index:
                self.transcript_index[transcript_key] = []
            self.transcript_index[transcript_key].append(record)
            
            # Company index
            if record.company not in self.company_index:
                self.company_index[record.company] = {}
            company_dict = self.company_index[record.company]
            
            if transcript_key not in company_dict:
                company_dict[transcript_key] = []
            company_dict[transcript_key].append(record)
            
            # Folder index
            if record.folder not in self.folder_index:
                self.folder_index[record.folder] = []
            self.folder_index[record.folder].append(record)
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent matching"""
        if not text:
            return ""
        
        # Remove extra whitespace and convert to lowercase
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        
        # Remove punctuation at the end but keep internal punctuation
        normalized = re.sub(r'[.!?;]+$', '', normalized)
        
        return normalized
    
    def search_exact_match(self, text: str, company: str = None, schema: str = None) -> List[AudioRecord]:
        """
        Search for exact text match following hierarchy: Schema → Company → Global
        This implements Andres's search process
        """
        normalized_text = self._normalize_text(text)
        
        if not normalized_text:
            return []
        
        # Search hierarchy: Schema → Company → Global
        search_contexts = []
        
        # 1. Schema-specific (if provided)
        if schema:
            search_contexts.append(f"schema_{schema.lower()}")
        
        # 2. Company-specific (if provided)
        if company:
            search_contexts.append(company.lower())
        
        # 3. Global (arcos)
        search_contexts.append("arcos")
        
        # Search in hierarchy order
        for context in search_contexts:
            if context in self.company_index:
                company_records = self.company_index[context]
                if normalized_text in company_records:
                    results = company_records[normalized_text]
                    self.logger.debug(f"Found exact match in {context}: {text} -> {[r.full_path for r in results]}")
                    return results
        
        # If no company-specific match, search global index
        if normalized_text in self.transcript_index:
            results = self.transcript_index[normalized_text]
            self.logger.debug(f"Found exact match globally: {text} -> {[r.full_path for r in results]}")
            return results
        
        return []
    
    def search_partial_match(self, text: str, company: str = None, min_score: float = 0.8) -> List[Tuple[AudioRecord, float]]:
        """
        Search for partial text matches with similarity scoring
        Useful for finding close matches when exact match fails
        """
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return []
        
        matches = []
        search_records = self.audio_records
        
        # Filter by company if provided
        if company:
            search_records = [r for r in self.audio_records if r.company == company.lower()]
        
        for record in search_records:
            normalized_transcript = self._normalize_text(record.transcript)
            
            # Simple similarity scoring (can be enhanced with more sophisticated algorithms)
            if normalized_text in normalized_transcript:
                score = len(normalized_text) / len(normalized_transcript)
            elif normalized_transcript in normalized_text:
                score = len(normalized_transcript) / len(normalized_text)
            else:
                # Calculate word overlap
                text_words = set(normalized_text.split())
                transcript_words = set(normalized_transcript.split())
                overlap = len(text_words.intersection(transcript_words))
                total_words = len(text_words.union(transcript_words))
                score = overlap / total_words if total_words > 0 else 0
            
            if score >= min_score:
                matches.append((record, score))
        
        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def get_companies(self) -> List[str]:
        """Get list of all companies in database"""
        return list(self.company_index.keys())
    
    def get_folders(self) -> List[str]:
        """Get list of all folders in database"""
        return list(self.folder_index.keys())
    
    def get_records_by_folder(self, folder: str) -> List[AudioRecord]:
        """Get all records for a specific folder"""
        return self.folder_index.get(folder, [])
    
    def get_records_by_company(self, company: str) -> List[AudioRecord]:
        """Get all records for a specific company"""
        company_lower = company.lower()
        if company_lower not in self.company_index:
            return []
        
        all_records = []
        for transcript_records in self.company_index[company_lower].values():
            all_records.extend(transcript_records)
        return all_records
    
    def get_sample_records(self, count: int = 10, company: str = None) -> List[AudioRecord]:
        """Get sample records for preview"""
        if company:
            records = self.get_records_by_company(company)
        else:
            records = self.audio_records
        
        return records[:count]
    
    def export_to_dataframe(self) -> pd.DataFrame:
        """Export audio records back to DataFrame format"""
        data = []
        for record in self.audio_records:
            data.append({
                'Company': record.company,
                'Folder': record.folder,
                'File Name': record.file_name,
                'Transcript': record.transcript
            })
        return pd.DataFrame(data)
    
    def stats(self) -> Dict[str, int]:
        """Get database statistics"""
        return {
            'total_records': len(self.audio_records),
            'unique_transcripts': len(self.transcript_index),
            'companies': len(self.company_index),
            'folders': len(self.folder_index)
        }
    
    def validate_database(self) -> Dict[str, Any]:
        """Validate database integrity and return report"""
        issues = []
        warnings = []
        
        # Check for duplicate audio IDs within same company/folder
        id_combinations = {}
        for record in self.audio_records:
            key = (record.company, record.folder, record.audio_id)
            if key in id_combinations:
                issues.append(f"Duplicate audio ID: {key}")
            else:
                id_combinations[key] = record
        
        # Check for empty transcripts
        empty_transcripts = [r for r in self.audio_records if not r.transcript.strip()]
        if empty_transcripts:
            warnings.append(f"Found {len(empty_transcripts)} records with empty transcripts")
        
        # Check for unusual file naming patterns
        unusual_files = [r for r in self.audio_records if not re.search(r'\d+', r.file_name)]
        if unusual_files:
            warnings.append(f"Found {len(unusual_files)} files without numeric IDs")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'stats': self.stats()
        }