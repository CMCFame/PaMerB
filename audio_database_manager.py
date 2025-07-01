"""
Audio Database Manager for IVR Code Generation
Handles loading, indexing, and searching the audio transcription database
Following Andres's manual process for exact audio file mapping
"""

import pandas as pd
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

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
    Manages the audio transcription database and provides search functionality
    Implements Andres's manual search process programmatically
    """
    
    def __init__(self, csv_path: str = None):
        self.audio_records: List[AudioRecord] = []
        self.transcript_index: Dict[str, List[AudioRecord]] = {}
        self.company_index: Dict[str, Dict[str, List[AudioRecord]]] = {}
        self.folder_index: Dict[str, List[AudioRecord]] = {}
        self.logger = logging.getLogger(__name__)
        
        if csv_path:
            self.load_database(csv_path)
    
    def load_database(self, csv_path: str) -> None:
        """Load and index the audio database from CSV"""
        try:
            df = pd.read_csv(csv_path)
            self.logger.info(f"Loading audio database from {csv_path}")
            
            # Validate required columns
            required_cols = ['Company', 'Folder', 'File Name', 'Transcript']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Process each record
            for _, row in df.iterrows():
                try:
                    audio_record = self._create_audio_record(row)
                    if audio_record:
                        self.audio_records.append(audio_record)
                except Exception as e:
                    self.logger.warning(f"Failed to process row: {row.to_dict()}, Error: {e}")
            
            # Build indexes for fast searching
            self._build_indexes()
            self.logger.info(f"Loaded {len(self.audio_records)} audio records")
            
        except Exception as e:
            self.logger.error(f"Failed to load database: {e}")
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
    
    def stats(self) -> Dict[str, int]:
        """Get database statistics"""
        return {
            'total_records': len(self.audio_records),
            'unique_transcripts': len(self.transcript_index),
            'companies': len(self.company_index),
            'folders': len(self.folder_index)
        }