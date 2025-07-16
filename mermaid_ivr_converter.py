"""
COMPLETE ENHANCED VERSION
"""

import re
import csv
import json
import requests
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

class ProductionIVRConverter:
    def __init__(self, uploaded_csv_file=None):
        # Real voice file database (8,555 entries)
        self.voice_files: List[VoiceFile] = []
        self.transcript_index: Dict[str, List[VoiceFile]] = {}
        self.exact_match_index: Dict[str, VoiceFile] = {}
        self.keyword_index: Dict[str, List[VoiceFile]] = {}
        
        # Load the database - either from uploaded file or fallback
        if uploaded_csv_file:
            self._load_database_from_upload(uploaded_csv_file)
        else:
            self._load_real_database()

    def _load_database_from_upload(self, uploaded_file):
        """Load database from uploaded cf_general_structure.csv file"""
        try:
            print(f"📥 Loading database from uploaded file: {uploaded_file.name}")
            
            # Read the uploaded CSV file
            import io
            content = uploaded_file.read()
            
            # Handle both bytes and string content
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # Debug: Check column names
            fieldnames = csv_reader.fieldnames
            print(f"📋 CSV columns found: {fieldnames}")
            
            row_count = 0
            
            for row in csv_reader:
                row_count += 1
                
                # Extract callflow ID from file name (remove .ulaw extension)
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
                
                # ENHANCED: Build better indexes
                transcript_clean = voice_file.transcript.lower().strip()
                if transcript_clean:
                    # Exact match index
                    self.exact_match_index[transcript_clean] = voice_file
                    
                    # Word-based index
                    words = re.findall(r'\b\w+\b', transcript_clean)
                    for word in words:
                        if word not in self.transcript_index:
                            self.transcript_index[word] = []
                        self.transcript_index[word].append(voice_file)
                    
                    # Keyword phrase index
                    self._build_keyword_index(transcript_clean, voice_file)
            
            print(f"✅ Successfully loaded {row_count} voice files from uploaded CSV")
            print(f"📊 Built indexes: {len(self.exact_match_index)} exact matches, {len(self.keyword_index)} keyword phrases")
            
        except Exception as e:
            print(f"❌ Error loading database: {e}")
            self._load_fallback_database()

    def _build_keyword_index(self, transcript: str, voice_file: VoiceFile):
        """Build enhanced keyword index for better matching"""
        
        # Common IVR phrases to index
        patterns = [
            r'enter.*pin.*pound',
            r'invalid.*entry',
            r'try.*again',
            r'press.*1',
            r'press.*3',
            r'press.*9',
            r'thank.*you',
            r'goodbye',
            r'welcome',
            r'pin.*changed',
            r'name.*recorded',
            r'first.*time',
            r'correct.*press',
            r'pound.*key',
            r'four.*digit',
            r'successfully',
            r'cannot.*be',
            r'recorded.*as',
            r'confirmation',
        ]
        
        for pattern in patterns:
            if re.search(pattern, transcript):
                if pattern not in self.keyword_index:
                    self.keyword_index[pattern] = []
                self.keyword_index[pattern].append(voice_file)

    def _load_real_database(self):
        """Load fallback database with common phrases"""
        fallback_data = [
            ("Welcome", "This is an automated callout", "1186"),
            ("Press", "Press", "PRESSNEU"),
            ("PIN Entry", "Please enter your four digit PIN followed by the pound key", "1008"),
            ("Invalid", "I'm sorry. That is an invalid entry. Please try again.", "1009"),
            ("Thank you", "Thank you.", "MSG023"),
            ("Goodbye", "Goodbye.", "1029"),
            ("PIN Changed", "Your PIN has been changed successfully.", "1167"),
            ("Name Recorded", "Your name has been recorded.", "1200"),
            ("Available", "All available.", "1111"),
            ("Error", "I'm sorry you are having problems.", "1351"),
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
            self._build_keyword_index(transcript.lower(), voice_file)

    def _load_fallback_database(self):
        """Load minimal fallback when CSV fails"""
        self._load_real_database()

    def _search_voice_database_enhanced(self, text_segment: str) -> Optional[str]:
        """ENHANCED: Much better database search with multiple strategies"""
        
        if not text_segment or len(text_segment.strip()) < 3:
            return None
            
        text_clean = text_segment.lower().strip()
        
        # 1. EXACT MATCH FIRST
        if text_clean in self.exact_match_index:
            voice_file = self.exact_match_index[text_clean]
            print(f"🎯 Exact match: '{text_segment}' -> callflow:{voice_file.callflow_id}")
            return f"callflow:{voice_file.callflow_id}"
        
        # 2. ENHANCED PATTERN MATCHING - Map common IVR patterns to known voice files
        pattern_mappings = {
            # PIN related
            r'enter.*pin.*pound.*key': '1008',
            r'please.*enter.*four.*digit.*pin': '1008', 
            r'new.*pin.*enter.*four.*digit': '1008',
            r're.?enter.*pin.*four.*digit': '1008',
            r'invalid.*entry.*try.*again': '1009',
            r'pin.*changed.*successfully': '1167',
            r'pin.*cannot.*be.*1234': '1351',
            r'your.*pin.*cannot.*1234': '1351',
            
            # Name recording
            r'first.*time.*users.*spoken.*name': '1200',
            r'name.*has.*been.*recorded.*as': '1201',
            r'name.*confirmation.*recorded': '1201',
            r'name.*changed.*successfully': '1202',
            r'employee.*information': '1203',
            
            # Standard responses  
            r'thank.*you.*goodbye': '1029',
            r'goodbye': '1029',
            r'press.*1.*correct': '1316',
            r'press.*3.*re.*record': '1316',
            r'if.*correct.*press.*1': '1316',
            
            # Confirmations
            r'correct.*press.*1': '1316',
            r'to.*re.*record.*press.*3': '1316',
            r'selection': '1320',
            r'valid.*digits': '1330',
        }
        
        for pattern, callflow_id in pattern_mappings.items():
            if re.search(pattern, text_clean):
                print(f"🎯 Pattern match: '{text_segment}' -> callflow:{callflow_id}")
                return f"callflow:{callflow_id}"
        
        # 3. KEYWORD PHRASE MATCHING
        for keyword_pattern, voice_files in self.keyword_index.items():
            if re.search(keyword_pattern, text_clean):
                best_file = voice_files[0]  # Take first match
                print(f"🔍 Keyword match: '{keyword_pattern}' -> callflow:{best_file.callflow_id}")
                return f"callflow:{best_file.callflow_id}"
        
        # 4. SINGLE KEYWORD MATCHING
        keyword_mappings = {
            'invalid': '1009',
            'goodbye': '1029', 
            'thank you': '1029',
            'welcome': '1186',
            'pin': '1008',
            'pound key': '1008',
            'press 1': 'PRS1DWN',
            'press 3': 'PRS3DWN',
            'successfully': '1167',
            'confirmation': '1201',
            'selection': '1320',
        }
        
        for keyword, callflow_id in keyword_mappings.items():
            if keyword in text_clean:
                print(f"🔍 Keyword match: '{keyword}' -> callflow:{callflow_id}")
                return f"callflow:{callflow_id}"
        
        # 5. FUZZY MATCHING for close matches
        best_match = None
        best_score = 0.0
        
        for transcript, voice_file in self.exact_match_index.items():
            if len(transcript) > 10:  # Only check longer transcripts
                similarity = SequenceMatcher(None, text_clean, transcript).ratio()
                if similarity > 0.8 and similarity > best_score:
                    best_score = similarity
                    best_match = voice_file
        
        if best_match:
            print(f"🎯 Fuzzy match ({best_score:.2f}): '{text_segment}' -> callflow:{best_match.callflow_id}")
            return f"callflow:{best_match.callflow_id}"
        
        # 6. FALLBACK: Mark as needed
        print(f"⚠️ No database match for: '{text_segment}' - voice file needed")
        return None

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
        
        # Extract connections with improved parsing
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
        """Determine node type from text content"""
        text_lower = text.lower()
        
        # Welcome nodes
        if any(phrase in text_lower for phrase in ["welcome", "this is an", "this is a", "automated"]):
            return NodeType.WELCOME
        
        # PIN entry nodes
        if any(phrase in text_lower for phrase in ["pin", "enter", "digits", "pound key"]) and not "invalid" in text_lower:
            return NodeType.PIN_ENTRY
        
        # Availability questions
        if "available" in text_lower and any(phrase in text_lower for phrase in ["work", "callout", "press 1", "press 3"]):
            return NodeType.AVAILABILITY
        
        # Response/action nodes
        if any(phrase in text_lower for phrase in ["accepted", "decline", "response", "recorded", "changed successfully"]):
            return NodeType.RESPONSE
        
        # Goodbye/disconnect nodes
        if any(phrase in text_lower for phrase in ["goodbye", "thank you", "disconnect"]):
            return NodeType.GOODBYE
        
        # Error/problem nodes
        if any(phrase in text_lower for phrase in ["invalid", "error", "problem", "try again"]):
            return NodeType.ERROR
        
        # Sleep/wait nodes
        if any(phrase in text_lower for phrase in ["more time", "continue", "press any key"]):
            return NodeType.SLEEP
        
        # Decision nodes - contain questions or comparisons
        if any(phrase in text_lower for phrase in ["?", "=", "yes", "no", "correct", "match"]) or len(text.split()) <= 5:
            return NodeType.DECISION
        
        # Default to action
        return NodeType.ACTION

    def _generate_meaningful_label(self, node_text: str, node_type: NodeType, node_id: str, all_nodes: List[Dict] = None) -> str:
        """ENHANCED: Generate meaningful labels with better parsing"""
        
        if node_text:
            text_lower = node_text.lower()
            
            # ENHANCED: Better PIN-related labels
            if "pin not 1234" in text_lower or "cannot be 1234" in text_lower:
                return "PIN Not 1234"
            elif "new pin" in text_lower and "enter" in text_lower:
                return "Enter New PIN"
            elif "re-enter" in text_lower and "pin" in text_lower:
                return "Re-enter PIN"
            elif "pin changed" in text_lower and "successfully" in text_lower:
                return "PIN Changed"
            elif "pin = 1234" in text_lower:
                return "Check PIN 1234"
            elif "match to first entry" in text_lower:
                return "Match PIN"
                
            # Name recording
            elif "first time users" in text_lower or "spoken name" in text_lower:
                return "Record Name"
            elif "name confirmation" in text_lower or "name has been recorded" in text_lower:
                return "Name Confirmation"
            elif "name changed" in text_lower and "successfully" in text_lower:
                return "Name Changed"
            elif "employee information" in text_lower:
                return "Employee Information"
            elif "name recorded previously" in text_lower:
                return "Check Name Exists"
                
            # Decision logic
            elif "valid digits" in text_lower:
                return "Validate Digits"
            elif node_text.strip() == "Selection":
                return "Process Selection"
            elif node_text.strip().lower() == "yes":
                return "Confirm Yes"
            elif "entered digits" in text_lower:
                return "Check Digits"
                
            # Standard nodes
            elif "invalid entry" in text_lower:
                return "Invalid Entry"
            elif "goodbye" in text_lower:
                return "Goodbye"
            elif "welcome" in text_lower:
                return "Welcome"
            
            # ENHANCED: Better fallback parsing
            # Remove common IVR words and focus on key content
            cleaned_text = re.sub(r'\b(please|press|enter|the|your|a|an|is|has|been|to|for|if|this)\b', ' ', text_lower)
            words = [w for w in cleaned_text.split() if len(w) > 2]
            
            if words:
                if len(words) <= 3:
                    return ' '.join(word.capitalize() for word in words)
                else:
                    # Take first 2-3 meaningful words
                    key_words = words[:3]
                    return ' '.join(word.capitalize() for word in key_words)
        
        # Last resort: Use node type and ID
        return f"{node_type.value.replace('_', ' ').title()}_{node_id}"

    def _create_ivr_node(self, node: Dict, connections: List[Dict], label: str, node_id_to_label: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """ENHANCED: Create proper IVR nodes with real voice files and logic"""
        text = node['text']
        node_type = node['type']
        
        # Create base node
        ivr_node = {'label': label}
        ivr_node['log'] = text.replace('\n', ' ').strip()
        
        # ENHANCED: Better playPrompt generation using real database
        voice_file = self._search_voice_database_enhanced(text)
        if voice_file:
            ivr_node['playPrompt'] = voice_file
        else:
            # Fallback: try to use a reasonable default based on node type
            fallback_prompts = {
                NodeType.PIN_ENTRY: 'callflow:1008',
                NodeType.ERROR: 'callflow:1009', 
                NodeType.GOODBYE: 'callflow:1029',
                NodeType.RESPONSE: 'callflow:1167',
            }
            
            if node_type in fallback_prompts:
                ivr_node['playPrompt'] = fallback_prompts[node_type]
                print(f"📝 Using fallback prompt for {label}: {fallback_prompts[node_type]}")
            else:
                # Last resort: use node ID but mark as needed
                ivr_node['playPrompt'] = f"callflow:{node['id']}"
                print(f"⚠️ Voice file needed for: {text[:50]}...")
        
        # ENHANCED: Add proper getDigits for PIN entry nodes
        if node_type == NodeType.PIN_ENTRY or ("pin" in text.lower() and "enter" in text.lower()):
            ivr_node['getDigits'] = {
                'numDigits': 5,  # 4 digits + pound
                'maxTries': 3,
                'maxTime': 10,   # Longer for PIN entry
                'validChoices': '{{new_pin}}' if 'new' in text.lower() else '{{pin}}',
                'errorPrompt': 'callflow:1009',
                'nonePrompt': 'callflow:1009'
            }
            
            # ENHANCED: Better PIN validation branching
            if connections:
                branch_map = {}
                for conn in connections:
                    target_label = node_id_to_label.get(conn['target'], 'Unknown')
                    label_text = conn.get('label', '').lower()
                    
                    if 'digits' in label_text or 'entered' in label_text:
                        # This connection handles the PIN processing
                        ivr_node['goto'] = target_label
                        return [ivr_node]
                
                # Default error handling
                ivr_node['branch'] = {
                    'error': 'Invalid Entry',
                    'none': 'Invalid Entry'
                }
        
        # ENHANCED: Add proper getDigits for confirmation nodes
        elif ("correct" in text.lower() and "press 1" in text.lower()) or ("name confirmation" in label.lower()):
            ivr_node['getDigits'] = {
                'numDigits': 1,
                'maxTries': 3,
                'maxTime': 7,
                'validChoices': '1|3',
                'errorPrompt': 'callflow:1009',
                'nonePrompt': 'callflow:1009'
            }
            
            # Find connections for press 1 and press 3
            branch_map = {}
            for conn in connections:
                target_label = node_id_to_label.get(conn['target'], 'Unknown')
                label_text = conn.get('label', '').lower()
                
                if 'entered digits' in label_text or 'retry logic' in label_text:
                    # This is the main processing path
                    ivr_node['goto'] = target_label
                    return [ivr_node]
            
            # Default confirmation branches
            ivr_node['branch'] = {
                '1': 'Name Changed',    # Confirmed
                '3': 'Record Name',     # Re-record  
                'error': 'Invalid Entry',
                'none': 'Invalid Entry'
            }
        
        # Handle response nodes (PIN Changed, Name Changed, etc.)
        elif node_type == NodeType.RESPONSE:
            if "changed successfully" in text.lower():
                # These are completion messages, not response recordings
                if connections and len(connections) == 1:
                    target_label = node_id_to_label.get(connections[0]['target'], 'Goodbye')
                    ivr_node['goto'] = target_label
                else:
                    ivr_node['goto'] = 'Goodbye'
                return [ivr_node]
            else:
                return self._create_response_nodes(ivr_node, label, connections, node_id_to_label)
        
        # Handle decision nodes - should have branch logic
        elif node_type == NodeType.DECISION:
            self._add_decision_logic_enhanced(ivr_node, connections, node, node_id_to_label)
        
        # Handle error nodes
        elif node_type == NodeType.ERROR:
            self._add_error_retry_logic(ivr_node, connections, node_id_to_label)
        
        # Single connection goto (only if no other logic)
        elif len(connections) == 1 and not ivr_node.get('branch') and not ivr_node.get('getDigits'):
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, self._generate_meaningful_label("", NodeType.ACTION, target_id))
            ivr_node['goto'] = target_label

        return [ivr_node]

    def _add_decision_logic_enhanced(self, ivr_node: Dict, connections: List[Dict], node: Dict, node_id_to_label: Dict[str, str]):
        """ENHANCED: Add proper decision logic with better branching"""
        
        text_lower = node['text'].lower()
        
        if "pin = 1234" in text_lower:
            # PIN validation check - system handles this automatically
            yes_target = None
            no_target = None
            
            for conn in connections:
                label = conn.get('label', '').lower()
                target_label = node_id_to_label.get(conn['target'], 'Unknown')
                
                if 'yes' in label:
                    yes_target = target_label  # Invalid PIN (1234)
                elif 'no' in label:
                    no_target = target_label   # Valid PIN (not 1234)
            
            # System branches based on PIN validation
            if yes_target and no_target:
                ivr_node['branch'] = {
                    'pin_1234': yes_target,    # If PIN is 1234 (invalid)
                    'pin_valid': no_target     # If PIN is not 1234 (valid)
                }
            elif connections:
                # Fallback to first connection
                ivr_node['goto'] = node_id_to_label.get(connections[0]['target'], 'Unknown')
                
        elif "match to first entry" in text_lower or "match" in text_lower:
            # PIN confirmation check
            for conn in connections:
                target_label = node_id_to_label.get(conn['target'], 'Unknown')
                # Assume first connection is success path
                ivr_node['goto'] = target_label
                break
                
        elif "name recorded previously" in text_lower:
            # Check if user has recorded name before
            yes_target = None
            no_target = None
            
            for conn in connections:
                label = conn.get('label', '').lower()
                target_label = node_id_to_label.get(conn['target'], 'Unknown')
                
                if 'yes' in label:
                    yes_target = target_label
                elif 'no' in label:
                    no_target = target_label
            
            if yes_target and no_target:
                ivr_node['branch'] = {
                    'has_name': yes_target,
                    'no_name': no_target
                }
            elif connections:
                ivr_node['goto'] = node_id_to_label.get(connections[0]['target'], 'Unknown')
                
        elif "valid digits" in text_lower:
            # Digit validation check
            for conn in connections:
                label = conn.get('label', '').lower() 
                target_label = node_id_to_label.get(conn['target'], 'Unknown')
                
                if 'no' in label:
                    ivr_node['branch'] = {'invalid': target_label}
                elif 'yes' in label:
                    if 'branch' not in ivr_node:
                        ivr_node['branch'] = {}
                    ivr_node['branch']['valid'] = target_label
                    
        elif text_lower.strip() == "selection":
            # Menu selection processing
            branch_map = {}
            for conn in connections:
                label = conn.get('label', '').lower()
                target_label = node_id_to_label.get(conn['target'], 'Unknown')
                
                if 'one' in label:
                    branch_map['1'] = target_label
                elif 'three' in label:
                    branch_map['3'] = target_label
            
            if branch_map:
                ivr_node['branch'] = branch_map
            elif connections:
                ivr_node['goto'] = node_id_to_label.get(connections[0]['target'], 'Unknown')
                
        else:
            # Generic decision - use first connection as default
            if connections:
                target_label = node_id_to_label.get(connections[0]['target'], 'Unknown')
                ivr_node['goto'] = target_label

    def _add_error_retry_logic(self, ivr_node: Dict, connections: List[Dict], node_id_to_label: Dict[str, str]):
        """Add proper retry logic for error nodes"""
        
        # Error nodes should return to appropriate points in the flow
        retry_targets = []
        
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'Unknown')
            
            if 'retry' in label:
                retry_targets.append(target_label)
        
        if retry_targets:
            # If multiple retry targets, use the first one
            ivr_node['goto'] = retry_targets[0]
        elif connections:
            # Default to first connection
            ivr_node['goto'] = node_id_to_label.get(connections[0]['target'], 'Unknown')
        else:
            # No connections - dead end error
            ivr_node['goto'] = 'Problems'

    def _create_response_nodes(self, base_node: Dict, label: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> List[Dict]:
        """Create proper response node structure like allflows LITE"""
        nodes = []
        
        # First node: gosub only
        gosub_node = {'label': label}
        
        label_lower = label.lower()
        if 'accept' in label_lower:
            gosub_node['gosub'] = ['SaveCallResult', 1001, 'Accept']
        elif 'decline' in label_lower:
            gosub_node['gosub'] = ['SaveCallResult', 1002, 'Decline']
        elif 'not home' in label_lower:
            gosub_node['gosub'] = ['SaveCallResult', 1006, 'NotHome']
        elif 'qualified' in label_lower:
            gosub_node['gosub'] = ['SaveCallResult', 1145, 'QualNo']
        
        nodes.append(gosub_node)
        
        # Second node: message and goto
        message_node = {
            'label': f"{label} Message",
            'log': base_node['log'],
            'playPrompt': base_node['playPrompt'],
            'nobarge': '1',
            'goto': 'Goodbye'
        }
        nodes.append(message_node)
        
        return nodes

    def convert_mermaid_to_ivr(self, mermaid_code: str, uploaded_csv_file=None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Main conversion method - ENHANCED WITH BETTER DATABASE SEARCH"""
        notes = []
        
        try:
            print(f"🚀 Starting conversion of Mermaid diagram...")
            print(f"📝 Input length: {len(mermaid_code)} characters")
            
            # Parse Mermaid diagram
            nodes, connections = self._parse_mermaid_diagram(mermaid_code)
            notes.append(f"Parsed {len(nodes)} nodes and {len(connections)} connections")
            
            if not nodes:
                notes.append("❌ No nodes found in diagram - check Mermaid syntax")
                print("❌ PARSING FAILED - No nodes extracted")
                return self._create_fallback_flow(), notes
            
            print(f"✅ Successfully parsed {len(nodes)} nodes")
            
            # Create a mapping of node IDs to meaningful labels
            node_id_to_label = {}
            used_labels = set()
            
            for node in nodes:
                base_label = self._generate_meaningful_label(node['text'], node['type'], node['id'], nodes)
                
                # Handle duplicate labels by adding suffix
                final_label = base_label
                counter = 1
                while final_label in used_labels:
                    final_label = f"{base_label} {counter}"
                    counter += 1
                
                node_id_to_label[node['id']] = final_label
                used_labels.add(final_label)
                print(f"🏷️ {node['id']} -> '{final_label}' ({node['type'].value})")
            
            # Generate IVR nodes with meaningful labels
            ivr_nodes = []
            
            for node in nodes:
                print(f"\n🔄 Processing node {node['id']}: {node['text'][:50]}...")
                
                # Get the meaningful label
                label = node_id_to_label[node['id']]
                
                # Get connections for this node
                node_connections = [c for c in connections if c['source'] == node['id']]
                print(f"🔗 Found {len(node_connections)} outgoing connections")
                
                # Create IVR node(s) - can return multiple nodes for responses
                created_nodes = self._create_ivr_node(node, node_connections, label, node_id_to_label)
                
                # Add all created nodes with safety check
                for created_node in created_nodes:
                    # Ensure every node has a label before adding
                    if 'label' not in created_node:
                        print(f"⚠️ WARNING: Node missing label, adding fallback: {created_node}")
                        created_node['label'] = f"Node_{len(ivr_nodes)}"
                    
                    ivr_nodes.append(created_node)
                    notes.append(f"Generated node: {created_node['label']}")
                    print(f"✅ Generated IVR node: {created_node['label']}")
            
            # ENHANCED: Better standard nodes
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
            
            # ENHANCED: Add voice file statistics
            voice_files_found = sum(1 for node in ivr_nodes if node.get('playPrompt', '').startswith('callflow:') and not node['playPrompt'].endswith(('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T')))
            voice_files_needed = len(ivr_nodes) - voice_files_found
            
            notes.append(f"✅ Generated {len(ivr_nodes)} production-ready IVR nodes")
            notes.append(f"📊 Voice files: {voice_files_found} found in database, {voice_files_needed} need recording")
            print(f"🎉 CONVERSION SUCCESSFUL - Generated {len(ivr_nodes)} nodes")
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
    """Production-ready conversion function with enhanced database search"""
    converter = ProductionIVRConverter(uploaded_csv_file)
    return converter.convert_mermaid_to_ivr(mermaid_code)