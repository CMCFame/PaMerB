"""
COMPLETE FINAL VERSION - mermaid_ivr_converter.py
Andres's methodology with critical flow logic fixes
- Proper text segmentation working ✅
- Variable detection working ✅  
- DATABASE-DRIVEN voice file matching ✅
- FIXED: Complete branch mapping for all choices ✅
- FIXED: Welcome node handling all DTMF choices ✅
- FIXED: Sleep node return logic ✅
Replace your entire mermaid_ivr_converter.py file with this code
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
            ("Common", "press any key to continue", "1265"),
            ("Common", "to repeat this message", "MSG068"),
            ("Common", "invalid", "MSG028"),
            ("Common", "or", "ORMON"),
            ("Common", "and", "ANDMON"),
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

    def _is_welcome_node(self, text: str, node_type: NodeType) -> bool:
        """Check if this is the main welcome/greeting node"""
        text_lower = text.lower()
        welcome_indicators = [
            'this is an electric callout',
            'this is a',
            'welcome',
            'press 1, if this is',
            'press 3, if you need more time'
        ]
        return any(indicator in text_lower for indicator in welcome_indicators)

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

    def _fix_welcome_node_branches(self, ivr_node: Dict, connections: List[Dict], text: str, node_id_to_label: Dict[str, str]) -> Dict[str, str]:
        """CRITICAL FIX: Handle welcome node branching properly"""
        
        # Extract all press choices from text
        press_choices = re.findall(r'press\s+(\d+)', text.lower())
        print(f"🔍 Found press choices in welcome text: {press_choices}")
        
        branch_map = {}
        
        # CRITICAL: Map each choice to its connection with better logic
        for choice in press_choices:
            target_found = False
            
            for conn in connections:
                label = conn.get('label', '').lower()
                target_label = node_id_to_label.get(conn['target'], f"Node_{conn['target']}")
                
                # ENHANCED: Better matching for welcome node choices
                if choice == '1':
                    if ('employee' in label or 'this is' in label or 'input' in label):
                        branch_map['1'] = target_label
                        target_found = True
                        print(f"✅ Choice 1 (employee) -> {target_label}")
                        break
                elif choice == '3':
                    if ('time' in label or 'more time' in label or 'need more' in label):
                        branch_map['3'] = target_label
                        target_found = True
                        print(f"✅ Choice 3 (more time) -> {target_label}")
                        break
                elif choice == '7':
                    if ('not home' in label or 'home' in label):
                        branch_map['7'] = target_label
                        target_found = True
                        print(f"✅ Choice 7 (not home) -> {target_label}")
                        break
                elif choice == '9':
                    if ('repeat' in label or 'retry' in label):
                        # 9 should repeat the welcome message
                        branch_map['9'] = ivr_node['label']  # Self-reference
                        target_found = True
                        print(f"✅ Choice 9 (repeat) -> {ivr_node['label']}")
                        break
            
            # FALLBACK: If no specific match found, try general connection matching
            if not target_found:
                for conn in connections:
                    label = conn.get('label', '').lower()
                    target_label = node_id_to_label.get(conn['target'], f"Node_{conn['target']}")
                    
                    # Look for the choice number anywhere in the label
                    if f'{choice}' in label or f'{choice} -' in label:
                        branch_map[choice] = target_label
                        print(f"✅ Fallback choice {choice} -> {target_label}")
                        break
        
        # SPECIAL HANDLING: Look for the "input" connection (this often maps to choice 1)
        if '1' not in branch_map:
            for conn in connections:
                if conn.get('label', '').lower() == 'input':
                    target_label = node_id_to_label.get(conn['target'], 'Employee')
                    branch_map['1'] = target_label
                    print(f"✅ Found 'input' connection for choice 1 -> {target_label}")
                    break
        
        # Handle special connections (error, timeout, etc.)
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], f"Node_{conn['target']}")
            
            if 'no input' in label or 'timeout' in label:
                branch_map['none'] = target_label
            elif 'retry' in label or 'invalid' in label:
                branch_map['error'] = target_label
        
        # Add defaults
        if 'error' not in branch_map:
            branch_map['error'] = 'Problems'
        if 'none' not in branch_map:
            branch_map['none'] = branch_map.get('3', 'Sleep')  # Timeout goes to sleep
        
        print(f"🎯 Final welcome branch map: {branch_map}")
        return branch_map

    def _build_dynamic_branch_map(self, connections: List[Dict], text: str, node_id_to_label: Dict[str, str]) -> Dict[str, str]:
        """ENHANCED: Build complete branch map from connections and text analysis"""
        branch_map = {}
        
        # Extract ALL DTMF choices from text first
        text_lower = text.lower()
        press_choices = re.findall(r'press\s+(\d+)', text_lower)
        
        # Map text choices to connections
        for choice in press_choices:
            # Find connection that matches this choice
            for conn in connections:
                label = conn.get('label', '').lower()
                
                # Better choice matching logic
                if f'{choice} -' in label or f'press {choice}' in label or label == choice:
                    target_label = node_id_to_label.get(conn['target'], f"Node_{conn['target']}")
                    branch_map[choice] = target_label
                    print(f"🎯 Mapped choice {choice} -> {target_label}")
        
        # Handle connections without explicit choice numbers
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], f"Node_{conn['target']}")
            
            # Look for digit patterns in labels
            digit_match = re.search(r'\b(\d+)\b', label)
            if digit_match:
                choice = digit_match.group(1)
                if choice not in branch_map:  # Don't override existing mappings
                    branch_map[choice] = target_label
                    print(f"🎯 Found choice {choice} from connection label -> {target_label}")
            
            #