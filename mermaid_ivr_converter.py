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
from decimal import Decimal
from db_connection import get_database

def safe_str(value: Any) -> str:
    """Safely convert any value (including decimal.Decimal) to string"""
    if value is None:
        return ''
    elif isinstance(value, Decimal):
        return str(value)
    elif isinstance(value, (int, float)):
        return str(value)
    else:
        return str(value)

def clean_branch_key(label: str) -> str:
    """Clean branch key by removing HTML tags and invalid characters"""
    if not label:
        return label
    
    # Remove HTML tags
    label = re.sub(r'<[^>]+>', '', label)
    
    # Remove quotes 
    label = label.strip('"\'')
    
    # Clean up whitespace
    label = ' '.join(label.split())
    
    return label

def detect_page_reference(node_text: str) -> Optional[str]:
    """Detect if a node references another page/flow"""
    text_lower = node_text.lower()
    
    # Look for page references
    page_match = re.search(r'page\s+(\d+)', text_lower)
    if page_match:
        return page_match.group(1)
    
    # Look for flow references
    flow_patterns = [
        r'availability.*status',
        r'contact.*numbers',
        r'test.*numbers', 
        r'pin.*name',
        r'change.*pin'
    ]
    
    for pattern in flow_patterns:
        if re.search(pattern, text_lower):
            return 'sub_flow'
    
    return None

@dataclass
class VoiceFile:
    company: str
    folder: str
    file_name: str
    transcript: str
    callflow_id: str
    priority: int  # Higher = better (ARCOS = 100, client-specific = 200)

