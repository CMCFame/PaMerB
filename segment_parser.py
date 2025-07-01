"""
Intelligent Segment Parser for IVR Text Processing
Breaks down complex IVR text into searchable segments following Andres's methodology
Handles grammar rules, dynamic variables, and segment combinations
"""

import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import logging

@dataclass
class TextSegment:
    """Represents a parsed text segment"""
    text: str
    segment_type: str  # 'static', 'dynamic', 'digit', 'grammar'
    position: int
    is_variable: bool = False
    variable_name: str = None
    grammar_context: str = None  # For "a" vs "an" detection

class SegmentParser:
    """
    Intelligent parser that breaks down IVR text into searchable segments
    Implements the logic Andres uses to manually segment and search for audio files
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common IVR phrase patterns that should stay together
        self.phrase_patterns = [
            r"this is an?",
            r"this is a",
            r"press \d+",
            r"press any key",
            r"to repeat",
            r"if this is",
            r"if you need",
            r"to get",
            r"to the phone",
            r"is not home",
            r"not home",
            r"need more time",
            r"more time",
            r"callout from",
            r"are you available",
            r"enter your pin",
            r"enter pin",
            r"invalid entry",
            r"please try again",
            r"goodbye",
            r"thank you"
        ]
        
        # Dynamic variable patterns
        self.variable_patterns = [
            r'\{\{(\w+)\}\}',  # {{variable_name}}
            r'\(([^)]+)\)',    # (variable_name)
            r'\[([^\]]+)\]'    # [variable_name]
        ]
        
        # Grammar rules for "a" vs "an"
        self.vowel_sounds = [
            'a', 'e', 'i', 'o', 'u',
            'hour', 'honest', 'honor',  # Silent h words
            'electric', 'emergency', 'urgent'  # Common callout types starting with vowels
        ]
        
        # Digits and special characters
        self.digit_patterns = [
            r'\b\d+\b',  # Standalone digits
            r'\b(?:zero|one|two|three|four|five|six|seven|eight|nine)\b'  # Spelled out numbers
        ]
    
    def parse_text(self, text: str, preserve_grammar: bool = True) -> List[TextSegment]:
        """
        Parse text into intelligent segments following Andres's methodology
        
        Args:
            text: Input text to parse
            preserve_grammar: Whether to apply grammar rules for "a"/"an"
            
        Returns:
            List of TextSegment objects
        """
        if not text:
            return []
        
        self.logger.debug(f"Parsing text: '{text}'")
        
        # Clean and normalize text
        normalized_text = self._normalize_text(text)
        
        # Identify and extract dynamic variables first
        variables, text_without_vars = self._extract_variables(normalized_text)
        
        # Split into potential segments
        segments = self._split_into_segments(text_without_vars)
        
        # Apply grammar rules if needed
        if preserve_grammar:
            segments = self._apply_grammar_rules(segments)
        
        # Merge variables back in
        final_segments = self._merge_variables(segments, variables)
        
        # Create TextSegment objects
        result = []
        for i, segment in enumerate(final_segments):
            if segment['is_variable']:
                result.append(TextSegment(
                    text=segment['text'],
                    segment_type='dynamic',
                    position=i,
                    is_variable=True,
                    variable_name=segment['variable_name']
                ))
            elif segment['text'].isdigit() or any(re.match(pattern, segment['text']) for pattern in self.digit_patterns):
                result.append(TextSegment(
                    text=segment['text'],
                    segment_type='digit',
                    position=i
                ))
            else:
                result.append(TextSegment(
                    text=segment['text'],
                    segment_type='static',
                    position=i,
                    grammar_context=segment.get('grammar_context')
                ))
        
        self.logger.debug(f"Parsed into {len(result)} segments: {[s.text for s in result]}")
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for processing"""
        # Remove HTML line breaks
        text = re.sub(r'<br\s*/?>', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Convert to lowercase for processing (we'll preserve case in final output)
        return text.lower()
    
    def _extract_variables(self, text: str) -> Tuple[List[Dict], str]:
        """Extract dynamic variables and return cleaned text"""
        variables = []
        text_without_vars = text
        
        for pattern in self.variable_patterns:
            matches = list(re.finditer(pattern, text))
            for match in reversed(matches):  # Reverse to maintain positions
                var_name = match.group(1)
                variables.append({
                    'text': match.group(0),
                    'variable_name': var_name,
                    'position': match.start(),
                    'is_variable': True
                })
                # Replace with placeholder
                text_without_vars = text_without_vars[:match.start()] + f"__VAR_{len(variables)-1}__" + text_without_vars[match.end():]
        
        return variables, text_without_vars
    
    def _split_into_segments(self, text: str) -> List[Dict]:
        """Split text into logical segments"""
        segments = []
        
        # First, identify known phrase patterns
        remaining_text = text
        used_positions = set()
        
        # Find phrase patterns
        for pattern in self.phrase_patterns:
            matches = list(re.finditer(pattern, remaining_text, re.IGNORECASE))
            for match in matches:
                start, end = match.span()
                if not any(pos in used_positions for pos in range(start, end)):
                    segments.append({
                        'text': match.group(0),
                        'start': start,
                        'end': end,
                        'type': 'phrase'
                    })
                    used_positions.update(range(start, end))
        
        # Fill gaps with individual words
        words = text.split()
        current_pos = 0
        
        for word in words:
            word_start = text.find(word, current_pos)
            word_end = word_start + len(word)
            
            if not any(pos in used_positions for pos in range(word_start, word_end)):
                segments.append({
                    'text': word,
                    'start': word_start,
                    'end': word_end,
                    'type': 'word'
                })
            
            current_pos = word_end
        
        # Sort by position and clean up
        segments.sort(key=lambda x: x['start'])
        
        # Return just the text and type
        return [{'text': seg['text'], 'type': seg['type']} for seg in segments]
    
    def _apply_grammar_rules(self, segments: List[Dict]) -> List[Dict]:
        """Apply grammar rules like "a" vs "an" based on following context"""
        result = []
        
        for i, segment in enumerate(segments):
            current_segment = segment.copy()
            
            # Check for "a" or "an" that needs grammar adjustment
            if segment['text'] in ['a', 'an']:
                # Look at next segment to determine correct article
                if i + 1 < len(segments):
                    next_text = segments[i + 1]['text']
                    next_text_clean = re.sub(r'__VAR_\d+__', '', next_text).strip()
                    
                    if next_text_clean:
                        # Check if next word starts with vowel sound
                        if self._starts_with_vowel_sound(next_text_clean):
                            current_segment['text'] = 'an'
                            current_segment['grammar_context'] = 'vowel_following'
                        else:
                            current_segment['text'] = 'a'
                            current_segment['grammar_context'] = 'consonant_following'
                    
                    # If next segment is a variable, we might need to use the variable name
                    elif '__VAR_' in next_text:
                        # For variables like {{callout_type}}, we assume consonant unless specified
                        current_segment['text'] = 'a'
                        current_segment['grammar_context'] = 'variable_following'
            
            result.append(current_segment)
        
        return result
    
    def _starts_with_vowel_sound(self, word: str) -> bool:
        """Check if word starts with vowel sound (for a/an grammar)"""
        if not word:
            return False
        
        word_lower = word.lower()
        
        # Check specific cases first
        for vowel_word in self.vowel_sounds:
            if word_lower.startswith(vowel_word):
                return True
        
        # Default vowel check
        return word_lower[0] in 'aeiou'
    
    def _merge_variables(self, segments: List[Dict], variables: List[Dict]) -> List[Dict]:
        """Merge extracted variables back into segment list"""
        result = []
        
        for segment in segments:
            text = segment['text']
            
            # Check if this segment contains variable placeholders
            var_matches = re.finditer(r'__VAR_(\d+)__', text)
            
            if any(var_matches):
                # This segment contains variables, split and merge
                var_matches = list(re.finditer(r'__VAR_(\d+)__', text))
                current_pos = 0
                
                for match in var_matches:
                    # Add text before variable
                    if match.start() > current_pos:
                        before_text = text[current_pos:match.start()].strip()
                        if before_text:
                            result.append({
                                'text': before_text,
                                'is_variable': False,
                                'type': segment.get('type', 'word')
                            })
                    
                    # Add variable
                    var_index = int(match.group(1))
                    if var_index < len(variables):
                        result.append(variables[var_index])
                    
                    current_pos = match.end()
                
                # Add text after last variable
                if current_pos < len(text):
                    after_text = text[current_pos:].strip()
                    if after_text:
                        result.append({
                            'text': after_text,
                            'is_variable': False,
                            'type': segment.get('type', 'word')
                        })
            else:
                # Regular segment
                result.append({
                    'text': text,
                    'is_variable': False,
                    'type': segment.get('type', 'word'),
                    'grammar_context': segment.get('grammar_context')
                })
        
        return result
    
    def get_segment_combinations(self, segments: List[TextSegment]) -> List[List[TextSegment]]:
        """
        Generate different combinations of segments for searching
        Follows Andres's approach of trying complete phrase first, then breaking down
        """
        if not segments:
            return []
        
        combinations = []
        
        # 1. Try complete phrase first
        combinations.append(segments)
        
        # 2. Try meaningful sub-combinations
        # Group consecutive static segments
        static_groups = []
        current_group = []
        
        for segment in segments:
            if segment.segment_type == 'static':
                current_group.append(segment)
            else:
                if current_group:
                    static_groups.append(current_group)
                    current_group = []
                static_groups.append([segment])  # Variables and digits as individual groups
        
        if current_group:
            static_groups.append(current_group)
        
        # Add each group as a combination
        for group in static_groups:
            if len(group) > 0:
                combinations.append(group)
        
        # 3. Individual segments
        for segment in segments:
            combinations.append([segment])
        
        return combinations
    
    def segments_to_text(self, segments: List[TextSegment]) -> str:
        """Convert segments back to text"""
        return ' '.join(segment.text for segment in segments)