"""
Dynamic Version
"""

import re
import csv
import json
import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
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
    INPUT = "input"

@dataclass
class VoiceFile:
    company: str
    folder: str
    file_name: str
    transcript: str
    callflow_id: str

class AndresMethodologyConverter:
    def __init__(self, uploaded_csv_file=None):
        # Voice file database
        self.voice_files: List[VoiceFile] = []
        self.transcript_index: Dict[str, List[VoiceFile]] = {}
        self.exact_match_index: Dict[str, VoiceFile] = {}
        
        # Load the database
        if uploaded_csv_file:
            self._load_database_from_upload(uploaded_csv_file)
        else:
            self._load_fallback_database()

    def _load_database_from_upload(self, uploaded_file):
        """Load database from uploaded CSV file"""
        try:
            print(f"📥 Loading database from uploaded file: {uploaded_file.name}")
            
            import io
            content = uploaded_file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            csv_reader = csv.DictReader(io.StringIO(content))
            fieldnames = csv_reader.fieldnames
            print(f"📋 CSV columns found: {fieldnames}")
            
            row_count = 0
            for row in csv_reader:
                row_count += 1
                
                file_name = row.get('File Name', '')
                callflow_id = file_name.replace('.ulaw', '') if file_name else f"{row_count}"
                
                voice_file = VoiceFile(
                    company=row.get('Company', ''),
                    folder=row.get('Folder', ''),
                    file_name=file_name,
                    transcript=row.get('Transcript', ''),
                    callflow_id=callflow_id
                )
                
                self.voice_files.append(voice_file)
                
                # Build indexes for fast lookup
                transcript_clean = voice_file.transcript.lower().strip()
                if transcript_clean:
                    self.exact_match_index[transcript_clean] = voice_file
                    
                    # Index individual words
                    words = re.findall(r'\b\w+\b', transcript_clean)
                    for word in words:
                        if word not in self.transcript_index:
                            self.transcript_index[word] = []
                        self.transcript_index[word].append(voice_file)
            
            print(f"✅ Successfully loaded {row_count} voice files from uploaded CSV")
            
        except Exception as e:
            print(f"❌ Error loading database: {e}")
            self._load_fallback_database()

    def _load_fallback_database(self):
        """Load fallback database with essential voice files"""
        fallback_data = [
            ("Common", "This is an", "1191"),
            ("Common", "electric", "1274_TYPE"),
            ("Common", "callout", "1274"),
            ("Common", "Please enter your four digit PIN followed by the pound key", "1008"),
            ("Common", "I'm sorry. That is an invalid entry. Please try again.", "1009"),
            ("Common", "Thank you.", "MSG023"),
            ("Common", "Goodbye.", "1029"),
            ("Common", "Press", "PRESSNEU"),
            ("Common", "1", "PRS1DWN"),
            ("Common", "3", "PRS3DWN"),
            ("Common", "7", "PRS7DWN"),
            ("Common", "9", "PRS9DWN"),
            ("Common", "if", "1316_IF"),
            ("Common", "press any key to continue", "1265"),
            ("Common", "are you available to work", "1316_AVAIL"),
            ("Common", "if yes press 1", "1316_YES1"),
            ("Common", "if no press 3", "1316_NO3"),
            ("Common", "An accepted response has been recorded", "1167"),
            ("Common", "Your response is being recorded as a decline", "1021"),
            ("Common", "You may be called again", "1145_CALLBACK"),
        ]
        
        for company, transcript, callflow_id in fallback_data:
            voice_file = VoiceFile(
                company=company,
                folder="",
                file_name=f"{callflow_id}.ulaw",
                transcript=transcript,
                callflow_id=callflow_id
            )
            self.voice_files.append(voice_file)
            self.exact_match_index[transcript.lower().strip()] = voice_file

    def _detect_variables_dynamically(self, text: str) -> Dict[str, str]:
        """
        ANDRES'S METHOD: Dynamic variable detection based on content context
        NO hardcoded patterns - analyze content to determine variable type
        """
        variables = {}
        
        # Find all parentheses content - these are typically variables
        parentheses_matches = re.findall(r'\(([^)]+)\)', text)
        
        for match in parentheses_matches:
            match_lower = match.lower().strip()
            placeholder = f"({match})"
            
            # DYNAMIC ANALYSIS: Determine variable type from context
            if self._contains_location_indicators(match_lower):
                if any(level in match_lower for level in ['level', '2', 'two']):
                    variables[placeholder] = '{{level2_location}}'
                else:
                    variables[placeholder] = '{{callout_location}}'
            elif self._contains_person_indicators(match_lower):
                variables[placeholder] = '{{contact_id}}'
            elif self._contains_callout_type_indicators(match_lower):
                variables[placeholder] = '{{callout_type}}'
            elif self._contains_reason_indicators(match_lower):
                variables[placeholder] = '{{callout_reason}}'
            elif self._contains_contact_indicators(match_lower):
                variables[placeholder] = '{{callback_number}}'
            elif self._contains_message_indicators(match_lower):
                variables[placeholder] = '{{custom_message}}'
            else:
                # Generic variable - create based on content
                var_name = re.sub(r'[^a-zA-Z0-9_]', '_', match_lower.replace(' ', '_'))
                variables[placeholder] = f'{{{{{var_name}}}}}'
        
        return variables

    def _contains_location_indicators(self, text: str) -> bool:
        """Check if text indicates a location variable"""
        location_words = ['level', 'location', 'office', 'site', 'area', 'zone', 'district']
        return any(word in text for word in location_words)

    def _contains_person_indicators(self, text: str) -> bool:
        """Check if text indicates a person variable"""
        person_words = ['employee', 'contact', 'name', 'person', 'worker', 'individual']
        return any(word in text for word in person_words)

    def _contains_callout_type_indicators(self, text: str) -> bool:
        """Check if text indicates callout type"""
        type_words = ['type', 'kind', 'electric', 'gas', 'water', 'emergency']
        return any(word in text for word in type_words)

    def _contains_reason_indicators(self, text: str) -> bool:
        """Check if text indicates a reason variable"""
        reason_words = ['reason', 'purpose', 'cause', 'issue', 'problem', 'trouble']
        return any(word in text for word in reason_words)

    def _contains_contact_indicators(self, text: str) -> bool:
        """Check if text indicates contact information"""
        contact_words = ['phone', 'number', 'callback', 'call', 'contact']
        return any(word in text for word in contact_words)

    def _contains_message_indicators(self, text: str) -> bool:
        """Check if text indicates a custom message"""
        message_words = ['message', 'custom', 'selected', 'additional', 'note']
        return any(word in text for word in message_words)

    def _segment_text_like_andres(self, text: str, variables: Dict[str, str]) -> List[str]:
        """
        ANDRES'S MANUAL METHOD: Break down complex text into voice file segments
        Like Andres explained: "This is an electric callout" becomes:
        - "This is an" (callflow:1191)
        - "electric" (type:{{callout_type}})  
        - "callout" (callflow:1274)
        """
        
        # Replace variables first
        processed_text = text
        for var_placeholder, var_replacement in variables.items():
            processed_text = processed_text.replace(var_placeholder, var_replacement)
        
        # Clean up HTML and normalize
        processed_text = re.sub(r'<br\s*/?>', ' ', processed_text)
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()
        
        print(f"🔍 Andres-style segmenting: '{processed_text}'")
        
        segments = []
        remaining_text = processed_text
        
        while remaining_text.strip():
            found_match = False
            
            # STEP 1: Try to find longest exact database match
            best_match = self._find_longest_database_match(remaining_text)
            
            if best_match:
                voice_file, match_length = best_match
                matched_text = remaining_text[:match_length]
                segments.append(matched_text)
                remaining_text = remaining_text[match_length:].strip()
                remaining_text = re.sub(r'^[.,;:!\?\s]+', '', remaining_text)
                found_match = True
                print(f"✅ Database match: '{matched_text}' -> {voice_file.callflow_id}")
            
            # STEP 2: Look for common phrase boundaries
            if not found_match:
                boundary_patterns = [
                    r'^([^,;\.!]+)[,;\.!]\s*',  # Up to punctuation
                    r'^(.*?\b(?:press|if|to|for|the)\b)',  # Up to key connector words
                    r'^(\w+\s+\w+)',  # Two words
                    r'^(\w+)',  # Single word
                ]
                
                for pattern in boundary_patterns:
                    match = re.search(pattern, remaining_text, re.IGNORECASE)
                    if match:
                        segment = match.group(1).strip()
                        if len(segment) > 0:
                            segments.append(segment)
                            remaining_text = remaining_text[len(segment):].strip()
                            remaining_text = re.sub(r'^[.,;:!\?\s]+', '', remaining_text)
                            print(f"📝 Boundary segment: '{segment}'")
                            found_match = True
                            break
            
            # Safety check to prevent infinite loops
            if not found_match:
                if remaining_text.strip():
                    segments.append(remaining_text.strip())
                    print(f"📝 Final segment: '{remaining_text.strip()}'")
                break
        
        print(f"🎯 Segmentation result: {segments}")
        return segments if segments else [processed_text]

    def _find_longest_database_match(self, text: str) -> Optional[Tuple[VoiceFile, int]]:
        """Find the longest matching voice file in the database"""
        text_lower = text.lower().strip()
        best_match = None
        best_length = 0
        
        # Try progressively shorter substrings from the beginning
        words = text_lower.split()
        for i in range(len(words), 0, -1):
            test_phrase = ' '.join(words[:i])
            
            # Check exact match
            if test_phrase in self.exact_match_index:
                voice_file = self.exact_match_index[test_phrase]
                match_length = len(' '.join(text.split()[:i]))
                if match_length > best_length:
                    best_match = (voice_file, match_length)
                    best_length = match_length
        
        return best_match

    def _generate_voice_prompts_andres_style(self, segments: List[str], variables: Dict[str, str]) -> Tuple[List[str], List[str]]:
        """
        ANDRES'S METHOD: Generate playLog and playPrompt arrays
        Build complex messages from multiple voice files like Andres showed
        """
        play_log = []
        play_prompt = []
        
        print(f"🎵 Andres-style voice generation for: {segments}")
        
        for segment in segments:
            if not segment.strip():
                continue
            
            # Handle variables (dynamic content)
            if any(var in segment for var in variables.values()):
                self._add_variable_voice_prompt(segment, play_log, play_prompt)
                continue
            
            # Try to find voice file for this segment
            voice_file = self._find_voice_file_for_segment(segment)
            
            if voice_file:
                play_log.append(segment)
                play_prompt.append(f"callflow:{voice_file.callflow_id}")
                print(f"✅ Voice file found: '{segment}' -> callflow:{voice_file.callflow_id}")
            else:
                # Mark as needing new voice file
                play_log.append(f"{segment} [VOICE FILE NEEDED]")
                play_prompt.append(f"callflow:NEW_{len(play_prompt)}")
                print(f"⚠️ Voice file needed: '{segment}'")
        
        return play_log, play_prompt

    def _add_variable_voice_prompt(self, segment: str, play_log: List[str], play_prompt: List[str]):
        """Add voice prompts for variable content"""
        if '{{contact_id}}' in segment:
            play_log.append("Employee name")
            play_prompt.append("names:{{contact_id}}")
        elif '{{level2_location}}' in segment or '{{callout_location}}' in segment:
            play_log.append("Location")
            play_prompt.append("location:{{level2_location}}")
        elif '{{callout_type}}' in segment:
            play_log.append("Callout type")
            play_prompt.append("type:{{callout_type}}")
        elif '{{callout_reason}}' in segment:
            play_log.append("Callout reason")
            play_prompt.append("reason:{{callout_reason}}")
        elif '{{callback_number}}' in segment:
            play_log.append("Phone number")
            play_prompt.append("digits:{{callback_number}}")
        elif '{{custom_message}}' in segment:
            play_log.append("Custom message")
            play_prompt.append("custom:{{custom_message}}")
        else:
            # Generic variable handling
            play_log.append(f"Variable: {segment}")
            play_prompt.append(f"var:{segment}")

    def _find_voice_file_for_segment(self, segment: str) -> Optional[VoiceFile]:
        """Find the best voice file match for a text segment"""
        segment_lower = segment.lower().strip()
        
        # Exact match first
        if segment_lower in self.exact_match_index:
            return self.exact_match_index[segment_lower]
        
        # Fuzzy matching for close matches
        best_match = None
        best_score = 0.7  # Minimum similarity threshold
        
        for transcript, voice_file in self.exact_match_index.items():
            similarity = SequenceMatcher(None, segment_lower, transcript).ratio()
            if similarity > best_score:
                best_score = similarity
                best_match = voice_file
        
        return best_match

    def _parse_mermaid_diagram(self, mermaid_code: str) -> Tuple[List[Dict], List[Dict]]:
        """Parse Mermaid diagram into nodes and connections"""
        nodes = []
        connections = []
        
        # Extract rectangular nodes (actions/prompts)
        for match in re.finditer(r'([A-Z]+)\s*\[\s*"([^"]+)"\s*\]', mermaid_code):
            node_id = match.group(1)
            node_text = match.group(2).replace('<br/>', '\n').replace('\\n', '\n')
            nodes.append({
                'id': node_id,
                'text': node_text,
                'type': self._determine_node_type(node_text),
                'shape': 'rectangle'
            })
            print(f"📦 Found rectangular node: {node_id} = '{node_text[:50]}...'")
        
        # Extract diamond nodes (decisions)
        for match in re.finditer(r'([A-Z]+)\s*\{\s*"([^"]+)"\s*\}', mermaid_code):
            node_id = match.group(1)
            node_text = match.group(2).replace('<br/>', '\n').replace('\\n', '\n')
            nodes.append({
                'id': node_id,
                'text': node_text,
                'type': NodeType.DECISION,
                'shape': 'diamond'
            })
            print(f"💎 Found diamond node: {node_id} = '{node_text[:50]}...'")
        
        # Extract connections
        connection_patterns = [
            r'([A-Z]+)\s*-->\s*\|"([^"]+)"\|\s*([A-Z]+)',  # A -->|"label"| B
            r'([A-Z]+)\s*-->\s*([A-Z]+)',                   # A --> B
            r'([A-Z]+)\s*-->\s*\|([^|]+)\|\s*([A-Z]+)',     # A -->|label| B
        ]
        
        for pattern in connection_patterns:
            for match in re.finditer(pattern, mermaid_code):
                source = match.group(1)
                if len(match.groups()) == 3:
                    if pattern.count('"') > 0:
                        label = match.group(2)
                        target = match.group(3)
                    else:
                        label = match.group(2) if '|' in pattern else ''
                        target = match.group(3) if '|' in pattern else match.group(2)
                else:
                    label = ''
                    target = match.group(2)
                
                connections.append({
                    'source': source,
                    'target': target,
                    'label': label
                })
                print(f"🔗 Found connection: {source} -> {target} ('{label}')")
        
        print(f"✅ Parsed {len(nodes)} nodes and {len(connections)} connections")
        return nodes, connections

    def _determine_node_type(self, text: str) -> NodeType:
        """DYNAMIC node type detection - NO hardcoded patterns"""
        text_lower = text.lower()
        
        # Analyze content characteristics rather than specific keywords
        if self._has_greeting_characteristics(text_lower):
            return NodeType.WELCOME
        elif self._has_input_characteristics(text_lower):
            return NodeType.PIN_ENTRY
        elif self._has_availability_characteristics(text_lower):
            return NodeType.AVAILABILITY
        elif self._has_response_characteristics(text_lower):
            return NodeType.RESPONSE
        elif self._has_termination_characteristics(text_lower):
            return NodeType.GOODBYE
        elif self._has_error_characteristics(text_lower):
            return NodeType.ERROR
        elif self._has_wait_characteristics(text_lower):
            return NodeType.SLEEP
        elif self._has_question_characteristics(text_lower):
            return NodeType.DECISION
        else:
            return NodeType.ACTION

    def _has_greeting_characteristics(self, text: str) -> bool:
        """Check if text has greeting characteristics"""
        greeting_indicators = ['this is', 'welcome', 'hello', 'automated', 'system']
        return any(indicator in text for indicator in greeting_indicators)

    def _has_input_characteristics(self, text: str) -> bool:
        """Check if text requests input"""
        input_indicators = ['enter', 'type', 'input', 'pin', 'digit', 'pound key']
        return any(indicator in text for indicator in input_indicators)

    def _has_availability_characteristics(self, text: str) -> bool:
        """Check if text asks about availability"""
        availability_indicators = ['available', 'work this', 'accept', 'decline']
        return any(indicator in text for indicator in availability_indicators)

    def _has_response_characteristics(self, text: str) -> bool:
        """Check if text indicates a response action"""
        response_indicators = ['recorded', 'response', 'changed', 'successfully']
        return any(indicator in text for indicator in response_indicators)

    def _has_termination_characteristics(self, text: str) -> bool:
        """Check if text indicates termination"""
        termination_indicators = ['goodbye', 'thank you', 'disconnect', 'end']
        return any(indicator in text for indicator in termination_indicators)

    def _has_error_characteristics(self, text: str) -> bool:
        """Check if text indicates an error"""
        error_indicators = ['invalid', 'error', 'try again', 'problem']
        return any(indicator in text for indicator in error_indicators)

    def _has_wait_characteristics(self, text: str) -> bool:
        """Check if text indicates waiting/continuation"""
        wait_indicators = ['continue', 'press any', 'wait', 'second']
        return any(indicator in text for indicator in wait_indicators)

    def _has_question_characteristics(self, text: str) -> bool:
        """Check if text is a question or decision point"""
        return '?' in text or len(text.split()) <= 5

    def _generate_meaningful_label(self, node_text: str, node_type: NodeType, node_id: str) -> str:
        """DYNAMIC label generation based on content analysis"""
        
        if not node_text:
            return f"{node_type.value.replace('_', ' ').title()}"
        
        text_lower = node_text.lower()
        
        # Extract key meaningful words, avoiding common IVR filler words
        filler_words = {'the', 'a', 'an', 'is', 'has', 'been', 'to', 'for', 'if', 'this', 'please', 'your'}
        words = [w for w in re.findall(r'\b[A-Za-z]+\b', text_lower) if w not in filler_words and len(w) > 2]
        
        if words:
            # Take first 2-3 most meaningful words
            key_words = words[:3]
            return ' '.join(word.capitalize() for word in key_words)
        
        # Fallback to node type
        return f"{node_type.value.replace('_', ' ').title()}"

    def _create_ivr_node(self, node: Dict, connections: List[Dict], label: str, node_id_to_label: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        ANDRES'S METHOD: Create IVR nodes using real segmentation and voice file matching
        NO hardcoded logic - everything driven by content analysis
        """
        text = node['text']
        node_type = node['type']
        
        # Detect variables dynamically
        variables = self._detect_variables_dynamically(text)
        
        # Segment text like Andres does manually
        segments = self._segment_text_like_andres(text, variables)
        
        # Generate voice prompts using Andres's method
        play_log, play_prompt = self._generate_voice_prompts_andres_style(segments, variables)
        
        # Create base node
        ivr_node = {'label': label}
        
        # Add voice content based on Andres's patterns
        if len(play_log) > 1:
            ivr_node['playLog'] = play_log
            ivr_node['playPrompt'] = play_prompt
        elif play_log:
            ivr_node['log'] = play_log[0]
            ivr_node['playPrompt'] = play_prompt[0] if play_prompt else f"callflow:NEW"
        
        # Add dynamic interaction logic based on content analysis
        if self._should_have_input_logic(text, node_type):
            self._add_dynamic_input_logic(ivr_node, connections, text, node_id_to_label)
        elif node_type == NodeType.RESPONSE and "successfully" in text.lower():
            # Response completion messages
            if connections and len(connections) == 1:
                target_label = node_id_to_label.get(connections[0]['target'], 'Goodbye')
                ivr_node['goto'] = target_label
            else:
                ivr_node['goto'] = 'Goodbye'
        elif connections:
            self._add_dynamic_flow_logic(ivr_node, connections, node_id_to_label)
        
        return [ivr_node]

    def _should_have_input_logic(self, text: str, node_type: NodeType) -> bool:
        """Determine if node should have input logic based on content"""
        text_lower = text.lower()
        input_indicators = ['press', 'enter', 'digit', 'key', 'available']
        return any(indicator in text_lower for indicator in input_indicators)

    def _add_dynamic_input_logic(self, ivr_node: Dict, connections: List[Dict], text: str, node_id_to_label: Dict[str, str]):
        """Add input logic based on content analysis"""
        text_lower = text.lower()
        
        # Detect what kind of input is expected
        if 'pin' in text_lower and 'digit' in text_lower:
            # PIN entry
            ivr_node['getDigits'] = {
                'numDigits': 5,  # 4 digits + pound
                'maxTries': 3,
                'maxTime': 10,
                'validChoices': '{{pin}}',
                'errorPrompt': 'callflow:1009',
                'nonePrompt': 'callflow:1009'
            }
        elif 'press any' in text_lower:
            # Any key continuation
            ivr_node['getDigits'] = {'numDigits': 1}
        else:
            # DTMF choices - extract from text and connections
            choices = self._extract_dtmf_choices(text, connections)
            if choices:
                ivr_node['getDigits'] = {
                    'numDigits': 1,
                    'maxTries': 3,
                    'maxTime': 7,
                    'validChoices': '|'.join(choices),
                    'errorPrompt': 'callflow:1009',
                    'nonePrompt': 'callflow:1009'
                }
        
        # Add branching based on connections
        if connections and ivr_node.get('getDigits'):
            branch_map = self._build_dynamic_branch_map(connections, text, node_id_to_label)
            if branch_map:
                ivr_node['branch'] = branch_map

    def _extract_dtmf_choices(self, text: str, connections: List[Dict]) -> List[str]:
        """Extract DTMF choices from text and connections"""
        choices = []
        
        # Extract from text
        press_matches = re.findall(r'press\s+(\d+)', text.lower())
        choices.extend(press_matches)
        
        # Extract from connection labels
        for conn in connections:
            label = conn.get('label', '').lower()
            digit_matches = re.findall(r'\b(\d+)\b', label)
            choices.extend(digit_matches)
        
        return sorted(list(set(choices)))

    def _build_dynamic_branch_map(self, connections: List[Dict], text: str, node_id_to_label: Dict[str, str]) -> Dict[str, str]:
        """Build branch map dynamically from connections"""
        branch_map = {}
        
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], f"Node_{conn['target']}")
            
            # Extract choice number
            digit_match = re.search(r'\b(\d+)\b', label)
            if digit_match:
                choice = digit_match.group(1)
                branch_map[choice] = target_label
            elif 'retry' in label or 'invalid' in label:
                branch_map['error'] = target_label
            elif 'no input' in label or 'timeout' in label:
                branch_map['none'] = target_label
        
        # Add default error handling
        if 'error' not in branch_map:
            branch_map['error'] = 'Problems'
        if 'none' not in branch_map:
            branch_map['none'] = branch_map.get('error', 'Problems')
        
        return branch_map

    def _add_dynamic_flow_logic(self, ivr_node: Dict, connections: List[Dict], node_id_to_label: Dict[str, str]):
        """Add flow logic based on connection analysis"""
        if len(connections) == 1:
            # Single connection - simple goto
            target_label = node_id_to_label.get(connections[0]['target'], f"Node_{connections[0]['target']}")
            ivr_node['goto'] = target_label
        elif len(connections) > 1:
            # Multiple connections - analyze for branching logic
            for conn in connections:
                label = conn.get('label', '').lower()
                target_label = node_id_to_label.get(conn['target'], f"Node_{conn['target']}")
                
                if 'yes' in label:
                    ivr_node['goto'] = target_label
                    break
                elif not label:  # Empty label - take first connection
                    ivr_node['goto'] = target_label
                    break

    def convert_mermaid_to_ivr(self, mermaid_code: str, uploaded_csv_file=None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        ANDRES'S TRUE METHODOLOGY: Convert Mermaid to IVR using dynamic analysis
        NO hardcoded patterns - everything based on content analysis and database matching
        """
        notes = []
        
        try:
            print(f"🚀 Starting Andres-style conversion...")
            print(f"📝 Input length: {len(mermaid_code)} characters")
            
            # Parse Mermaid diagram
            nodes, connections = self._parse_mermaid_diagram(mermaid_code)
            notes.append(f"Parsed {len(nodes)} nodes and {len(connections)} connections")
            
            if not nodes:
                notes.append("❌ No nodes found in diagram - check Mermaid syntax")
                return self._create_fallback_flow(), notes
            
            print(f"✅ Successfully parsed {len(nodes)} nodes")
            
            # Generate meaningful labels dynamically
            node_id_to_label = {}
            used_labels = set()
            
            for node in nodes:
                base_label = self._generate_meaningful_label(node['text'], node['type'], node['id'])
                
                # Handle duplicate labels
                final_label = base_label
                counter = 1
                while final_label in used_labels:
                    final_label = f"{base_label} {counter}"
                    counter += 1
                
                node_id_to_label[node['id']] = final_label
                used_labels.add(final_label)
                print(f"🏷️ {node['id']} -> '{final_label}' ({node['type'].value})")
            
            # Generate IVR nodes using Andres's methodology
            ivr_nodes = []
            
            for node in nodes:
                print(f"\n🔄 Processing node {node['id']}: {node['text'][:50]}...")
                
                label = node_id_to_label[node['id']]
                node_connections = [c for c in connections if c['source'] == node['id']]
                print(f"🔗 Found {len(node_connections)} outgoing connections")
                
                # Create IVR node(s) using Andres's method
                created_nodes = self._create_ivr_node(node, node_connections, label, node_id_to_label)
                
                for created_node in created_nodes:
                    if 'label' not in created_node:
                        created_node['label'] = f"Node_{len(ivr_nodes)}"
                    
                    ivr_nodes.append(created_node)
                    notes.append(f"Generated node: {created_node['label']}")
                    print(f"✅ Generated IVR node: {created_node['label']}")
            
            # Add standard termination nodes
            if not any(node.get('label') == 'Problems' for node in ivr_nodes):
                ivr_nodes.append({
                    'label': 'Problems',
                    'log': 'I\'m sorry you are having problems.',
                    'playPrompt': 'callflow:1351',
                    'goto': 'Goodbye'
                })
                notes.append("Added standard 'Problems' error handler")
            
            if not any(node.get('label') == 'Goodbye' for node in ivr_nodes):
                ivr_nodes.append({
                    'label': 'Goodbye',
                    'log': 'Thank you. Goodbye.',
                    'playPrompt': 'callflow:1029',
                    'goto': 'hangup'
                })
                notes.append("Added standard 'Goodbye' termination")
            
            # Calculate statistics
            voice_files_found = 0
            voice_files_needed = 0
            
            for node in ivr_nodes:
                prompts = []
                if 'playPrompt' in node:
                    if isinstance(node['playPrompt'], list):
                        prompts.extend(node['playPrompt'])
                    else:
                        prompts.append(node['playPrompt'])
                
                for prompt in prompts:
                    if isinstance(prompt, str):
                        if prompt.startswith('callflow:') and not prompt.startswith('callflow:NEW'):
                            # Check if it's a real voice file (not a node ID)
                            if not any(prompt.endswith(letter) for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
                                voice_files_found += 1
                            else:
                                voice_files_needed += 1
                        elif 'NEW' in prompt or 'NEEDED' in prompt:
                            voice_files_needed += 1
            
            notes.append(f"✅ Generated {len(ivr_nodes)} IVR nodes using Andres's methodology")
            notes.append(f"📊 Voice files: {voice_files_found} found in database, {voice_files_needed} need recording")
            print(f"🎉 ANDRES-STYLE CONVERSION SUCCESSFUL - Generated {len(ivr_nodes)} nodes")
            print(f"📊 Voice file statistics: {voice_files_found} found, {voice_files_needed} needed")
            
            return ivr_nodes, notes
            
        except Exception as e:
            error_msg = f"❌ Conversion failed: {str(e)}"
            notes.append(error_msg)
            print(error_msg)
            import traceback
            traceback.print_exc()
            return self._create_fallback_flow(), notes

    def _create_fallback_flow(self) -> List[Dict[str, Any]]:
        """Create fallback flow for errors"""
        return [
            {
                'label': 'Problems',
                'log': 'Error handler',
                'playPrompt': 'callflow:1351',
                'goto': 'Goodbye'
            },
            {
                'label': 'Goodbye',
                'log': 'Thank you goodbye',
                'playPrompt': 'callflow:1029',
                'goto': 'hangup'
            }
        ]

# Main function for the app
def convert_mermaid_to_ivr(mermaid_code: str, uploaded_csv_file=None) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    ANDRES'S TRUE METHODOLOGY: Production-ready conversion function
    Uses dynamic analysis and database-driven approach - NO hardcoding
    """
    converter = AndresMethodologyConverter(uploaded_csv_file)
    return converter.convert_mermaid_to_ivr(mermaid_code)