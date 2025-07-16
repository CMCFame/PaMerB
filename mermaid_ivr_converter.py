"""
ARCOS-Integrated Production IVR Converter
Prioritizes ARCOS recordings as foundation with client-specific overrides
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

class ARCOSIntegratedConverter:
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
        """Convert Mermaid to IVR using ARCOS-integrated approach"""
        print(f"\n🚀 Starting ARCOS-integrated conversion...")
        
        # Parse the Mermaid diagram
        nodes, connections = self._parse_mermaid_enhanced(mermaid_code)
        if not nodes:
            raise ValueError("No nodes found in Mermaid diagram")
        
        # Create node ID to label mapping
        node_id_to_label = {}
        for node_id, node_text in nodes.items():
            meaningful_label = self._generate_production_label(node_text, node_id)
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
                ivr_node = self._convert_node_to_ivr(node_id, nodes[node_id], connections, node_id_to_label)
                ivr_flow.append(ivr_node)
        
        # Generate JavaScript output
        js_output = self._generate_javascript_output(ivr_flow)
        
        print(f"✅ ARCOS-integrated conversion completed! Generated {len(ivr_flow)} nodes")
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
        """Find the starting node (welcome/greeting)"""
        incoming_targets = {conn['target'] for conn in connections}
        start_candidates = [node_id for node_id in nodes if node_id not in incoming_targets]
        
        if start_candidates:
            # Prefer welcome-like nodes
            for node_id in start_candidates:
                text = nodes[node_id].lower()
                if any(phrase in text for phrase in ['welcome', 'this is an', 'electric callout']):
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
        ivr_node = self._convert_node_to_ivr(node_id, nodes[node_id], connections, node_id_to_label)
        ivr_flow.append(ivr_node)
        
        # Process connected nodes
        outgoing_connections = [conn for conn in connections if conn['source'] == node_id]
        for conn in outgoing_connections:
            self._process_node_recursive(conn['target'], nodes, connections, node_id_to_label, ivr_flow, processed)

    def _generate_production_label(self, node_text: str, node_id: str) -> str:
        """Generate production-quality labels matching allflows LITE"""
        text_lower = node_text.lower()
        
        # Production labels matching allflows LITE patterns
        if 'this is an electric callout' in text_lower and 'press 1' in text_lower:
            return "Live Answer"
        elif 'enter your' in text_lower and 'pin' in text_lower:
            return "Enter PIN"
        elif 'available' in text_lower and 'work this callout' in text_lower:
            return "Available For Callout"
        elif 'accepted response' in text_lower:
            return "Accept"
        elif 'decline' in text_lower and 'recorded' in text_lower:
            return "Decline"
        elif 'not home' in text_lower:
            return "Not Home"
        elif 'invalid' in text_lower:
            return "Invalid Entry"
        elif 'goodbye' in text_lower:
            return "Goodbye"
        elif '30-second' in text_lower or 'press any key' in text_lower:
            return "Sleep"
        elif 'qualified' in text_lower:
            return "Qualified No"
        elif 'problems' in text_lower:
            return "Problems"
        elif 'correct' in text_lower and 'pin' in text_lower:
            return "Check PIN"
        elif 'disconnect' in text_lower:
            return "hangup"
        
        # Fallback
        return f"Node_{node_id}"

    def _convert_node_to_ivr(self, node_id: str, node_text: str, connections: List[Dict], 
                            node_id_to_label: Dict[str, str]) -> Dict:
        """Convert node to production IVR format with ARCOS integration"""
        
        node_connections = [conn for conn in connections if conn['source'] == node_id]
        meaningful_label = node_id_to_label[node_id]
        
        # Base node structure
        ivr_node = {
            "label": meaningful_label,
            "log": f"{node_text.replace('\n', ' ')[:80]}..."
        }
        
        # Generate ARCOS-integrated voice prompts
        play_prompts = self._generate_arcos_prompts(node_text, meaningful_label)
        if play_prompts:
            ivr_node["playPrompt"] = play_prompts
        
        # Handle node types with ARCOS patterns
        if self._is_welcome_node(node_text):
            # Welcome node with CRITICAL FIX for choice "1"
            ivr_node.update(self._create_arcos_welcome_node(node_text, node_connections, node_id_to_label))
            
        elif self._has_input_characteristics(node_text):
            # PIN entry
            ivr_node.update(self._create_arcos_pin_node(node_text, node_connections, node_id_to_label))
            
        elif self._has_availability_characteristics(node_text):
            # Availability question
            ivr_node.update(self._create_arcos_availability_node(node_text, node_connections, node_id_to_label))
            
        elif len(node_connections) == 1:
            # Single connection - goto
            target_label = node_id_to_label.get(node_connections[0]['target'], 'hangup')
            ivr_node["goto"] = target_label
            
        elif len(node_connections) == 0:
            # Terminal node
            ivr_node["goto"] = "hangup"
        
        # Add ARCOS-style response handling
        if self._has_response_characteristics(node_text):
            if 'accept' in node_text.lower():
                ivr_node["gosub"] = ["SaveCallResult", [1001, "Accept"]]
            elif 'decline' in node_text.lower():
                ivr_node["gosub"] = ["SaveCallResult", [1002, "Decline"]]
            elif 'qualified' in node_text.lower():
                ivr_node["gosub"] = ["SaveCallResult", [1145, "QualNo"]]
        
        return ivr_node

    def _is_welcome_node(self, text: str) -> bool:
        """Check if this is the welcome node"""
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in [
            'this is an electric callout',
            'press 1, if this is',
            'press 3, if you need',
            'press 7, if',
            'press 9, to repeat'
        ])

    def _has_input_characteristics(self, text: str) -> bool:
        return any(phrase in text for phrase in ['enter your', 'pin', 'digit', 'pound key'])

    def _has_availability_characteristics(self, text: str) -> bool:
        return any(phrase in text for phrase in ['available', 'work this callout', 'if yes, press'])

    def _has_response_characteristics(self, text: str) -> bool:
        return any(phrase in text for phrase in ['response has been', 'recorded', 'accepted', 'decline'])

    def _create_arcos_welcome_node(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create welcome node with ARCOS patterns and CRITICAL FIX for choice 1"""
        
        choices = re.findall(r'press\s+(\d+)', text.lower())
        branch_map = {}
        
        # CRITICAL FIX: Map connections to choices
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'hangup')
            
            # FIXED: "input" connection maps to choice "1" 
            if label == 'input' or '1 - this is employee' in label:
                branch_map['1'] = target_label
                print(f"✅ CRITICAL FIX: Choice 1 -> {target_label}")
            elif '3' in label or 'need more time' in label:
                branch_map['3'] = target_label
            elif '7' in label or 'not home' in label:
                branch_map['7'] = target_label
            elif '9' in label or 'repeat' in label:
                branch_map['9'] = "Live Answer"  # Self-reference
            elif 'no input' in label:
                branch_map['none'] = target_label
        
        # Add ARCOS defaults
        if 'error' not in branch_map:
            branch_map['error'] = 'Live Answer'
        if 'none' not in branch_map:
            branch_map['none'] = 'Real Answering Machine'  # ARCOS pattern
        
        return {
            "getDigits": {
                "numDigits": 1,
                "maxTime": 1,  # ARCOS pattern
                "validChoices": "|".join(choices),
                "errorPrompt": "callflow:1009"  # ARCOS standard
            },
            "branch": branch_map
        }

    def _create_arcos_pin_node(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create PIN entry node with ARCOS patterns"""
        
        branch_map = {}
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'hangup')
            
            if 'yes' in label or 'correct' in label:
                branch_map['{{pin}}'] = target_label  # ARCOS variable pattern
            elif 'no' in label or 'invalid' in label:
                branch_map['error'] = target_label
        
        if 'error' not in branch_map:
            branch_map['error'] = 'Invalid Entry'
        
        return {
            "getDigits": {
                "numDigits": 5,  # 4 digits + pound
                "maxTries": 3,
                "maxTime": 7,
                "validChoices": "{{pin}}",  # ARCOS variable
                "errorPrompt": "callflow:1009"  # ARCOS standard
            },
            "branch": branch_map
        }

    def _create_arcos_availability_node(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create availability node with ARCOS patterns"""
        
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

    def _generate_arcos_prompts(self, text: str, label: str) -> List[str]:
        """Generate voice prompts using ARCOS-integrated approach"""
        
        # For welcome nodes, use ARCOS segmented pattern like allflows LITE
        if self._is_welcome_node(text):
            return [
                "callflow:1177",           # "This is an" (ARCOS)
                "company:1202",            # company name (variable)
                "callflow:1178",           # "electric callout" (ARCOS)
                "callflow:1231",           # "It is" (ARCOS)
                "current: dow, date, time", # current date/time (ARCOS variable)
                "callflow:1002",           # "Press 1 if this is" (ARCOS)
                "names:{{contact_id}}",    # employee name (ARCOS variable)
                "callflow:1005",           # "if you need more time" (ARCOS)
                "names:{{contact_id}}",    # employee name (ARCOS variable)
                "callflow:1006",           # "to the phone" (ARCOS)
                "standard:PRS7NEU",        # "Press 7" (ARCOS standard)
                "callflow:1641",           # "if" (ARCOS)
                "names:{{contact_id}}",    # employee name (ARCOS variable)
                "callflow:1004",           # "is not home" (ARCOS)
                "standard:PRS9NEU",        # "Press 9" (ARCOS standard)
                "callflow:1643"            # "to repeat this message" (ARCOS)
            ]
        
        # For other nodes, find best ARCOS match
        best_match = self._find_best_arcos_match(text)
        if best_match:
            return [f"callflow:{best_match}"]
        
        return ["[VOICE FILE NEEDED]"]

    def _find_best_arcos_match(self, text: str) -> Optional[str]:
        """Find best matching ARCOS voice file with priority system"""
        text_lower = text.lower().strip()
        
        # Try exact transcript match first (prioritizes client overrides)
        for voice_file in self.voice_files:
            if voice_file.transcript.lower() == text_lower:
                return voice_file.callflow_id
        
        # Try keyword matching with priority
        text_words = set(text_lower.split())
        best_match = None
        best_score = 0
        
        for voice_file in self.voice_files:
            transcript_words = set(voice_file.transcript.lower().split())
            common_words = text_words.intersection(transcript_words)
            if common_words:
                # Score includes priority boost
                base_score = len(common_words) / max(len(text_words), len(transcript_words))
                priority_boost = voice_file.priority / 1000  # Small boost for higher priority
                score = base_score + priority_boost
                
                if score > best_score and base_score > 0.4:  # 40% similarity threshold
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
    """Main function for ARCOS-integrated conversion"""
    converter = ARCOSIntegratedConverter(cf_general_csv, arcos_csv)
    return converter.convert_mermaid_to_ivr(mermaid_code)