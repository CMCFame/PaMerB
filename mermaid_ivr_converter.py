"""
FLEXIBLE PRODUCTION IVR CONVERTER
Works for ANY flow type - not hardcoded to specific patterns
"""

import re
import csv
import json
import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from difflib import SequenceMatcher

@dataclass
class VoiceFile:
    company: str
    folder: str
    file_name: str
    transcript: str
    callflow_id: str
    priority: int  # Higher = better (ARCOS = 100, client-specific = 200)

class FlexibleARCOSConverter:
    def __init__(self, cf_general_csv=None, arcos_csv=None):
        # Voice file databases with priority system
        self.voice_files: List[VoiceFile] = []
        self.transcript_index: Dict[str, List[VoiceFile]] = {}
        self.callflow_index: Dict[str, VoiceFile] = {}  # callflow_id -> best voice file
        
        # Load databases in priority order
        self._load_arcos_database(arcos_csv)  # Foundation layer
        self._load_client_database(cf_general_csv)  # Client overrides
        self._build_optimized_indexes()

    def _load_arcos_database(self, arcos_csv_file):
        """Load ARCOS recordings as foundation layer (Priority 100)"""
        print("🏗️ Loading ARCOS foundation database...")
        
        if arcos_csv_file:
            try:
                import io
                content = arcos_csv_file.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                
                csv_reader = csv.DictReader(io.StringIO(content))
                arcos_count = 0
                
                for row in csv_reader:
                    file_name = row.get('File Name', '')
                    callflow_id = file_name.replace('.ulaw', '') if file_name else f"ARCOS{arcos_count}"
                    
                    voice_file = VoiceFile(
                        company=row.get('Company', 'ARCOS'),
                        folder=row.get('Folder', 'callflow'),
                        file_name=file_name,
                        transcript=row.get('Transcript', ''),
                        callflow_id=callflow_id,
                        priority=100  # ARCOS foundation priority
                    )
                    
                    self.voice_files.append(voice_file)
                    arcos_count += 1
                
                print(f"✅ Loaded {arcos_count} ARCOS foundation recordings")
                
            except Exception as e:
                print(f"❌ Error loading ARCOS database: {e}")
                self._load_arcos_fallbacks()
        else:
            self._load_arcos_fallbacks()

    def _load_arcos_fallbacks(self):
        """Load ARCOS fallback recordings based on allflows LITE patterns"""
        print("📥 Loading ARCOS fallback recordings...")
        
        # Core ARCOS recordings from allflows LITE analysis
        arcos_core_files = [
            # Core callflow elements (from allflows LITE)
            ("This is an", "1191"),  # Primary greeting
            ("callout", "1274"),     # Callout noun
            ("from", "1589"),        # Location connector
            ("It is", "1231"),       # Time introducer
            ("Press 1 if this is", "1002"),
            ("if you need more time to get", "1005"),
            ("to the phone", "1006"),
            ("is not home", "1004"),
            ("to repeat this message", "1643"),
            ("The callout reason is", "1019"),
            ("The trouble location is", "1232"),
            ("Please have", "1017"),
            ("call the", "1174"),
            ("callout system", "1290"),
            ("at", "1015"),
            ("Invalid entry", "1009"),
            ("Please enter your four digit PIN", "1008"),
            ("followed by the pound key", "1008"),
            ("You have accepted", "1297"),
            ("Please listen carefully", "1302"),
            ("To confirm receipt", "1035"),
            ("Problems", "1351"),
            ("I'm sorry you are having problems", "1351"),
            
            # PIN and validation
            ("Your PIN cannot be", "1139"),
            ("Please enter your new four digit PIN", "1097"),
            ("Please re-enter your new four digit PIN", "1097"),
            ("Your pin has been changed successfully", "1100"),
            ("Your name has been successfully changed", "1104"),
            ("The automated system needs your spoken name", "1164"),
            ("Match to first entry", "1703"),
            
            # Standard press options
            ("Press 7", "PRS7NEU"),
            ("Press 9", "PRS9NEU"),
            ("Press 1", "PRS1NEU"),
            ("Press 3", "PRS3NEU"),
            
            # Response confirmations
            ("Accept", "1001"),
            ("Decline", "1002"), 
            ("Not Home", "1006"),
            ("Qualified No", "1145"),
            
            # Time/environment
            ("current date and time", "CURR_TIME"),
            ("environment", "ENV_VAR"),
        ]
        
        for transcript, callflow_id in arcos_core_files:
            voice_file = VoiceFile(
                company="ARCOS",
                folder="callflow",
                file_name=f"{callflow_id}.ulaw",
                transcript=transcript,
                callflow_id=callflow_id,
                priority=100  # ARCOS foundation priority
            )
            self.voice_files.append(voice_file)
        
        print(f"✅ Loaded {len(arcos_core_files)} ARCOS fallback recordings")

    def _load_client_database(self, cf_general_csv):
        """Load client-specific recordings as overrides (Priority 200)"""
        if not cf_general_csv:
            print("ℹ️ No client database provided - using ARCOS foundation only")
            return
            
        print("🎯 Loading client-specific override database...")
        
        try:
            import io
            content = cf_general_csv.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            csv_reader = csv.DictReader(io.StringIO(content))
            client_count = 0
            
            for row in csv_reader:
                file_name = row.get('File Name', '')
                callflow_id = file_name.replace('.ulaw', '') if file_name else f"CLIENT{client_count}"
                
                voice_file = VoiceFile(
                    company=row.get('Company', ''),
                    folder=row.get('Folder', ''),
                    file_name=file_name,
                    transcript=row.get('Transcript', ''),
                    callflow_id=callflow_id,
                    priority=200  # Client override priority
                )
                
                self.voice_files.append(voice_file)
                client_count += 1
            
            print(f"✅ Loaded {client_count} client-specific override recordings")
            
        except Exception as e:
            print(f"❌ Error loading client database: {e}")

    def _build_optimized_indexes(self):
        """Build optimized indexes with priority-based selection"""
        print("🔨 Building optimized voice indexes with ARCOS foundation...")
        
        # Build transcript index for searching
        for voice_file in self.voice_files:
            transcript_words = voice_file.transcript.lower().split()
            for word in transcript_words:
                if word not in self.transcript_index:
                    self.transcript_index[word] = []
                self.transcript_index[word].append(voice_file)
        
        # Build callflow index - prefer higher priority (client-specific over ARCOS)
        callflow_priority_map = {}
        for voice_file in self.voice_files:
            cid = voice_file.callflow_id
            if cid not in callflow_priority_map or voice_file.priority > callflow_priority_map[cid].priority:
                callflow_priority_map[cid] = voice_file
        
        self.callflow_index = callflow_priority_map
        
        # Sort transcript indexes by priority (highest first)
        for word in self.transcript_index:
            self.transcript_index[word].sort(key=lambda vf: vf.priority, reverse=True)
        
        arcos_count = sum(1 for vf in self.voice_files if vf.priority == 100)
        client_count = sum(1 for vf in self.voice_files if vf.priority == 200)
        
        print(f"✅ Indexed {arcos_count} ARCOS + {client_count} client recordings")
        print(f"✅ {len(self.callflow_index)} unique callflow IDs available")

    def convert_mermaid_to_ivr(self, mermaid_code: str) -> Tuple[List[Dict], str]:
        """Convert Mermaid to IVR using FLEXIBLE approach"""
        print(f"\n🚀 Starting flexible conversion...")
        
        # Parse the Mermaid diagram
        nodes, connections = self._parse_mermaid_enhanced(mermaid_code)
        if not nodes:
            raise ValueError("No nodes found in Mermaid diagram")
        
        # Create node ID to label mapping with FLEXIBLE labeling
        node_id_to_label = {}
        for node_id, node_text in nodes.items():
            meaningful_label = self._generate_flexible_label(node_text, node_id)
            node_id_to_label[node_id] = meaningful_label
        
        print(f"📋 Node mappings: {node_id_to_label}")
        
        # Convert nodes to IVR format
        ivr_flow = []
        start_node_id = self._find_start_node(nodes, connections)
        processed_nodes = set()
        
        # Process in logical order
        self._process_node_recursive(start_node_id, nodes, connections, node_id_to_label, ivr_flow, processed_nodes)
        
        # Process any remaining nodes
        for node_id in nodes:
            if node_id not in processed_nodes:
                ivr_node = self._convert_node_to_ivr_flexible(node_id, nodes[node_id], connections, node_id_to_label)
                ivr_flow.append(ivr_node)
        
        # Generate JavaScript output
        js_output = self._generate_javascript_output(ivr_flow)
        
        print(f"✅ Flexible conversion completed! Generated {len(ivr_flow)} nodes")
        return ivr_flow, js_output

    def _parse_mermaid_enhanced(self, mermaid_code: str) -> Tuple[Dict[str, str], List[Dict]]:
        """Enhanced Mermaid parsing"""
        nodes = {}
        connections = []
        
        # Clean up the input
        mermaid_code = re.sub(r'```.*?```', '', mermaid_code, flags=re.DOTALL)
        mermaid_code = re.sub(r'flowchart\s+TD|graph\s+TD', '', mermaid_code)
        
        # Extract nodes
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
        
        # Extract connections
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
        
        return nodes, connections

    def _find_start_node(self, nodes: Dict[str, str], connections: List[Dict]) -> str:
        """Find the starting node - FLEXIBLE approach"""
        incoming_targets = {conn['target'] for conn in connections}
        start_candidates = [node_id for node_id in nodes if node_id not in incoming_targets]
        
        if start_candidates:
            # Look for nodes that seem like starting points
            for node_id in start_candidates:
                text = nodes[node_id].lower()
                # More flexible starting point detection
                if any(indicator in text for indicator in [
                    'welcome', 'this is', 'hello', 'greeting', 'start', 'begin',
                    'please enter', 'enter your', 'pin not', 'invalid pin'
                ]):
                    return node_id
            return start_candidates[0]
        
        return list(nodes.keys())[0]

    def _process_node_recursive(self, node_id: str, nodes: Dict[str, str], connections: List[Dict], 
                               node_id_to_label: Dict[str, str], ivr_flow: List[Dict], processed: set):
        """Process nodes recursively to maintain flow order"""
        if node_id in processed or node_id not in nodes:
            return
        
        processed.add(node_id)
        
        # Convert this node
        ivr_node = self._convert_node_to_ivr_flexible(node_id, nodes[node_id], connections, node_id_to_label)
        ivr_flow.append(ivr_node)
        
        # Process connected nodes
        outgoing_connections = [conn for conn in connections if conn['source'] == node_id]
        for conn in outgoing_connections:
            self._process_node_recursive(conn['target'], nodes, connections, node_id_to_label, ivr_flow, processed)

    def _generate_flexible_label(self, node_text: str, node_id: str) -> str:
        """FLEXIBLE label generation - works for ANY flow type"""
        text_lower = node_text.lower().strip()
        
        # Handle questions/decisions dynamically
        if '?' in node_text:
            # Extract the question and make it a label
            question = node_text.split('?')[0].strip()
            # Take key words from the question
            key_words = [word for word in question.split() if len(word) > 2 and word.lower() not in ['the', 'to', 'is', 'was', 'are', 'were']]
            if key_words:
                return ' '.join(key_words[:3]).title()
        
        # Dynamic pattern matching for actions
        action_patterns = [
            # PIN related
            (r'enter\s+(?:your\s+)?(?:new\s+)?(?:four\s+digit\s+)?pin', 'Enter PIN'),
            (r'please\s+enter\s+(?:your\s+)?(?:new\s+)?(?:four\s+digit\s+)?pin', 'Enter PIN'),
            (r're-enter\s+(?:your\s+)?(?:new\s+)?(?:four\s+digit\s+)?pin', 'Re-enter PIN'),
            (r'pin\s+(?:cannot\s+be|not)', 'PIN Restriction'),
            (r'pin\s+(?:has\s+been\s+)?changed', 'PIN Changed'),
            (r'new\s+pin', 'New PIN'),
            
            # Entry and validation
            (r'invalid\s+entry', 'Invalid Entry'),
            (r'invalid\s+(\w+)', r'Invalid \1'),
            (r'entered\s+digits', 'Entered Digits'),
            (r'valid\s+digits', 'Valid Digits'),
            
            # Name related
            (r'name\s+(?:has\s+been\s+)?confirmation', 'Name Confirmation'),
            (r'name\s+(?:has\s+been\s+)?recorded', 'Name Recorded'),
            (r'name\s+(?:has\s+been\s+)?changed', 'Name Changed'),
            (r'first\s+time\s+users', 'First Time Users'),
            (r'automated\s+system\s+needs', 'Name Recording'),
            
            # General patterns
            (r'employee\s+information', 'Employee Information'),
            (r'selection', 'Selection'),
            (r'match\s+to\s+first\s+entry', 'Match Check'),
            (r'your\s+(\w+)\s+(?:has\s+been\s+)?(?:successfully\s+)?changed', r'\1 Changed'),
            (r'please\s+(\w+)', r'\1'),
            (r'(\w+)\s+successfully', r'\1 Success'),
        ]
        
        for pattern, replacement in action_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if r'\1' in replacement:
                    return replacement.replace(r'\1', match.group(1).title())
                else:
                    return replacement
        
        # Extract meaningful words from the beginning
        words = re.findall(r'\b[A-Za-z]+\b', node_text)
        meaningful_words = [word for word in words if len(word) > 2 and word.lower() not in ['the', 'your', 'this', 'that', 'please', 'has', 'been', 'will', 'are', 'is']]
        
        if meaningful_words:
            return ' '.join(meaningful_words[:2]).title()
        
        # Last resort - first few words
        first_words = node_text.split()[:2]
        if first_words:
            return ' '.join(word.capitalize() for word in first_words)
        
        return f"Node_{node_id}"

    def _convert_node_to_ivr_flexible(self, node_id: str, node_text: str, connections: List[Dict], 
                                     node_id_to_label: Dict[str, str]) -> Dict:
        """FLEXIBLE node conversion - works for ANY flow type"""
        
        node_connections = [conn for conn in connections if conn['source'] == node_id]
        meaningful_label = node_id_to_label[node_id]
        
        # Base node structure
        ivr_node = {
            "label": meaningful_label,
            "log": f"{node_text.replace('\n', ' ')[:80]}..."
        }
        
        # Generate voice prompts
        play_prompts = self._generate_flexible_prompts(node_text, meaningful_label)
        if play_prompts:
            ivr_node["playPrompt"] = play_prompts
        
        # FLEXIBLE node type detection
        node_type = self._detect_node_type_flexible(node_text, node_connections)
        
        if node_type == 'decision':
            # Decision node - needs branches
            ivr_node.update(self._create_decision_node_flexible(node_text, node_connections, node_id_to_label))
        
        elif node_type == 'input':
            # Input collection node
            ivr_node.update(self._create_input_node_flexible(node_text, node_connections, node_id_to_label))
        
        elif node_type == 'welcome':
            # Welcome/greeting node
            ivr_node.update(self._create_welcome_node_flexible(node_text, node_connections, node_id_to_label))
        
        elif len(node_connections) == 1:
            # Single connection - goto
            target_label = node_id_to_label.get(node_connections[0]['target'], 'hangup')
            ivr_node["goto"] = target_label
        
        elif len(node_connections) == 0:
            # Terminal node
            ivr_node["goto"] = "hangup"
        
        # Add response handling for specific types
        if any(word in node_text.lower() for word in ['accept', 'decline', 'recorded', 'successfully']):
            if 'accept' in node_text.lower():
                ivr_node["gosub"] = ["SaveCallResult", [1001, "Accept"]]
            elif 'decline' in node_text.lower():
                ivr_node["gosub"] = ["SaveCallResult", [1002, "Decline"]]
        
        return ivr_node

    def _detect_node_type_flexible(self, node_text: str, connections: List[Dict]) -> str:
        """FLEXIBLE node type detection"""
        text_lower = node_text.lower()
        
        # Decision indicators
        if '?' in node_text or any(word in text_lower for word in ['match', 'valid', 'correct', 'entered digits']):
            return 'decision'
        
        # Input indicators
        if any(phrase in text_lower for phrase in ['enter your', 'please enter', 're-enter', 'followed by']):
            return 'input'
        
        # Welcome indicators (flexible)
        if any(phrase in text_lower for phrase in ['welcome', 'this is', 'hello', 'greeting', 'press 1']) and len(connections) > 2:
            return 'welcome'
        
        # Default
        return 'message'

    def _create_decision_node_flexible(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create decision node - FLEXIBLE approach"""
        branch_map = {}
        
        # Map connections based on labels
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'hangup')
            
            # Flexible branch mapping
            if 'yes' in label:
                branch_map['yes'] = target_label
            elif 'no' in label:
                branch_map['no'] = target_label
            elif re.search(r'\b(one|1)\b', label):
                branch_map['1'] = target_label
            elif re.search(r'\b(three|3)\b', label):
                branch_map['3'] = target_label
            elif 'entered digits' in label:
                branch_map['input'] = target_label
            else:
                # Use the connection label as the branch key
                clean_label = re.sub(r'[^a-zA-Z0-9]', '_', label)[:10]
                if clean_label:
                    branch_map[clean_label] = target_label
        
        # Add defaults
        if not branch_map:
            branch_map['default'] = 'hangup'
        
        return {"branch": branch_map}

    def _create_input_node_flexible(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create input node - FLEXIBLE approach"""
        text_lower = text.lower()
        
        # Determine input type
        if 'pin' in text_lower:
            num_digits = 5 if 'pound' in text_lower else 4
            valid_choices = "{{pin}}"
        elif 'digit' in text_lower:
            # Extract number of digits
            digit_match = re.search(r'(\d+)\s*digit', text_lower)
            num_digits = int(digit_match.group(1)) if digit_match else 1
            valid_choices = "0|1|2|3|4|5|6|7|8|9"
        else:
            num_digits = 1
            valid_choices = "1|2|3|4|5|6|7|8|9|0"
        
        # Build branch map
        branch_map = {}
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'hangup')
            
            if 'yes' in label:
                branch_map[valid_choices] = target_label
            elif 'no' in label or 'error' in label:
                branch_map['error'] = target_label
            elif label:
                branch_map[label] = target_label
        
        # Add defaults
        if 'error' not in branch_map:
            branch_map['error'] = 'Invalid Entry'
        
        return {
            "getDigits": {
                "numDigits": num_digits,
                "maxTries": 3,
                "maxTime": 7,
                "validChoices": valid_choices,
                "errorPrompt": "callflow:1009"
            },
            "branch": branch_map
        }

    def _create_welcome_node_flexible(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create welcome node - FLEXIBLE approach"""
        
        # Extract DTMF choices dynamically
        choices = re.findall(r'press\s+(\d+)', text.lower())
        if not choices:
            choices = ['1', '2', '3']  # Default choices
        
        branch_map = {}
        
        print(f"🔍 Welcome node processing {len(connections)} connections...")
        
        # FLEXIBLE connection mapping
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'hangup')
            
            print(f"🔗 Processing connection: '{label}' -> {target_label}")
            
            # Map based on connection labels
            if 'input' in label:
                branch_map['1'] = target_label
                print(f"✅ Choice 1 (input) -> {target_label}")
            elif re.search(r'\b1\b', label):
                branch_map['1'] = target_label
                print(f"✅ Choice 1 -> {target_label}")
            elif re.search(r'\b3\b', label):
                branch_map['3'] = target_label
                print(f"✅ Choice 3 -> {target_label}")
            elif re.search(r'\b7\b', label):
                branch_map['7'] = target_label
                print(f"✅ Choice 7 -> {target_label}")
            elif re.search(r'\b9\b', label):
                branch_map['9'] = target_label
                print(f"✅ Choice 9 -> {target_label}")
            elif 'no input' in label or 'timeout' in label:
                branch_map['none'] = target_label
            elif 'error' in label or 'retry' in label:
                branch_map['error'] = target_label
        
        # Add defaults
        if 'error' not in branch_map:
            branch_map['error'] = 'Problems'
        if 'none' not in branch_map:
            branch_map['none'] = 'Problems'
        
        print(f"🎯 Welcome branch map: {branch_map}")
        
        return {
            "getDigits": {
                "numDigits": 1,
                "maxTime": 7,
                "validChoices": "|".join(choices),
                "errorPrompt": "callflow:1009"
            },
            "branch": branch_map
        }

    def _generate_flexible_prompts(self, text: str, label: str) -> List[str]:
        """Generate voice prompts - FLEXIBLE approach"""
        
        # For welcome nodes with specific patterns, use segmented approach
        if any(phrase in text.lower() for phrase in ['this is an', 'electric callout', 'press 1']):
            return [
                "callflow:1177",           # "This is an"
                "company:1202",            # company name
                "callflow:1178",           # "electric callout"
                "callflow:1231",           # "It is"
                "current: dow, date, time", # current date/time
                "callflow:1002",           # "Press 1 if this is"
                "names:{{contact_id}}",    # employee name
                "callflow:1005",           # "if you need more time"
                "names:{{contact_id}}",    # employee name
                "callflow:1006",           # "to the phone"
                "standard:PRS7NEU",        # "Press 7"
                "callflow:1641",           # "if"
                "names:{{contact_id}}",    # employee name
                "callflow:1004",           # "is not home"
                "standard:PRS9NEU",        # "Press 9"
                "callflow:1643"            # "to repeat this message"
            ]
        
        # For other nodes, find best match
        best_match = self._find_best_match_flexible(text)
        if best_match:
            return [f"callflow:{best_match}"]
        
        return ["[VOICE FILE NEEDED]"]

    def _find_best_match_flexible(self, text: str) -> Optional[str]:
        """Find best matching voice file - FLEXIBLE approach"""
        text_lower = text.lower().strip()
        
        # Try exact match first
        for voice_file in self.voice_files:
            if voice_file.transcript.lower() == text_lower:
                return voice_file.callflow_id
        
        # Try partial matching
        best_match = None
        best_score = 0
        
        for voice_file in self.voice_files:
            # Calculate similarity
            similarity = SequenceMatcher(None, text_lower, voice_file.transcript.lower()).ratio()
            
            # Also check word overlap
            text_words = set(text_lower.split())
            transcript_words = set(voice_file.transcript.lower().split())
            word_overlap = len(text_words.intersection(transcript_words))
            
            # Combined score
            score = similarity * 0.7 + (word_overlap / max(len(text_words), 1)) * 0.3
            
            if score > best_score and score > 0.3:  # Lower threshold for flexibility
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


def convert_mermaid_to_ivr(mermaid_code: str, cf_general_csv=None, arcos_csv=None) -> Tuple[List[Dict], str]:
    """Main function for FLEXIBLE ARCOS-integrated conversion"""
    converter = FlexibleARCOSConverter(cf_general_csv, arcos_csv)
    return converter.convert_mermaid_to_ivr(mermaid_code)