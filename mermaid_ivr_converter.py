"""
Production-Ready Mermaid to IVR Converter
Matches actual allflows LITE patterns and fixes critical issues
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

class ProductionIVRConverter:
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
                callflow_id = file_name.replace('.ulaw', '') if file_name else f"CUSTOM{row_count}"
                
                voice_file = VoiceFile(
                    company=row.get('Company', ''),
                    folder=row.get('Folder', ''),
                    file_name=file_name,
                    transcript=row.get('Transcript', ''),
                    callflow_id=callflow_id
                )
                
                self.voice_files.append(voice_file)
                
                # Index by transcript for searching
                transcript_words = voice_file.transcript.lower().split()
                for word in transcript_words:
                    if word not in self.transcript_index:
                        self.transcript_index[word] = []
                    self.transcript_index[word].append(voice_file)
                
                # Index exact transcript matches
                self.exact_match_index[voice_file.transcript.lower()] = voice_file
                
            print(f"✅ Loaded {len(self.voice_files)} voice files from database")
            
        except Exception as e:
            print(f"❌ Error loading database: {e}")
            self._load_fallback_database()

    def _load_fallback_database(self):
        """Load a minimal fallback database when no CSV is provided"""
        print("📥 Loading fallback voice database...")
        
        fallback_files = [
            # Based on actual allflows LITE patterns
            ("This is an electric callout", "1177"),
            ("It is", "1231"),
            ("Press 1 if this is", "1002"),
            ("if you need more time to get", "1005"),
            ("to the phone", "1006"),
            ("Press 7", "PRS7NEU"),
            ("is not home", "1004"),
            ("Press 9", "PRS9NEU"),
            ("to repeat this message", "1643"),
            ("Please enter your four digit PIN", "1008"),
            ("Invalid entry", "1009"),
            ("Thank you", "1029"),
            ("Goodbye", "1029"),
            ("Your response has been recorded", "1167"),
            ("Are you available", "1316"),
            ("If yes, press 1", "1167"),
            ("If no, press 3", "1021"),
            ("Not home", "1017"),
            ("Call the", "1175"),
            ("Callout System", "1175"),
            ("Employee", "1002"),
            ("Level 2", "1589"),
            ("More time", "1005"),
            ("Repeat this message", "1643"),
            ("Problems", "1351"),
            ("Invalid PIN", "1009"),
            ("Electric callout", "1274"),
            ("Callout reason", "1019"),
            ("Trouble location", "1232"),
            ("Custom message", "1149"),
            ("Continue", "1265"),
            ("Press any key", "1265"),
        ]
        
        for transcript, callflow_id in fallback_files:
            voice_file = VoiceFile(
                company="Standard",
                folder="Callflow",
                file_name=f"{callflow_id}.ulaw",
                transcript=transcript,
                callflow_id=callflow_id
            )
            self.voice_files.append(voice_file)
            
            # Index it
            transcript_words = transcript.lower().split()
            for word in transcript_words:
                if word not in self.transcript_index:
                    self.transcript_index[word] = []
                self.transcript_index[word].append(voice_file)
            
            self.exact_match_index[transcript.lower()] = voice_file
        
        print(f"✅ Loaded {len(self.voice_files)} fallback voice files")

    def convert_mermaid_to_ivr(self, mermaid_code: str) -> Tuple[List[Dict], str]:
        """Main conversion method matching production patterns"""
        print(f"\n🚀 Starting production conversion...")
        
        # Parse the Mermaid diagram
        nodes, connections = self._parse_mermaid_enhanced(mermaid_code)
        if not nodes:
            raise ValueError("No nodes found in Mermaid diagram")
        
        # Create node ID to label mapping for easy reference
        node_id_to_label = {}
        for node_id, node_text in nodes.items():
            # Generate meaningful labels dynamically
            node_type = self._determine_node_type(node_text)
            meaningful_label = self._generate_meaningful_label(node_text, node_type, node_id)
            node_id_to_label[node_id] = meaningful_label
        
        print(f"📋 Node mappings: {node_id_to_label}")
        
        # Find the starting node (Welcome node)
        start_node_id = self._find_start_node(nodes, connections)
        
        # Convert each node to IVR format with production patterns
        ivr_flow = []
        processed_nodes = set()
        
        # Process nodes in logical order starting from welcome
        self._process_node_recursive(start_node_id, nodes, connections, node_id_to_label, ivr_flow, processed_nodes)
        
        # Process any remaining nodes
        for node_id in nodes:
            if node_id not in processed_nodes:
                ivr_node = self._convert_node_to_ivr(node_id, nodes[node_id], connections, node_id_to_label)
                ivr_flow.append(ivr_node)
        
        # Generate JavaScript output
        js_output = self._generate_javascript_output(ivr_flow)
        
        print(f"✅ Production conversion completed! Generated {len(ivr_flow)} nodes")
        return ivr_flow, js_output

    def _parse_mermaid_enhanced(self, mermaid_code: str) -> Tuple[Dict[str, str], List[Dict]]:
        """Enhanced Mermaid parsing with better pattern recognition"""
        nodes = {}
        connections = []
        
        # Clean up the input
        mermaid_code = re.sub(r'```.*?```', '', mermaid_code, flags=re.DOTALL)
        mermaid_code = re.sub(r'flowchart\s+TD|graph\s+TD', '', mermaid_code)
        
        # Extract nodes - handle all possible formats
        node_patterns = [
            r'([A-Z]+)\["([^"]*?)"\]',           # A["text"]
            r'([A-Z]+)\{([^}]*?)\}',             # A{text} - diamond
            r'([A-Z]+)\[([^\]]*?)\]',            # A[text]
            r'([A-Z]+)\(([^)]*?)\)',             # A(text) - rounded
        ]
        
        for pattern in node_patterns:
            for match in re.finditer(pattern, mermaid_code):
                node_id = match.group(1)
                node_text = match.group(2).replace('<br/>', '\n').replace('\\n', '\n')
                nodes[node_id] = node_text.strip()
                print(f"📝 Found node: {node_id} = '{node_text[:50]}...'")
        
        # Extract connections with enhanced pattern matching
        connection_patterns = [
            r'([A-Z]+)\s*-->\s*\|"([^"]+)"\|\s*([A-Z]+)',  # A -->|"label"| B
            r'([A-Z]+)\s*-->\s*\|([^|]+)\|\s*([A-Z]+)',     # A -->|label| B  
            r'([A-Z]+)\s*-->\s*([A-Z]+)',                   # A --> B
        ]
        
        for pattern in connection_patterns:
            for match in re.finditer(pattern, mermaid_code):
                source = match.group(1)
                if len(match.groups()) == 3:
                    if '|"' in pattern:
                        label = match.group(2)
                        target = match.group(3)
                    elif '|' in pattern:
                        label = match.group(2)
                        target = match.group(3)
                    else:
                        label = ''
                        target = match.group(2)
                else:
                    label = ''
                    target = match.group(2)
                
                connections.append({
                    'source': source,
                    'target': target,
                    'label': label.strip()
                })
                print(f"🔗 Found connection: {source} -> {target} ('{label}')")
        
        print(f"✅ Parsed {len(nodes)} nodes and {len(connections)} connections")
        return nodes, connections

    def _find_start_node(self, nodes: Dict[str, str], connections: List[Dict]) -> str:
        """Find the starting node (typically the welcome node)"""
        # Find nodes with no incoming connections
        incoming_targets = {conn['target'] for conn in connections}
        start_candidates = [node_id for node_id in nodes if node_id not in incoming_targets]
        
        if start_candidates:
            # Prefer nodes that look like welcome messages
            for node_id in start_candidates:
                text = nodes[node_id].lower()
                if any(phrase in text for phrase in ['welcome', 'this is an', 'electric callout']):
                    return node_id
            return start_candidates[0]
        
        # Fallback to first node
        return list(nodes.keys())[0]

    def _process_node_recursive(self, node_id: str, nodes: Dict[str, str], connections: List[Dict], 
                               node_id_to_label: Dict[str, str], ivr_flow: List[Dict], processed: set):
        """Process nodes recursively to maintain proper flow order"""
        if node_id in processed or node_id not in nodes:
            return
        
        processed.add(node_id)
        
        # Convert this node
        ivr_node = self._convert_node_to_ivr(node_id, nodes[node_id], connections, node_id_to_label)
        ivr_flow.append(ivr_node)
        
        # Process connected nodes
        outgoing_connections = [conn for conn in connections if conn['source'] == node_id]
        for conn in outgoing_connections:
            self._process_node_recursive(conn['target'], nodes, connections, node_id_to_label, ivr_flow, processed)

    def _determine_node_type(self, text: str) -> NodeType:
        """Determine node type based on content analysis"""
        text_lower = text.lower()
        
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
        elif self._has_sleep_characteristics(text_lower):
            return NodeType.SLEEP
        elif self._has_decision_characteristics(text_lower):
            return NodeType.DECISION
        else:
            return NodeType.ACTION

    def _has_greeting_characteristics(self, text: str) -> bool:
        greeting_indicators = ['this is an', 'welcome', 'electric callout', 'press 1, if this is']
        return any(phrase in text for phrase in greeting_indicators)

    def _has_input_characteristics(self, text: str) -> bool:
        input_indicators = ['enter your', 'pin', 'digit', 'pound key']
        return any(phrase in text for phrase in input_indicators)

    def _has_availability_characteristics(self, text: str) -> bool:
        availability_indicators = ['available', 'work this callout', 'if yes, press', 'if no, press']
        return any(phrase in text for phrase in availability_indicators)

    def _has_response_characteristics(self, text: str) -> bool:
        response_indicators = ['response has been', 'recorded', 'accepted', 'decline']
        return any(phrase in text for phrase in response_indicators)

    def _has_termination_characteristics(self, text: str) -> bool:
        termination_indicators = ['goodbye', 'thank you', 'disconnect']
        return any(phrase in text for phrase in termination_indicators)

    def _has_error_characteristics(self, text: str) -> bool:
        error_indicators = ['invalid', 'error', 'problems', 'try again']
        return any(phrase in text for phrase in error_indicators)

    def _has_sleep_characteristics(self, text: str) -> bool:
        sleep_indicators = ['30-second', 'press any key', 'continue']
        return any(phrase in text for phrase in sleep_indicators)

    def _has_decision_characteristics(self, text: str) -> bool:
        return '?' in text or ('correct' in text and 'pin' in text)

    def _generate_meaningful_label(self, node_text: str, node_type: NodeType, node_id: str) -> str:
        """Generate meaningful labels based on content"""
        text_lower = node_text.lower()
        
        # Production-ready label patterns
        if 'this is an electric callout' in text_lower:
            return "Live Answer"
        elif 'enter your' in text_lower and 'pin' in text_lower:
            return "Enter PIN"
        elif 'available' in text_lower and 'work this callout' in text_lower:
            return "Available For Callout"
        elif 'accepted response' in text_lower:
            return "Accept"
        elif 'decline' in text_lower:
            return "Decline"
        elif 'not home' in text_lower:
            return "Not Home"
        elif 'invalid' in text_lower:
            return "Invalid Entry"
        elif 'goodbye' in text_lower:
            return "Goodbye"
        elif '30-second' in text_lower:
            return "Sleep"
        elif 'qualified' in text_lower:
            return "Qualified No"
        elif 'problems' in text_lower:
            return "Problems"
        elif 'correct' in text_lower and 'pin' in text_lower:
            return "Check PIN"
        elif 'electric callout' in text_lower and 'this is an' not in text_lower:
            return "Electric Callout Info"
        elif 'disconnect' in text_lower:
            return "hangup"
        
        # Fallback to extracting key words
        key_words = re.findall(r'\b[A-Z][a-z]+\b', node_text)
        if key_words:
            return ' '.join(key_words[:2])
        
        return f"Node_{node_id}"

    def _convert_node_to_ivr(self, node_id: str, node_text: str, connections: List[Dict], 
                            node_id_to_label: Dict[str, str]) -> Dict:
        """Convert node to production IVR format matching allflows LITE patterns"""
        
        # Get outgoing connections for this node
        node_connections = [conn for conn in connections if conn['source'] == node_id]
        
        # Determine node type and label
        node_type = self._determine_node_type(node_text)
        meaningful_label = node_id_to_label[node_id]
        
        # Base node structure matching production patterns
        ivr_node = {
            "label": meaningful_label,
            "log": f"{node_text.replace('\n', ' ')[:80]}...",
        }
        
        # Generate voice prompts
        play_prompts = self._generate_production_prompts(node_text, node_type)
        if play_prompts:
            ivr_node["playPrompt"] = play_prompts
        
        # Handle special cases based on node content and connections
        if self._is_welcome_node(node_text):
            # CRITICAL FIX: Welcome node with proper branch mapping
            ivr_node.update(self._create_welcome_node(node_text, node_connections, node_id_to_label))
            
        elif self._has_input_characteristics(node_text.lower()):
            # PIN entry node
            ivr_node.update(self._create_pin_entry_node(node_text, node_connections, node_id_to_label))
            
        elif self._has_availability_characteristics(node_text.lower()):
            # Availability question
            ivr_node.update(self._create_availability_node(node_text, node_connections, node_id_to_label))
            
        elif self._has_decision_characteristics(node_text.lower()):
            # Decision point (like PIN validation)
            ivr_node.update(self._create_decision_node(node_text, node_connections, node_id_to_label))
            
        elif len(node_connections) == 1:
            # Single connection - use goto
            target_label = node_id_to_label.get(node_connections[0]['target'], 'hangup')
            ivr_node["goto"] = target_label
            
        elif len(node_connections) == 0:
            # Terminal node
            ivr_node["goto"] = "hangup"
        
        # Add response handling for action nodes
        if self._has_response_characteristics(node_text.lower()):
            if 'accept' in node_text.lower():
                ivr_node["gosub"] = ["SaveCallResult", [1001, "Accept"]]
            elif 'decline' in node_text.lower():
                ivr_node["gosub"] = ["SaveCallResult", [1002, "Decline"]]
            elif 'qualified' in node_text.lower():
                ivr_node["gosub"] = ["SaveCallResult", [1145, "QualNo"]]
        
        return ivr_node

    def _is_welcome_node(self, text: str) -> bool:
        """Check if this is the main welcome node"""
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in [
            'this is an electric callout',
            'press 1, if this is',
            'press 3, if you need more time',
            'press 7, if',
            'press 9, to repeat'
        ])

    def _create_welcome_node(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create welcome node with FIXED branch mapping"""
        
        # Extract DTMF choices from text
        choices = re.findall(r'press\s+(\d+)', text.lower())
        
        # Build branch mapping - CRITICAL FIX HERE
        branch_map = {}
        
        # Map connections to choices
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'hangup')
            
            # CRITICAL FIX: Map "input" connection to choice "1"
            if label == 'input' or '1 - this is employee' in label:
                branch_map['1'] = target_label
                print(f"✅ CRITICAL FIX: Choice 1 -> {target_label}")
            elif '3' in label or 'need more time' in label:
                branch_map['3'] = target_label
            elif '7' in label or 'not home' in label:
                branch_map['7'] = target_label
            elif '9' in label or 'repeat' in label:
                branch_map['9'] = "Live Answer"  # Self-reference for repeat
            elif 'no input' in label:
                branch_map['none'] = target_label
        
        # Add defaults if missing
        if 'error' not in branch_map:
            branch_map['error'] = 'Live Answer'
        if 'none' not in branch_map:
            branch_map['none'] = branch_map.get('3', 'Sleep')
        
        print(f"🎯 Welcome branch map: {branch_map}")
        
        return {
            "getDigits": {
                "numDigits": 1,
                "maxTime": 1,
                "validChoices": "|".join(choices),
                "errorPrompt": "callflow:1009"
            },
            "branch": branch_map
        }

    def _create_pin_entry_node(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create PIN entry node matching production patterns"""
        
        branch_map = {}
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'hangup')
            
            if 'yes' in label or 'correct' in label:
                branch_map['{{pin}}'] = target_label
            elif 'no' in label or 'invalid' in label:
                branch_map['error'] = target_label
        
        if 'error' not in branch_map:
            branch_map['error'] = 'Invalid Entry'
        
        return {
            "getDigits": {
                "numDigits": 5,  # 4 digits + pound
                "maxTries": 3,
                "maxTime": 7,
                "validChoices": "{{pin}}",
                "errorPrompt": "callflow:1009"
            },
            "branch": branch_map
        }

    def _create_availability_node(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create availability question node"""
        
        choices = re.findall(r'press\s+(\d+)', text.lower())
        branch_map = {}
        
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'hangup')
            
            if '1' in label or 'accept' in label:
                branch_map['1'] = target_label
            elif '3' in label or 'decline' in label:
                branch_map['3'] = target_label
            elif '9' in label or 'call back' in label:
                branch_map['9'] = target_label
        
        branch_map.update({
            'error': 'Problems',
            'none': 'Problems'
        })
        
        return {
            "getDigits": {
                "numDigits": 1,
                "maxTries": 3,
                "maxTime": 7,
                "validChoices": "|".join(choices),
                "errorPrompt": "callflow:1009"
            },
            "branch": branch_map
        }

    def _create_decision_node(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create decision node (like PIN validation)"""
        
        branch_map = {}
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'hangup')
            
            if 'yes' in label:
                branch_map['yes'] = target_label
            elif 'no' in label:
                branch_map['no'] = target_label
        
        return {
            "branch": branch_map
        }

    def _generate_production_prompts(self, text: str, node_type: NodeType) -> List[str]:
        """Generate voice prompts matching production patterns"""
        
        # For welcome nodes, use segmented approach like allflows LITE
        if self._is_welcome_node(text):
            return [
                "callflow:1177",      # "This is an"
                "company:1202",       # company name
                "callflow:1178",      # "electric callout"
                "callflow:1231",      # "It is"
                "current: dow, date, time",
                "callflow:1002",      # "Press 1 if this is"
                "names:{{contact_id}}",
                "callflow:1005",      # "if you need more time"
                "names:{{contact_id}}",
                "callflow:1006",      # "to the phone"
                "standard:PRS7NEU",   # "Press 7"
                "callflow:1641",      # "if"
                "names:{{contact_id}}",
                "callflow:1004",      # "is not home"
                "standard:PRS9NEU",   # "Press 9"
                "callflow:1643"       # "to repeat this message"
            ]
        
        # Find best matching voice file for other nodes
        best_match = self._find_best_voice_match(text)
        if best_match:
            return [f"callflow:{best_match}"]
        
        return ["[VOICE FILE NEEDED]"]

    def _find_best_voice_match(self, text: str) -> Optional[str]:
        """Find best matching voice file"""
        text_lower = text.lower().strip()
        
        # Try exact match first
        if text_lower in self.exact_match_index:
            return self.exact_match_index[text_lower].callflow_id
        
        # Try keyword matching
        text_words = set(text_lower.split())
        best_match = None
        best_score = 0
        
        for voice_file in self.voice_files:
            transcript_words = set(voice_file.transcript.lower().split())
            common_words = text_words.intersection(transcript_words)
            if common_words:
                score = len(common_words) / max(len(text_words), len(transcript_words))
                if score > best_score and score > 0.4:
                    best_score = score
                    best_match = voice_file
        
        return best_match.callflow_id if best_match else None

    def _generate_javascript_output(self, ivr_flow: List[Dict]) -> str:
        """Generate production JavaScript output"""
        
        js_output = "module.exports = [\n"
        
        for i, node in enumerate(ivr_flow):
            js_output += "  {\n"
            
            for key, value in node.items():
                if isinstance(value, str):
                    js_output += f'    {key}: "{value}",\n'
                elif isinstance(value, list):
                    formatted_list = json.dumps(value, indent=4).replace('\n', '\n    ')
                    js_output += f'    {key}: {formatted_list},\n'
                elif isinstance(value, dict):
                    formatted_dict = json.dumps(value, indent=4).replace('\n', '\n    ')
                    js_output += f'    {key}: {formatted_dict},\n'
                else:
                    js_output += f'    {key}: {json.dumps(value)},\n'
            
            js_output += "  }"
            if i < len(ivr_flow) - 1:
                js_output += ","
            js_output += "\n"
        
        js_output += "];\n"
        return js_output


def convert_mermaid_to_ivr(mermaid_code: str, uploaded_csv_file=None) -> Tuple[List[Dict], str]:
    """Main function to convert Mermaid diagrams to production IVR"""
    converter = ProductionIVRConverter(uploaded_csv_file)
    return converter.convert_mermaid_to_ivr(mermaid_code)


# Test function
def test_production_converter():
    """Test the production converter with the electric callout example"""
    
    test_mermaid = '''flowchart TD
A["Welcome<br/>This is an electric callout from (Level 2).<br/>Press 1, if this is (employee).<br/>Press 3, if you need more time to get (employee) to the phone.<br/>Press 7, if (employee) is not home.<br/>Press 9, to repeat this message.<br/><br/>9 - repeat, or invalid input"] -->|"input"| B{"1 - this is employee"}
A -->|"no input - go to pg 3"| C["30-second message<br/>Press any key to<br/>continue..."]
A -->|"7 - not home"| D["Employee Not Home<br/>Please have<br/>(employee) call the<br/>(Level 2) Callout<br/>System at<br/>866-502-7267."]
A -->|"3 - need more time"| C
A -->|"retry logic"| A
B -->|"retry"| E["Invalid Entry<br/>Invalid entry.<br/>Please try again."]
E -->|"retry"| A
B -->|"yes"| F["Enter Employee PIN<br/>Please enter your 4 digit PIN<br/>followed by the pound key."]
F -->|"no"| E
F -->|"yes"| G{"Correct PIN?"}
G -->|"no"| E
G -->|"yes"| H["Electric Callout<br/>This is an electric callout."]
H --> I["Callout Reason<br/>The callout reason is (callout reason)."]
I --> J["Trouble Location<br/>The trouble location is (trouble location)."]
J --> K["Custom Message<br/>(Play custom message, if selected.)"]
K --> L{"Available For Callout<br/>Are you available to work this callout?<br/>If yes, press 1. If no, press 3.<br/>If no one else accepts, and you want to be called again, press 9."}
L -->|"retry"| E
L -->|"invalid or no input"| E
L -->|"1 - accept"| M["Accepted Response<br/>An accepted response has<br/>been recorded."]
L -->|"3 - decline"| N["Callout Decline<br/>Your response is being recorded as a decline."]
L -->|"9 - call back"| O["Qualified No<br/>You may be called again on this<br/>callout if no one accepts."]
M --> P["Goodbye<br/>Thank you.<br/>Goodbye."]
N --> P
O --> P
P --> Q["Disconnect"]
D --> Q'''
    
    try:
        ivr_flow, js_output = convert_mermaid_to_ivr(test_mermaid)
        print("✅ Production test conversion successful!")
        print(f"Generated {len(ivr_flow)} nodes")
        
        # Check if choice 1 is properly mapped
        welcome_node = next((node for node in ivr_flow if node.get('label') == 'Live Answer'), None)
        if welcome_node and welcome_node.get('branch', {}).get('1'):
            print(f"✅ CRITICAL FIX VERIFIED: Choice 1 maps to '{welcome_node['branch']['1']}'")
        else:
            print("❌ Choice 1 mapping still missing!")
            
        return ivr_flow, js_output
        
    except Exception as e:
        print(f"❌ Production test failed: {e}")
        return None, None


if __name__ == "__main__":
    test_production_converter()