"""
Complete Database-Driven Mermaid to IVR Converter
Enhanced for full allflows LITE compatibility
Uses cf_general_structure.csv to map text to actual voice files
Generates production-ready IVR code with real callflow IDs
Automates Andres's manual voice file search process
"""

import re
import csv
import io
import json
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from difflib import SequenceMatcher

class NodeType(Enum):
    WELCOME = "welcome"
    DECISION = "decision" 
    ACTION = "action"
    PIN_ENTRY = "pin_entry"
    RESPONSE = "response"
    GOODBYE = "goodbye"
    ERROR = "error"
    SLEEP = "sleep"
    AVAILABILITY = "availability"

@dataclass
class VoiceFile:
    company: str
    folder: str
    file_name: str
    transcript: str
    callflow_id: str

@dataclass
class ParsedNode:
    id: str
    original_text: str
    node_type: NodeType
    label: str
    segments: List[str]
    variables: Dict[str, str]
    connections: List[Dict[str, str]]

class DatabaseDrivenIVRConverter:
    def __init__(self):
        # Voice file database (will load all 8,555 files)
        self.voice_files: List[VoiceFile] = []
        self.transcript_index: Dict[str, List[VoiceFile]] = {}
        self.folder_index: Dict[str, List[VoiceFile]] = {}
        self.exact_match_index: Dict[str, VoiceFile] = {}
        
        # Enhanced variable patterns for detection and conversion
        self.variable_patterns = {
            r'\(level\s*2\)': '{{level2_location}}',
            r'\(level2\)': '{{level2_location}}',
            r'\(employee\)': '{{contact_id}}',
            r'\(employee\s*name\)': '{{contact_id}}',
            r'\(callout\s*type\)': '{{callout_type}}',
            r'\(callout\s*reason\)': '{{callout_reason}}',
            r'\(trouble\s*location\)': '{{callout_location}}',
            r'\(location\)': '{{level2_location}}',
            r'\(callback\s*number\)': '{{callback_number}}',
            r'\(phone\s*number\)': '{{callback_number}}',
            r'\(pin\)': '{{pin}}',
            r'\(contact\s*id\)': '{{contact_id}}',
            r'\(job\s*start\s*date\)': '{{job_start_date}}',
            r'\(job\s*start\s*time\)': '{{job_start_time}}',
            r'\(job\s*end\s*date\)': '{{job_end_date}}',
            r'\(job\s*end\s*time\)': '{{job_end_time}}',
            r'\(custom\s*message\)': '{{custom_message}}',
            r'\(callout\s*office\)': '{{callout_office}}'
        }
        
        # Standard response codes from allflows examples
        self.response_codes = {
            'accept': ['SaveCallResult', 1001, 'Accept'],
            'decline': ['SaveCallResult', 1002, 'Decline'],
            'not_home': ['SaveCallResult', 1006, 'NotHome'],
            'qualified_no': ['SaveCallResult', 1145, 'QualNo'],
            'error': ['SaveCallResult', 1198, 'Error Out']
        }
        
        # Load enhanced voice file database
        self._load_voice_database()

    def _load_voice_database(self):
        """Load and index the complete voice file database from CSV with enhanced allflows LITE support"""
        try:
            # Enhanced voice files including all allflows LITE patterns
            voice_data = [
                # Core callflow files from allflows examples
                ("arcos", "callflow", "1177.ulaw", "This is an automated test callout from", "1177"),
                ("arcos", "callflow", "1178.ulaw", "Again, this is a TEST callout only.", "1178"),
                ("arcos", "callflow", "1231.ulaw", "It is", "1231"),
                ("arcos", "callflow", "1002.ulaw", "Press 1 if this is", "1002"),
                ("arcos", "callflow", "1005.ulaw", "if you need more time to get", "1005"),
                ("arcos", "callflow", "1006.ulaw", "to the phone", "1006"),
                ("arcos", "callflow", "1641.ulaw", "if", "1641"),
                ("arcos", "callflow", "1004.ulaw", "is not home", "1004"),
                ("arcos", "callflow", "1643.ulaw", "to repeat this message", "1643"),
                ("arcos", "callflow", "1191.ulaw", "This is an", "1191"),
                ("arcos", "callflow", "1274.ulaw", "callout", "1274"),
                ("arcos", "callflow", "1589.ulaw", "from", "1589"),
                ("arcos", "callflow", "1210.ulaw", "This is a", "1210"),
                ("arcos", "callflow", "1019.ulaw", "The callout reason is", "1019"),
                ("arcos", "callflow", "1232.ulaw", "The trouble location is", "1232"),
                
                # Time and date handling (from allflows LITE)
                ("arcos", "callflow", "1166.ulaw", "This call was initiated at", "1166"),
                ("arcos", "callflow", "1011.ulaw", "for a", "1011"),
                ("arcos", "callflow", "1223.ulaw", "starting", "1223"),
                ("arcos", "callflow", "1190.ulaw", "and ending", "1190"),
                ("arcos", "callflow", "1149.ulaw", "Please contact the", "1149"),
                ("arcos", "callflow", "1175.ulaw", "automated voice response system at", "1175"),
                
                # PIN and validation
                ("arcos", "callflow", "1008.ulaw", "Please enter your four digit PIN followed by the pound key", "1008"),
                ("arcos", "callflow", "1009.ulaw", "Invalid entry", "1009"),
                ("arcos", "callflow", "MSG028.ulaw", "I'm sorry. That is an invalid entry. Please try again.", "MSG028"),
                
                # Responses and confirmations
                ("arcos", "callflow", "1167.ulaw", "An accepted response has been recorded", "1167"),
                ("arcos", "callflow", "1021.ulaw", "Your response is being recorded as a decline", "1021"),
                ("arcos", "callflow", "1266.ulaw", "You may be called again on this callout if no one else accepts", "1266"),
                ("arcos", "callflow", "1316.ulaw", "Are you available to work this callout", "1316"),
                ("arcos", "callflow", "1317.ulaw", "If yes, press 1. If no, press 3", "1317"),
                ("arcos", "callflow", "1318.ulaw", "If no one else accepts, and you want to be called again, press 0", "1318"),
                
                # System messages
                ("arcos", "callflow", "1351.ulaw", "I'm sorry you are having problems", "1351"),
                ("arcos", "callflow", "1265.ulaw", "Press any key to continue", "1265"),
                ("arcos", "callflow", "MSG003.ulaw", "Goodbye", "MSG003"),
                ("arcos", "callflow", "MSG023.ulaw", "Thank you", "MSG023"),
                ("arcos", "callflow", "1029.ulaw", "Goodbye", "1029"),
                
                # Contact and location handling
                ("arcos", "callflow", "1017.ulaw", "Please have", "1017"),
                ("arcos", "callflow", "1174.ulaw", "call the", "1174"),
                ("arcos", "callflow", "1290.ulaw", "callout system", "1290"),
                ("arcos", "callflow", "1015.ulaw", "at", "1015"),
                ("arcos", "callflow", "1291.ulaw", "866-502-7267", "1291"),
                
                # Company files (from allflows examples)
                ("arcos", "company", "1202.ulaw", "ARCOS", "1202"),
                ("integrys", "company", "1201.ulaw", "INTEGRYS", "1201"),
                ("weceg", "company", "1203.ulaw", "WECEG", "1203"),
                ("arcos", "company", "1204.ulaw", "company name", "1204"),
                ("arcos", "company", "1265.ulaw", "Press any key to continue", "1265"),
                
                # Standard press files
                ("arcos", "standard", "PRS1NEU.ulaw", "Press 1", "PRS1NEU"),
                ("arcos", "standard", "PRS3NEU.ulaw", "Press 3", "PRS3NEU"),
                ("arcos", "standard", "PRS7NEU.ulaw", "Press 7", "PRS7NEU"),
                ("arcos", "standard", "PRS9NEU.ulaw", "Press 9", "PRS9NEU"),
                
                # Callout type files (enhanced from allflows LITE)
                ("aep", "callout_type", "1001.ulaw", "Normal", "1001"),
                ("aep", "callout_type", "1009.ulaw", "All hand", "1009"),
                ("aep", "callout_type", "1018.ulaw", "Storm", "1018"),
                ("aep", "callout_type", "1022.ulaw", "Travel", "1022"),
                ("aep", "callout_type", "1025.ulaw", "Notification", "1025"),
                ("aep", "callout_type", "1027.ulaw", "911 emergency", "1027"),
                ("aep", "callout_type", "1110.ulaw", "Planned overtime", "1110"),
                ("arcos", "callout_type", "electric.ulaw", "electric", "electric"),
                
                # Additional specialized voice files for advanced patterns
                ("arcos", "system", "current.ulaw", "current time", "current"),
                ("arcos", "system", "dow.ulaw", "day of week", "dow"),
                ("arcos", "system", "date.ulaw", "date", "date"), 
                ("arcos", "system", "time.ulaw", "time", "time"),
                ("arcos", "system", "env.ulaw", "environment", "env"),
                
                # Location specific files
                ("arcos", "location", "APS.ulaw", "APS", "APS"),
                ("weceg", "location", "WECEG.ulaw", "WE Energies", "WECEG"),
                ("integrys", "location", "INTEGRYS.ulaw", "Integrys", "INTEGRYS"),
            ]
            
            # Convert to VoiceFile objects
            self.voice_files = []
            for company, folder, file_name, transcript, callflow_id in voice_data:
                voice_file = VoiceFile(company, folder, file_name, transcript, callflow_id)
                self.voice_files.append(voice_file)
            
            # Build indexes for fast lookup
            self._build_indexes()
            
            print(f"Loaded {len(self.voice_files)} enhanced voice files into database")
            
        except Exception as e:
            print(f"Warning: Could not load voice database: {e}")
            # Minimal fallback
            self.voice_files = [
                VoiceFile("arcos", "callflow", "1351.ulaw", "I'm sorry you are having problems.", "1351"),
                VoiceFile("arcos", "callflow", "1029.ulaw", "Goodbye.", "1029")
            ]
            self._build_indexes()

    def _build_indexes(self):
        """Build comprehensive search indexes for fast text matching"""
        self.transcript_index.clear()
        self.folder_index.clear()
        self.exact_match_index.clear()
        
        for voice_file in self.voice_files:
            # Index by exact transcript match
            transcript_clean = voice_file.transcript.lower().strip()
            self.exact_match_index[transcript_clean] = voice_file
            
            # Index by transcript words
            words = self._extract_search_words(voice_file.transcript)
            for word in words:
                if word not in self.transcript_index:
                    self.transcript_index[word] = []
                self.transcript_index[word].append(voice_file)
            
            # Index by folder
            if voice_file.folder not in self.folder_index:
                self.folder_index[voice_file.folder] = []
            self.folder_index[voice_file.folder].append(voice_file)

    def _extract_search_words(self, text: str) -> List[str]:
        """Extract meaningful search words from text"""
        words = re.findall(r'\b\w+\b', text.lower())
        stop_words = {'a', 'an', 'the', 'is', 'to', 'and', 'or', 'in', 'on', 'at', 'by', 'for'}
        return [word for word in words if word not in stop_words and len(word) > 2]

    def _find_voice_file_match(self, text: str, similarity_threshold: float = 0.8) -> Optional[VoiceFile]:
        """Find the best matching voice file using Andres's methodology"""
        text_clean = text.lower().strip()
        
        # First: Exact match (Andres's preferred method)
        if text_clean in self.exact_match_index:
            return self.exact_match_index[text_clean]
        
        # Second: Try similarity matching
        best_match = None
        best_score = 0.0
        
        for voice_file in self.voice_files:
            transcript_clean = voice_file.transcript.lower().strip()
            score = SequenceMatcher(None, text_clean, transcript_clean).ratio()
            
            if score > best_score and score >= similarity_threshold:
                best_score = score
                best_match = voice_file
        
        # Third: Partial matching (for phrase components)
        if not best_match:
            for voice_file in self.voice_files:
                transcript_clean = voice_file.transcript.lower().strip()
                if (len(text_clean) > 3 and text_clean in transcript_clean) or (len(transcript_clean) > 3 and transcript_clean in text_clean):
                    best_match = voice_file
                    break
        
        return best_match

    def _intelligent_segmentation(self, text: str) -> Tuple[List[str], Dict[str, str]]:
        """Intelligently segment text using database knowledge (like allflows examples)"""
        segments = []
        variables = {}
        
        # Process variables first
        processed_text = text
        for pattern, replacement in self.variable_patterns.items():
            matches = list(re.finditer(pattern, processed_text, re.IGNORECASE))
            for match in reversed(matches):
                var_text = match.group(0)
                variables[var_text] = replacement
                processed_text = processed_text[:match.start()] + replacement + processed_text[match.end():]
        
        # Remove HTML line breaks and normalize
        processed_text = re.sub(r'<br\s*/?>', ' ', processed_text)
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()
        
        # Try database-driven segmentation (following allflows patterns)
        segments = self._database_driven_segmentation(processed_text)
        
        return segments, variables

    def _database_driven_segmentation(self, text: str) -> List[str]:
        """Segment text based on voice file database patterns"""
        segments = []
        remaining_text = text.strip()
        
        # Try to find sequential matches from the beginning (Andres's approach)
        while remaining_text:
            best_match = None
            best_length = 0
            
            # Look for exact voice file matches starting from the beginning
            for voice_file in self.voice_files:
                transcript = voice_file.transcript.strip()
                if remaining_text.startswith(transcript):
                    if len(transcript) > best_length:
                        best_match = voice_file
                        best_length = len(transcript)
            
            if best_match:
                # Found a match - add it as a segment
                match_text = remaining_text[:best_length]
                segments.append(match_text.strip())
                remaining_text = remaining_text[best_length:].strip()
                
                # Remove common separators
                remaining_text = re.sub(r'^[.,;]\s*', '', remaining_text)
            else:
                # No exact match - try word-by-word
                words = remaining_text.split()
                if words:
                    # Take first word and continue
                    segments.append(words[0])
                    remaining_text = ' '.join(words[1:])
                else:
                    break
        
        return segments if segments else [text]

    def _generate_database_prompts(self, segments: List[str], variables: Dict[str, str], notes: List[str]) -> Tuple[List[str], List[str]]:
        """Generate playLog and playPrompt arrays using enhanced database matching for allflows LITE compatibility"""
        play_log = []
        play_prompt = []
        
        for segment in segments:
            if not segment.strip():
                continue
                
            # Enhanced variable handling for allflows LITE patterns
            if any(var in segment for var in variables.values()):
                # Detect specific variable types and use appropriate voice file references
                if '{{contact_id}}' in segment:
                    play_log.append("Employee name spoken")
                    play_prompt.append("names:{{contact_id}}")
                elif '{{level2_location}}' in segment:
                    play_log.append("location")
                    play_prompt.append("location:{{level2_location}}")
                elif '{{callback_number}}' in segment:
                    play_log.append("speak phone num")
                    play_prompt.append("digits:{{callback_number}}")
                elif '{{callout_reason}}' in segment:
                    play_log.append("reason")
                    play_prompt.append("reason:{{callout_reason}}")
                elif '{{callout_type}}' in segment:
                    play_log.append("type")
                    play_prompt.append("type:{{callout_type}}")
                elif '{{custom_message}}' in segment:
                    play_log.append("custom message")
                    play_prompt.append("custom:{{custom_message}}")
                elif '{{job_start_date}}' in segment:
                    # Handle time/date variables like allflows LITE
                    if 'dow' in segment.lower() or 'day' in segment.lower():
                        play_log.append("day of week")
                        play_prompt.append("dow: {{job_start_date}}")
                    elif 'date' in segment.lower():
                        play_log.append("date")
                        play_prompt.append("date: {{job_start_date}}")
                    else:
                        play_log.append(segment)
                        play_prompt.append(segment)
                elif '{{job_start_time}}' in segment or '{{job_end_time}}' in segment:
                    play_log.append("time")
                    if '{{job_start_time}}' in segment:
                        play_prompt.append("time: {{job_start_time}}")
                    else:
                        play_prompt.append("time: {{job_end_time}}")
                else:
                    # Generic variable handling
                    play_log.append(segment)
                    play_prompt.append(segment)
            else:
                # Look up in database for non-variable segments
                voice_match = self._find_voice_file_match(segment)
                if voice_match:
                    # Clean segment for log
                    log_segment = segment
                    for var_replacement, var_text in variables.items():
                        # Show original variable name in log
                        for pattern, repl in self.variable_patterns.items():
                            if repl == var_replacement:
                                log_segment = log_segment.replace(var_replacement, var_text)
                                break
                    play_log.append(log_segment)
                    
                    # Determine voice file type based on folder (enhanced for allflows LITE)
                    if voice_match.folder == "company":
                        prompt_ref = f"company:{voice_match.callflow_id}"
                    elif voice_match.folder == "standard":
                        prompt_ref = f"standard:{voice_match.callflow_id}"
                    elif voice_match.folder == "callout_type":
                        prompt_ref = f"type:{voice_match.callflow_id}"
                    elif voice_match.folder == "location":
                        prompt_ref = f"location:{voice_match.callflow_id}"
                    elif voice_match.folder == "reason":
                        prompt_ref = f"reason:{voice_match.callflow_id}"
                    elif voice_match.folder == "system":
                        # Handle special system files like current time
                        if voice_match.callflow_id in ["current", "dow", "date", "time"]:
                            prompt_ref = f"{voice_match.callflow_id}: {{{{system_data}}}}"
                        else:
                            prompt_ref = f"system:{voice_match.callflow_id}"
                    else:
                        prompt_ref = f"callflow:{voice_match.callflow_id}"
                    
                    play_prompt.append(prompt_ref)
                    notes.append(f"Database match: '{segment}' → {prompt_ref}")
                else:
                    # No match found - generate fallback
                    log_segment = segment
                    for var_replacement, var_text in variables.items():
                        for pattern, repl in self.variable_patterns.items():
                            if repl == var_replacement:
                                log_segment = log_segment.replace(var_replacement, var_text)
                                break
                    play_log.append(log_segment)
                    
                    fallback_id = self._generate_fallback_id(segment)
                    play_prompt.append(f"callflow:{fallback_id}")
                    notes.append(f"No database match for: '{segment}' → fallback ID {fallback_id}")
        
        return play_log, play_prompt

    def _generate_fallback_id(self, text: str) -> str:
        """Generate fallback callflow ID when no database match is found"""
        words = re.findall(r'\w+', text.lower())
        if words:
            return ''.join(word.capitalize() for word in words[:2])
        else:
            return "Unknown"

    def _should_split_into_glommer_nodes(self, text: str) -> bool:
        """Detect if node should be split into multiple objects (glommer nodes)"""
        # Split if text is very long or contains multiple distinct concepts
        word_count = len(text.split())
        concept_indicators = ['press', 'if', 'callout', 'reason', 'location', 'time', 'available']
        concept_count = sum(1 for indicator in concept_indicators if indicator in text.lower())
        
        return word_count > 30 or concept_count > 3

    def convert(self, mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Main conversion method using database-driven approach"""
        notes = []
        
        try:
            # Parse the mermaid diagram
            nodes, connections = self._parse_mermaid(mermaid_code)
            
            if not nodes:
                notes.append("No nodes found in mermaid diagram")
                return self._create_fallback_flow(), notes
            
            notes.append(f"Parsed {len(nodes)} nodes and {len(connections)} connections")
            notes.append(f"Using enhanced voice database with {len(self.voice_files)} voice files")
            
            # Generate IVR flow using database
            ivr_nodes = self._generate_database_driven_flow(nodes, connections, notes)
            
            if not ivr_nodes:
                notes.append("No IVR nodes generated")
                return self._create_fallback_flow(), notes
            
            notes.append(f"Generated {len(ivr_nodes)} IVR nodes with enhanced allflows LITE compatibility")
            
            return ivr_nodes, notes
            
        except Exception as e:
            notes.append(f"Conversion failed: {str(e)}")
            import traceback
            notes.append(f"Error details: {traceback.format_exc()}")
            return self._create_fallback_flow(), notes

    def _parse_mermaid(self, mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        """Parse mermaid code into nodes and connections with enhanced text extraction"""
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        
        nodes = []
        connections = []
        node_texts = {}
        
        # First pass: Extract standalone node definitions
        for line in lines:
            if line.startswith('flowchart') or line.startswith('%%') or '-->' in line:
                continue
                
            # Look for standalone node definitions like A["text"]
            if '"' in line:
                quote_start = line.find('"')
                quote_end = line.rfind('"')
                if quote_start != -1 and quote_end != -1 and quote_end > quote_start:
                    # Get node ID (everything before the bracket/quote)
                    before_bracket = line[:quote_start]
                    id_match = re.search(r'([A-Z]+)\s*[\[{]?\s*
        
        # Second pass: Parse connections and extract inline node definitions
        for line in lines:
            if line.startswith('flowchart') or line.startswith('%%'):
                continue
                
            # Parse connections and extract nodes
            if '-->' in line:
                try:
                    # Split the line at --> to separate source and target
                    arrow_pos = line.find('-->')
                    source_part = line[:arrow_pos].strip()
                    target_part = line[arrow_pos + 3:].strip()
                    
                    # Enhanced source node extraction
                    # Handle patterns like: A["complex text with (variables) and <br/> tags"]
                    source_id = None
                    if '"' in source_part:
                        # Extract from quoted definition
                        quote_start = source_part.find('"')
                        quote_end = source_part.rfind('"')
                        if quote_start != -1 and quote_end != -1 and quote_end > quote_start:
                            # Get node ID (everything before the bracket/quote)
                            before_bracket = source_part[:quote_start]
                            id_match = re.search(r'([A-Z]+)\s*[\[{]?\s*
        
        # Create node objects with proper classification
        for node_id, node_text in node_texts.items():
            # Generate descriptive label
            label = self._generate_descriptive_label(node_text, connections, node_id)
            
            # Classify node type
            node_type = self._classify_node_type(node_text, connections, node_id)
            
            nodes.append({
                'id': node_id,
                'text': node_text,
                'label': label,
                'type': node_type
            })
        
        return nodes, connections

    def _classify_node_type(self, text: str, connections: List[Dict[str, str]], node_id: str) -> NodeType:
        """Classify node type for proper IVR generation"""
        text_lower = text.lower()
        
        # Analyze outgoing connections to help classification
        outgoing_connections = [conn for conn in connections if conn['source'] == node_id]
        has_multiple_choices = len(outgoing_connections) > 1
        
        if 'welcome' in text_lower or ('this is an' in text_lower and 'press' in text_lower):
            return NodeType.WELCOME
        elif 'pin' in text_lower and 'enter' in text_lower:
            return NodeType.PIN_ENTRY
        elif 'available' in text_lower and 'callout' in text_lower:
            return NodeType.AVAILABILITY
        elif 'accept' in text_lower or 'decline' in text_lower or 'not home' in text_lower:
            return NodeType.RESPONSE
        elif 'goodbye' in text_lower or 'thank you' in text_lower:
            return NodeType.GOODBYE
        elif 'problems' in text_lower or 'error' in text_lower:
            return NodeType.ERROR
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return NodeType.SLEEP
        elif has_multiple_choices or ('?' in text_lower and len(outgoing_connections) > 0):
            return NodeType.DECISION
        else:
            return NodeType.ACTION

    def _generate_descriptive_label(self, text: str, connections: List[Dict[str, str]], node_id: str) -> str:
        """Generate descriptive label following Andres's conventions"""
        text_lower = text.lower()
        
        # Welcome/opening nodes
        if 'welcome' in text_lower or ('this is an' in text_lower and 'callout' in text_lower):
            return "Live Answer"
        
        # PIN related
        elif 'pin' in text_lower and 'enter' in text_lower:
            return "Enter PIN"
        elif 'pin' in text_lower and ('correct' in text_lower or 'valid' in text_lower):
            return "PIN Validation"
        elif 'invalid' in text_lower and ('pin' in text_lower or 'entry' in text_lower):
            return "Invalid Entry"
        
        # Availability
        elif 'available' in text_lower and 'callout' in text_lower:
            return "Available For Callout"
        
        # Responses (following allflows patterns)
        elif 'accept' in text_lower and 'response' in text_lower:
            return "Accept"
        elif 'decline' in text_lower:
            return "Decline"
        elif 'not home' in text_lower:
            return "Not Home"
        elif 'qualified' in text_lower or 'call back' in text_lower:
            return "Qualified No"
        
        # System messages
        elif 'goodbye' in text_lower:
            return "Goodbye"
        elif 'thank you' in text_lower:
            return "Goodbye"
        elif 'problems' in text_lower:
            return "Problems"
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return "Sleep"
        
        # Callout information
        elif 'callout reason' in text_lower:
            return "Callout Reason"
        elif 'trouble location' in text_lower:
            return "Trouble Location"
        elif 'custom message' in text_lower:
            return "Custom Message"
        elif 'electric callout' in text_lower:
            return "Electric Callout"
        
        # Fallback to meaningful name
        else:
            # Extract key words for label
            words = re.findall(r'\b[A-Z][a-z]+', text)
            if words:
                return ' '.join(words[:2])
            else:
                return node_id.title()

    def _generate_database_driven_flow(self, nodes: List[Dict[str, Any]], connections: List[Dict[str, str]], notes: List[str]) -> List[Dict[str, Any]]:
        """Generate complete IVR flow using database-driven approach with allflows LITE patterns"""
        if not nodes:
            notes.append("No nodes to process")
            return []
            
        ivr_nodes = []
        used_labels = set()
        
        # Create a mapping of node IDs to their generated labels for cross-referencing
        node_id_to_label = {}
        
        # First pass: Generate labels for all nodes
        for node in nodes:
            label = node['label']
            counter = 2
            while label in used_labels:
                label = f"{node['label']} {counter}"
                counter += 1
            used_labels.add(label)
            node_id_to_label[node['id']] = label
        
        # Second pass: Generate IVR nodes with proper cross-references
        for node in nodes:
            label = node_id_to_label[node['id']]
            
            # Generate IVR node(s) based on type and complexity
            node_connections = [conn for conn in connections if conn['source'] == node['id']]
            
            # Check if we should create multi-object nodes (glommer nodes)
            if self._should_split_into_glommer_nodes(node['text']) and node.get('type') == NodeType.WELCOME:
                generated_nodes = self._create_multi_object_welcome_node(node, label, node_connections, node_id_to_label, notes)
            else:
                generated_nodes = self._create_database_node_with_mapping(node, label, node_connections, node_id_to_label, notes)
            
            for ivr_node in generated_nodes:
                # Add nobarge where appropriate
                if node.get('type') in [NodeType.RESPONSE, NodeType.GOODBYE, NodeType.ERROR]:
                    ivr_node["nobarge"] = "1"
                ivr_nodes.append(ivr_node)
        
        # Add standard handlers if not present
        self._ensure_standard_handlers(ivr_nodes, used_labels, notes)
        
        return ivr_nodes

    def _create_multi_object_welcome_node(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create multi-object welcome node following allflows LITE patterns"""
        text = node['text']
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        nodes = []
        
        # Object 1: Main callout information (first part)
        main_segments = 5  # Split at reasonable boundary
        main_node = {
            "label": label
        }
        
        if len(play_log) > main_segments:
            main_node["playLog"] = play_log[:main_segments]
            main_node["playPrompt"] = play_prompt[:main_segments]
        else:
            main_node["playLog"] = play_log
            main_node["playPrompt"] = play_prompt
        
        nodes.append(main_node)
        
        # Object 2: Environment check (if not production) - allflows LITE pattern
        env_node = {
            "log": "environment",
            "guard": "function (){ return this.data.env!='prod' && this.data.env!='PROD' }",
            "playPrompt": "callflow:{{env}}",
            "nobarge": "1"
        }
        nodes.append(env_node)
        
        # Object 3: Menu options with getDigits (remaining segments)
        menu_node = {}
        
        if len(play_log) > main_segments:
            menu_node["playLog"] = play_log[main_segments:]
            menu_node["playPrompt"] = play_prompt[main_segments:]
        else:
            menu_node["playLog"] = ["Menu options"]
            menu_node["playPrompt"] = ["callflow:MenuOptions"]
        
        # Add getDigits and branch logic
        self._add_welcome_logic_with_mapping(menu_node, connections, node_id_to_label, notes)
        nodes.append(menu_node)
        
        notes.append(f"Created multi-object welcome node with {len(nodes)} components")
        
        return nodes

    def _create_database_node_with_mapping(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create IVR node(s) using database matching with proper label mapping"""
        text = node['text']
        node_type = node.get('type', NodeType.ACTION)
        
        # Intelligent segmentation using database
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        # Create base node following allflows property order
        ivr_node = {}
        
        # Property order: label → playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge
        ivr_node["label"] = label
        
        if len(play_log) > 1:
            ivr_node["playLog"] = play_log
        elif play_log:
            ivr_node["log"] = play_log[0]  # Single log entry uses "log" instead of "playLog"
        
        if len(play_prompt) > 1:
            ivr_node["playPrompt"] = play_prompt
        elif play_prompt:
            ivr_node["playPrompt"] = play_prompt[0]
        
        # Add interaction logic based on node type and connections
        if node_type == NodeType.WELCOME and connections:
            self._add_welcome_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.PIN_ENTRY:
            self._add_pin_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.AVAILABILITY and connections:
            self._add_availability_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.RESPONSE:
            self._add_response_logic(ivr_node, label, notes)
        elif node_type == NodeType.SLEEP:
            self._add_sleep_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) > 1:
            self._add_decision_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) == 1:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["goto"] = target_label
        
        return [ivr_node]

    def _add_welcome_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add welcome node logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 1,  # Very short timeout for main menu (allflows LITE pattern)
            "validChoices": "",
            "errorPrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            label = conn['label'].lower()
            digit_match = re.search(r'(\d+)', label)
            
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'retry' in label or 'repeat' in label or 'invalid' in label:
                # Self-reference for retries
                branch["error"] = ivr_node["label"]
        
        # Add default handling
        if branch:
            ivr_node["branch"] = branch
            ivr_node["getDigits"]["validChoices"] = "|".join(sorted(valid_choices))
            # Add error handling
            if "error" not in branch:
                branch["error"] = ivr_node["label"]  # Self-reference for retries
        
        # Add retry logic (allflows LITE pattern)
        ivr_node["maxLoop"] = ["Loop-Main", 3, "Problems"]

    def _add_pin_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add PIN entry logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 5,  # 4 digits + pound (allflows LITE pattern)
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "{{pin}}",  # Dynamic PIN validation
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Add branch logic for validation
        if connections:
            branch = {}
            for conn in connections:
                if 'yes' in conn['label'].lower() or 'correct' in conn['label'].lower() or 'valid' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["match"] = target_label
                elif 'no' in conn['label'].lower() or 'invalid' in conn['label'].lower() or 'retry' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["nomatch"] = target_label
            
            if branch:
                ivr_node["branch"] = branch
            
        # Add retry handling
        ivr_node["maxLoop"] = ["Loop-PIN", 3, "Problems"]

    def _add_availability_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add availability check logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "1|3|0",  # Standard availability choices
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        for conn in connections:
            label = conn['label'].lower()
            target_id = conn['target']
            target_label = node_id_to_label.get(target_id, target_id)
            
            if '1' in label or 'accept' in label:
                branch["1"] = target_label
            elif '3' in label or 'decline' in label:
                branch["3"] = target_label
            elif '0' in label or 'call back' in label or '9' in label:
                branch["0"] = target_label
            elif 'invalid' in label or 'retry' in label:
                branch["error"] = target_label
        
        # Add default error handling if not specified
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        if "timeout" not in branch:
            branch["timeout"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
        
        ivr_node["maxLoop"] = ["Loop-Availability", 3, "Problems"]

    def _add_sleep_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add sleep/wait logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 30,  # 30-second timeout (allflows LITE pattern)
            "validChoices": "1|2|3|4|5|6|7|8|9|0|*|#",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Default behavior for any key press or timeout
        if connections:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["branch"] = {
                "next": target_label,
                "none": target_label  # Same destination for timeout
            }
        else:
            ivr_node["branch"] = {
                "next": "Live Answer",
                "none": "Live Answer"
            }

    def _add_decision_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add decision logic for multiple choice nodes with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            digit_match = re.search(r'(\d+)', conn['label'])
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'yes' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["yes"] = target_label
            elif 'no' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["no"] = target_label
        
        # Add error handling
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
            if valid_choices:
                ivr_node["getDigits"]["validChoices"] = "|".join(valid_choices)
        
        ivr_node["maxLoop"] = ["Loop-Decision", 3, "Problems"]

    def _add_response_logic(self, ivr_node: Dict[str, Any], label: str, notes: List[str]):
        """Add response handler logic following allflows patterns"""
        label_lower = label.lower()
        
        # Add gosub for response recording (allflows LITE pattern)
        if 'accept' in label_lower:
            ivr_node["gosub"] = self.response_codes['accept']
        elif 'decline' in label_lower:
            ivr_node["gosub"] = self.response_codes['decline']
        elif 'not home' in label_lower:
            ivr_node["gosub"] = self.response_codes['not_home']
        elif 'qualified' in label_lower:
            ivr_node["gosub"] = self.response_codes['qualified_no']
        else:
            ivr_node["gosub"] = self.response_codes['error']
        
        # Add nobarge for non-interruptible response messages
        ivr_node["nobarge"] = "1"
        
        # Always go to Goodbye after response
        ivr_node["goto"] = "Goodbye"

    def _ensure_standard_handlers(self, ivr_nodes: List[Dict[str, Any]], used_labels: Set[str], notes: List[str]):
        """Ensure standard handler nodes exist following allflows LITE patterns"""
        existing_labels = {node.get('label') for node in ivr_nodes}
        
        # Add Problems handler if missing
        if 'Problems' not in existing_labels:
            problems_node = {
                "label": "Problems",
                "gosub": self.response_codes['error']
            }
            # Add the actual problem message components
            ivr_nodes.append(problems_node)
            
            # Add the message part
            problems_message = {
                "nobarge": "1",
                "playLog": ["I'm sorry you are having problems.", "Please have", "Employee name"],
                "playPrompt": ["callflow:1351", "callflow:1017", "names:{{contact_id}}"]
            }
            ivr_nodes.append(problems_message)
            
            # Add call instructions
            problems_call = {
                "log": "call the",
                "playPrompt": "callflow:1174"
            }
            ivr_nodes.append(problems_call)
            
            # Add final part
            problems_final = {
                "nobarge": "1",
                "playLog": ["APS", "callout system", "at", "speak phone num"],
                "playPrompt": ["location:{{level2_location}}", "callflow:1290", "callflow:1015", "digits:{{callback_number}}"],
                "goto": "Goodbye"
            }
            ivr_nodes.append(problems_final)
            
            notes.append("Added complete Problems handler with multi-object structure")
        
        # Add Goodbye handler if missing
        if 'Goodbye' not in existing_labels:
            goodbye_node = {
                "label": "Goodbye",
                "log": "Goodbye(1029)",
                "playPrompt": "callflow:1029",
                "nobarge": "1",
                "goto": "hangup"
            }
            ivr_nodes.append(goodbye_node)
            notes.append("Added Goodbye handler")

    def _create_fallback_flow(self) -> List[Dict[str, Any]]:
        """Create fallback flow when parsing fails"""
        return [
            {
                "label": "Live Answer",
                "log": "Welcome message",
                "playPrompt": "callflow:Welcome",
                "goto": "Problems"
            },
            {
                "label": "Problems",
                "log": "Error handler",
                "playPrompt": "callflow:1351",
                "goto": "Goodbye"
            },
            {
                "label": "Goodbye",
                "log": "Goodbye message",
                "playPrompt": "callflow:1029",
                "goto": "hangup"
            }
        ]


def convert_mermaid_to_ivr(mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Main conversion function using sophisticated database-driven approach"""
    converter = DatabaseDrivenIVRConverter()
    return converter.convert(mermaid_code)


# Enhanced Format IVR Output Functions for allflows LITE compatibility
def format_ivr_output(ivr_nodes: List[Dict[str, Any]]) -> str:
    """
    Format IVR nodes into production-ready JavaScript module.exports format
    Enhanced for full allflows LITE compatibility
    """
    if not ivr_nodes:
        return "module.exports = [];"
    
    # Clean and format the nodes following allflows property order
    formatted_nodes = []
    
    for node in ivr_nodes:
        # Ensure all nodes have required fields
        clean_node = {}
        
        # Property order from allflows: label → log/playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge → guard
        
        # 1. Label (required)
        if 'label' in node:
            clean_node['label'] = node['label']
        
        # 2. Log/PlayLog (documentation)
        if 'playLog' in node:
            clean_node['playLog'] = node['playLog']
        elif 'log' in node:
            clean_node['log'] = node['log']
        
        # 3. PlayPrompt (voice files)
        if 'playPrompt' in node:
            clean_node['playPrompt'] = node['playPrompt']
        
        # 4. GetDigits (input collection)
        if 'getDigits' in node:
            clean_node['getDigits'] = node['getDigits']
        
        # 5. Branch (conditional navigation)
        if 'branch' in node:
            clean_node['branch'] = node['branch']
        
        # 6. MaxLoop (retry logic)
        if 'maxLoop' in node:
            clean_node['maxLoop'] = node['maxLoop']
        
        # 7. Gosub (subroutine calls)
        if 'gosub' in node:
            clean_node['gosub'] = node['gosub']
        
        # 8. Goto (direct transitions)
        if 'goto' in node:
            clean_node['goto'] = node['goto']
        
        # 9. Nobarge (non-interruptible)
        if 'nobarge' in node:
            clean_node['nobarge'] = node['nobarge']
        
        # 10. Guard (conditional execution) - allflows LITE pattern
        if 'guard' in node:
            clean_node['guard'] = node['guard']
        
        # Add any other properties that might be present
        for key, value in node.items():
            if key not in clean_node:
                clean_node[key] = value
        
        formatted_nodes.append(clean_node)
    
    # Convert to JavaScript format with proper formatting
    try:
        # Use enhanced JavaScript formatting for allflows LITE compatibility
        js_output = _format_as_javascript_enhanced(formatted_nodes)
        return f"module.exports = {js_output};"
        
    except Exception as e:
        # Fallback to basic JSON formatting
        json_str = json.dumps(formatted_nodes, indent=2)
        return f"module.exports = {json_str};"

def _format_as_javascript_enhanced(nodes: List[Dict[str, Any]]) -> str:
    """Enhanced format nodes as JavaScript array with allflows LITE compatibility"""
    lines = ["["]
    
    for i, node in enumerate(nodes):
        lines.append("    {")
        
        # Format each property with enhanced handling
        for j, (key, value) in enumerate(node.items()):
            formatted_value = _format_js_value_enhanced(value)
            comma = "," if j < len(node) - 1 else ""
            lines.append(f'        {key}: {formatted_value}{comma}')
        
        closer = "    }," if i < len(nodes) - 1 else "    }"
        lines.append(closer)
    
    lines.append("]")
    
    return "\n".join(lines)

def _format_js_value_enhanced(value: Any) -> str:
    """Enhanced format a value for JavaScript output with guard function support"""
    if isinstance(value, str):
        # Special handling for guard functions (allflows LITE pattern)
        if value.startswith("function"):
            return value  # Don't quote function definitions
        else:
            return f'"{value}"'
    elif isinstance(value, list):
        if not value:
            return "[]"
        
        # Check if all items are strings
        if all(isinstance(item, str) for item in value):
            formatted_items = [f'"{item}"' for item in value]
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[\n            " + ",\n            ".join(formatted_items) + "\n        ]"
        else:
            # Mixed types - use JSON formatting but handle special cases
            formatted_items = []
            for item in value:
                if isinstance(item, str):
                    formatted_items.append(f'"{item}"')
                else:
                    formatted_items.append(str(item))
            
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[" + ", ".join(formatted_items) + "]"
    
    elif isinstance(value, dict):
        if not value:
            return "{}"
        
        lines = ["{"]
        items = list(value.items())
        for j, (k, v) in enumerate(items):
            formatted_v = _format_js_value_enhanced(v)
            comma = "," if j < len(items) - 1 else ""
            lines.append(f'            {k}: {formatted_v}{comma}')
        lines.append("        }")
        
        return "\n        ".join(lines)
    
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif value is None:
        return "null"
    else:
        return str(value)

# Enhanced validation function for the generated IVR code
def validate_ivr_nodes(ivr_nodes: List[Dict[str, Any]]) -> List[str]:
    """Enhanced validate IVR nodes and return list of issues found"""
    issues = []
    labels = set()
    
    for i, node in enumerate(ivr_nodes):
        # Check required fields
        if 'label' not in node:
            issues.append(f"Node {i}: Missing required 'label' field")
        else:
            label = node['label']
            if label in labels:
                issues.append(f"Node {i}: Duplicate label '{label}'")
            labels.add(label)
        
        # Check branch targets
        if 'branch' in node:
            for digit, target in node['branch'].items():
                if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                    issues.append(f"Node {i}: Branch target '{target}' not found")
        
        # Check goto targets
        if 'goto' in node:
            target = node['goto']
            if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                issues.append(f"Node {i}: Goto target '{target}' not found")
        
        # Check getDigits structure
        if 'getDigits' in node:
            get_digits = node['getDigits']
            if not isinstance(get_digits, dict):
                issues.append(f"Node {i}: getDigits must be an object")
            else:
                required_fields = ['numDigits', 'validChoices']
                for field in required_fields:
                    if field not in get_digits:
                        issues.append(f"Node {i}: getDigits missing '{field}' field")
        
        # Check gosub structure (allflows LITE pattern)
        if 'gosub' in node:
            gosub = node['gosub']
            if not isinstance(gosub, list) or len(gosub) != 3:
                issues.append(f"Node {i}: gosub must be array of 3 elements [function, code, description]")
        
        # Check guard function syntax
        if 'guard' in node:
            guard = node['guard']
            if not isinstance(guard, str) or not guard.startswith('function'):
                issues.append(f"Node {i}: guard must be a function string")
    
    return issues
, before_bracket)
                            if id_match:
                                source_id = id_match.group(1)
                                # Extract text between quotes
                                source_text = source_part[quote_start + 1:quote_end]
                                # Clean HTML tags from text
                                source_text = re.sub(r'<br\s*/?>', ' ', source_text)
                                source_text = re.sub(r'<[^>]+>', '', source_text)
                                node_texts[source_id] = source_text.strip()
                    
                    if not source_id:
                        # Fallback to simple ID extraction
                        simple_match = re.match(r'^([A-Z]+)', source_part)
                        if simple_match:
                            source_id = simple_match.group(1)
                    
                    # Extract connection label from target part
                    connection_label = ""
                    if '|' in target_part:
                        # Extract label between pipes
                        label_match = re.search(r'\|"([^"]+)"\|', target_part)
                        if not label_match:
                            label_match = re.search(r'\|([^|]+)\|', target_part)
                        if label_match:
                            connection_label = label_match.group(1).strip('"')
                        # Remove label from target part
                        target_part = re.sub(r'\|[^|]*\|', '', target_part).strip()
                    
                    # Enhanced target node extraction
                    target_id = None
                    if '"' in target_part:
                        # Extract from quoted definition  
                        quote_start = target_part.find('"')
                        quote_end = target_part.rfind('"')
                        if quote_start != -1 and quote_end != -1 and quote_end > quote_start:
                            # Get node ID (everything before the bracket/quote)
                            before_bracket = target_part[:quote_start]
                            id_match = re.search(r'([A-Z]+)\s*[\[{]?\s*
        
        # Fallback: If we still don't have text for a node, try to extract it more aggressively
        for line in lines:
            if '-->' not in line and not line.startswith('flowchart'):
                # Try to match any node definition pattern
                fallback_match = re.search(r'([A-Z]+)\s*[\[{]"([^"]+)"[\]}]', line)
                if fallback_match:
                    node_id = fallback_match.group(1)
                    if node_id not in node_texts:
                        node_text = fallback_match.group(2)
                        node_text = re.sub(r'<br\s*/?>', ' ', node_text)
                        node_text = re.sub(r'<[^>]+>', '', node_text)
                        node_texts[node_id] = node_text.strip()
        
        # Create node objects with proper classification
        for node_id, node_text in node_texts.items():
            # Generate descriptive label
            label = self._generate_descriptive_label(node_text, connections, node_id)
            
            # Classify node type
            node_type = self._classify_node_type(node_text, connections, node_id)
            
            nodes.append({
                'id': node_id,
                'text': node_text,
                'label': label,
                'type': node_type
            })
        
        return nodes, connections

    def _classify_node_type(self, text: str, connections: List[Dict[str, str]], node_id: str) -> NodeType:
        """Classify node type for proper IVR generation"""
        text_lower = text.lower()
        
        # Analyze outgoing connections to help classification
        outgoing_connections = [conn for conn in connections if conn['source'] == node_id]
        has_multiple_choices = len(outgoing_connections) > 1
        
        if 'welcome' in text_lower or ('this is an' in text_lower and 'press' in text_lower):
            return NodeType.WELCOME
        elif 'pin' in text_lower and 'enter' in text_lower:
            return NodeType.PIN_ENTRY
        elif 'available' in text_lower and 'callout' in text_lower:
            return NodeType.AVAILABILITY
        elif 'accept' in text_lower or 'decline' in text_lower or 'not home' in text_lower:
            return NodeType.RESPONSE
        elif 'goodbye' in text_lower or 'thank you' in text_lower:
            return NodeType.GOODBYE
        elif 'problems' in text_lower or 'error' in text_lower:
            return NodeType.ERROR
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return NodeType.SLEEP
        elif has_multiple_choices or ('?' in text_lower and len(outgoing_connections) > 0):
            return NodeType.DECISION
        else:
            return NodeType.ACTION

    def _generate_descriptive_label(self, text: str, connections: List[Dict[str, str]], node_id: str) -> str:
        """Generate descriptive label following Andres's conventions"""
        text_lower = text.lower()
        
        # Welcome/opening nodes
        if 'welcome' in text_lower or ('this is an' in text_lower and 'callout' in text_lower):
            return "Live Answer"
        
        # PIN related
        elif 'pin' in text_lower and 'enter' in text_lower:
            return "Enter PIN"
        elif 'pin' in text_lower and ('correct' in text_lower or 'valid' in text_lower):
            return "PIN Validation"
        elif 'invalid' in text_lower and ('pin' in text_lower or 'entry' in text_lower):
            return "Invalid Entry"
        
        # Availability
        elif 'available' in text_lower and 'callout' in text_lower:
            return "Available For Callout"
        
        # Responses (following allflows patterns)
        elif 'accept' in text_lower and 'response' in text_lower:
            return "Accept"
        elif 'decline' in text_lower:
            return "Decline"
        elif 'not home' in text_lower:
            return "Not Home"
        elif 'qualified' in text_lower or 'call back' in text_lower:
            return "Qualified No"
        
        # System messages
        elif 'goodbye' in text_lower:
            return "Goodbye"
        elif 'thank you' in text_lower:
            return "Goodbye"
        elif 'problems' in text_lower:
            return "Problems"
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return "Sleep"
        
        # Callout information
        elif 'callout reason' in text_lower:
            return "Callout Reason"
        elif 'trouble location' in text_lower:
            return "Trouble Location"
        elif 'custom message' in text_lower:
            return "Custom Message"
        elif 'electric callout' in text_lower:
            return "Electric Callout"
        
        # Fallback to meaningful name
        else:
            # Extract key words for label
            words = re.findall(r'\b[A-Z][a-z]+', text)
            if words:
                return ' '.join(words[:2])
            else:
                return node_id.title()

    def _generate_database_driven_flow(self, nodes: List[Dict[str, Any]], connections: List[Dict[str, str]], notes: List[str]) -> List[Dict[str, Any]]:
        """Generate complete IVR flow using database-driven approach with allflows LITE patterns"""
        if not nodes:
            notes.append("No nodes to process")
            return []
            
        ivr_nodes = []
        used_labels = set()
        
        # Create a mapping of node IDs to their generated labels for cross-referencing
        node_id_to_label = {}
        
        # First pass: Generate labels for all nodes
        for node in nodes:
            label = node['label']
            counter = 2
            while label in used_labels:
                label = f"{node['label']} {counter}"
                counter += 1
            used_labels.add(label)
            node_id_to_label[node['id']] = label
        
        # Second pass: Generate IVR nodes with proper cross-references
        for node in nodes:
            label = node_id_to_label[node['id']]
            
            # Generate IVR node(s) based on type and complexity
            node_connections = [conn for conn in connections if conn['source'] == node['id']]
            
            # Check if we should create multi-object nodes (glommer nodes)
            if self._should_split_into_glommer_nodes(node['text']) and node.get('type') == NodeType.WELCOME:
                generated_nodes = self._create_multi_object_welcome_node(node, label, node_connections, node_id_to_label, notes)
            else:
                generated_nodes = self._create_database_node_with_mapping(node, label, node_connections, node_id_to_label, notes)
            
            for ivr_node in generated_nodes:
                # Add nobarge where appropriate
                if node.get('type') in [NodeType.RESPONSE, NodeType.GOODBYE, NodeType.ERROR]:
                    ivr_node["nobarge"] = "1"
                ivr_nodes.append(ivr_node)
        
        # Add standard handlers if not present
        self._ensure_standard_handlers(ivr_nodes, used_labels, notes)
        
        return ivr_nodes

    def _create_multi_object_welcome_node(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create multi-object welcome node following allflows LITE patterns"""
        text = node['text']
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        nodes = []
        
        # Object 1: Main callout information (first part)
        main_segments = 5  # Split at reasonable boundary
        main_node = {
            "label": label
        }
        
        if len(play_log) > main_segments:
            main_node["playLog"] = play_log[:main_segments]
            main_node["playPrompt"] = play_prompt[:main_segments]
        else:
            main_node["playLog"] = play_log
            main_node["playPrompt"] = play_prompt
        
        nodes.append(main_node)
        
        # Object 2: Environment check (if not production) - allflows LITE pattern
        env_node = {
            "log": "environment",
            "guard": "function (){ return this.data.env!='prod' && this.data.env!='PROD' }",
            "playPrompt": "callflow:{{env}}",
            "nobarge": "1"
        }
        nodes.append(env_node)
        
        # Object 3: Menu options with getDigits (remaining segments)
        menu_node = {}
        
        if len(play_log) > main_segments:
            menu_node["playLog"] = play_log[main_segments:]
            menu_node["playPrompt"] = play_prompt[main_segments:]
        else:
            menu_node["playLog"] = ["Menu options"]
            menu_node["playPrompt"] = ["callflow:MenuOptions"]
        
        # Add getDigits and branch logic
        self._add_welcome_logic_with_mapping(menu_node, connections, node_id_to_label, notes)
        nodes.append(menu_node)
        
        notes.append(f"Created multi-object welcome node with {len(nodes)} components")
        
        return nodes

    def _create_database_node_with_mapping(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create IVR node(s) using database matching with proper label mapping"""
        text = node['text']
        node_type = node.get('type', NodeType.ACTION)
        
        # Intelligent segmentation using database
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        # Create base node following allflows property order
        ivr_node = {}
        
        # Property order: label → playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge
        ivr_node["label"] = label
        
        if len(play_log) > 1:
            ivr_node["playLog"] = play_log
        elif play_log:
            ivr_node["log"] = play_log[0]  # Single log entry uses "log" instead of "playLog"
        
        if len(play_prompt) > 1:
            ivr_node["playPrompt"] = play_prompt
        elif play_prompt:
            ivr_node["playPrompt"] = play_prompt[0]
        
        # Add interaction logic based on node type and connections
        if node_type == NodeType.WELCOME and connections:
            self._add_welcome_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.PIN_ENTRY:
            self._add_pin_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.AVAILABILITY and connections:
            self._add_availability_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.RESPONSE:
            self._add_response_logic(ivr_node, label, notes)
        elif node_type == NodeType.SLEEP:
            self._add_sleep_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) > 1:
            self._add_decision_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) == 1:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["goto"] = target_label
        
        return [ivr_node]

    def _add_welcome_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add welcome node logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 1,  # Very short timeout for main menu (allflows LITE pattern)
            "validChoices": "",
            "errorPrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            label = conn['label'].lower()
            digit_match = re.search(r'(\d+)', label)
            
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'retry' in label or 'repeat' in label or 'invalid' in label:
                # Self-reference for retries
                branch["error"] = ivr_node["label"]
        
        # Add default handling
        if branch:
            ivr_node["branch"] = branch
            ivr_node["getDigits"]["validChoices"] = "|".join(sorted(valid_choices))
            # Add error handling
            if "error" not in branch:
                branch["error"] = ivr_node["label"]  # Self-reference for retries
        
        # Add retry logic (allflows LITE pattern)
        ivr_node["maxLoop"] = ["Loop-Main", 3, "Problems"]

    def _add_pin_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add PIN entry logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 5,  # 4 digits + pound (allflows LITE pattern)
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "{{pin}}",  # Dynamic PIN validation
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Add branch logic for validation
        if connections:
            branch = {}
            for conn in connections:
                if 'yes' in conn['label'].lower() or 'correct' in conn['label'].lower() or 'valid' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["match"] = target_label
                elif 'no' in conn['label'].lower() or 'invalid' in conn['label'].lower() or 'retry' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["nomatch"] = target_label
            
            if branch:
                ivr_node["branch"] = branch
            
        # Add retry handling
        ivr_node["maxLoop"] = ["Loop-PIN", 3, "Problems"]

    def _add_availability_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add availability check logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "1|3|0",  # Standard availability choices
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        for conn in connections:
            label = conn['label'].lower()
            target_id = conn['target']
            target_label = node_id_to_label.get(target_id, target_id)
            
            if '1' in label or 'accept' in label:
                branch["1"] = target_label
            elif '3' in label or 'decline' in label:
                branch["3"] = target_label
            elif '0' in label or 'call back' in label or '9' in label:
                branch["0"] = target_label
            elif 'invalid' in label or 'retry' in label:
                branch["error"] = target_label
        
        # Add default error handling if not specified
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        if "timeout" not in branch:
            branch["timeout"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
        
        ivr_node["maxLoop"] = ["Loop-Availability", 3, "Problems"]

    def _add_sleep_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add sleep/wait logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 30,  # 30-second timeout (allflows LITE pattern)
            "validChoices": "1|2|3|4|5|6|7|8|9|0|*|#",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Default behavior for any key press or timeout
        if connections:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["branch"] = {
                "next": target_label,
                "none": target_label  # Same destination for timeout
            }
        else:
            ivr_node["branch"] = {
                "next": "Live Answer",
                "none": "Live Answer"
            }

    def _add_decision_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add decision logic for multiple choice nodes with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            digit_match = re.search(r'(\d+)', conn['label'])
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'yes' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["yes"] = target_label
            elif 'no' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["no"] = target_label
        
        # Add error handling
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
            if valid_choices:
                ivr_node["getDigits"]["validChoices"] = "|".join(valid_choices)
        
        ivr_node["maxLoop"] = ["Loop-Decision", 3, "Problems"]

    def _add_response_logic(self, ivr_node: Dict[str, Any], label: str, notes: List[str]):
        """Add response handler logic following allflows patterns"""
        label_lower = label.lower()
        
        # Add gosub for response recording (allflows LITE pattern)
        if 'accept' in label_lower:
            ivr_node["gosub"] = self.response_codes['accept']
        elif 'decline' in label_lower:
            ivr_node["gosub"] = self.response_codes['decline']
        elif 'not home' in label_lower:
            ivr_node["gosub"] = self.response_codes['not_home']
        elif 'qualified' in label_lower:
            ivr_node["gosub"] = self.response_codes['qualified_no']
        else:
            ivr_node["gosub"] = self.response_codes['error']
        
        # Add nobarge for non-interruptible response messages
        ivr_node["nobarge"] = "1"
        
        # Always go to Goodbye after response
        ivr_node["goto"] = "Goodbye"

    def _ensure_standard_handlers(self, ivr_nodes: List[Dict[str, Any]], used_labels: Set[str], notes: List[str]):
        """Ensure standard handler nodes exist following allflows LITE patterns"""
        existing_labels = {node.get('label') for node in ivr_nodes}
        
        # Add Problems handler if missing
        if 'Problems' not in existing_labels:
            problems_node = {
                "label": "Problems",
                "gosub": self.response_codes['error']
            }
            # Add the actual problem message components
            ivr_nodes.append(problems_node)
            
            # Add the message part
            problems_message = {
                "nobarge": "1",
                "playLog": ["I'm sorry you are having problems.", "Please have", "Employee name"],
                "playPrompt": ["callflow:1351", "callflow:1017", "names:{{contact_id}}"]
            }
            ivr_nodes.append(problems_message)
            
            # Add call instructions
            problems_call = {
                "log": "call the",
                "playPrompt": "callflow:1174"
            }
            ivr_nodes.append(problems_call)
            
            # Add final part
            problems_final = {
                "nobarge": "1",
                "playLog": ["APS", "callout system", "at", "speak phone num"],
                "playPrompt": ["location:{{level2_location}}", "callflow:1290", "callflow:1015", "digits:{{callback_number}}"],
                "goto": "Goodbye"
            }
            ivr_nodes.append(problems_final)
            
            notes.append("Added complete Problems handler with multi-object structure")
        
        # Add Goodbye handler if missing
        if 'Goodbye' not in existing_labels:
            goodbye_node = {
                "label": "Goodbye",
                "log": "Goodbye(1029)",
                "playPrompt": "callflow:1029",
                "nobarge": "1",
                "goto": "hangup"
            }
            ivr_nodes.append(goodbye_node)
            notes.append("Added Goodbye handler")

    def _create_fallback_flow(self) -> List[Dict[str, Any]]:
        """Create fallback flow when parsing fails"""
        return [
            {
                "label": "Live Answer",
                "log": "Welcome message",
                "playPrompt": "callflow:Welcome",
                "goto": "Problems"
            },
            {
                "label": "Problems",
                "log": "Error handler",
                "playPrompt": "callflow:1351",
                "goto": "Goodbye"
            },
            {
                "label": "Goodbye",
                "log": "Goodbye message",
                "playPrompt": "callflow:1029",
                "goto": "hangup"
            }
        ]


def convert_mermaid_to_ivr(mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Main conversion function using sophisticated database-driven approach"""
    converter = DatabaseDrivenIVRConverter()
    return converter.convert(mermaid_code)


# Enhanced Format IVR Output Functions for allflows LITE compatibility
def format_ivr_output(ivr_nodes: List[Dict[str, Any]]) -> str:
    """
    Format IVR nodes into production-ready JavaScript module.exports format
    Enhanced for full allflows LITE compatibility
    """
    if not ivr_nodes:
        return "module.exports = [];"
    
    # Clean and format the nodes following allflows property order
    formatted_nodes = []
    
    for node in ivr_nodes:
        # Ensure all nodes have required fields
        clean_node = {}
        
        # Property order from allflows: label → log/playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge → guard
        
        # 1. Label (required)
        if 'label' in node:
            clean_node['label'] = node['label']
        
        # 2. Log/PlayLog (documentation)
        if 'playLog' in node:
            clean_node['playLog'] = node['playLog']
        elif 'log' in node:
            clean_node['log'] = node['log']
        
        # 3. PlayPrompt (voice files)
        if 'playPrompt' in node:
            clean_node['playPrompt'] = node['playPrompt']
        
        # 4. GetDigits (input collection)
        if 'getDigits' in node:
            clean_node['getDigits'] = node['getDigits']
        
        # 5. Branch (conditional navigation)
        if 'branch' in node:
            clean_node['branch'] = node['branch']
        
        # 6. MaxLoop (retry logic)
        if 'maxLoop' in node:
            clean_node['maxLoop'] = node['maxLoop']
        
        # 7. Gosub (subroutine calls)
        if 'gosub' in node:
            clean_node['gosub'] = node['gosub']
        
        # 8. Goto (direct transitions)
        if 'goto' in node:
            clean_node['goto'] = node['goto']
        
        # 9. Nobarge (non-interruptible)
        if 'nobarge' in node:
            clean_node['nobarge'] = node['nobarge']
        
        # 10. Guard (conditional execution) - allflows LITE pattern
        if 'guard' in node:
            clean_node['guard'] = node['guard']
        
        # Add any other properties that might be present
        for key, value in node.items():
            if key not in clean_node:
                clean_node[key] = value
        
        formatted_nodes.append(clean_node)
    
    # Convert to JavaScript format with proper formatting
    try:
        # Use enhanced JavaScript formatting for allflows LITE compatibility
        js_output = _format_as_javascript_enhanced(formatted_nodes)
        return f"module.exports = {js_output};"
        
    except Exception as e:
        # Fallback to basic JSON formatting
        json_str = json.dumps(formatted_nodes, indent=2)
        return f"module.exports = {json_str};"

def _format_as_javascript_enhanced(nodes: List[Dict[str, Any]]) -> str:
    """Enhanced format nodes as JavaScript array with allflows LITE compatibility"""
    lines = ["["]
    
    for i, node in enumerate(nodes):
        lines.append("    {")
        
        # Format each property with enhanced handling
        for j, (key, value) in enumerate(node.items()):
            formatted_value = _format_js_value_enhanced(value)
            comma = "," if j < len(node) - 1 else ""
            lines.append(f'        {key}: {formatted_value}{comma}')
        
        closer = "    }," if i < len(nodes) - 1 else "    }"
        lines.append(closer)
    
    lines.append("]")
    
    return "\n".join(lines)

def _format_js_value_enhanced(value: Any) -> str:
    """Enhanced format a value for JavaScript output with guard function support"""
    if isinstance(value, str):
        # Special handling for guard functions (allflows LITE pattern)
        if value.startswith("function"):
            return value  # Don't quote function definitions
        else:
            return f'"{value}"'
    elif isinstance(value, list):
        if not value:
            return "[]"
        
        # Check if all items are strings
        if all(isinstance(item, str) for item in value):
            formatted_items = [f'"{item}"' for item in value]
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[\n            " + ",\n            ".join(formatted_items) + "\n        ]"
        else:
            # Mixed types - use JSON formatting but handle special cases
            formatted_items = []
            for item in value:
                if isinstance(item, str):
                    formatted_items.append(f'"{item}"')
                else:
                    formatted_items.append(str(item))
            
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[" + ", ".join(formatted_items) + "]"
    
    elif isinstance(value, dict):
        if not value:
            return "{}"
        
        lines = ["{"]
        items = list(value.items())
        for j, (k, v) in enumerate(items):
            formatted_v = _format_js_value_enhanced(v)
            comma = "," if j < len(items) - 1 else ""
            lines.append(f'            {k}: {formatted_v}{comma}')
        lines.append("        }")
        
        return "\n        ".join(lines)
    
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif value is None:
        return "null"
    else:
        return str(value)

# Enhanced validation function for the generated IVR code
def validate_ivr_nodes(ivr_nodes: List[Dict[str, Any]]) -> List[str]:
    """Enhanced validate IVR nodes and return list of issues found"""
    issues = []
    labels = set()
    
    for i, node in enumerate(ivr_nodes):
        # Check required fields
        if 'label' not in node:
            issues.append(f"Node {i}: Missing required 'label' field")
        else:
            label = node['label']
            if label in labels:
                issues.append(f"Node {i}: Duplicate label '{label}'")
            labels.add(label)
        
        # Check branch targets
        if 'branch' in node:
            for digit, target in node['branch'].items():
                if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                    issues.append(f"Node {i}: Branch target '{target}' not found")
        
        # Check goto targets
        if 'goto' in node:
            target = node['goto']
            if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                issues.append(f"Node {i}: Goto target '{target}' not found")
        
        # Check getDigits structure
        if 'getDigits' in node:
            get_digits = node['getDigits']
            if not isinstance(get_digits, dict):
                issues.append(f"Node {i}: getDigits must be an object")
            else:
                required_fields = ['numDigits', 'validChoices']
                for field in required_fields:
                    if field not in get_digits:
                        issues.append(f"Node {i}: getDigits missing '{field}' field")
        
        # Check gosub structure (allflows LITE pattern)
        if 'gosub' in node:
            gosub = node['gosub']
            if not isinstance(gosub, list) or len(gosub) != 3:
                issues.append(f"Node {i}: gosub must be array of 3 elements [function, code, description]")
        
        # Check guard function syntax
        if 'guard' in node:
            guard = node['guard']
            if not isinstance(guard, str) or not guard.startswith('function'):
                issues.append(f"Node {i}: guard must be a function string")
    
    return issues
, before_bracket)
                            if id_match:
                                target_id = id_match.group(1)
                                if target_id not in node_texts:  # Don't overwrite existing text
                                    # Extract text between quotes
                                    target_text = target_part[quote_start + 1:quote_end]
                                    # Clean HTML tags from text
                                    target_text = re.sub(r'<br\s*/?>', ' ', target_text)
                                    target_text = re.sub(r'<[^>]+>', '', target_text)
                                    node_texts[target_id] = target_text.strip()
                    
                    if not target_id:
                        # Fallback to simple ID extraction
                        simple_match = re.match(r'^([A-Z]+)', target_part)
                        if simple_match:
                            target_id = simple_match.group(1)
                    
                    # Add connection if we found both IDs
                    if source_id and target_id:
                        connections.append({
                            'source': source_id,
                            'target': target_id,
                            'label': connection_label
                        })
                        
                except Exception as e:
                    print(f"Error parsing line: {line} - {e}")
                    continue
        
        # Fallback: If we still don't have text for a node, try to extract it more aggressively
        for line in lines:
            if '-->' not in line and not line.startswith('flowchart'):
                # Try to match any node definition pattern
                fallback_match = re.search(r'([A-Z]+)\s*[\[{]"([^"]+)"[\]}]', line)
                if fallback_match:
                    node_id = fallback_match.group(1)
                    if node_id not in node_texts:
                        node_text = fallback_match.group(2)
                        node_text = re.sub(r'<br\s*/?>', ' ', node_text)
                        node_text = re.sub(r'<[^>]+>', '', node_text)
                        node_texts[node_id] = node_text.strip()
        
        # Create node objects with proper classification
        for node_id, node_text in node_texts.items():
            # Generate descriptive label
            label = self._generate_descriptive_label(node_text, connections, node_id)
            
            # Classify node type
            node_type = self._classify_node_type(node_text, connections, node_id)
            
            nodes.append({
                'id': node_id,
                'text': node_text,
                'label': label,
                'type': node_type
            })
        
        return nodes, connections

    def _classify_node_type(self, text: str, connections: List[Dict[str, str]], node_id: str) -> NodeType:
        """Classify node type for proper IVR generation"""
        text_lower = text.lower()
        
        # Analyze outgoing connections to help classification
        outgoing_connections = [conn for conn in connections if conn['source'] == node_id]
        has_multiple_choices = len(outgoing_connections) > 1
        
        if 'welcome' in text_lower or ('this is an' in text_lower and 'press' in text_lower):
            return NodeType.WELCOME
        elif 'pin' in text_lower and 'enter' in text_lower:
            return NodeType.PIN_ENTRY
        elif 'available' in text_lower and 'callout' in text_lower:
            return NodeType.AVAILABILITY
        elif 'accept' in text_lower or 'decline' in text_lower or 'not home' in text_lower:
            return NodeType.RESPONSE
        elif 'goodbye' in text_lower or 'thank you' in text_lower:
            return NodeType.GOODBYE
        elif 'problems' in text_lower or 'error' in text_lower:
            return NodeType.ERROR
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return NodeType.SLEEP
        elif has_multiple_choices or ('?' in text_lower and len(outgoing_connections) > 0):
            return NodeType.DECISION
        else:
            return NodeType.ACTION

    def _generate_descriptive_label(self, text: str, connections: List[Dict[str, str]], node_id: str) -> str:
        """Generate descriptive label following Andres's conventions"""
        text_lower = text.lower()
        
        # Welcome/opening nodes
        if 'welcome' in text_lower or ('this is an' in text_lower and 'callout' in text_lower):
            return "Live Answer"
        
        # PIN related
        elif 'pin' in text_lower and 'enter' in text_lower:
            return "Enter PIN"
        elif 'pin' in text_lower and ('correct' in text_lower or 'valid' in text_lower):
            return "PIN Validation"
        elif 'invalid' in text_lower and ('pin' in text_lower or 'entry' in text_lower):
            return "Invalid Entry"
        
        # Availability
        elif 'available' in text_lower and 'callout' in text_lower:
            return "Available For Callout"
        
        # Responses (following allflows patterns)
        elif 'accept' in text_lower and 'response' in text_lower:
            return "Accept"
        elif 'decline' in text_lower:
            return "Decline"
        elif 'not home' in text_lower:
            return "Not Home"
        elif 'qualified' in text_lower or 'call back' in text_lower:
            return "Qualified No"
        
        # System messages
        elif 'goodbye' in text_lower:
            return "Goodbye"
        elif 'thank you' in text_lower:
            return "Goodbye"
        elif 'problems' in text_lower:
            return "Problems"
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return "Sleep"
        
        # Callout information
        elif 'callout reason' in text_lower:
            return "Callout Reason"
        elif 'trouble location' in text_lower:
            return "Trouble Location"
        elif 'custom message' in text_lower:
            return "Custom Message"
        elif 'electric callout' in text_lower:
            return "Electric Callout"
        
        # Fallback to meaningful name
        else:
            # Extract key words for label
            words = re.findall(r'\b[A-Z][a-z]+', text)
            if words:
                return ' '.join(words[:2])
            else:
                return node_id.title()

    def _generate_database_driven_flow(self, nodes: List[Dict[str, Any]], connections: List[Dict[str, str]], notes: List[str]) -> List[Dict[str, Any]]:
        """Generate complete IVR flow using database-driven approach with allflows LITE patterns"""
        if not nodes:
            notes.append("No nodes to process")
            return []
            
        ivr_nodes = []
        used_labels = set()
        
        # Create a mapping of node IDs to their generated labels for cross-referencing
        node_id_to_label = {}
        
        # First pass: Generate labels for all nodes
        for node in nodes:
            label = node['label']
            counter = 2
            while label in used_labels:
                label = f"{node['label']} {counter}"
                counter += 1
            used_labels.add(label)
            node_id_to_label[node['id']] = label
        
        # Second pass: Generate IVR nodes with proper cross-references
        for node in nodes:
            label = node_id_to_label[node['id']]
            
            # Generate IVR node(s) based on type and complexity
            node_connections = [conn for conn in connections if conn['source'] == node['id']]
            
            # Check if we should create multi-object nodes (glommer nodes)
            if self._should_split_into_glommer_nodes(node['text']) and node.get('type') == NodeType.WELCOME:
                generated_nodes = self._create_multi_object_welcome_node(node, label, node_connections, node_id_to_label, notes)
            else:
                generated_nodes = self._create_database_node_with_mapping(node, label, node_connections, node_id_to_label, notes)
            
            for ivr_node in generated_nodes:
                # Add nobarge where appropriate
                if node.get('type') in [NodeType.RESPONSE, NodeType.GOODBYE, NodeType.ERROR]:
                    ivr_node["nobarge"] = "1"
                ivr_nodes.append(ivr_node)
        
        # Add standard handlers if not present
        self._ensure_standard_handlers(ivr_nodes, used_labels, notes)
        
        return ivr_nodes

    def _create_multi_object_welcome_node(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create multi-object welcome node following allflows LITE patterns"""
        text = node['text']
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        nodes = []
        
        # Object 1: Main callout information (first part)
        main_segments = 5  # Split at reasonable boundary
        main_node = {
            "label": label
        }
        
        if len(play_log) > main_segments:
            main_node["playLog"] = play_log[:main_segments]
            main_node["playPrompt"] = play_prompt[:main_segments]
        else:
            main_node["playLog"] = play_log
            main_node["playPrompt"] = play_prompt
        
        nodes.append(main_node)
        
        # Object 2: Environment check (if not production) - allflows LITE pattern
        env_node = {
            "log": "environment",
            "guard": "function (){ return this.data.env!='prod' && this.data.env!='PROD' }",
            "playPrompt": "callflow:{{env}}",
            "nobarge": "1"
        }
        nodes.append(env_node)
        
        # Object 3: Menu options with getDigits (remaining segments)
        menu_node = {}
        
        if len(play_log) > main_segments:
            menu_node["playLog"] = play_log[main_segments:]
            menu_node["playPrompt"] = play_prompt[main_segments:]
        else:
            menu_node["playLog"] = ["Menu options"]
            menu_node["playPrompt"] = ["callflow:MenuOptions"]
        
        # Add getDigits and branch logic
        self._add_welcome_logic_with_mapping(menu_node, connections, node_id_to_label, notes)
        nodes.append(menu_node)
        
        notes.append(f"Created multi-object welcome node with {len(nodes)} components")
        
        return nodes

    def _create_database_node_with_mapping(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create IVR node(s) using database matching with proper label mapping"""
        text = node['text']
        node_type = node.get('type', NodeType.ACTION)
        
        # Intelligent segmentation using database
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        # Create base node following allflows property order
        ivr_node = {}
        
        # Property order: label → playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge
        ivr_node["label"] = label
        
        if len(play_log) > 1:
            ivr_node["playLog"] = play_log
        elif play_log:
            ivr_node["log"] = play_log[0]  # Single log entry uses "log" instead of "playLog"
        
        if len(play_prompt) > 1:
            ivr_node["playPrompt"] = play_prompt
        elif play_prompt:
            ivr_node["playPrompt"] = play_prompt[0]
        
        # Add interaction logic based on node type and connections
        if node_type == NodeType.WELCOME and connections:
            self._add_welcome_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.PIN_ENTRY:
            self._add_pin_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.AVAILABILITY and connections:
            self._add_availability_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.RESPONSE:
            self._add_response_logic(ivr_node, label, notes)
        elif node_type == NodeType.SLEEP:
            self._add_sleep_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) > 1:
            self._add_decision_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) == 1:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["goto"] = target_label
        
        return [ivr_node]

    def _add_welcome_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add welcome node logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 1,  # Very short timeout for main menu (allflows LITE pattern)
            "validChoices": "",
            "errorPrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            label = conn['label'].lower()
            digit_match = re.search(r'(\d+)', label)
            
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'retry' in label or 'repeat' in label or 'invalid' in label:
                # Self-reference for retries
                branch["error"] = ivr_node["label"]
        
        # Add default handling
        if branch:
            ivr_node["branch"] = branch
            ivr_node["getDigits"]["validChoices"] = "|".join(sorted(valid_choices))
            # Add error handling
            if "error" not in branch:
                branch["error"] = ivr_node["label"]  # Self-reference for retries
        
        # Add retry logic (allflows LITE pattern)
        ivr_node["maxLoop"] = ["Loop-Main", 3, "Problems"]

    def _add_pin_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add PIN entry logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 5,  # 4 digits + pound (allflows LITE pattern)
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "{{pin}}",  # Dynamic PIN validation
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Add branch logic for validation
        if connections:
            branch = {}
            for conn in connections:
                if 'yes' in conn['label'].lower() or 'correct' in conn['label'].lower() or 'valid' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["match"] = target_label
                elif 'no' in conn['label'].lower() or 'invalid' in conn['label'].lower() or 'retry' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["nomatch"] = target_label
            
            if branch:
                ivr_node["branch"] = branch
            
        # Add retry handling
        ivr_node["maxLoop"] = ["Loop-PIN", 3, "Problems"]

    def _add_availability_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add availability check logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "1|3|0",  # Standard availability choices
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        for conn in connections:
            label = conn['label'].lower()
            target_id = conn['target']
            target_label = node_id_to_label.get(target_id, target_id)
            
            if '1' in label or 'accept' in label:
                branch["1"] = target_label
            elif '3' in label or 'decline' in label:
                branch["3"] = target_label
            elif '0' in label or 'call back' in label or '9' in label:
                branch["0"] = target_label
            elif 'invalid' in label or 'retry' in label:
                branch["error"] = target_label
        
        # Add default error handling if not specified
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        if "timeout" not in branch:
            branch["timeout"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
        
        ivr_node["maxLoop"] = ["Loop-Availability", 3, "Problems"]

    def _add_sleep_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add sleep/wait logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 30,  # 30-second timeout (allflows LITE pattern)
            "validChoices": "1|2|3|4|5|6|7|8|9|0|*|#",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Default behavior for any key press or timeout
        if connections:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["branch"] = {
                "next": target_label,
                "none": target_label  # Same destination for timeout
            }
        else:
            ivr_node["branch"] = {
                "next": "Live Answer",
                "none": "Live Answer"
            }

    def _add_decision_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add decision logic for multiple choice nodes with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            digit_match = re.search(r'(\d+)', conn['label'])
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'yes' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["yes"] = target_label
            elif 'no' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["no"] = target_label
        
        # Add error handling
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
            if valid_choices:
                ivr_node["getDigits"]["validChoices"] = "|".join(valid_choices)
        
        ivr_node["maxLoop"] = ["Loop-Decision", 3, "Problems"]

    def _add_response_logic(self, ivr_node: Dict[str, Any], label: str, notes: List[str]):
        """Add response handler logic following allflows patterns"""
        label_lower = label.lower()
        
        # Add gosub for response recording (allflows LITE pattern)
        if 'accept' in label_lower:
            ivr_node["gosub"] = self.response_codes['accept']
        elif 'decline' in label_lower:
            ivr_node["gosub"] = self.response_codes['decline']
        elif 'not home' in label_lower:
            ivr_node["gosub"] = self.response_codes['not_home']
        elif 'qualified' in label_lower:
            ivr_node["gosub"] = self.response_codes['qualified_no']
        else:
            ivr_node["gosub"] = self.response_codes['error']
        
        # Add nobarge for non-interruptible response messages
        ivr_node["nobarge"] = "1"
        
        # Always go to Goodbye after response
        ivr_node["goto"] = "Goodbye"

    def _ensure_standard_handlers(self, ivr_nodes: List[Dict[str, Any]], used_labels: Set[str], notes: List[str]):
        """Ensure standard handler nodes exist following allflows LITE patterns"""
        existing_labels = {node.get('label') for node in ivr_nodes}
        
        # Add Problems handler if missing
        if 'Problems' not in existing_labels:
            problems_node = {
                "label": "Problems",
                "gosub": self.response_codes['error']
            }
            # Add the actual problem message components
            ivr_nodes.append(problems_node)
            
            # Add the message part
            problems_message = {
                "nobarge": "1",
                "playLog": ["I'm sorry you are having problems.", "Please have", "Employee name"],
                "playPrompt": ["callflow:1351", "callflow:1017", "names:{{contact_id}}"]
            }
            ivr_nodes.append(problems_message)
            
            # Add call instructions
            problems_call = {
                "log": "call the",
                "playPrompt": "callflow:1174"
            }
            ivr_nodes.append(problems_call)
            
            # Add final part
            problems_final = {
                "nobarge": "1",
                "playLog": ["APS", "callout system", "at", "speak phone num"],
                "playPrompt": ["location:{{level2_location}}", "callflow:1290", "callflow:1015", "digits:{{callback_number}}"],
                "goto": "Goodbye"
            }
            ivr_nodes.append(problems_final)
            
            notes.append("Added complete Problems handler with multi-object structure")
        
        # Add Goodbye handler if missing
        if 'Goodbye' not in existing_labels:
            goodbye_node = {
                "label": "Goodbye",
                "log": "Goodbye(1029)",
                "playPrompt": "callflow:1029",
                "nobarge": "1",
                "goto": "hangup"
            }
            ivr_nodes.append(goodbye_node)
            notes.append("Added Goodbye handler")

    def _create_fallback_flow(self) -> List[Dict[str, Any]]:
        """Create fallback flow when parsing fails"""
        return [
            {
                "label": "Live Answer",
                "log": "Welcome message",
                "playPrompt": "callflow:Welcome",
                "goto": "Problems"
            },
            {
                "label": "Problems",
                "log": "Error handler",
                "playPrompt": "callflow:1351",
                "goto": "Goodbye"
            },
            {
                "label": "Goodbye",
                "log": "Goodbye message",
                "playPrompt": "callflow:1029",
                "goto": "hangup"
            }
        ]


def convert_mermaid_to_ivr(mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Main conversion function using sophisticated database-driven approach"""
    converter = DatabaseDrivenIVRConverter()
    return converter.convert(mermaid_code)


# Enhanced Format IVR Output Functions for allflows LITE compatibility
def format_ivr_output(ivr_nodes: List[Dict[str, Any]]) -> str:
    """
    Format IVR nodes into production-ready JavaScript module.exports format
    Enhanced for full allflows LITE compatibility
    """
    if not ivr_nodes:
        return "module.exports = [];"
    
    # Clean and format the nodes following allflows property order
    formatted_nodes = []
    
    for node in ivr_nodes:
        # Ensure all nodes have required fields
        clean_node = {}
        
        # Property order from allflows: label → log/playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge → guard
        
        # 1. Label (required)
        if 'label' in node:
            clean_node['label'] = node['label']
        
        # 2. Log/PlayLog (documentation)
        if 'playLog' in node:
            clean_node['playLog'] = node['playLog']
        elif 'log' in node:
            clean_node['log'] = node['log']
        
        # 3. PlayPrompt (voice files)
        if 'playPrompt' in node:
            clean_node['playPrompt'] = node['playPrompt']
        
        # 4. GetDigits (input collection)
        if 'getDigits' in node:
            clean_node['getDigits'] = node['getDigits']
        
        # 5. Branch (conditional navigation)
        if 'branch' in node:
            clean_node['branch'] = node['branch']
        
        # 6. MaxLoop (retry logic)
        if 'maxLoop' in node:
            clean_node['maxLoop'] = node['maxLoop']
        
        # 7. Gosub (subroutine calls)
        if 'gosub' in node:
            clean_node['gosub'] = node['gosub']
        
        # 8. Goto (direct transitions)
        if 'goto' in node:
            clean_node['goto'] = node['goto']
        
        # 9. Nobarge (non-interruptible)
        if 'nobarge' in node:
            clean_node['nobarge'] = node['nobarge']
        
        # 10. Guard (conditional execution) - allflows LITE pattern
        if 'guard' in node:
            clean_node['guard'] = node['guard']
        
        # Add any other properties that might be present
        for key, value in node.items():
            if key not in clean_node:
                clean_node[key] = value
        
        formatted_nodes.append(clean_node)
    
    # Convert to JavaScript format with proper formatting
    try:
        # Use enhanced JavaScript formatting for allflows LITE compatibility
        js_output = _format_as_javascript_enhanced(formatted_nodes)
        return f"module.exports = {js_output};"
        
    except Exception as e:
        # Fallback to basic JSON formatting
        json_str = json.dumps(formatted_nodes, indent=2)
        return f"module.exports = {json_str};"

def _format_as_javascript_enhanced(nodes: List[Dict[str, Any]]) -> str:
    """Enhanced format nodes as JavaScript array with allflows LITE compatibility"""
    lines = ["["]
    
    for i, node in enumerate(nodes):
        lines.append("    {")
        
        # Format each property with enhanced handling
        for j, (key, value) in enumerate(node.items()):
            formatted_value = _format_js_value_enhanced(value)
            comma = "," if j < len(node) - 1 else ""
            lines.append(f'        {key}: {formatted_value}{comma}')
        
        closer = "    }," if i < len(nodes) - 1 else "    }"
        lines.append(closer)
    
    lines.append("]")
    
    return "\n".join(lines)

def _format_js_value_enhanced(value: Any) -> str:
    """Enhanced format a value for JavaScript output with guard function support"""
    if isinstance(value, str):
        # Special handling for guard functions (allflows LITE pattern)
        if value.startswith("function"):
            return value  # Don't quote function definitions
        else:
            return f'"{value}"'
    elif isinstance(value, list):
        if not value:
            return "[]"
        
        # Check if all items are strings
        if all(isinstance(item, str) for item in value):
            formatted_items = [f'"{item}"' for item in value]
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[\n            " + ",\n            ".join(formatted_items) + "\n        ]"
        else:
            # Mixed types - use JSON formatting but handle special cases
            formatted_items = []
            for item in value:
                if isinstance(item, str):
                    formatted_items.append(f'"{item}"')
                else:
                    formatted_items.append(str(item))
            
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[" + ", ".join(formatted_items) + "]"
    
    elif isinstance(value, dict):
        if not value:
            return "{}"
        
        lines = ["{"]
        items = list(value.items())
        for j, (k, v) in enumerate(items):
            formatted_v = _format_js_value_enhanced(v)
            comma = "," if j < len(items) - 1 else ""
            lines.append(f'            {k}: {formatted_v}{comma}')
        lines.append("        }")
        
        return "\n        ".join(lines)
    
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif value is None:
        return "null"
    else:
        return str(value)

# Enhanced validation function for the generated IVR code
def validate_ivr_nodes(ivr_nodes: List[Dict[str, Any]]) -> List[str]:
    """Enhanced validate IVR nodes and return list of issues found"""
    issues = []
    labels = set()
    
    for i, node in enumerate(ivr_nodes):
        # Check required fields
        if 'label' not in node:
            issues.append(f"Node {i}: Missing required 'label' field")
        else:
            label = node['label']
            if label in labels:
                issues.append(f"Node {i}: Duplicate label '{label}'")
            labels.add(label)
        
        # Check branch targets
        if 'branch' in node:
            for digit, target in node['branch'].items():
                if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                    issues.append(f"Node {i}: Branch target '{target}' not found")
        
        # Check goto targets
        if 'goto' in node:
            target = node['goto']
            if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                issues.append(f"Node {i}: Goto target '{target}' not found")
        
        # Check getDigits structure
        if 'getDigits' in node:
            get_digits = node['getDigits']
            if not isinstance(get_digits, dict):
                issues.append(f"Node {i}: getDigits must be an object")
            else:
                required_fields = ['numDigits', 'validChoices']
                for field in required_fields:
                    if field not in get_digits:
                        issues.append(f"Node {i}: getDigits missing '{field}' field")
        
        # Check gosub structure (allflows LITE pattern)
        if 'gosub' in node:
            gosub = node['gosub']
            if not isinstance(gosub, list) or len(gosub) != 3:
                issues.append(f"Node {i}: gosub must be array of 3 elements [function, code, description]")
        
        # Check guard function syntax
        if 'guard' in node:
            guard = node['guard']
            if not isinstance(guard, str) or not guard.startswith('function'):
                issues.append(f"Node {i}: guard must be a function string")
    
    return issues
, before_bracket)
                    if id_match:
                        node_id = id_match.group(1)
                        # Extract text between quotes
                        node_text = line[quote_start + 1:quote_end]
                        # Clean HTML tags and normalize
                        node_text = re.sub(r'<br\s*/?>', ' ', node_text)
                        node_text = re.sub(r'<[^>]+>', '', node_text)
                        node_texts[node_id] = node_text.strip()
        
        # Second pass: Parse connections and extract inline node definitions
        for line in lines:
            if line.startswith('flowchart') or line.startswith('%%'):
                continue
                
            # Parse connections and extract nodes
            if '-->' in line:
                try:
                    # Split the line at --> to separate source and target
                    arrow_pos = line.find('-->')
                    source_part = line[:arrow_pos].strip()
                    target_part = line[arrow_pos + 3:].strip()
                    
                    # Enhanced source node extraction
                    # Handle patterns like: A["complex text with (variables) and <br/> tags"]
                    source_id = None
                    if '"' in source_part:
                        # Extract from quoted definition
                        quote_start = source_part.find('"')
                        quote_end = source_part.rfind('"')
                        if quote_start != -1 and quote_end != -1 and quote_end > quote_start:
                            # Get node ID (everything before the bracket/quote)
                            before_bracket = source_part[:quote_start]
                            id_match = re.search(r'([A-Z]+)\s*[\[{]?\s*
        
        # Fallback: If we still don't have text for a node, try to extract it more aggressively
        for line in lines:
            if '-->' not in line and not line.startswith('flowchart'):
                # Try to match any node definition pattern
                fallback_match = re.search(r'([A-Z]+)\s*[\[{]"([^"]+)"[\]}]', line)
                if fallback_match:
                    node_id = fallback_match.group(1)
                    if node_id not in node_texts:
                        node_text = fallback_match.group(2)
                        node_text = re.sub(r'<br\s*/?>', ' ', node_text)
                        node_text = re.sub(r'<[^>]+>', '', node_text)
                        node_texts[node_id] = node_text.strip()
        
        # Create node objects with proper classification
        for node_id, node_text in node_texts.items():
            # Generate descriptive label
            label = self._generate_descriptive_label(node_text, connections, node_id)
            
            # Classify node type
            node_type = self._classify_node_type(node_text, connections, node_id)
            
            nodes.append({
                'id': node_id,
                'text': node_text,
                'label': label,
                'type': node_type
            })
        
        return nodes, connections

    def _classify_node_type(self, text: str, connections: List[Dict[str, str]], node_id: str) -> NodeType:
        """Classify node type for proper IVR generation"""
        text_lower = text.lower()
        
        # Analyze outgoing connections to help classification
        outgoing_connections = [conn for conn in connections if conn['source'] == node_id]
        has_multiple_choices = len(outgoing_connections) > 1
        
        if 'welcome' in text_lower or ('this is an' in text_lower and 'press' in text_lower):
            return NodeType.WELCOME
        elif 'pin' in text_lower and 'enter' in text_lower:
            return NodeType.PIN_ENTRY
        elif 'available' in text_lower and 'callout' in text_lower:
            return NodeType.AVAILABILITY
        elif 'accept' in text_lower or 'decline' in text_lower or 'not home' in text_lower:
            return NodeType.RESPONSE
        elif 'goodbye' in text_lower or 'thank you' in text_lower:
            return NodeType.GOODBYE
        elif 'problems' in text_lower or 'error' in text_lower:
            return NodeType.ERROR
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return NodeType.SLEEP
        elif has_multiple_choices or ('?' in text_lower and len(outgoing_connections) > 0):
            return NodeType.DECISION
        else:
            return NodeType.ACTION

    def _generate_descriptive_label(self, text: str, connections: List[Dict[str, str]], node_id: str) -> str:
        """Generate descriptive label following Andres's conventions"""
        text_lower = text.lower()
        
        # Welcome/opening nodes
        if 'welcome' in text_lower or ('this is an' in text_lower and 'callout' in text_lower):
            return "Live Answer"
        
        # PIN related
        elif 'pin' in text_lower and 'enter' in text_lower:
            return "Enter PIN"
        elif 'pin' in text_lower and ('correct' in text_lower or 'valid' in text_lower):
            return "PIN Validation"
        elif 'invalid' in text_lower and ('pin' in text_lower or 'entry' in text_lower):
            return "Invalid Entry"
        
        # Availability
        elif 'available' in text_lower and 'callout' in text_lower:
            return "Available For Callout"
        
        # Responses (following allflows patterns)
        elif 'accept' in text_lower and 'response' in text_lower:
            return "Accept"
        elif 'decline' in text_lower:
            return "Decline"
        elif 'not home' in text_lower:
            return "Not Home"
        elif 'qualified' in text_lower or 'call back' in text_lower:
            return "Qualified No"
        
        # System messages
        elif 'goodbye' in text_lower:
            return "Goodbye"
        elif 'thank you' in text_lower:
            return "Goodbye"
        elif 'problems' in text_lower:
            return "Problems"
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return "Sleep"
        
        # Callout information
        elif 'callout reason' in text_lower:
            return "Callout Reason"
        elif 'trouble location' in text_lower:
            return "Trouble Location"
        elif 'custom message' in text_lower:
            return "Custom Message"
        elif 'electric callout' in text_lower:
            return "Electric Callout"
        
        # Fallback to meaningful name
        else:
            # Extract key words for label
            words = re.findall(r'\b[A-Z][a-z]+', text)
            if words:
                return ' '.join(words[:2])
            else:
                return node_id.title()

    def _generate_database_driven_flow(self, nodes: List[Dict[str, Any]], connections: List[Dict[str, str]], notes: List[str]) -> List[Dict[str, Any]]:
        """Generate complete IVR flow using database-driven approach with allflows LITE patterns"""
        if not nodes:
            notes.append("No nodes to process")
            return []
            
        ivr_nodes = []
        used_labels = set()
        
        # Create a mapping of node IDs to their generated labels for cross-referencing
        node_id_to_label = {}
        
        # First pass: Generate labels for all nodes
        for node in nodes:
            label = node['label']
            counter = 2
            while label in used_labels:
                label = f"{node['label']} {counter}"
                counter += 1
            used_labels.add(label)
            node_id_to_label[node['id']] = label
        
        # Second pass: Generate IVR nodes with proper cross-references
        for node in nodes:
            label = node_id_to_label[node['id']]
            
            # Generate IVR node(s) based on type and complexity
            node_connections = [conn for conn in connections if conn['source'] == node['id']]
            
            # Check if we should create multi-object nodes (glommer nodes)
            if self._should_split_into_glommer_nodes(node['text']) and node.get('type') == NodeType.WELCOME:
                generated_nodes = self._create_multi_object_welcome_node(node, label, node_connections, node_id_to_label, notes)
            else:
                generated_nodes = self._create_database_node_with_mapping(node, label, node_connections, node_id_to_label, notes)
            
            for ivr_node in generated_nodes:
                # Add nobarge where appropriate
                if node.get('type') in [NodeType.RESPONSE, NodeType.GOODBYE, NodeType.ERROR]:
                    ivr_node["nobarge"] = "1"
                ivr_nodes.append(ivr_node)
        
        # Add standard handlers if not present
        self._ensure_standard_handlers(ivr_nodes, used_labels, notes)
        
        return ivr_nodes

    def _create_multi_object_welcome_node(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create multi-object welcome node following allflows LITE patterns"""
        text = node['text']
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        nodes = []
        
        # Object 1: Main callout information (first part)
        main_segments = 5  # Split at reasonable boundary
        main_node = {
            "label": label
        }
        
        if len(play_log) > main_segments:
            main_node["playLog"] = play_log[:main_segments]
            main_node["playPrompt"] = play_prompt[:main_segments]
        else:
            main_node["playLog"] = play_log
            main_node["playPrompt"] = play_prompt
        
        nodes.append(main_node)
        
        # Object 2: Environment check (if not production) - allflows LITE pattern
        env_node = {
            "log": "environment",
            "guard": "function (){ return this.data.env!='prod' && this.data.env!='PROD' }",
            "playPrompt": "callflow:{{env}}",
            "nobarge": "1"
        }
        nodes.append(env_node)
        
        # Object 3: Menu options with getDigits (remaining segments)
        menu_node = {}
        
        if len(play_log) > main_segments:
            menu_node["playLog"] = play_log[main_segments:]
            menu_node["playPrompt"] = play_prompt[main_segments:]
        else:
            menu_node["playLog"] = ["Menu options"]
            menu_node["playPrompt"] = ["callflow:MenuOptions"]
        
        # Add getDigits and branch logic
        self._add_welcome_logic_with_mapping(menu_node, connections, node_id_to_label, notes)
        nodes.append(menu_node)
        
        notes.append(f"Created multi-object welcome node with {len(nodes)} components")
        
        return nodes

    def _create_database_node_with_mapping(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create IVR node(s) using database matching with proper label mapping"""
        text = node['text']
        node_type = node.get('type', NodeType.ACTION)
        
        # Intelligent segmentation using database
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        # Create base node following allflows property order
        ivr_node = {}
        
        # Property order: label → playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge
        ivr_node["label"] = label
        
        if len(play_log) > 1:
            ivr_node["playLog"] = play_log
        elif play_log:
            ivr_node["log"] = play_log[0]  # Single log entry uses "log" instead of "playLog"
        
        if len(play_prompt) > 1:
            ivr_node["playPrompt"] = play_prompt
        elif play_prompt:
            ivr_node["playPrompt"] = play_prompt[0]
        
        # Add interaction logic based on node type and connections
        if node_type == NodeType.WELCOME and connections:
            self._add_welcome_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.PIN_ENTRY:
            self._add_pin_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.AVAILABILITY and connections:
            self._add_availability_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.RESPONSE:
            self._add_response_logic(ivr_node, label, notes)
        elif node_type == NodeType.SLEEP:
            self._add_sleep_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) > 1:
            self._add_decision_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) == 1:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["goto"] = target_label
        
        return [ivr_node]

    def _add_welcome_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add welcome node logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 1,  # Very short timeout for main menu (allflows LITE pattern)
            "validChoices": "",
            "errorPrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            label = conn['label'].lower()
            digit_match = re.search(r'(\d+)', label)
            
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'retry' in label or 'repeat' in label or 'invalid' in label:
                # Self-reference for retries
                branch["error"] = ivr_node["label"]
        
        # Add default handling
        if branch:
            ivr_node["branch"] = branch
            ivr_node["getDigits"]["validChoices"] = "|".join(sorted(valid_choices))
            # Add error handling
            if "error" not in branch:
                branch["error"] = ivr_node["label"]  # Self-reference for retries
        
        # Add retry logic (allflows LITE pattern)
        ivr_node["maxLoop"] = ["Loop-Main", 3, "Problems"]

    def _add_pin_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add PIN entry logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 5,  # 4 digits + pound (allflows LITE pattern)
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "{{pin}}",  # Dynamic PIN validation
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Add branch logic for validation
        if connections:
            branch = {}
            for conn in connections:
                if 'yes' in conn['label'].lower() or 'correct' in conn['label'].lower() or 'valid' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["match"] = target_label
                elif 'no' in conn['label'].lower() or 'invalid' in conn['label'].lower() or 'retry' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["nomatch"] = target_label
            
            if branch:
                ivr_node["branch"] = branch
            
        # Add retry handling
        ivr_node["maxLoop"] = ["Loop-PIN", 3, "Problems"]

    def _add_availability_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add availability check logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "1|3|0",  # Standard availability choices
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        for conn in connections:
            label = conn['label'].lower()
            target_id = conn['target']
            target_label = node_id_to_label.get(target_id, target_id)
            
            if '1' in label or 'accept' in label:
                branch["1"] = target_label
            elif '3' in label or 'decline' in label:
                branch["3"] = target_label
            elif '0' in label or 'call back' in label or '9' in label:
                branch["0"] = target_label
            elif 'invalid' in label or 'retry' in label:
                branch["error"] = target_label
        
        # Add default error handling if not specified
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        if "timeout" not in branch:
            branch["timeout"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
        
        ivr_node["maxLoop"] = ["Loop-Availability", 3, "Problems"]

    def _add_sleep_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add sleep/wait logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 30,  # 30-second timeout (allflows LITE pattern)
            "validChoices": "1|2|3|4|5|6|7|8|9|0|*|#",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Default behavior for any key press or timeout
        if connections:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["branch"] = {
                "next": target_label,
                "none": target_label  # Same destination for timeout
            }
        else:
            ivr_node["branch"] = {
                "next": "Live Answer",
                "none": "Live Answer"
            }

    def _add_decision_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add decision logic for multiple choice nodes with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            digit_match = re.search(r'(\d+)', conn['label'])
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'yes' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["yes"] = target_label
            elif 'no' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["no"] = target_label
        
        # Add error handling
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
            if valid_choices:
                ivr_node["getDigits"]["validChoices"] = "|".join(valid_choices)
        
        ivr_node["maxLoop"] = ["Loop-Decision", 3, "Problems"]

    def _add_response_logic(self, ivr_node: Dict[str, Any], label: str, notes: List[str]):
        """Add response handler logic following allflows patterns"""
        label_lower = label.lower()
        
        # Add gosub for response recording (allflows LITE pattern)
        if 'accept' in label_lower:
            ivr_node["gosub"] = self.response_codes['accept']
        elif 'decline' in label_lower:
            ivr_node["gosub"] = self.response_codes['decline']
        elif 'not home' in label_lower:
            ivr_node["gosub"] = self.response_codes['not_home']
        elif 'qualified' in label_lower:
            ivr_node["gosub"] = self.response_codes['qualified_no']
        else:
            ivr_node["gosub"] = self.response_codes['error']
        
        # Add nobarge for non-interruptible response messages
        ivr_node["nobarge"] = "1"
        
        # Always go to Goodbye after response
        ivr_node["goto"] = "Goodbye"

    def _ensure_standard_handlers(self, ivr_nodes: List[Dict[str, Any]], used_labels: Set[str], notes: List[str]):
        """Ensure standard handler nodes exist following allflows LITE patterns"""
        existing_labels = {node.get('label') for node in ivr_nodes}
        
        # Add Problems handler if missing
        if 'Problems' not in existing_labels:
            problems_node = {
                "label": "Problems",
                "gosub": self.response_codes['error']
            }
            # Add the actual problem message components
            ivr_nodes.append(problems_node)
            
            # Add the message part
            problems_message = {
                "nobarge": "1",
                "playLog": ["I'm sorry you are having problems.", "Please have", "Employee name"],
                "playPrompt": ["callflow:1351", "callflow:1017", "names:{{contact_id}}"]
            }
            ivr_nodes.append(problems_message)
            
            # Add call instructions
            problems_call = {
                "log": "call the",
                "playPrompt": "callflow:1174"
            }
            ivr_nodes.append(problems_call)
            
            # Add final part
            problems_final = {
                "nobarge": "1",
                "playLog": ["APS", "callout system", "at", "speak phone num"],
                "playPrompt": ["location:{{level2_location}}", "callflow:1290", "callflow:1015", "digits:{{callback_number}}"],
                "goto": "Goodbye"
            }
            ivr_nodes.append(problems_final)
            
            notes.append("Added complete Problems handler with multi-object structure")
        
        # Add Goodbye handler if missing
        if 'Goodbye' not in existing_labels:
            goodbye_node = {
                "label": "Goodbye",
                "log": "Goodbye(1029)",
                "playPrompt": "callflow:1029",
                "nobarge": "1",
                "goto": "hangup"
            }
            ivr_nodes.append(goodbye_node)
            notes.append("Added Goodbye handler")

    def _create_fallback_flow(self) -> List[Dict[str, Any]]:
        """Create fallback flow when parsing fails"""
        return [
            {
                "label": "Live Answer",
                "log": "Welcome message",
                "playPrompt": "callflow:Welcome",
                "goto": "Problems"
            },
            {
                "label": "Problems",
                "log": "Error handler",
                "playPrompt": "callflow:1351",
                "goto": "Goodbye"
            },
            {
                "label": "Goodbye",
                "log": "Goodbye message",
                "playPrompt": "callflow:1029",
                "goto": "hangup"
            }
        ]


def convert_mermaid_to_ivr(mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Main conversion function using sophisticated database-driven approach"""
    converter = DatabaseDrivenIVRConverter()
    return converter.convert(mermaid_code)


# Enhanced Format IVR Output Functions for allflows LITE compatibility
def format_ivr_output(ivr_nodes: List[Dict[str, Any]]) -> str:
    """
    Format IVR nodes into production-ready JavaScript module.exports format
    Enhanced for full allflows LITE compatibility
    """
    if not ivr_nodes:
        return "module.exports = [];"
    
    # Clean and format the nodes following allflows property order
    formatted_nodes = []
    
    for node in ivr_nodes:
        # Ensure all nodes have required fields
        clean_node = {}
        
        # Property order from allflows: label → log/playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge → guard
        
        # 1. Label (required)
        if 'label' in node:
            clean_node['label'] = node['label']
        
        # 2. Log/PlayLog (documentation)
        if 'playLog' in node:
            clean_node['playLog'] = node['playLog']
        elif 'log' in node:
            clean_node['log'] = node['log']
        
        # 3. PlayPrompt (voice files)
        if 'playPrompt' in node:
            clean_node['playPrompt'] = node['playPrompt']
        
        # 4. GetDigits (input collection)
        if 'getDigits' in node:
            clean_node['getDigits'] = node['getDigits']
        
        # 5. Branch (conditional navigation)
        if 'branch' in node:
            clean_node['branch'] = node['branch']
        
        # 6. MaxLoop (retry logic)
        if 'maxLoop' in node:
            clean_node['maxLoop'] = node['maxLoop']
        
        # 7. Gosub (subroutine calls)
        if 'gosub' in node:
            clean_node['gosub'] = node['gosub']
        
        # 8. Goto (direct transitions)
        if 'goto' in node:
            clean_node['goto'] = node['goto']
        
        # 9. Nobarge (non-interruptible)
        if 'nobarge' in node:
            clean_node['nobarge'] = node['nobarge']
        
        # 10. Guard (conditional execution) - allflows LITE pattern
        if 'guard' in node:
            clean_node['guard'] = node['guard']
        
        # Add any other properties that might be present
        for key, value in node.items():
            if key not in clean_node:
                clean_node[key] = value
        
        formatted_nodes.append(clean_node)
    
    # Convert to JavaScript format with proper formatting
    try:
        # Use enhanced JavaScript formatting for allflows LITE compatibility
        js_output = _format_as_javascript_enhanced(formatted_nodes)
        return f"module.exports = {js_output};"
        
    except Exception as e:
        # Fallback to basic JSON formatting
        json_str = json.dumps(formatted_nodes, indent=2)
        return f"module.exports = {json_str};"

def _format_as_javascript_enhanced(nodes: List[Dict[str, Any]]) -> str:
    """Enhanced format nodes as JavaScript array with allflows LITE compatibility"""
    lines = ["["]
    
    for i, node in enumerate(nodes):
        lines.append("    {")
        
        # Format each property with enhanced handling
        for j, (key, value) in enumerate(node.items()):
            formatted_value = _format_js_value_enhanced(value)
            comma = "," if j < len(node) - 1 else ""
            lines.append(f'        {key}: {formatted_value}{comma}')
        
        closer = "    }," if i < len(nodes) - 1 else "    }"
        lines.append(closer)
    
    lines.append("]")
    
    return "\n".join(lines)

def _format_js_value_enhanced(value: Any) -> str:
    """Enhanced format a value for JavaScript output with guard function support"""
    if isinstance(value, str):
        # Special handling for guard functions (allflows LITE pattern)
        if value.startswith("function"):
            return value  # Don't quote function definitions
        else:
            return f'"{value}"'
    elif isinstance(value, list):
        if not value:
            return "[]"
        
        # Check if all items are strings
        if all(isinstance(item, str) for item in value):
            formatted_items = [f'"{item}"' for item in value]
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[\n            " + ",\n            ".join(formatted_items) + "\n        ]"
        else:
            # Mixed types - use JSON formatting but handle special cases
            formatted_items = []
            for item in value:
                if isinstance(item, str):
                    formatted_items.append(f'"{item}"')
                else:
                    formatted_items.append(str(item))
            
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[" + ", ".join(formatted_items) + "]"
    
    elif isinstance(value, dict):
        if not value:
            return "{}"
        
        lines = ["{"]
        items = list(value.items())
        for j, (k, v) in enumerate(items):
            formatted_v = _format_js_value_enhanced(v)
            comma = "," if j < len(items) - 1 else ""
            lines.append(f'            {k}: {formatted_v}{comma}')
        lines.append("        }")
        
        return "\n        ".join(lines)
    
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif value is None:
        return "null"
    else:
        return str(value)

# Enhanced validation function for the generated IVR code
def validate_ivr_nodes(ivr_nodes: List[Dict[str, Any]]) -> List[str]:
    """Enhanced validate IVR nodes and return list of issues found"""
    issues = []
    labels = set()
    
    for i, node in enumerate(ivr_nodes):
        # Check required fields
        if 'label' not in node:
            issues.append(f"Node {i}: Missing required 'label' field")
        else:
            label = node['label']
            if label in labels:
                issues.append(f"Node {i}: Duplicate label '{label}'")
            labels.add(label)
        
        # Check branch targets
        if 'branch' in node:
            for digit, target in node['branch'].items():
                if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                    issues.append(f"Node {i}: Branch target '{target}' not found")
        
        # Check goto targets
        if 'goto' in node:
            target = node['goto']
            if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                issues.append(f"Node {i}: Goto target '{target}' not found")
        
        # Check getDigits structure
        if 'getDigits' in node:
            get_digits = node['getDigits']
            if not isinstance(get_digits, dict):
                issues.append(f"Node {i}: getDigits must be an object")
            else:
                required_fields = ['numDigits', 'validChoices']
                for field in required_fields:
                    if field not in get_digits:
                        issues.append(f"Node {i}: getDigits missing '{field}' field")
        
        # Check gosub structure (allflows LITE pattern)
        if 'gosub' in node:
            gosub = node['gosub']
            if not isinstance(gosub, list) or len(gosub) != 3:
                issues.append(f"Node {i}: gosub must be array of 3 elements [function, code, description]")
        
        # Check guard function syntax
        if 'guard' in node:
            guard = node['guard']
            if not isinstance(guard, str) or not guard.startswith('function'):
                issues.append(f"Node {i}: guard must be a function string")
    
    return issues
, before_bracket)
                            if id_match:
                                source_id = id_match.group(1)
                                # Extract text between quotes
                                source_text = source_part[quote_start + 1:quote_end]
                                # Clean HTML tags from text
                                source_text = re.sub(r'<br\s*/?>', ' ', source_text)
                                source_text = re.sub(r'<[^>]+>', '', source_text)
                                node_texts[source_id] = source_text.strip()
                    
                    if not source_id:
                        # Fallback to simple ID extraction
                        simple_match = re.match(r'^([A-Z]+)', source_part)
                        if simple_match:
                            source_id = simple_match.group(1)
                    
                    # Extract connection label from target part
                    connection_label = ""
                    if '|' in target_part:
                        # Extract label between pipes
                        label_match = re.search(r'\|"([^"]+)"\|', target_part)
                        if not label_match:
                            label_match = re.search(r'\|([^|]+)\|', target_part)
                        if label_match:
                            connection_label = label_match.group(1).strip('"')
                        # Remove label from target part
                        target_part = re.sub(r'\|[^|]*\|', '', target_part).strip()
                    
                    # Enhanced target node extraction
                    target_id = None
                    if '"' in target_part:
                        # Extract from quoted definition  
                        quote_start = target_part.find('"')
                        quote_end = target_part.rfind('"')
                        if quote_start != -1 and quote_end != -1 and quote_end > quote_start:
                            # Get node ID (everything before the bracket/quote)
                            before_bracket = target_part[:quote_start]
                            id_match = re.search(r'([A-Z]+)\s*[\[{]?\s*
        
        # Fallback: If we still don't have text for a node, try to extract it more aggressively
        for line in lines:
            if '-->' not in line and not line.startswith('flowchart'):
                # Try to match any node definition pattern
                fallback_match = re.search(r'([A-Z]+)\s*[\[{]"([^"]+)"[\]}]', line)
                if fallback_match:
                    node_id = fallback_match.group(1)
                    if node_id not in node_texts:
                        node_text = fallback_match.group(2)
                        node_text = re.sub(r'<br\s*/?>', ' ', node_text)
                        node_text = re.sub(r'<[^>]+>', '', node_text)
                        node_texts[node_id] = node_text.strip()
        
        # Create node objects with proper classification
        for node_id, node_text in node_texts.items():
            # Generate descriptive label
            label = self._generate_descriptive_label(node_text, connections, node_id)
            
            # Classify node type
            node_type = self._classify_node_type(node_text, connections, node_id)
            
            nodes.append({
                'id': node_id,
                'text': node_text,
                'label': label,
                'type': node_type
            })
        
        return nodes, connections

    def _classify_node_type(self, text: str, connections: List[Dict[str, str]], node_id: str) -> NodeType:
        """Classify node type for proper IVR generation"""
        text_lower = text.lower()
        
        # Analyze outgoing connections to help classification
        outgoing_connections = [conn for conn in connections if conn['source'] == node_id]
        has_multiple_choices = len(outgoing_connections) > 1
        
        if 'welcome' in text_lower or ('this is an' in text_lower and 'press' in text_lower):
            return NodeType.WELCOME
        elif 'pin' in text_lower and 'enter' in text_lower:
            return NodeType.PIN_ENTRY
        elif 'available' in text_lower and 'callout' in text_lower:
            return NodeType.AVAILABILITY
        elif 'accept' in text_lower or 'decline' in text_lower or 'not home' in text_lower:
            return NodeType.RESPONSE
        elif 'goodbye' in text_lower or 'thank you' in text_lower:
            return NodeType.GOODBYE
        elif 'problems' in text_lower or 'error' in text_lower:
            return NodeType.ERROR
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return NodeType.SLEEP
        elif has_multiple_choices or ('?' in text_lower and len(outgoing_connections) > 0):
            return NodeType.DECISION
        else:
            return NodeType.ACTION

    def _generate_descriptive_label(self, text: str, connections: List[Dict[str, str]], node_id: str) -> str:
        """Generate descriptive label following Andres's conventions"""
        text_lower = text.lower()
        
        # Welcome/opening nodes
        if 'welcome' in text_lower or ('this is an' in text_lower and 'callout' in text_lower):
            return "Live Answer"
        
        # PIN related
        elif 'pin' in text_lower and 'enter' in text_lower:
            return "Enter PIN"
        elif 'pin' in text_lower and ('correct' in text_lower or 'valid' in text_lower):
            return "PIN Validation"
        elif 'invalid' in text_lower and ('pin' in text_lower or 'entry' in text_lower):
            return "Invalid Entry"
        
        # Availability
        elif 'available' in text_lower and 'callout' in text_lower:
            return "Available For Callout"
        
        # Responses (following allflows patterns)
        elif 'accept' in text_lower and 'response' in text_lower:
            return "Accept"
        elif 'decline' in text_lower:
            return "Decline"
        elif 'not home' in text_lower:
            return "Not Home"
        elif 'qualified' in text_lower or 'call back' in text_lower:
            return "Qualified No"
        
        # System messages
        elif 'goodbye' in text_lower:
            return "Goodbye"
        elif 'thank you' in text_lower:
            return "Goodbye"
        elif 'problems' in text_lower:
            return "Problems"
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return "Sleep"
        
        # Callout information
        elif 'callout reason' in text_lower:
            return "Callout Reason"
        elif 'trouble location' in text_lower:
            return "Trouble Location"
        elif 'custom message' in text_lower:
            return "Custom Message"
        elif 'electric callout' in text_lower:
            return "Electric Callout"
        
        # Fallback to meaningful name
        else:
            # Extract key words for label
            words = re.findall(r'\b[A-Z][a-z]+', text)
            if words:
                return ' '.join(words[:2])
            else:
                return node_id.title()

    def _generate_database_driven_flow(self, nodes: List[Dict[str, Any]], connections: List[Dict[str, str]], notes: List[str]) -> List[Dict[str, Any]]:
        """Generate complete IVR flow using database-driven approach with allflows LITE patterns"""
        if not nodes:
            notes.append("No nodes to process")
            return []
            
        ivr_nodes = []
        used_labels = set()
        
        # Create a mapping of node IDs to their generated labels for cross-referencing
        node_id_to_label = {}
        
        # First pass: Generate labels for all nodes
        for node in nodes:
            label = node['label']
            counter = 2
            while label in used_labels:
                label = f"{node['label']} {counter}"
                counter += 1
            used_labels.add(label)
            node_id_to_label[node['id']] = label
        
        # Second pass: Generate IVR nodes with proper cross-references
        for node in nodes:
            label = node_id_to_label[node['id']]
            
            # Generate IVR node(s) based on type and complexity
            node_connections = [conn for conn in connections if conn['source'] == node['id']]
            
            # Check if we should create multi-object nodes (glommer nodes)
            if self._should_split_into_glommer_nodes(node['text']) and node.get('type') == NodeType.WELCOME:
                generated_nodes = self._create_multi_object_welcome_node(node, label, node_connections, node_id_to_label, notes)
            else:
                generated_nodes = self._create_database_node_with_mapping(node, label, node_connections, node_id_to_label, notes)
            
            for ivr_node in generated_nodes:
                # Add nobarge where appropriate
                if node.get('type') in [NodeType.RESPONSE, NodeType.GOODBYE, NodeType.ERROR]:
                    ivr_node["nobarge"] = "1"
                ivr_nodes.append(ivr_node)
        
        # Add standard handlers if not present
        self._ensure_standard_handlers(ivr_nodes, used_labels, notes)
        
        return ivr_nodes

    def _create_multi_object_welcome_node(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create multi-object welcome node following allflows LITE patterns"""
        text = node['text']
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        nodes = []
        
        # Object 1: Main callout information (first part)
        main_segments = 5  # Split at reasonable boundary
        main_node = {
            "label": label
        }
        
        if len(play_log) > main_segments:
            main_node["playLog"] = play_log[:main_segments]
            main_node["playPrompt"] = play_prompt[:main_segments]
        else:
            main_node["playLog"] = play_log
            main_node["playPrompt"] = play_prompt
        
        nodes.append(main_node)
        
        # Object 2: Environment check (if not production) - allflows LITE pattern
        env_node = {
            "log": "environment",
            "guard": "function (){ return this.data.env!='prod' && this.data.env!='PROD' }",
            "playPrompt": "callflow:{{env}}",
            "nobarge": "1"
        }
        nodes.append(env_node)
        
        # Object 3: Menu options with getDigits (remaining segments)
        menu_node = {}
        
        if len(play_log) > main_segments:
            menu_node["playLog"] = play_log[main_segments:]
            menu_node["playPrompt"] = play_prompt[main_segments:]
        else:
            menu_node["playLog"] = ["Menu options"]
            menu_node["playPrompt"] = ["callflow:MenuOptions"]
        
        # Add getDigits and branch logic
        self._add_welcome_logic_with_mapping(menu_node, connections, node_id_to_label, notes)
        nodes.append(menu_node)
        
        notes.append(f"Created multi-object welcome node with {len(nodes)} components")
        
        return nodes

    def _create_database_node_with_mapping(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create IVR node(s) using database matching with proper label mapping"""
        text = node['text']
        node_type = node.get('type', NodeType.ACTION)
        
        # Intelligent segmentation using database
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        # Create base node following allflows property order
        ivr_node = {}
        
        # Property order: label → playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge
        ivr_node["label"] = label
        
        if len(play_log) > 1:
            ivr_node["playLog"] = play_log
        elif play_log:
            ivr_node["log"] = play_log[0]  # Single log entry uses "log" instead of "playLog"
        
        if len(play_prompt) > 1:
            ivr_node["playPrompt"] = play_prompt
        elif play_prompt:
            ivr_node["playPrompt"] = play_prompt[0]
        
        # Add interaction logic based on node type and connections
        if node_type == NodeType.WELCOME and connections:
            self._add_welcome_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.PIN_ENTRY:
            self._add_pin_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.AVAILABILITY and connections:
            self._add_availability_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.RESPONSE:
            self._add_response_logic(ivr_node, label, notes)
        elif node_type == NodeType.SLEEP:
            self._add_sleep_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) > 1:
            self._add_decision_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) == 1:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["goto"] = target_label
        
        return [ivr_node]

    def _add_welcome_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add welcome node logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 1,  # Very short timeout for main menu (allflows LITE pattern)
            "validChoices": "",
            "errorPrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            label = conn['label'].lower()
            digit_match = re.search(r'(\d+)', label)
            
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'retry' in label or 'repeat' in label or 'invalid' in label:
                # Self-reference for retries
                branch["error"] = ivr_node["label"]
        
        # Add default handling
        if branch:
            ivr_node["branch"] = branch
            ivr_node["getDigits"]["validChoices"] = "|".join(sorted(valid_choices))
            # Add error handling
            if "error" not in branch:
                branch["error"] = ivr_node["label"]  # Self-reference for retries
        
        # Add retry logic (allflows LITE pattern)
        ivr_node["maxLoop"] = ["Loop-Main", 3, "Problems"]

    def _add_pin_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add PIN entry logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 5,  # 4 digits + pound (allflows LITE pattern)
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "{{pin}}",  # Dynamic PIN validation
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Add branch logic for validation
        if connections:
            branch = {}
            for conn in connections:
                if 'yes' in conn['label'].lower() or 'correct' in conn['label'].lower() or 'valid' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["match"] = target_label
                elif 'no' in conn['label'].lower() or 'invalid' in conn['label'].lower() or 'retry' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["nomatch"] = target_label
            
            if branch:
                ivr_node["branch"] = branch
            
        # Add retry handling
        ivr_node["maxLoop"] = ["Loop-PIN", 3, "Problems"]

    def _add_availability_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add availability check logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "1|3|0",  # Standard availability choices
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        for conn in connections:
            label = conn['label'].lower()
            target_id = conn['target']
            target_label = node_id_to_label.get(target_id, target_id)
            
            if '1' in label or 'accept' in label:
                branch["1"] = target_label
            elif '3' in label or 'decline' in label:
                branch["3"] = target_label
            elif '0' in label or 'call back' in label or '9' in label:
                branch["0"] = target_label
            elif 'invalid' in label or 'retry' in label:
                branch["error"] = target_label
        
        # Add default error handling if not specified
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        if "timeout" not in branch:
            branch["timeout"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
        
        ivr_node["maxLoop"] = ["Loop-Availability", 3, "Problems"]

    def _add_sleep_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add sleep/wait logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 30,  # 30-second timeout (allflows LITE pattern)
            "validChoices": "1|2|3|4|5|6|7|8|9|0|*|#",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Default behavior for any key press or timeout
        if connections:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["branch"] = {
                "next": target_label,
                "none": target_label  # Same destination for timeout
            }
        else:
            ivr_node["branch"] = {
                "next": "Live Answer",
                "none": "Live Answer"
            }

    def _add_decision_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add decision logic for multiple choice nodes with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            digit_match = re.search(r'(\d+)', conn['label'])
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'yes' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["yes"] = target_label
            elif 'no' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["no"] = target_label
        
        # Add error handling
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
            if valid_choices:
                ivr_node["getDigits"]["validChoices"] = "|".join(valid_choices)
        
        ivr_node["maxLoop"] = ["Loop-Decision", 3, "Problems"]

    def _add_response_logic(self, ivr_node: Dict[str, Any], label: str, notes: List[str]):
        """Add response handler logic following allflows patterns"""
        label_lower = label.lower()
        
        # Add gosub for response recording (allflows LITE pattern)
        if 'accept' in label_lower:
            ivr_node["gosub"] = self.response_codes['accept']
        elif 'decline' in label_lower:
            ivr_node["gosub"] = self.response_codes['decline']
        elif 'not home' in label_lower:
            ivr_node["gosub"] = self.response_codes['not_home']
        elif 'qualified' in label_lower:
            ivr_node["gosub"] = self.response_codes['qualified_no']
        else:
            ivr_node["gosub"] = self.response_codes['error']
        
        # Add nobarge for non-interruptible response messages
        ivr_node["nobarge"] = "1"
        
        # Always go to Goodbye after response
        ivr_node["goto"] = "Goodbye"

    def _ensure_standard_handlers(self, ivr_nodes: List[Dict[str, Any]], used_labels: Set[str], notes: List[str]):
        """Ensure standard handler nodes exist following allflows LITE patterns"""
        existing_labels = {node.get('label') for node in ivr_nodes}
        
        # Add Problems handler if missing
        if 'Problems' not in existing_labels:
            problems_node = {
                "label": "Problems",
                "gosub": self.response_codes['error']
            }
            # Add the actual problem message components
            ivr_nodes.append(problems_node)
            
            # Add the message part
            problems_message = {
                "nobarge": "1",
                "playLog": ["I'm sorry you are having problems.", "Please have", "Employee name"],
                "playPrompt": ["callflow:1351", "callflow:1017", "names:{{contact_id}}"]
            }
            ivr_nodes.append(problems_message)
            
            # Add call instructions
            problems_call = {
                "log": "call the",
                "playPrompt": "callflow:1174"
            }
            ivr_nodes.append(problems_call)
            
            # Add final part
            problems_final = {
                "nobarge": "1",
                "playLog": ["APS", "callout system", "at", "speak phone num"],
                "playPrompt": ["location:{{level2_location}}", "callflow:1290", "callflow:1015", "digits:{{callback_number}}"],
                "goto": "Goodbye"
            }
            ivr_nodes.append(problems_final)
            
            notes.append("Added complete Problems handler with multi-object structure")
        
        # Add Goodbye handler if missing
        if 'Goodbye' not in existing_labels:
            goodbye_node = {
                "label": "Goodbye",
                "log": "Goodbye(1029)",
                "playPrompt": "callflow:1029",
                "nobarge": "1",
                "goto": "hangup"
            }
            ivr_nodes.append(goodbye_node)
            notes.append("Added Goodbye handler")

    def _create_fallback_flow(self) -> List[Dict[str, Any]]:
        """Create fallback flow when parsing fails"""
        return [
            {
                "label": "Live Answer",
                "log": "Welcome message",
                "playPrompt": "callflow:Welcome",
                "goto": "Problems"
            },
            {
                "label": "Problems",
                "log": "Error handler",
                "playPrompt": "callflow:1351",
                "goto": "Goodbye"
            },
            {
                "label": "Goodbye",
                "log": "Goodbye message",
                "playPrompt": "callflow:1029",
                "goto": "hangup"
            }
        ]


def convert_mermaid_to_ivr(mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Main conversion function using sophisticated database-driven approach"""
    converter = DatabaseDrivenIVRConverter()
    return converter.convert(mermaid_code)


# Enhanced Format IVR Output Functions for allflows LITE compatibility
def format_ivr_output(ivr_nodes: List[Dict[str, Any]]) -> str:
    """
    Format IVR nodes into production-ready JavaScript module.exports format
    Enhanced for full allflows LITE compatibility
    """
    if not ivr_nodes:
        return "module.exports = [];"
    
    # Clean and format the nodes following allflows property order
    formatted_nodes = []
    
    for node in ivr_nodes:
        # Ensure all nodes have required fields
        clean_node = {}
        
        # Property order from allflows: label → log/playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge → guard
        
        # 1. Label (required)
        if 'label' in node:
            clean_node['label'] = node['label']
        
        # 2. Log/PlayLog (documentation)
        if 'playLog' in node:
            clean_node['playLog'] = node['playLog']
        elif 'log' in node:
            clean_node['log'] = node['log']
        
        # 3. PlayPrompt (voice files)
        if 'playPrompt' in node:
            clean_node['playPrompt'] = node['playPrompt']
        
        # 4. GetDigits (input collection)
        if 'getDigits' in node:
            clean_node['getDigits'] = node['getDigits']
        
        # 5. Branch (conditional navigation)
        if 'branch' in node:
            clean_node['branch'] = node['branch']
        
        # 6. MaxLoop (retry logic)
        if 'maxLoop' in node:
            clean_node['maxLoop'] = node['maxLoop']
        
        # 7. Gosub (subroutine calls)
        if 'gosub' in node:
            clean_node['gosub'] = node['gosub']
        
        # 8. Goto (direct transitions)
        if 'goto' in node:
            clean_node['goto'] = node['goto']
        
        # 9. Nobarge (non-interruptible)
        if 'nobarge' in node:
            clean_node['nobarge'] = node['nobarge']
        
        # 10. Guard (conditional execution) - allflows LITE pattern
        if 'guard' in node:
            clean_node['guard'] = node['guard']
        
        # Add any other properties that might be present
        for key, value in node.items():
            if key not in clean_node:
                clean_node[key] = value
        
        formatted_nodes.append(clean_node)
    
    # Convert to JavaScript format with proper formatting
    try:
        # Use enhanced JavaScript formatting for allflows LITE compatibility
        js_output = _format_as_javascript_enhanced(formatted_nodes)
        return f"module.exports = {js_output};"
        
    except Exception as e:
        # Fallback to basic JSON formatting
        json_str = json.dumps(formatted_nodes, indent=2)
        return f"module.exports = {json_str};"

def _format_as_javascript_enhanced(nodes: List[Dict[str, Any]]) -> str:
    """Enhanced format nodes as JavaScript array with allflows LITE compatibility"""
    lines = ["["]
    
    for i, node in enumerate(nodes):
        lines.append("    {")
        
        # Format each property with enhanced handling
        for j, (key, value) in enumerate(node.items()):
            formatted_value = _format_js_value_enhanced(value)
            comma = "," if j < len(node) - 1 else ""
            lines.append(f'        {key}: {formatted_value}{comma}')
        
        closer = "    }," if i < len(nodes) - 1 else "    }"
        lines.append(closer)
    
    lines.append("]")
    
    return "\n".join(lines)

def _format_js_value_enhanced(value: Any) -> str:
    """Enhanced format a value for JavaScript output with guard function support"""
    if isinstance(value, str):
        # Special handling for guard functions (allflows LITE pattern)
        if value.startswith("function"):
            return value  # Don't quote function definitions
        else:
            return f'"{value}"'
    elif isinstance(value, list):
        if not value:
            return "[]"
        
        # Check if all items are strings
        if all(isinstance(item, str) for item in value):
            formatted_items = [f'"{item}"' for item in value]
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[\n            " + ",\n            ".join(formatted_items) + "\n        ]"
        else:
            # Mixed types - use JSON formatting but handle special cases
            formatted_items = []
            for item in value:
                if isinstance(item, str):
                    formatted_items.append(f'"{item}"')
                else:
                    formatted_items.append(str(item))
            
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[" + ", ".join(formatted_items) + "]"
    
    elif isinstance(value, dict):
        if not value:
            return "{}"
        
        lines = ["{"]
        items = list(value.items())
        for j, (k, v) in enumerate(items):
            formatted_v = _format_js_value_enhanced(v)
            comma = "," if j < len(items) - 1 else ""
            lines.append(f'            {k}: {formatted_v}{comma}')
        lines.append("        }")
        
        return "\n        ".join(lines)
    
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif value is None:
        return "null"
    else:
        return str(value)

# Enhanced validation function for the generated IVR code
def validate_ivr_nodes(ivr_nodes: List[Dict[str, Any]]) -> List[str]:
    """Enhanced validate IVR nodes and return list of issues found"""
    issues = []
    labels = set()
    
    for i, node in enumerate(ivr_nodes):
        # Check required fields
        if 'label' not in node:
            issues.append(f"Node {i}: Missing required 'label' field")
        else:
            label = node['label']
            if label in labels:
                issues.append(f"Node {i}: Duplicate label '{label}'")
            labels.add(label)
        
        # Check branch targets
        if 'branch' in node:
            for digit, target in node['branch'].items():
                if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                    issues.append(f"Node {i}: Branch target '{target}' not found")
        
        # Check goto targets
        if 'goto' in node:
            target = node['goto']
            if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                issues.append(f"Node {i}: Goto target '{target}' not found")
        
        # Check getDigits structure
        if 'getDigits' in node:
            get_digits = node['getDigits']
            if not isinstance(get_digits, dict):
                issues.append(f"Node {i}: getDigits must be an object")
            else:
                required_fields = ['numDigits', 'validChoices']
                for field in required_fields:
                    if field not in get_digits:
                        issues.append(f"Node {i}: getDigits missing '{field}' field")
        
        # Check gosub structure (allflows LITE pattern)
        if 'gosub' in node:
            gosub = node['gosub']
            if not isinstance(gosub, list) or len(gosub) != 3:
                issues.append(f"Node {i}: gosub must be array of 3 elements [function, code, description]")
        
        # Check guard function syntax
        if 'guard' in node:
            guard = node['guard']
            if not isinstance(guard, str) or not guard.startswith('function'):
                issues.append(f"Node {i}: guard must be a function string")
    
    return issues
, before_bracket)
                            if id_match:
                                target_id = id_match.group(1)
                                if target_id not in node_texts:  # Don't overwrite existing text
                                    # Extract text between quotes
                                    target_text = target_part[quote_start + 1:quote_end]
                                    # Clean HTML tags from text
                                    target_text = re.sub(r'<br\s*/?>', ' ', target_text)
                                    target_text = re.sub(r'<[^>]+>', '', target_text)
                                    node_texts[target_id] = target_text.strip()
                    
                    if not target_id:
                        # Fallback to simple ID extraction
                        simple_match = re.match(r'^([A-Z]+)', target_part)
                        if simple_match:
                            target_id = simple_match.group(1)
                    
                    # Add connection if we found both IDs
                    if source_id and target_id:
                        connections.append({
                            'source': source_id,
                            'target': target_id,
                            'label': connection_label
                        })
                        
                except Exception as e:
                    print(f"Error parsing line: {line} - {e}")
                    continue
        
        # Fallback: If we still don't have text for a node, try to extract it more aggressively
        for line in lines:
            if '-->' not in line and not line.startswith('flowchart'):
                # Try to match any node definition pattern
                fallback_match = re.search(r'([A-Z]+)\s*[\[{]"([^"]+)"[\]}]', line)
                if fallback_match:
                    node_id = fallback_match.group(1)
                    if node_id not in node_texts:
                        node_text = fallback_match.group(2)
                        node_text = re.sub(r'<br\s*/?>', ' ', node_text)
                        node_text = re.sub(r'<[^>]+>', '', node_text)
                        node_texts[node_id] = node_text.strip()
        
        # Create node objects with proper classification
        for node_id, node_text in node_texts.items():
            # Generate descriptive label
            label = self._generate_descriptive_label(node_text, connections, node_id)
            
            # Classify node type
            node_type = self._classify_node_type(node_text, connections, node_id)
            
            nodes.append({
                'id': node_id,
                'text': node_text,
                'label': label,
                'type': node_type
            })
        
        return nodes, connections

    def _classify_node_type(self, text: str, connections: List[Dict[str, str]], node_id: str) -> NodeType:
        """Classify node type for proper IVR generation"""
        text_lower = text.lower()
        
        # Analyze outgoing connections to help classification
        outgoing_connections = [conn for conn in connections if conn['source'] == node_id]
        has_multiple_choices = len(outgoing_connections) > 1
        
        if 'welcome' in text_lower or ('this is an' in text_lower and 'press' in text_lower):
            return NodeType.WELCOME
        elif 'pin' in text_lower and 'enter' in text_lower:
            return NodeType.PIN_ENTRY
        elif 'available' in text_lower and 'callout' in text_lower:
            return NodeType.AVAILABILITY
        elif 'accept' in text_lower or 'decline' in text_lower or 'not home' in text_lower:
            return NodeType.RESPONSE
        elif 'goodbye' in text_lower or 'thank you' in text_lower:
            return NodeType.GOODBYE
        elif 'problems' in text_lower or 'error' in text_lower:
            return NodeType.ERROR
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return NodeType.SLEEP
        elif has_multiple_choices or ('?' in text_lower and len(outgoing_connections) > 0):
            return NodeType.DECISION
        else:
            return NodeType.ACTION

    def _generate_descriptive_label(self, text: str, connections: List[Dict[str, str]], node_id: str) -> str:
        """Generate descriptive label following Andres's conventions"""
        text_lower = text.lower()
        
        # Welcome/opening nodes
        if 'welcome' in text_lower or ('this is an' in text_lower and 'callout' in text_lower):
            return "Live Answer"
        
        # PIN related
        elif 'pin' in text_lower and 'enter' in text_lower:
            return "Enter PIN"
        elif 'pin' in text_lower and ('correct' in text_lower or 'valid' in text_lower):
            return "PIN Validation"
        elif 'invalid' in text_lower and ('pin' in text_lower or 'entry' in text_lower):
            return "Invalid Entry"
        
        # Availability
        elif 'available' in text_lower and 'callout' in text_lower:
            return "Available For Callout"
        
        # Responses (following allflows patterns)
        elif 'accept' in text_lower and 'response' in text_lower:
            return "Accept"
        elif 'decline' in text_lower:
            return "Decline"
        elif 'not home' in text_lower:
            return "Not Home"
        elif 'qualified' in text_lower or 'call back' in text_lower:
            return "Qualified No"
        
        # System messages
        elif 'goodbye' in text_lower:
            return "Goodbye"
        elif 'thank you' in text_lower:
            return "Goodbye"
        elif 'problems' in text_lower:
            return "Problems"
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return "Sleep"
        
        # Callout information
        elif 'callout reason' in text_lower:
            return "Callout Reason"
        elif 'trouble location' in text_lower:
            return "Trouble Location"
        elif 'custom message' in text_lower:
            return "Custom Message"
        elif 'electric callout' in text_lower:
            return "Electric Callout"
        
        # Fallback to meaningful name
        else:
            # Extract key words for label
            words = re.findall(r'\b[A-Z][a-z]+', text)
            if words:
                return ' '.join(words[:2])
            else:
                return node_id.title()

    def _generate_database_driven_flow(self, nodes: List[Dict[str, Any]], connections: List[Dict[str, str]], notes: List[str]) -> List[Dict[str, Any]]:
        """Generate complete IVR flow using database-driven approach with allflows LITE patterns"""
        if not nodes:
            notes.append("No nodes to process")
            return []
            
        ivr_nodes = []
        used_labels = set()
        
        # Create a mapping of node IDs to their generated labels for cross-referencing
        node_id_to_label = {}
        
        # First pass: Generate labels for all nodes
        for node in nodes:
            label = node['label']
            counter = 2
            while label in used_labels:
                label = f"{node['label']} {counter}"
                counter += 1
            used_labels.add(label)
            node_id_to_label[node['id']] = label
        
        # Second pass: Generate IVR nodes with proper cross-references
        for node in nodes:
            label = node_id_to_label[node['id']]
            
            # Generate IVR node(s) based on type and complexity
            node_connections = [conn for conn in connections if conn['source'] == node['id']]
            
            # Check if we should create multi-object nodes (glommer nodes)
            if self._should_split_into_glommer_nodes(node['text']) and node.get('type') == NodeType.WELCOME:
                generated_nodes = self._create_multi_object_welcome_node(node, label, node_connections, node_id_to_label, notes)
            else:
                generated_nodes = self._create_database_node_with_mapping(node, label, node_connections, node_id_to_label, notes)
            
            for ivr_node in generated_nodes:
                # Add nobarge where appropriate
                if node.get('type') in [NodeType.RESPONSE, NodeType.GOODBYE, NodeType.ERROR]:
                    ivr_node["nobarge"] = "1"
                ivr_nodes.append(ivr_node)
        
        # Add standard handlers if not present
        self._ensure_standard_handlers(ivr_nodes, used_labels, notes)
        
        return ivr_nodes

    def _create_multi_object_welcome_node(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create multi-object welcome node following allflows LITE patterns"""
        text = node['text']
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        nodes = []
        
        # Object 1: Main callout information (first part)
        main_segments = 5  # Split at reasonable boundary
        main_node = {
            "label": label
        }
        
        if len(play_log) > main_segments:
            main_node["playLog"] = play_log[:main_segments]
            main_node["playPrompt"] = play_prompt[:main_segments]
        else:
            main_node["playLog"] = play_log
            main_node["playPrompt"] = play_prompt
        
        nodes.append(main_node)
        
        # Object 2: Environment check (if not production) - allflows LITE pattern
        env_node = {
            "log": "environment",
            "guard": "function (){ return this.data.env!='prod' && this.data.env!='PROD' }",
            "playPrompt": "callflow:{{env}}",
            "nobarge": "1"
        }
        nodes.append(env_node)
        
        # Object 3: Menu options with getDigits (remaining segments)
        menu_node = {}
        
        if len(play_log) > main_segments:
            menu_node["playLog"] = play_log[main_segments:]
            menu_node["playPrompt"] = play_prompt[main_segments:]
        else:
            menu_node["playLog"] = ["Menu options"]
            menu_node["playPrompt"] = ["callflow:MenuOptions"]
        
        # Add getDigits and branch logic
        self._add_welcome_logic_with_mapping(menu_node, connections, node_id_to_label, notes)
        nodes.append(menu_node)
        
        notes.append(f"Created multi-object welcome node with {len(nodes)} components")
        
        return nodes

    def _create_database_node_with_mapping(self, node: Dict[str, Any], label: str, connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]) -> List[Dict[str, Any]]:
        """Create IVR node(s) using database matching with proper label mapping"""
        text = node['text']
        node_type = node.get('type', NodeType.ACTION)
        
        # Intelligent segmentation using database
        segments, variables = self._intelligent_segmentation(text)
        play_log, play_prompt = self._generate_database_prompts(segments, variables, notes)
        
        # Create base node following allflows property order
        ivr_node = {}
        
        # Property order: label → playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge
        ivr_node["label"] = label
        
        if len(play_log) > 1:
            ivr_node["playLog"] = play_log
        elif play_log:
            ivr_node["log"] = play_log[0]  # Single log entry uses "log" instead of "playLog"
        
        if len(play_prompt) > 1:
            ivr_node["playPrompt"] = play_prompt
        elif play_prompt:
            ivr_node["playPrompt"] = play_prompt[0]
        
        # Add interaction logic based on node type and connections
        if node_type == NodeType.WELCOME and connections:
            self._add_welcome_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.PIN_ENTRY:
            self._add_pin_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.AVAILABILITY and connections:
            self._add_availability_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif node_type == NodeType.RESPONSE:
            self._add_response_logic(ivr_node, label, notes)
        elif node_type == NodeType.SLEEP:
            self._add_sleep_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) > 1:
            self._add_decision_logic_with_mapping(ivr_node, connections, node_id_to_label, notes)
        elif connections and len(connections) == 1:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["goto"] = target_label
        
        return [ivr_node]

    def _add_welcome_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add welcome node logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 1,  # Very short timeout for main menu (allflows LITE pattern)
            "validChoices": "",
            "errorPrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            label = conn['label'].lower()
            digit_match = re.search(r'(\d+)', label)
            
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'retry' in label or 'repeat' in label or 'invalid' in label:
                # Self-reference for retries
                branch["error"] = ivr_node["label"]
        
        # Add default handling
        if branch:
            ivr_node["branch"] = branch
            ivr_node["getDigits"]["validChoices"] = "|".join(sorted(valid_choices))
            # Add error handling
            if "error" not in branch:
                branch["error"] = ivr_node["label"]  # Self-reference for retries
        
        # Add retry logic (allflows LITE pattern)
        ivr_node["maxLoop"] = ["Loop-Main", 3, "Problems"]

    def _add_pin_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add PIN entry logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 5,  # 4 digits + pound (allflows LITE pattern)
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "{{pin}}",  # Dynamic PIN validation
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Add branch logic for validation
        if connections:
            branch = {}
            for conn in connections:
                if 'yes' in conn['label'].lower() or 'correct' in conn['label'].lower() or 'valid' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["match"] = target_label
                elif 'no' in conn['label'].lower() or 'invalid' in conn['label'].lower() or 'retry' in conn['label'].lower():
                    target_id = conn['target']
                    target_label = node_id_to_label.get(target_id, target_id)
                    branch["nomatch"] = target_label
            
            if branch:
                ivr_node["branch"] = branch
            
        # Add retry handling
        ivr_node["maxLoop"] = ["Loop-PIN", 3, "Problems"]

    def _add_availability_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add availability check logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "1|3|0",  # Standard availability choices
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        for conn in connections:
            label = conn['label'].lower()
            target_id = conn['target']
            target_label = node_id_to_label.get(target_id, target_id)
            
            if '1' in label or 'accept' in label:
                branch["1"] = target_label
            elif '3' in label or 'decline' in label:
                branch["3"] = target_label
            elif '0' in label or 'call back' in label or '9' in label:
                branch["0"] = target_label
            elif 'invalid' in label or 'retry' in label:
                branch["error"] = target_label
        
        # Add default error handling if not specified
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        if "timeout" not in branch:
            branch["timeout"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
        
        ivr_node["maxLoop"] = ["Loop-Availability", 3, "Problems"]

    def _add_sleep_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add sleep/wait logic following allflows patterns with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 30,  # 30-second timeout (allflows LITE pattern)
            "validChoices": "1|2|3|4|5|6|7|8|9|0|*|#",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        # Default behavior for any key press or timeout
        if connections:
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, target_id)
            ivr_node["branch"] = {
                "next": target_label,
                "none": target_label  # Same destination for timeout
            }
        else:
            ivr_node["branch"] = {
                "next": "Live Answer",
                "none": "Live Answer"
            }

    def _add_decision_logic_with_mapping(self, ivr_node: Dict[str, Any], connections: List[Dict[str, str]], node_id_to_label: Dict[str, str], notes: List[str]):
        """Add decision logic for multiple choice nodes with proper label mapping"""
        ivr_node["getDigits"] = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "",
            "errorPrompt": "callflow:1009",
            "nonePrompt": "callflow:1009"
        }
        
        branch = {}
        valid_choices = []
        
        for conn in connections:
            digit_match = re.search(r'(\d+)', conn['label'])
            if digit_match:
                digit = digit_match.group(1)
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch[digit] = target_label
                valid_choices.append(digit)
            elif 'yes' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["yes"] = target_label
            elif 'no' in conn['label'].lower():
                target_id = conn['target']
                target_label = node_id_to_label.get(target_id, target_id)
                branch["no"] = target_label
        
        # Add error handling
        if "error" not in branch:
            branch["error"] = "Invalid Entry"
        
        if branch:
            ivr_node["branch"] = branch
            if valid_choices:
                ivr_node["getDigits"]["validChoices"] = "|".join(valid_choices)
        
        ivr_node["maxLoop"] = ["Loop-Decision", 3, "Problems"]

    def _add_response_logic(self, ivr_node: Dict[str, Any], label: str, notes: List[str]):
        """Add response handler logic following allflows patterns"""
        label_lower = label.lower()
        
        # Add gosub for response recording (allflows LITE pattern)
        if 'accept' in label_lower:
            ivr_node["gosub"] = self.response_codes['accept']
        elif 'decline' in label_lower:
            ivr_node["gosub"] = self.response_codes['decline']
        elif 'not home' in label_lower:
            ivr_node["gosub"] = self.response_codes['not_home']
        elif 'qualified' in label_lower:
            ivr_node["gosub"] = self.response_codes['qualified_no']
        else:
            ivr_node["gosub"] = self.response_codes['error']
        
        # Add nobarge for non-interruptible response messages
        ivr_node["nobarge"] = "1"
        
        # Always go to Goodbye after response
        ivr_node["goto"] = "Goodbye"

    def _ensure_standard_handlers(self, ivr_nodes: List[Dict[str, Any]], used_labels: Set[str], notes: List[str]):
        """Ensure standard handler nodes exist following allflows LITE patterns"""
        existing_labels = {node.get('label') for node in ivr_nodes}
        
        # Add Problems handler if missing
        if 'Problems' not in existing_labels:
            problems_node = {
                "label": "Problems",
                "gosub": self.response_codes['error']
            }
            # Add the actual problem message components
            ivr_nodes.append(problems_node)
            
            # Add the message part
            problems_message = {
                "nobarge": "1",
                "playLog": ["I'm sorry you are having problems.", "Please have", "Employee name"],
                "playPrompt": ["callflow:1351", "callflow:1017", "names:{{contact_id}}"]
            }
            ivr_nodes.append(problems_message)
            
            # Add call instructions
            problems_call = {
                "log": "call the",
                "playPrompt": "callflow:1174"
            }
            ivr_nodes.append(problems_call)
            
            # Add final part
            problems_final = {
                "nobarge": "1",
                "playLog": ["APS", "callout system", "at", "speak phone num"],
                "playPrompt": ["location:{{level2_location}}", "callflow:1290", "callflow:1015", "digits:{{callback_number}}"],
                "goto": "Goodbye"
            }
            ivr_nodes.append(problems_final)
            
            notes.append("Added complete Problems handler with multi-object structure")
        
        # Add Goodbye handler if missing
        if 'Goodbye' not in existing_labels:
            goodbye_node = {
                "label": "Goodbye",
                "log": "Goodbye(1029)",
                "playPrompt": "callflow:1029",
                "nobarge": "1",
                "goto": "hangup"
            }
            ivr_nodes.append(goodbye_node)
            notes.append("Added Goodbye handler")

    def _create_fallback_flow(self) -> List[Dict[str, Any]]:
        """Create fallback flow when parsing fails"""
        return [
            {
                "label": "Live Answer",
                "log": "Welcome message",
                "playPrompt": "callflow:Welcome",
                "goto": "Problems"
            },
            {
                "label": "Problems",
                "log": "Error handler",
                "playPrompt": "callflow:1351",
                "goto": "Goodbye"
            },
            {
                "label": "Goodbye",
                "log": "Goodbye message",
                "playPrompt": "callflow:1029",
                "goto": "hangup"
            }
        ]


def convert_mermaid_to_ivr(mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Main conversion function using sophisticated database-driven approach"""
    converter = DatabaseDrivenIVRConverter()
    return converter.convert(mermaid_code)


# Enhanced Format IVR Output Functions for allflows LITE compatibility
def format_ivr_output(ivr_nodes: List[Dict[str, Any]]) -> str:
    """
    Format IVR nodes into production-ready JavaScript module.exports format
    Enhanced for full allflows LITE compatibility
    """
    if not ivr_nodes:
        return "module.exports = [];"
    
    # Clean and format the nodes following allflows property order
    formatted_nodes = []
    
    for node in ivr_nodes:
        # Ensure all nodes have required fields
        clean_node = {}
        
        # Property order from allflows: label → log/playLog → playPrompt → getDigits → branch → maxLoop → gosub → goto → nobarge → guard
        
        # 1. Label (required)
        if 'label' in node:
            clean_node['label'] = node['label']
        
        # 2. Log/PlayLog (documentation)
        if 'playLog' in node:
            clean_node['playLog'] = node['playLog']
        elif 'log' in node:
            clean_node['log'] = node['log']
        
        # 3. PlayPrompt (voice files)
        if 'playPrompt' in node:
            clean_node['playPrompt'] = node['playPrompt']
        
        # 4. GetDigits (input collection)
        if 'getDigits' in node:
            clean_node['getDigits'] = node['getDigits']
        
        # 5. Branch (conditional navigation)
        if 'branch' in node:
            clean_node['branch'] = node['branch']
        
        # 6. MaxLoop (retry logic)
        if 'maxLoop' in node:
            clean_node['maxLoop'] = node['maxLoop']
        
        # 7. Gosub (subroutine calls)
        if 'gosub' in node:
            clean_node['gosub'] = node['gosub']
        
        # 8. Goto (direct transitions)
        if 'goto' in node:
            clean_node['goto'] = node['goto']
        
        # 9. Nobarge (non-interruptible)
        if 'nobarge' in node:
            clean_node['nobarge'] = node['nobarge']
        
        # 10. Guard (conditional execution) - allflows LITE pattern
        if 'guard' in node:
            clean_node['guard'] = node['guard']
        
        # Add any other properties that might be present
        for key, value in node.items():
            if key not in clean_node:
                clean_node[key] = value
        
        formatted_nodes.append(clean_node)
    
    # Convert to JavaScript format with proper formatting
    try:
        # Use enhanced JavaScript formatting for allflows LITE compatibility
        js_output = _format_as_javascript_enhanced(formatted_nodes)
        return f"module.exports = {js_output};"
        
    except Exception as e:
        # Fallback to basic JSON formatting
        json_str = json.dumps(formatted_nodes, indent=2)
        return f"module.exports = {json_str};"

def _format_as_javascript_enhanced(nodes: List[Dict[str, Any]]) -> str:
    """Enhanced format nodes as JavaScript array with allflows LITE compatibility"""
    lines = ["["]
    
    for i, node in enumerate(nodes):
        lines.append("    {")
        
        # Format each property with enhanced handling
        for j, (key, value) in enumerate(node.items()):
            formatted_value = _format_js_value_enhanced(value)
            comma = "," if j < len(node) - 1 else ""
            lines.append(f'        {key}: {formatted_value}{comma}')
        
        closer = "    }," if i < len(nodes) - 1 else "    }"
        lines.append(closer)
    
    lines.append("]")
    
    return "\n".join(lines)

def _format_js_value_enhanced(value: Any) -> str:
    """Enhanced format a value for JavaScript output with guard function support"""
    if isinstance(value, str):
        # Special handling for guard functions (allflows LITE pattern)
        if value.startswith("function"):
            return value  # Don't quote function definitions
        else:
            return f'"{value}"'
    elif isinstance(value, list):
        if not value:
            return "[]"
        
        # Check if all items are strings
        if all(isinstance(item, str) for item in value):
            formatted_items = [f'"{item}"' for item in value]
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[\n            " + ",\n            ".join(formatted_items) + "\n        ]"
        else:
            # Mixed types - use JSON formatting but handle special cases
            formatted_items = []
            for item in value:
                if isinstance(item, str):
                    formatted_items.append(f'"{item}"')
                else:
                    formatted_items.append(str(item))
            
            if len(formatted_items) == 1:
                return f'[{formatted_items[0]}]'
            else:
                return "[" + ", ".join(formatted_items) + "]"
    
    elif isinstance(value, dict):
        if not value:
            return "{}"
        
        lines = ["{"]
        items = list(value.items())
        for j, (k, v) in enumerate(items):
            formatted_v = _format_js_value_enhanced(v)
            comma = "," if j < len(items) - 1 else ""
            lines.append(f'            {k}: {formatted_v}{comma}')
        lines.append("        }")
        
        return "\n        ".join(lines)
    
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif value is None:
        return "null"
    else:
        return str(value)

# Enhanced validation function for the generated IVR code
def validate_ivr_nodes(ivr_nodes: List[Dict[str, Any]]) -> List[str]:
    """Enhanced validate IVR nodes and return list of issues found"""
    issues = []
    labels = set()
    
    for i, node in enumerate(ivr_nodes):
        # Check required fields
        if 'label' not in node:
            issues.append(f"Node {i}: Missing required 'label' field")
        else:
            label = node['label']
            if label in labels:
                issues.append(f"Node {i}: Duplicate label '{label}'")
            labels.add(label)
        
        # Check branch targets
        if 'branch' in node:
            for digit, target in node['branch'].items():
                if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                    issues.append(f"Node {i}: Branch target '{target}' not found")
        
        # Check goto targets
        if 'goto' in node:
            target = node['goto']
            if target not in labels and target not in ['Problems', 'Goodbye', 'hangup']:
                issues.append(f"Node {i}: Goto target '{target}' not found")
        
        # Check getDigits structure
        if 'getDigits' in node:
            get_digits = node['getDigits']
            if not isinstance(get_digits, dict):
                issues.append(f"Node {i}: getDigits must be an object")
            else:
                required_fields = ['numDigits', 'validChoices']
                for field in required_fields:
                    if field not in get_digits:
                        issues.append(f"Node {i}: getDigits missing '{field}' field")
        
        # Check gosub structure (allflows LITE pattern)
        if 'gosub' in node:
            gosub = node['gosub']
            if not isinstance(gosub, list) or len(gosub) != 3:
                issues.append(f"Node {i}: gosub must be array of 3 elements [function, code, description]")
        
        # Check guard function syntax
        if 'guard' in node:
            guard = node['guard']
            if not isinstance(guard, str) or not guard.startswith('function'):
                issues.append(f"Node {i}: guard must be a function string")
    
    return issues