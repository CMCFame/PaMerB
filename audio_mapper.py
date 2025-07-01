"""
Intelligent Audio Mapper for IVR Code Generation
Maps text segments to audio IDs following Andres's exact methodology
Handles complete phrase matching, segment building, and missing audio detection
"""

from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import logging
import re

from audio_database_manager import AudioDatabaseManager, AudioRecord
from segment_parser import SegmentParser, TextSegment

@dataclass
class AudioMapping:
    """Represents the result of mapping text to audio"""
    original_text: str
    play_prompt: List[str]  # Array of audio IDs like ["callflow:1191", "type:{{callout_type}}"]
    play_log: List[str]     # Human-readable description
    missing_segments: List[str]  # Segments that couldn't be mapped
    success_rate: float     # Percentage of text successfully mapped
    mapping_method: str     # How the mapping was achieved

class AudioMapper:
    """
    Maps IVR text to audio file IDs using intelligent segment analysis
    Implements Andres's manual process: exact match → segment building → flag missing
    """
    
    def __init__(self, database_manager: AudioDatabaseManager):
        self.db = database_manager
        self.parser = SegmentParser()
        self.logger = logging.getLogger(__name__)
        
        # Common dynamic variable mappings
        self.variable_mappings = {
            'callout_type': 'type:{{callout_type}}',
            'callout_reason': 'reason:{{callout_reason}}',
            'callout_location': 'location:{{callout_location}}',
            'level1_location': 'location:{{level1_location}}',
            'level2_location': 'location:{{level2_location}}',
            'level3_location': 'location:{{level3_location}}',
            'level4_location': 'location:{{level4_location}}',
            'contact_id': 'names:{{contact_id}}',
            'employee': 'names:{{contact_id}}',  # Alias
            'employee_name': 'names:{{contact_id}}',  # Alias
            'custom_message': 'custom:{{custom_message}}',
            'env': 'callflow:{{env}}',
            'pin': 'pin:{{pin}}'
        }
        
        # Digit mappings
        self.digit_mappings = {
            '1': 'digits:1', '2': 'digits:2', '3': 'digits:3',
            '4': 'digits:4', '5': 'digits:5', '6': 'digits:6',
            '7': 'digits:7', '8': 'digits:8', '9': 'digits:9',
            '0': 'digits:0',
            'one': 'digits:1', 'two': 'digits:2', 'three': 'digits:3',
            'four': 'digits:4', 'five': 'digits:5', 'six': 'digits:6',
            'seven': 'digits:7', 'eight': 'digits:8', 'nine': 'digits:9',
            'zero': 'digits:0'
        }
    
    def map_text_to_audio(self, text: str, company: str = None, schema: str = None) -> AudioMapping:
        """
        Map text to audio IDs following Andres's methodology
        
        Args:
            text: Text to map to audio
            company: Company context for hierarchy search
            schema: Schema context for hierarchy search
            
        Returns:
            AudioMapping with results
        """
        self.logger.info(f"Mapping text to audio: '{text}' (company: {company}, schema: {schema})")
        
        if not text.strip():
            return AudioMapping(
                original_text=text,
                play_prompt=[],
                play_log=[],
                missing_segments=[],
                success_rate=0.0,
                mapping_method="empty_text"
            )
        
        # Step 1: Try exact match first (Andres's first approach)
        exact_match = self._try_exact_match(text, company, schema)
        if exact_match:
            return exact_match
        
        # Step 2: Parse into segments and build from parts
        segments = self.parser.parse_text(text)
        if not segments:
            return AudioMapping(
                original_text=text,
                play_prompt=[],
                play_log=[text],
                missing_segments=[text],
                success_rate=0.0,
                mapping_method="parse_failed"
            )
        
        # Step 3: Map individual segments
        segment_mapping = self._map_segments(segments, company, schema)
        
        return segment_mapping
    
    def _try_exact_match(self, text: str, company: str = None, schema: str = None) -> Optional[AudioMapping]:
        """Try to find exact match in database"""
        records = self.db.search_exact_match(text, company, schema)
        
        if records:
            # Use the first match (could be enhanced to choose best match)
            record = records[0]
            self.logger.info(f"Found exact match: '{text}' -> {record.full_path}")
            
            return AudioMapping(
                original_text=text,
                play_prompt=[record.full_path],
                play_log=[text],
                missing_segments=[],
                success_rate=1.0,
                mapping_method="exact_match"
            )
        
        return None
    
    def _map_segments(self, segments: List[TextSegment], company: str = None, schema: str = None) -> AudioMapping:
        """Map individual segments to audio IDs"""
        play_prompt = []
        play_log = []
        missing_segments = []
        mapped_count = 0
        
        for segment in segments:
            mapping_result = self._map_single_segment(segment, company, schema)
            
            if mapping_result['audio_id']:
                play_prompt.append(mapping_result['audio_id'])
                play_log.append(mapping_result['description'])
                mapped_count += 1
            else:
                missing_segments.append(segment.text)
                play_log.append(f"[MISSING: {segment.text}]")
        
        success_rate = mapped_count / len(segments) if segments else 0.0
        
        # Try to group consecutive segments for better matching
        if missing_segments and len(missing_segments) < len(segments):
            # Attempt to find multi-segment matches
            improved_mapping = self._try_segment_combinations(segments, company, schema)
            if improved_mapping and improved_mapping.success_rate > success_rate:
                return improved_mapping
        
        return AudioMapping(
            original_text=' '.join(s.text for s in segments),
            play_prompt=play_prompt,
            play_log=play_log,
            missing_segments=missing_segments,
            success_rate=success_rate,
            mapping_method="segment_mapping"
        )
    
    def _map_single_segment(self, segment: TextSegment, company: str = None, schema: str = None) -> Dict[str, str]:
        """Map a single segment to audio ID"""
        
        # Handle dynamic variables
        if segment.is_variable:
            return self._map_variable_segment(segment)
        
        # Handle digits
        if segment.segment_type == 'digit':
            return self._map_digit_segment(segment)
        
        # Handle static text
        return self._map_static_segment(segment, company, schema)
    
    def _map_variable_segment(self, segment: TextSegment) -> Dict[str, str]:
        """Map dynamic variable segment"""
        var_name = segment.variable_name or segment.text.strip('{}()')
        
        # Normalize variable name
        var_name_clean = var_name.lower().replace(' ', '_')
        
        if var_name_clean in self.variable_mappings:
            audio_id = self.variable_mappings[var_name_clean]
            description = f"[{var_name}]"
            self.logger.debug(f"Mapped variable: {segment.text} -> {audio_id}")
            return {'audio_id': audio_id, 'description': description}
        
        # If not found, create a generic mapping
        audio_id = f"dynamic:{{{{var_name_clean}}}}"
        description = f"[{var_name}]"
        self.logger.warning(f"Unknown variable: {segment.text} -> {audio_id}")
        return {'audio_id': audio_id, 'description': description}
    
    def _map_digit_segment(self, segment: TextSegment) -> Dict[str, str]:
        """Map digit segment"""
        digit_text = segment.text.lower()
        
        if digit_text in self.digit_mappings:
            audio_id = self.digit_mappings[digit_text]
            description = digit_text
            self.logger.debug(f"Mapped digit: {segment.text} -> {audio_id}")
            return {'audio_id': audio_id, 'description': description}
        
        return {'audio_id': None, 'description': segment.text}
    
    def _map_static_segment(self, segment: TextSegment, company: str = None, schema: str = None) -> Dict[str, str]:
        """Map static text segment"""
        records = self.db.search_exact_match(segment.text, company, schema)
        
        if records:
            record = records[0]
            self.logger.debug(f"Mapped static segment: {segment.text} -> {record.full_path}")
            return {'audio_id': record.full_path, 'description': segment.text}
        
        # Try some common variations
        variations = self._generate_text_variations(segment.text)
        for variation in variations:
            records = self.db.search_exact_match(variation, company, schema)
            if records:
                record = records[0]
                self.logger.debug(f"Mapped variation: {segment.text} ({variation}) -> {record.full_path}")
                return {'audio_id': record.full_path, 'description': segment.text}
        
        return {'audio_id': None, 'description': segment.text}
    
    def _generate_text_variations(self, text: str) -> List[str]:
        """Generate common variations of text for searching"""
        variations = []
        
        # Remove punctuation
        no_punct = re.sub(r'[^\w\s]', '', text)
        if no_punct != text:
            variations.append(no_punct)
        
        # Add punctuation
        variations.extend([
            f"{text}.",
            f"{text}!",
            f"{text}?",
            f"{text},",
        ])
        
        # Try with different articles
        if text.startswith('a '):
            variations.append(text.replace('a ', 'an ', 1))
        elif text.startswith('an '):
            variations.append(text.replace('an ', 'a ', 1))
        
        return variations
    
    def _try_segment_combinations(self, segments: List[TextSegment], company: str = None, schema: str = None) -> Optional[AudioMapping]:
        """Try different combinations of segments for better matching"""
        combinations = self.parser.get_segment_combinations(segments)
        
        best_mapping = None
        best_score = 0.0
        
        for combination in combinations:
            if len(combination) <= 1:
                continue  # Skip individual segments, already tried
            
            combined_text = self.parser.segments_to_text(combination)
            exact_match = self._try_exact_match(combined_text, company, schema)
            
            if exact_match and exact_match.success_rate > best_score:
                best_mapping = exact_match
                best_score = exact_match.success_rate
        
        return best_mapping
    
    def get_mapping_report(self, mapping: AudioMapping) -> str:
        """Generate a human-readable report of the mapping"""
        report = []
        report.append(f"Text: '{mapping.original_text}'")
        report.append(f"Method: {mapping.mapping_method}")
        report.append(f"Success Rate: {mapping.success_rate:.1%}")
        
        if mapping.play_prompt:
            report.append("Audio Prompts:")
            for i, (prompt, log) in enumerate(zip(mapping.play_prompt, mapping.play_log)):
                report.append(f"  {i+1}. {prompt} // {log}")
        
        if mapping.missing_segments:
            report.append("Missing Segments:")
            for segment in mapping.missing_segments:
                report.append(f"  - '{segment}' (needs recording)")
        
        return '\n'.join(report)
    
    def batch_map_texts(self, texts: List[str], company: str = None, schema: str = None) -> List[AudioMapping]:
        """Map multiple texts at once"""
        results = []
        
        for text in texts:
            mapping = self.map_text_to_audio(text, company, schema)
            results.append(mapping)
        
        return results
    
    def analyze_coverage(self, texts: List[str], company: str = None, schema: str = None) -> Dict:
        """Analyze how well the database covers a list of texts"""
        mappings = self.batch_map_texts(texts, company, schema)
        
        total_texts = len(texts)
        fully_mapped = sum(1 for m in mappings if m.success_rate == 1.0)
        partially_mapped = sum(1 for m in mappings if 0 < m.success_rate < 1.0)
        unmapped = sum(1 for m in mappings if m.success_rate == 0.0)
        
        all_missing = []
        for mapping in mappings:
            all_missing.extend(mapping.missing_segments)
        
        unique_missing = list(set(all_missing))
        
        return {
            'total_texts': total_texts,
            'fully_mapped': fully_mapped,
            'partially_mapped': partially_mapped,
            'unmapped': unmapped,
            'overall_success_rate': sum(m.success_rate for m in mappings) / total_texts if total_texts > 0 else 0.0,
            'unique_missing_segments': unique_missing,
            'missing_count': len(unique_missing),
            'mappings': mappings
        }