class FlexibleARCOSConverter:
    def __init__(self, cf_general_csv=None, arcos_csv=None, use_dynamodb=True):
        # Voice file databases with priority system
        self.voice_files: List[VoiceFile] = []
        self.transcript_index: Dict[str, List[VoiceFile]] = {}
        self.callflow_index: Dict[str, VoiceFile] = {}  # callflow_id -> best voice file
        self.use_dynamodb = use_dynamodb
        
        # Load databases in priority order
        if use_dynamodb:
            print("Using DynamoDB for voice file database...")
            self._load_dynamodb_database()
        else:
            print("Using CSV files for voice file database...")
            self._load_arcos_database(arcos_csv)  # Foundation layer
            self._load_client_database(cf_general_csv)  # Client overrides
        
        self._build_optimized_indexes()

    def _load_dynamodb_database(self):
        """Load voice files from DynamoDB table"""
        print("Loading voice files from DynamoDB...")
        
        try:
            db = get_database()
            connection_status = db.get_connection_status()
            
            if connection_status["status"] != "connected":
                print(f"ERROR: Cannot connect to DynamoDB: {connection_status.get('error', 'Unknown error')}")
                print("INFO: Falling back to CSV database files...")
                self._load_csv_fallback_database()
                return
            
            # Get all voice files from DynamoDB
            db_voice_files = db.get_all_voice_files()
            
            if not db_voice_files:
                print("WARNING: No voice files found in DynamoDB. Using CSV fallback.")
                self._load_csv_fallback_database()
                return
            
            # Convert DynamoDB records to VoiceFile objects
            db_count = 0
            for db_record in db_voice_files:
                # Parse the voice file ID for callflow reference - safely convert to string
                voice_file_id = safe_str(db_record.get('voice_file_id', ''))
                
                # Determine priority based on company (can be enhanced later)
                company = safe_str(db_record.get('company', 'UNKNOWN'))
                if company.upper() == 'ARCOS':
                    priority = 100  # ARCOS foundation
                else:
                    priority = 200  # Client-specific override
                
                # Safely convert all DynamoDB fields to strings to avoid decimal.Decimal issues
                voice_file = VoiceFile(
                    company=company,
                    folder=safe_str(db_record.get('voice_file_type', 'callflow')),
                    file_name=f"{voice_file_id}.ulaw",
                    transcript=safe_str(db_record.get('transcript', '')),
                    callflow_id=voice_file_id,
                    priority=priority
                )
                
                self.voice_files.append(voice_file)
                db_count += 1
            
            print(f"SUCCESS: Loaded {db_count} voice files from DynamoDB")
            
            # Add ARCOS fallback for any missing core files
            self._add_arcos_fallback_if_missing()
            
        except Exception as e:
            print(f"ERROR: Loading from DynamoDB: {e}")
            print("INFO: Falling back to CSV database files...")
            self._load_csv_fallback_database()

    def _load_csv_fallback_database(self):
        """Load CSV files from dbinfo folder as fallback when DynamoDB fails"""
        print("Loading CSV fallback database from dbinfo folder...")
        
        import os
        import io
        
        # Try to load ARCOS database from dbinfo folder
        arcos_csv_path = os.path.join(os.path.dirname(__file__), 'dbinfo', 'arcos_general_structure.csv')
        cf_csv_path = os.path.join(os.path.dirname(__file__), 'dbinfo', 'cf_general_structure.csv')
        
        # Load ARCOS foundation
        if os.path.exists(arcos_csv_path):
            try:
                print(f"Loading ARCOS database from: {arcos_csv_path}")
                with open(arcos_csv_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Create a mock file object for compatibility with existing method
                    mock_file = io.StringIO(content)
                    mock_file.name = 'arcos_general_structure.csv'
                    mock_file.size = len(content)
                    self._load_arcos_database(mock_file)
            except Exception as e:
                print(f"ERROR: Failed to load ARCOS CSV: {e}")
                print("INFO: Using built-in ARCOS fallback...")
                self._load_arcos_fallback_database()
        else:
            print(f"WARNING: ARCOS CSV not found at {arcos_csv_path}")
            print("INFO: Using built-in ARCOS fallback...")
            self._load_arcos_fallback_database()
        
        # Load client database
        if os.path.exists(cf_csv_path):
            try:
                print(f"Loading client database from: {cf_csv_path}")
                with open(cf_csv_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Create a mock file object for compatibility with existing method
                    mock_file = io.StringIO(content)
                    mock_file.name = 'cf_general_structure.csv'
                    mock_file.size = len(content)
                    self._load_client_database(mock_file)
            except Exception as e:
                print(f"ERROR: Failed to load client CSV: {e}")
        else:
            print(f"INFO: Client CSV not found at {cf_csv_path} - using ARCOS only")

    def _load_arcos_fallback_database(self):
        """Load ARCOS foundation database as fallback when DynamoDB fails"""
        print("Loading ARCOS fallback database...")
        
        # Essential ARCOS callflow files for IVR operation
        arcos_core_files = [
            # Welcome and navigation
            ("Welcome to the", "1011"),
            ("automated callout system", "1011"), 
            ("If you are the employee", "1012"),
            ("Press 1 if you are the employee", "1012"),
            ("Otherwise press 2", "1013"),
            ("Press 2 if you are not the employee", "1013"),
            
            # PIN entry and validation  
            ("Please enter your four digit PIN", "1008"),
            ("followed by the pound key", "1008"),
            ("Invalid PIN", "1009"),
            ("Thank you", "1014"),
            
            # Call flow responses
            ("You are being called to", "1025"),
            ("If you can report", "1020"),
            ("Press 1 to accept", "1001"),
            ("Press 2 to decline", "1002"),
            ("Press 3 for qualified no", "1145"),
            ("You have accepted", "1297"),
            ("You have declined", "1298"),
            
            # Error handling and confirmations
            ("Invalid entry", "1009"),
            ("Please try again", "1009"),
            ("Thank you for your response", "1035"),
            ("Good bye", "1040"),
            
            # Additional common prompts
            ("Please listen carefully", "1302"),
            ("To confirm receipt", "1035"),
            ("call the", "1174"),
            ("callout system", "1290"),
            ("at", "1015"),
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
        
        print(f"SUCCESS: Loaded {len(arcos_core_files)} ARCOS fallback recordings")

    def _add_arcos_fallback_if_missing(self):
        """Add ARCOS fallback files for any critical IDs not found in DynamoDB"""
        existing_callflow_ids = {vf.callflow_id for vf in self.voice_files}
        
        critical_arcos_files = [
            ("Invalid entry", "1009"),
            ("Please enter your four digit PIN", "1008"), 
            ("You have accepted", "1297"),
            ("You have declined", "1298"),
            ("Accept", "1001"),
            ("Decline", "1002"),
            ("Good bye", "1040"),
        ]
        
        added_count = 0
        for transcript, callflow_id in critical_arcos_files:
            if callflow_id not in existing_callflow_ids:
                voice_file = VoiceFile(
                    company="ARCOS",
                    folder="callflow", 
                    file_name=f"{callflow_id}.ulaw",
                    transcript=transcript,
                    callflow_id=callflow_id,
                    priority=90  # Lower than DB files but available as fallback
                )
                self.voice_files.append(voice_file)
                added_count += 1
        
        if added_count > 0:
            print(f"INFO: Added {added_count} critical ARCOS fallback files")

    def _load_arcos_database(self, arcos_csv_file):
        """Load ARCOS recordings as foundation layer (Priority 100)"""
        print("Loading ARCOS foundation database...")
        
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
                
                print(f"Loaded {arcos_count} ARCOS foundation recordings")
                
            except Exception as e:
                print(f"Error loading ARCOS database: {e}")
                self._load_arcos_fallbacks()
        else:
            self._load_arcos_fallbacks()

    def _load_arcos_fallbacks(self):
        """Load ARCOS fallback recordings based on allflows LITE patterns"""
        print("Loading ARCOS fallback recordings...")
        
        # Enhanced ARCOS recordings based on developer feedback
        arcos_core_files = [
            # Notification/Message recordings (from developer feedback)
            ("This is an important call notification message. Please listen carefully.", "1302"),
            ("This is not a callout request", "1614"),
            ("This is not a callout- do not report to work", "1615"),
            ("you have accepted receipt of this message", "1297"),
            ("to confirm receipt of the msg, press1. to replay the msg press 3", "1035"),
            
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
        
        print(f"Loaded {len(arcos_core_files)} ARCOS fallback recordings")

    def _load_client_database(self, cf_general_csv):
        """Load client-specific recordings as overrides (Priority 200)"""
        if not cf_general_csv:
            print("INFO: No client database provided - using ARCOS foundation only")
            return
            
        print("LOADING: Client-specific override database...")
        
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
            
            print(f"SUCCESS: Loaded {client_count} client-specific override recordings")
            
        except Exception as e:
            print(f"ERROR: Loading client database: {e}")

    def _build_optimized_indexes(self):
        """Build optimized indexes with priority-based selection"""
        print("BUILDING: Optimized voice indexes with ARCOS foundation...")
        
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
        
        print(f"SUCCESS: Indexed {arcos_count} ARCOS + {client_count} client recordings")
        print(f"SUCCESS: {len(self.callflow_index)} unique callflow IDs available")

    def convert_mermaid_to_ivr(self, mermaid_code: str) -> Tuple[List[Dict], str]:
        """Convert Mermaid to IVR using FLEXIBLE approach"""
        print(f"\nSTARTING: Flexible conversion...")
        
        # Parse the Mermaid diagram
        nodes, connections = self._parse_mermaid_enhanced(mermaid_code)
        if not nodes:
            raise ValueError("No nodes found in Mermaid diagram")
        
        # Create node ID to label mapping with FLEXIBLE labeling
        node_id_to_label = {}
        label_counts = {}  # Track duplicate labels
        
        for node_id, node_text in nodes.items():
            meaningful_label = self._generate_flexible_label(node_text, node_id)
            
            # Handle duplicate labels by adding suffixes
            original_label = meaningful_label
            if meaningful_label in label_counts:
                label_counts[meaningful_label] += 1
                meaningful_label = f"{original_label} {label_counts[meaningful_label]}"
            else:
                label_counts[meaningful_label] = 0
            
            node_id_to_label[node_id] = meaningful_label
        
        print(f"MAPPINGS: Node mappings: {node_id_to_label}")
        
        # Convert nodes to IVR format
        ivr_flow = []
        start_node_id = self._find_start_node(nodes, connections)
        processed_nodes = set()
        
        # Process in logical order
        self._process_node_recursive(start_node_id, nodes, connections, node_id_to_label, ivr_flow, processed_nodes)
        
        # Process any remaining nodes
        for node_id in nodes:
            if node_id not in processed_nodes:
                ivr_result = self._convert_node_to_ivr_flexible(node_id, nodes[node_id], connections, node_id_to_label)
                # Handle multi-section nodes (like welcome nodes with multiple sections)
                if isinstance(ivr_result, list):
                    ivr_flow.extend(ivr_result)
                else:
                    ivr_flow.append(ivr_result)
        
        # Remove unnecessary nodes for inbound flows (based on developer feedback)
        ivr_flow = self._clean_inbound_flow_nodes(ivr_flow)
        
        # Generate JavaScript output
        js_output = self._generate_javascript_output(ivr_flow)
        
        print(f"SUCCESS: Flexible conversion completed! Generated {len(ivr_flow)} nodes")
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
        
        # Extract connections - enhanced to handle node definitions in the same line
        connection_patterns = [
            # Handle lines with node definitions: A["text"] -->|"label"| B{"text"}
            r'([A-Z]+)(?:\[.*?\]|\{.*?\})?\s*-->\s*\|"([^"]+)"\|\s*([A-Z]+)(?:\[.*?\]|\{.*?\})?',
            # Handle lines with node definitions: A["text"] -->|label| B{"text"}  
            r'([A-Z]+)(?:\[.*?\]|\{.*?\})?\s*-->\s*\|([^|]+)\|\s*([A-Z]+)(?:\[.*?\]|\{.*?\})?',
            # Handle simple connections: A --> B
            r'([A-Z]+)(?:\[.*?\]|\{.*?\})?\s*-->\s*([A-Z]+)(?:\[.*?\]|\{.*?\})?',
        ]
        
        for pattern in connection_patterns:
            for match in re.finditer(pattern, mermaid_code):
                source = match.group(1)
                if len(match.groups()) == 3:
                    # Has label and target
                    label = match.group(2)
                    target = match.group(3)
                else:
                    # Direct connection without label
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
        ivr_result = self._convert_node_to_ivr_flexible(node_id, nodes[node_id], connections, node_id_to_label)
        # Handle multi-section nodes (like welcome nodes with multiple sections)
        if isinstance(ivr_result, list):
            ivr_flow.extend(ivr_result)
        else:
            ivr_flow.append(ivr_result)
        
        # Process connected nodes
        outgoing_connections = [conn for conn in connections if conn['source'] == node_id]
        for conn in outgoing_connections:
            self._process_node_recursive(conn['target'], nodes, connections, node_id_to_label, ivr_flow, processed)

    def _generate_flexible_label(self, node_text: str, node_id: str) -> str:
        """FLEXIBLE label generation - works for ANY flow type"""
        text_lower = node_text.lower().strip()
        
        # Special IVR label patterns based on developer feedback and allflows LITE
        ivr_label_patterns = [
            # Welcome/main entry node patterns (critical fix)
            (r'welcome.*this is an.*electric callout.*press 1', 'Live Answer'),
            (r'this is an.*electric callout.*press 1', 'Live Answer'), 
            (r'electric callout.*press 1.*press 3.*press 7.*press 9', 'Live Answer'),
            (r'press 1.*press 3.*press 7.*press 9', 'Live Answer'),
            # Additional patterns for electric callout welcome
            (r'this is an electric callout from.*press 1.*press 3.*press 7.*press 9', 'Live Answer'),
            (r'welcome.*press 1.*press 3.*press 7.*press 9', 'Live Answer'),
            
            # Core IVR patterns
            (r'notification.*callout', 'Callout'),
            (r'custom\s+message', 'Custom Message'),
            (r'confirm.*receipt', 'Offer'),  # "Confirm" becomes "Offer" per developer feedback
            (r'accepted?\s+response', 'Accept'),
            (r'invalid\s+entry', 'Invalid Entry'),
            (r'disconnect', 'Hangup'),
            (r'main\s+menu', 'Main Menu'),
            
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
        
        # Handle questions/decisions dynamically
        if '?' in node_text:
            # Extract the question and make it a label
            question = node_text.split('?')[0].strip()
            # Take key words from the question
            key_words = [word for word in question.split() if len(word) > 2 and word.lower() not in ['the', 'to', 'is', 'was', 'are', 'were']]
            if key_words:
                return ' '.join(key_words[:3]).title()
        
        for pattern, replacement in ivr_label_patterns:
            match = re.search(pattern, text_lower, re.DOTALL)
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
                                     node_id_to_label: Dict[str, str]) -> Any:
        """FLEXIBLE node conversion - works for ANY flow type"""
        
        node_connections = [conn for conn in connections if conn['source'] == node_id]
        meaningful_label = node_id_to_label[node_id]
        
        # Base node structure
        ivr_node = {
            "label": meaningful_label,
            "log": f"{node_text.replace('\n', ' ')[:80]}..."
        }
        
        # Generate voice prompts and logs
        play_prompts, play_logs = self._generate_flexible_prompts_and_logs(node_text, meaningful_label)
        if play_prompts:
            ivr_node["playPrompt"] = play_prompts
        if play_logs:
            ivr_node["playLog"] = play_logs
        
        # FLEXIBLE node type detection
        node_type = self._detect_node_type_flexible(node_text, node_connections)
        
        if node_type == 'decision':
            # Decision node - needs branches
            decision_data = self._create_decision_node_flexible(node_text, node_connections, node_id_to_label)
            ivr_node.update(decision_data)
            
            # Special handling for employee verification decision nodes
            if any(pattern in node_text.lower() for pattern in ['this is employee', 'this is the employee', 'employee verification', 'verify employee']):
                # Override prompts and logs for proper employee verification question
                ivr_node["playPrompt"] = ["callflow:1002"]  # Generic question prompt
                ivr_node["playLog"] = ["Is this the employee?"]
                ivr_node["log"] = "Employee verification - Is this the employee?"
        
        elif node_type == 'input':
            # Input collection node
            ivr_node.update(self._create_input_node_flexible(node_text, node_connections, node_id_to_label))
        
        elif node_type == 'menu':
            # Main Menu node - needs getDigits for user input
            menu_data = self._create_menu_node_flexible(node_text, node_connections, node_id_to_label)
            ivr_node.update(menu_data)
        
        elif node_type == 'welcome':
            # Welcome/greeting node - PRODUCTION MULTI-SECTION approach
            welcome_sections = self._create_welcome_node_flexible(node_text, node_connections, node_id_to_label)
            # Return the sections as separate nodes for production-style structure
            return welcome_sections
        
        elif len(node_connections) == 1:
            # Single connection - check if it's a page reference
            target_label = node_id_to_label.get(node_connections[0]['target'], 'hangup')
            page_ref = detect_page_reference(target_label)
            
            if page_ref and page_ref.isdigit():
                # This is a page reference - use gosub for sub-flow
                ivr_node["gosub"] = [f"Page{page_ref}", "RETURN"]
            elif 'page' in target_label.lower():
                # Generic page reference - use gosub
                page_name = target_label.replace(' ', '').replace('/', '')
                ivr_node["gosub"] = [page_name, "RETURN"]
            else:
                # Regular goto
                ivr_node["goto"] = target_label
        
        elif len(node_connections) == 0:
            # Terminal node
            ivr_node["goto"] = "hangup"
        
        # Add special IVR attributes based on node content
        self._add_special_ivr_attributes(ivr_node, node_text, meaningful_label, node_type)
        
        # Add conditional logic patterns (PRODUCTION FEATURE)
        self._add_conditional_logic(ivr_node, node_text, meaningful_label)
        
        # Add confirmation patterns for critical actions (PRODUCTION FEATURE)
        confirmation_nodes = self._generate_confirmation_patterns(ivr_node, node_text, meaningful_label)
        if confirmation_nodes:
            return confirmation_nodes
        
        # Add response handling for specific types
        if any(word in node_text.lower() for word in ['accept', 'decline', 'recorded', 'successfully']):
            if 'accept' in node_text.lower():
                # Simple gosub structure matching allflows LITE format
                ivr_node["gosub"] = ["SaveCallResult", 1001, "Accept"]
            elif 'decline' in node_text.lower():
                ivr_node["gosub"] = ["SaveCallResult", 1002, "Decline"]
            elif 'qualified' in node_text.lower():
                ivr_node["gosub"] = ["SaveCallResult", 1145, "QualNo"]
        
        return ivr_node

    def _add_special_ivr_attributes(self, ivr_node: Dict, node_text: str, label: str, node_type: str):
        """Add special IVR attributes based on node content and type"""
        text_lower = node_text.lower()
        
        # Add nobarge for message/notification nodes
        if any(phrase in text_lower for phrase in ['notification', 'message', 'important', 'listen carefully']):
            ivr_node["nobarge"] = 1
        
        # Add maxLoop for welcome/main nodes (matching allflows LITE pattern)
        if 'welcome' in label.lower() or 'live answer' in label.lower() or any(phrase in text_lower for phrase in ['this is an', 'electric callout', 'press 1']):
            # Main loop with 3 tries then go to Problems
            ivr_node["maxLoop"] = ["Main", 3, "Problems"]
        
        # Add maxLoop for recursive/callout nodes
        elif any(phrase in text_lower for phrase in ['callout', 'notification']) and 'message' in text_lower:
            # Based on developer feedback: on 4th try make them accept
            ivr_node["maxLoop"] = ["PLAYMESSAGE", 3, "Accept-1025"]
        
        # Add returnsub for inbound flows (based on developer feedback)
        if 'accept' in text_lower and any(phrase in text_lower for phrase in ['receipt', 'message']):
            ivr_node["returnsub"] = 1
        
        # Enhanced error handling patterns (PRODUCTION FEATURE)
        self._add_enhanced_error_handling(ivr_node, node_text, label, node_type)

    def _detect_node_type_flexible(self, node_text: str, connections: List[Dict]) -> str:
        """FLEXIBLE node type detection"""
        text_lower = node_text.lower()
        
        # Welcome/main entry detection (critical for electric callout)
        if ('press 1' in text_lower and 'press 3' in text_lower and 'press 7' in text_lower and 'press 9' in text_lower):
            return 'welcome'  # This is the main welcome node with all DTMF options
        
        # Main Menu detection - menu with press options but not the main welcome
        if ('press 1' in text_lower and 'press 2' in text_lower and 'press 3' in text_lower) or \
           ('press 1' in text_lower and 'press 2' in text_lower and 'press 4' in text_lower) or \
           'main menu' in text_lower:
            return 'menu'
        
        # Decision indicators - check for press options with multiple choices
        if ('press 1' in text_lower and 'press 3' in text_lower) or 'confirm' in text_lower:
            return 'decision'
        
        # Decision indicators
        if '?' in node_text or any(word in text_lower for word in ['match', 'valid', 'correct', 'entered digits']):
            return 'decision'
        
        # Input indicators
        if any(phrase in text_lower for phrase in ['enter your', 'please enter', 're-enter', 'followed by']):
            return 'input'
        
        # Welcome indicators (flexible) - callout pattern with connections
        if any(phrase in text_lower for phrase in ['welcome', 'this is.*callout', 'hello', 'greeting']) and len(connections) > 2:
            return 'welcome'
        
        # Employee verification decision nodes (CRITICAL FIX for choice 1 mapping)
        # This catches patterns like "1 - this is employee" which should ask "Is this the employee?"
        if any(pattern in text_lower for pattern in ['this is employee', 'this is the employee', 'employee verification', 'verify employee']):
            return 'decision'
        
        # Additional verification patterns that require yes/no responses
        if any(pattern in text_lower for pattern in ['this is', 'are you', 'is this']) and 'employee' in text_lower:
            return 'decision'
        
        # Default
        return 'message'

    def _create_decision_node_flexible(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create decision node - FLEXIBLE approach"""
        branch_map = {}
        
        print(f"PROCESSING: Decision node processing {len(connections)} connections...")
        
        # Check if this is an employee verification decision node
        is_employee_verification = any(pattern in text.lower() for pattern in ['this is employee', 'this is the employee', 'employee verification', 'verify employee'])
        
        # Map connections based on labels
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'hangup')
            
            print(f"CONNECTING: Processing decision connection: '{label}' -> {target_label}")
            
            # Special handling for employee verification nodes
            if is_employee_verification:
                # Employee verification should only have yes/no responses, not direct DTMF mappings
                if 'yes' in label:
                    branch_map['yes'] = target_label
                    print(f"MAPPED: Employee verification YES -> {target_label}")
                elif 'no' in label or 'retry' in label:
                    branch_map['no'] = target_label
                    print(f"MAPPED: Employee verification NO -> {target_label}")
                continue
            
            # Enhanced branch mapping based on developer feedback
            # Check the target node to determine correct mapping
            target_node_text = conn['target']
            
            if 'accept' in label and 'accept' in target_label.lower():
                branch_map['1'] = target_label
                print(f"MAPPED: Choice 1 (accept) -> {target_label}")
            elif 'repeat' in label or ('3' in label and 'repeat' in label):
                branch_map['3'] = target_label
                print(f"MAPPED: Choice 3 (repeat) -> {target_label}")
            elif '1' in label and ('accept' in target_label.lower() or 'response' in target_label.lower()):
                branch_map['1'] = target_label
                print(f"MAPPED: Choice 1 -> {target_label}")
            elif '3' in label and ('custom' in target_label.lower() or 'message' in target_label.lower()):
                branch_map['3'] = target_label
                print(f"MAPPED: Choice 3 -> {target_label}")
            elif 'invalid' in label or 'no input' in label:
                branch_map['error'] = target_label
                branch_map['none'] = target_label
                print(f"MAPPED: Error/None -> {target_label}")
            elif 'retry' in label:
                branch_map['error'] = target_label
                print(f"MAPPED: Error (retry) -> {target_label}")
            elif 'yes' in label:
                branch_map['yes'] = target_label
            elif 'no' in label:
                branch_map['no'] = target_label
        
        # Add required defaults
        if 'error' not in branch_map:
            branch_map['error'] = 'Problems'
        if 'none' not in branch_map:
            branch_map['none'] = 'Problems'
        
        print(f"RESULT: Decision branch map: {branch_map}")
        
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
                clean_label = clean_branch_key(label)
                if clean_label:  # Only add if cleaning didn't remove everything
                    branch_map[clean_label] = target_label
        
        # Add defaults
        if 'error' not in branch_map:
            branch_map['error'] = 'Invalid Entry'
        
        return {
            "getDigits": {
                "numDigits": num_digits,
                "maxTries": 3,
                "maxTime": 7,
                "validChoices": valid_choices,
                "errorPrompt": "callflow:1009",
                "nonePrompt": "callflow:1009"
            },
            "branch": branch_map
        }

    def _create_welcome_node_flexible(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> List[Dict]:
        """Create welcome node - PRODUCTION MULTI-SECTION approach like real IVR scripts"""
        
        # Extract DTMF choices from the text
        choices = re.findall(r'press\s+(\d+)', text.lower())
        if not choices:
            choices = ['1', '3', '7', '9']  # Standard electric callout choices
        
        branch_map = {}
        
        print(f"PROCESSING: Welcome node processing {len(connections)} connections...")
        print(f"DETECTED: DTMF choices in text: {choices}")
        
        # Map connections based on labels and targets
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], 'hangup')
            
            print(f"CONNECTING: Processing connection: '{label}' -> {target_label}")
            
            # Enhanced mapping logic - prioritize exact "input" connection
            if label == 'input' or label == '"input"':
                branch_map['1'] = target_label  # Choice 1: Employee verification (from input connection)
                print(f"MAPPED: Choice 1 (input connection) -> {target_label}")
            elif 'input' in label and 'no input' not in label:
                branch_map['1'] = target_label  # Choice 1: Employee verification
                print(f"MAPPED: Choice 1 (employee) -> {target_label}")
            elif ('3' in label and 'need more time' in label) or ('3' in label and 'time' in target_label.lower()):
                branch_map['3'] = target_label  # Choice 3: Need more time
                print(f"MAPPED: Choice 3 (need time) -> {target_label}")
            elif ('7' in label and 'not home' in label) or ('7' in label and 'home' in target_label.lower()):
                branch_map['7'] = target_label  # Choice 7: Not home
                print(f"MAPPED: Choice 7 (not home) -> {target_label}")
            elif ('9' in label and 'repeat' in label) or ('retry logic' in label):
                branch_map['9'] = target_label  # Choice 9: Repeat/retry
                print(f"MAPPED: Choice 9 (repeat) -> {target_label}")
            elif 'no input' in label:
                branch_map['error'] = target_label  # No input handling
                print(f"MAPPED: No input -> {target_label}")
            elif re.search(r'\b(\d)\b', label):
                # General number mapping
                num = re.search(r'\b(\d)\b', label).group(1)
                if num in ['1', '3', '7', '9']:
                    branch_map[num] = target_label
                    print(f"MAPPED: Choice {num} -> {target_label}")
        
        # Add required defaults matching allflows LITE pattern
        if 'error' not in branch_map:
            branch_map['error'] = 'Live Answer'  # Retry back to main menu
        
        print(f"RESULT: Welcome branch map: {branch_map}")
        
        # Generate multi-section nodes like production scripts
        welcome_sections = []
        
        # Section 1: Main greeting with maxLoop
        prompts, logs = self._generate_flexible_prompts_and_logs(text, "Live Answer")
        
        section1 = {
            "label": "Live Answer",
            "maxLoop": ["Main", 3, "Problems"],
            "playLog": logs[:3] if len(logs) >= 3 else logs,  # First few segments
            "playPrompt": prompts[:3] if len(prompts) >= 3 else prompts
        }
        welcome_sections.append(section1)
        
        # Section 2: Environment check (production pattern)
        section2 = {
            "label": "Environment Check",
            "log": "environment",
            "playLog": ["Environment check"],
            "guard": "function (){ return this.data.env!='prod' && this.data.env!='PROD' }",
            "playPrompt": "callflow:{{env}}",
            "nobarge": 1
        }
        welcome_sections.append(section2)
        
        # Section 3: Main choice menu with getDigits
        section3 = {
            "label": "Main Menu",
            "log": "Main menu with DTMF choices",
            "playLog": logs[3:] if len(logs) > 3 else logs,  # Remaining segments
            "playPrompt": prompts[3:] if len(prompts) > 3 else prompts,
            "getDigits": {
                "numDigits": 1,
                "maxTime": 1,  # Short timeout like allflows LITE
                "validChoices": "1|3|7|9",  # Fixed choices for electric callout
                "errorPrompt": "callflow:1009"
            },
            "branch": branch_map
        }
        welcome_sections.append(section3)
        
        return welcome_sections

    def _create_menu_node_flexible(self, text: str, connections: List[Dict], node_id_to_label: Dict[str, str]) -> Dict:
        """Create main menu node with proper getDigits"""
        text_lower = text.lower()
        
        # Extract menu choices from text and connections
        branch_map = {}
        valid_choices = []
        
        # Analyze connections to determine valid choices and handle page references
        for conn in connections:
            label = conn.get('label', '').lower()
            target_label = node_id_to_label.get(conn['target'], conn['target'])
            
            # Check if target is a page reference
            target_node_text = ''  # We'll need to get this from somewhere
            page_ref = detect_page_reference(target_label)
            
            # Clean the label for branch key
            clean_label = clean_branch_key(label)
            
            # Extract number from press statements or connection labels
            for num in ['1', '2', '3', '4', '8']:
                if num in label or f'press {num}' in text_lower:
                    # If target is a page reference, use gosub instead of branch
                    if page_ref:
                        # Handle as a gosub call to another flow
                        branch_map[num] = target_label  # Keep as is for now
                    else:
                        branch_map[num] = target_label
                    
                    if num not in valid_choices:
                        valid_choices.append(num)
                    break
        
        # Add default branches
        if 'error' not in branch_map:
            branch_map['error'] = 'Invalid Entry'
        if 'none' not in branch_map:
            branch_map['none'] = 'Invalid Entry'
        
        # Always parse the text for press instructions to ensure we get all choices
        text_choices = []
        for num in ['1', '2', '3', '4', '8']:
            if f'press {num}' in text_lower:
                text_choices.append(num)
                
                # Map to appropriate targets based on common patterns if not already mapped
                if num not in branch_map:
                    if num == '1' and 'availability' in text_lower:
                        branch_map[num] = 'Availability Status'
                    elif num == '2' and 'contact' in text_lower:
                        branch_map[num] = 'Add Change'
                    elif num == '3' and 'test' in text_lower:
                        branch_map[num] = 'Test Numbers'
                    elif num == '4' and 'pin' in text_lower:
                        branch_map[num] = 'Pin And'
                    elif num == '8' and 'repeat' in text_lower:
                        branch_map[num] = 'Main Menu'  # Loop back to self
        
        # Combine connection-based and text-based choices
        all_choices = list(set(valid_choices + text_choices))
        if all_choices:
            valid_choices = all_choices
        
        # Determine valid choices string
        if not valid_choices:
            # Default menu choices if none detected
            valid_choices = ['1', '2', '3', '4', '8']
        valid_choices_str = '|'.join(sorted(valid_choices))
        
        return {
            "getDigits": {
                "numDigits": 1,
                "maxTries": 3,
                "maxTime": 7,
                "validChoices": valid_choices_str,
                "errorPrompt": "callflow:1009",
                "nonePrompt": "callflow:1009"
            },
            "branch": branch_map,
            "maxLoop": ["PLAYMESSAGE", 3, "Invalid Entry"]
        }

    def _generate_flexible_prompts_and_logs(self, text: str, label: str) -> Tuple[List[str], List[str]]:
        """Generate voice prompts and corresponding logs - PRODUCTION ENHANCED with template variables"""
        
        # Split text into logical segments for better matching
        text_segments = self._split_text_into_segments(text)
        
        prompts = []
        logs = []
        
        for segment in text_segments:
            segment_clean = segment.strip()
            if not segment_clean:
                continue
                
            # Check for template variable patterns first (PRODUCTION FEATURE)
            template_result = self._generate_template_variables(segment_clean, label)
            if template_result:
                prompts.extend(template_result['prompts'])
                logs.extend(template_result['logs'])
                continue
                
            # Find best match for this segment
            best_match = self._find_best_match_flexible(segment_clean)
            if best_match:
                prompts.append(f"callflow:{best_match}")
                logs.append(segment_clean)
            else:
                # Check for custom message patterns
                if 'custom message' in segment_clean.lower():
                    prompts.append("custom:{{custom_message}}")
                    logs.append("[Custom Message]")
                elif segment_clean:
                    prompts.append("[VOICE FILE NEEDED]")
                    logs.append(segment_clean)
        
        # If no segments found or matched, fallback to original logic
        if not prompts:
            best_match = self._find_best_match_flexible(text)
            if best_match:
                prompts = [f"callflow:{best_match}"]
                logs = [text.replace('\n', ' ').strip()]
            else:
                prompts = ["[VOICE FILE NEEDED]"]
                logs = [text.replace('\n', ' ').strip()]
        
        return prompts, logs

    def _generate_template_variables(self, text: str, label: str) -> Optional[Dict[str, List[str]]]:
        """Generate template variables and macros like production IVR scripts"""
        text_lower = text.lower().strip()
        
        # Template variable patterns based on production scripts
        template_patterns = [
            # Employee name patterns
            {
                'pattern': r'if this is\s*\([^)]*employee[^)]*\)',
                'prompts': ["callflow:1002", "names:{{contact_id}}"],
                'logs': ["Press 1 if this is", "Employee name spoken({{contact_id}})"]
            },
            {
                'pattern': r'employee[^)]*\)\s*is not home',
                'prompts': ["names:{{contact_id}}", "callflow:1004"],
                'logs': ["Employee name spoken", "is not home"]
            },
            {
                'pattern': r'get\s*\([^)]*employee[^)]*\)\s*to the phone',
                'prompts': ["names:{{contact_id}}", "callflow:1006"],
                'logs': ["Employee name spoken", "to the phone"]
            },
            {
                'pattern': r'please have[^)]*\([^)]*employee[^)]*\)',
                'prompts': ["callflow:1017", "names:{{contact_id}}"],
                'logs': ["Please have", "Employee name spoken"]
            },
            
            # Location patterns
            {
                'pattern': r'electric callout from\s*\([^)]*level[^)]*\)',
                'prompts': ["callflow:1614", "location:{{level1_location}}"],
                'logs': ["This is an electric callout from", "Level location spoken"]
            },
            {
                'pattern': r'call the[^)]*\([^)]*level[^)]*\)',
                'prompts': ["callflow:1174", "location:{{level1_location}}"],
                'logs': ["call the", "Level location spoken"]
            },
            
            # Callout type patterns
            {
                'pattern': r'callout reason is\s*\([^)]*\)',
                'prompts': ["callflow:1019", "reason:{{callout_reason}}"],
                'logs': ["The callout reason is", "Callout reason spoken"]
            },
            {
                'pattern': r'trouble location is\s*\([^)]*\)',
                'prompts': ["callflow:1232", "location:{{callout_location}}"],
                'logs': ["The trouble location is", "Trouble location spoken"]
            },
            
            # Time/Date patterns
            {
                'pattern': r'initiated on.*speaks date.*speaks time',
                'prompts': ["callflow:1014", "date:{{job_start_date}}", "callflow:1015", "time:{{job_start_time}}"],
                'logs': ["callout was initiated on", "Speaks date", "at", "Speaks time"]
            },
            
            # Phone number patterns
            {
                'pattern': r'call.*system.*at.*phone',
                'prompts': ["callflow:1174", "callflow:1290", "callflow:1015", "digits:{{callback_number}}"],
                'logs': ["call the", "callout system", "at", "speak phone number"]
            }
        ]
        
        # Check for matches
        for pattern_info in template_patterns:
            if re.search(pattern_info['pattern'], text_lower):
                return {
                    'prompts': pattern_info['prompts'],
                    'logs': pattern_info['logs']
                }
        
        return None

    def _add_conditional_logic(self, ivr_node: Dict, node_text: str, label: str):
        """Add conditional logic patterns like production IVR scripts"""
        text_lower = node_text.lower().strip()
        
        # Conditional patterns based on production scripts
        conditional_patterns = [
            # PIN requirement check
            {
                'pattern': r'pin.*required|check.*pin|enter.*pin',
                'branchOn': '{{pin_req}}',
                'branch': {
                    '1': 'Enter PIN',
                    'next': 'After PIN'
                }
            },
            
            # Environment-based conditions
            {
                'pattern': r'environment|env.*prod|development',
                'guard': 'function(){ return this.data.env!="prod" && this.data.env!="PROD" }',
                'guardPrompt': 'callflow:{{env}}'
            },
            
            # Custom message conditions
            {
                'pattern': r'custom.*message|play.*custom',
                'guardPrompt': 'custom:{{custom_message}}'
            },
            
            # Callout reason conditions
            {
                'pattern': r'callout.*reason|reason.*is',
                'guardPrompt': 'reason:{{callout_reason}}'
            },
            
            # Job classification conditions
            {
                'pattern': r'job.*classification|working.*as',
                'guardPrompt': 'class:{{job_classification}}'
            },
            
            # Location-based conditions
            {
                'pattern': r'trouble.*location|location.*is',
                'guardPrompt': 'location:{{callout_location}}'
            },
            
            # English-only conditions
            {
                'pattern': r'english.*only|en.*only',
                'branchOn': '{{en_only}}',
                'branch': {
                    '1': 'Problems EnOnly',
                    'next': 'Problems Employee'
                }
            }
        ]
        
        # Check for conditional patterns
        for pattern_info in conditional_patterns:
            if re.search(pattern_info['pattern'], text_lower):
                # Add branchOn conditional
                if 'branchOn' in pattern_info:
                    ivr_node['branchOn'] = pattern_info['branchOn']
                    if 'branch' in pattern_info:
                        ivr_node['branch'] = pattern_info['branch']
                
                # Add guard function
                if 'guard' in pattern_info:
                    ivr_node['guard'] = pattern_info['guard']
                
                # Add guardPrompt
                if 'guardPrompt' in pattern_info:
                    ivr_node['guardPrompt'] = pattern_info['guardPrompt']
                
                break  # Use first match

    def _generate_confirmation_patterns(self, ivr_node: Dict, node_text: str, label: str) -> Optional[List[Dict]]:
        """Generate confirmation patterns for critical actions like production scripts"""
        text_lower = node_text.lower().strip()
        
        # Critical actions that need confirmation
        critical_patterns = [
            {
                'trigger': r'accept.*callout|available.*to.*work',
                'action': 'Accept',
                'choice': '1',
                'confirm_text': 'You pressed 1 to accept. Please press 1 again to confirm',
                'confirm_prompt': 'callflow:1366'
            },
            {
                'trigger': r'decline.*callout|not.*available',
                'action': 'Decline', 
                'choice': '9',
                'confirm_text': 'You pressed 9 to decline. Please press 9 again to confirm',
                'confirm_prompt': 'callflow:2135'
            },
            {
                'trigger': r'supervisor.*acknowledgement|supervisor.*only',
                'action': 'Supervisor',
                'choice': '3', 
                'confirm_text': 'You pressed 3. This is for supervisors only. Press 3 again to confirm',
                'confirm_prompt': 'callflow:2137'
            },
            {
                'trigger': r'qualified.*no|call.*again',
                'action': 'QualNo',
                'choice': '7',
                'confirm_text': 'You pressed 7 to be called again. Please press 7 again to confirm', 
                'confirm_prompt': 'callflow:2136'
            }
        ]
        
        # Check if this node needs confirmation
        for pattern_info in critical_patterns:
            if re.search(pattern_info['trigger'], text_lower):
                # Generate confirmation pattern nodes
                confirmation_nodes = []
                
                # Original choice node (modified to go to confirmation)
                confirm_label = f"Confirm {pattern_info['action']}"
                if 'branch' in ivr_node:
                    # Update existing branch to point to confirmation
                    ivr_node['branch'][pattern_info['choice']] = confirm_label
                
                confirmation_nodes.append(ivr_node)
                
                # Confirmation node
                confirm_node = {
                    'label': confirm_label,
                    'log': pattern_info['confirm_text'],
                    'playPrompt': [pattern_info['confirm_prompt']],
                    'playLog': [pattern_info['confirm_text']],
                    'getDigits': {
                        'numDigits': 1,
                        'maxTries': 1,
                        'maxTime': 7,
                        'validChoices': pattern_info['choice']
                    },
                    'branch': {
                        pattern_info['choice']: pattern_info['action'],
                        'error': 'Invalid_Response',
                        'none': 'Invalid_Response'
                    }
                }
                confirmation_nodes.append(confirm_node)
                
                # Invalid response handler
                invalid_node = {
                    'label': 'Invalid_Response',
                    'log': 'Invalid entry. Please try again',
                    'playPrompt': ['callflow:1009'],
                    'playLog': ['Invalid entry. Please try again'],
                    'maxLoop': ['Loop-D', 3, 'Problems'],
                    'goto': 'Offer',
                    'nobarge': 1
                }
                confirmation_nodes.append(invalid_node)
                
                return confirmation_nodes
        
        return None

    def _add_enhanced_error_handling(self, ivr_node: Dict, node_text: str, label: str, node_type: str):
        """Add enhanced error handling patterns like production scripts"""
        text_lower = node_text.lower().strip()
        
        # Error handling patterns based on production scripts
        error_patterns = [
            # Input validation errors
            {
                'trigger': r'invalid.*entry|invalid.*input|try.*again',
                'maxLoop': ['Loop-Invalid Entry', 5, 'Problems'],
                'errorPrompt': 'callflow:1009',
                'nonePrompt': 'callflow:1009',
                'nobarge': 1
            },
            
            # PIN entry errors
            {
                'trigger': r'pin.*incorrect|wrong.*pin|invalid.*pin',
                'maxLoop': ['Loop-PIN', 3, 'Problems'],
                'errorPrompt': 'callflow:1009',
                'nonePrompt': 'callflow:1009'
            },
            
            # Offer retry patterns
            {
                'trigger': r'offer.*retry|retry.*offer|try.*again.*offer',
                'maxLoop': ['Loop-E', 3, 'Problems'],
                'resetLoop': 'Main'
            },
            
            # Decision retry patterns
            {
                'trigger': r'confirm.*retry|confirmation.*error',
                'maxLoop': ['Loop-F', 3, 'Problems']
            },
            
            # Transfer failure patterns
            {
                'trigger': r'transfer.*failed|unable.*transfer',
                'errorPrompt': 'callflow:1353',
                'goto': 'Problems'
            }
        ]
        
        # Apply error handling patterns
        for pattern_info in error_patterns:
            if re.search(pattern_info['trigger'], text_lower):
                # Add maxLoop for retry logic
                if 'maxLoop' in pattern_info:
                    ivr_node['maxLoop'] = pattern_info['maxLoop']
                
                # Add error prompts
                if 'errorPrompt' in pattern_info:
                    if 'getDigits' not in ivr_node:
                        ivr_node['getDigits'] = {}
                    ivr_node['getDigits']['errorPrompt'] = pattern_info['errorPrompt']
                
                # Add none prompts
                if 'nonePrompt' in pattern_info:
                    if 'getDigits' not in ivr_node:
                        ivr_node['getDigits'] = {}
                    ivr_node['getDigits']['nonePrompt'] = pattern_info['nonePrompt']
                
                # Add nobarge
                if 'nobarge' in pattern_info:
                    ivr_node['nobarge'] = pattern_info['nobarge']
                
                # Add resetLoop
                if 'resetLoop' in pattern_info:
                    ivr_node['resetLoop'] = pattern_info['resetLoop']
                
                # Add goto for terminal errors
                if 'goto' in pattern_info:
                    ivr_node['goto'] = pattern_info['goto']
                
                break  # Use first match
        
        # Add sophisticated error branches for getDigits nodes
        if 'getDigits' in ivr_node and 'branch' in ivr_node:
            # Ensure error and none branches exist
            if 'error' not in ivr_node['branch']:
                if 'invalid' in label.lower():
                    ivr_node['branch']['error'] = 'Problems'
                else:
                    ivr_node['branch']['error'] = 'Invalid Entry'
            
            if 'none' not in ivr_node['branch']:
                if 'offer' in label.lower() or 'available' in text_lower:
                    ivr_node['branch']['none'] = 'Invalid Entry'
                else:
                    ivr_node['branch']['none'] = 'Problems'

    def _split_text_into_segments(self, text: str) -> List[str]:
        """Split text into logical segments for voice file matching"""
        # Remove HTML breaks and normalize
        text = text.replace('<br/>', '\n').replace('\\n', '\n')
        
        # Clean up quotes and formatting
        text = text.replace('"', '').replace('\\', '')
        
        # Split by newlines first
        segments = []
        for line in text.split('\n'):
            line = line.strip()
            if line:
                # Further split by sentence-ending punctuation
                import re
                sentence_parts = re.split(r'[.!?]+', line)
                for part in sentence_parts:
                    part = part.strip()
                    if part and len(part) > 3:  # Skip very short segments
                        segments.append(part)
        
        return segments if segments else [text.strip()]

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

    def _clean_inbound_flow_nodes(self, ivr_flow: List[Dict]) -> List[Dict]:
        """Remove unnecessary nodes for inbound flows based on developer feedback"""
        cleaned_flow = []
        
        for node in ivr_flow:
            label = node.get('label', '')
            
            # Skip unnecessary nodes for inbound flows
            if label in ['Main Menu', 'Hangup'] and any('returnsub' in n.get('', {}) for n in ivr_flow):
                print(f"REMOVING: Unnecessary inbound node: {label}")
                continue
            
            # Update goto references to removed nodes
            if 'goto' in node:
                if node['goto'] in ['Main Menu', 'Hangup']:
                    # For inbound flows, acceptance should use returnsub
                    if 'accept' in label.lower():
                        # Remove goto, the returnsub will handle flow
                        del node['goto']
                    else:
                        node['goto'] = 'hangup'
            
            cleaned_flow.append(node)
        
        return cleaned_flow

    def _generate_javascript_output(self, ivr_flow: List[Dict]) -> str:
        """Generate production JavaScript output matching allflows LITE structure"""
        
        js_output = "module.exports = [\n"
        
        for i, node in enumerate(ivr_flow):
            js_output += "    {\n"
            
            for key, value in node.items():
                if isinstance(value, str):
                    # Clean log entries - no truncation or double quotes
                    if key == "log":
                        # Remove quotes and truncation
                        clean_value = value.replace('"', '').replace('...', '').strip()
                        if len(clean_value) > 100:
                            clean_value = clean_value[:100]  # Reasonable limit without "..."
                        js_output += f'        {key}: "{clean_value}",\n'
                    else:
                        escaped_value = value.replace('"', '\\"').replace('\n', '\\n')
                        js_output += f'        {key}: "{escaped_value}",\n'
                        
                elif isinstance(value, list):
                    # Handle arrays - special formatting for gosub
                    if key == "gosub" and len(value) == 3:
                        # Simple gosub format: ["SaveCallResult", 1001, "Accept"]
                        js_output += f'        {key}: ["{value[0]}", {value[1]}, "{value[2]}"],\n'
                    else:
                        js_output += f'        {key}: [\n'
                        for j, item in enumerate(value):
                            if isinstance(item, str):
                                escaped_item = item.replace('"', '\\"')
                                js_output += f'            "{escaped_item}"'
                            else:
                                js_output += f'            {json.dumps(item)}'
                            if j < len(value) - 1:
                                js_output += ","
                            js_output += "\n"
                        js_output += "        ],\n"
                        
                elif isinstance(value, dict):
                    # Handle objects - NO quotes around property names for allflows LITE format
                    js_output += f'        {key}: {{\n'
                    dict_items = list(value.items())
                    for j, (dict_key, dict_value) in enumerate(dict_items):
                        # Check if dict_key should be unquoted (numbers, error, none, etc.)
                        if dict_key.isdigit() or dict_key in ['error', 'none', 'yes', 'no']:
                            property_name = dict_key  # No quotes for numbers and standard keys
                        else:
                            property_name = dict_key  # Keep as is for other keys
                            
                        if isinstance(dict_value, str):
                            escaped_dict_value = dict_value.replace('"', '\\"')
                            js_output += f'            {property_name}: "{escaped_dict_value}"'
                        else:
                            js_output += f'            {property_name}: {json.dumps(dict_value)}'
                        if j < len(dict_items) - 1:
                            js_output += ","
                        js_output += "\n"
                    js_output += "        },\n"
                    
                elif isinstance(value, int):
                    js_output += f'        {key}: {value},\n'
                else:
                    js_output += f'        {key}: {json.dumps(value)},\n'
            
            js_output += "    }"
            if i < len(ivr_flow) - 1:
                js_output += ","
            js_output += "\n"
        
        js_output += "];\n"
        return js_output


def convert_mermaid_to_ivr(mermaid_code: str, cf_general_csv=None, arcos_csv=None, use_dynamodb=True) -> Tuple[List[Dict], str]:
    """Main function for FLEXIBLE ARCOS-integrated conversion with DynamoDB support"""
    converter = FlexibleARCOSConverter(cf_general_csv, arcos_csv, use_dynamodb)
    return converter.convert_mermaid_to_ivr(mermaid_code)