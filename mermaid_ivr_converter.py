"""
Production-Ready Mermaid to IVR Converter
Follows exact allflows lite conventions for deployable IVR code
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

class NodeType(Enum):
    WELCOME = "welcome"
    DECISION = "decision"
    ACTION = "action"
    PIN_ENTRY = "pin_entry"
    RESPONSE = "response"
    GOODBYE = "goodbye"
    ERROR = "error"
    SLEEP = "sleep"

@dataclass
class ParsedNode:
    id: str
    original_text: str
    node_type: NodeType
    label: str
    segments: List[str]
    variables: Dict[str, str]
    connections: List[Dict[str, str]]

class ProductionMermaidIVRConverter:
    def __init__(self):
        # Variable patterns for detection and conversion
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
            r'\(contact\s*id\)': '{{contact_id}}'
        }
        
        # Production callflow ID mappings
        self.callflow_mappings = {
            'this_is_an': '1191',
            'callout': '1274',
            'from': '1589',
            'press_1': '1002',
            'press_3': '1005',
            'press_7': '1641',
            'press_9': '1643',
            'if_this_is': '1002',
            'need_more_time': '1005',
            'to_the_phone': '1006',
            'is_not_home': '1004',
            'to_repeat': '1643',
            'enter_pin': '1008',
            'invalid_entry': '1009',
            'available_callout': '1316',
            'accepted_response': '1167',
            'decline_response': '1021',
            'qualified_no': '1266',
            'not_home': '1017',
            'goodbye': '1029',
            'problems': '1351',
            'please_have': '1017',
            'call_the': '1174',
            'callout_system': '1290',
            'at': '1015',
            'press_any_key': '1265',
            'thank_you': '1029',
            'error_message': '1351'
        }
        
        # Standard response codes
        self.response_codes = {
            'accept': ['SaveCallResult', 1001, 'Accept'],
            'decline': ['SaveCallResult', 1002, 'Decline'],
            'not_home': ['SaveCallResult', 1006, 'NotHome'],
            'qualified_no': ['SaveCallResult', 1145, 'QualNo'],
            'error': ['SaveCallResult', 1198, 'Error Out']
        }
        
        # Callflow ID counter for unique IDs
        self.callflow_counter = 2000

    def convert(self, mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Main conversion method"""
        notes = []
        
        try:
            # Parse the mermaid diagram
            parsed_nodes, connections = self._parse_mermaid(mermaid_code)
            
            if not parsed_nodes:
                notes.append("No nodes parsed from Mermaid diagram")
                return self._create_fallback_flow(), notes
            
            notes.append(f"Parsed {len(parsed_nodes)} nodes and {len(connections)} connections")
            
            # Generate production IVR flow
            ivr_nodes = self._generate_production_flow(parsed_nodes, connections)
            
            if not ivr_nodes:
                notes.append("No IVR nodes generated")
                return self._create_fallback_flow(), notes
            
            notes.append(f"Generated {len(ivr_nodes)} production IVR nodes")
            
            return ivr_nodes, notes
            
        except Exception as e:
            notes.append(f"Conversion failed: {str(e)}")
            return self._create_fallback_flow(), notes

    def _parse_mermaid(self, mermaid_code: str) -> Tuple[Dict[str, ParsedNode], List[Dict[str, str]]]:
        """Parse mermaid code following production patterns"""
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        
        nodes = {}
        connections = []
        
        for line in lines:
            if line.startswith('flowchart') or line.startswith('%%'):
                continue
            
            # Parse connections and extract inline nodes
            if '-->' in line:
                conn = self._parse_connection(line)
                if conn:
                    connections.append(conn)
                
                # Extract inline node definitions
                inline_nodes = self._extract_inline_nodes(line)
                for node in inline_nodes:
                    if node.id not in nodes:
                        nodes[node.id] = node
            else:
                # Parse standalone node definitions
                node = self._parse_node_definition(line)
                if node:
                    nodes[node.id] = node
        
        return nodes, connections

    def _parse_connection(self, line: str) -> Optional[Dict[str, str]]:
        """Parse connections with robust pattern matching"""
        patterns = [
            r'^(\w+)\s*-->\s*\|"([^"]+)"\|\s*(\w+)',  # A -->|"label"| B
            r'^(\w+)\s*-->\s*\|([^|]+)\|\s*(\w+)',    # A -->|label| B  
            r'^(\w+)\s*-->\s*(\w+)',                  # A --> B
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    source, label, target = groups
                    return {
                        'source': source.strip(),
                        'target': target.strip(),
                        'label': label.strip() if label else ''
                    }
                elif len(groups) == 2:
                    source, target = groups
                    return {
                        'source': source.strip(),
                        'target': target.strip(),
                        'label': ''
                    }
        return None

    def _extract_inline_nodes(self, line: str) -> List[ParsedNode]:
        """Extract inline node definitions from connection lines"""
        inline_nodes = []
        node_patterns = [
            r'(\w+)\s*\["([^"]+)"\]',  # A["text"]
            r'(\w+)\s*\{"([^"]+)"\}',  # A{"text"}
            r'(\w+)\s*\("([^"]+)"\)',  # A("text")
        ]
        
        for pattern in node_patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                node_id, text = match.groups()
                clean_text = re.sub(r'<br\s*/?>', ' ', text).strip()
                
                node_type = self._determine_node_type(clean_text)
                label = self._generate_production_label(clean_text, node_type)
                segments, variables = self._segment_for_production(clean_text)
                
                inline_nodes.append(ParsedNode(
                    id=node_id,
                    original_text=clean_text,
                    node_type=node_type,
                    label=label,
                    segments=segments,
                    variables=variables,
                    connections=[]
                ))
        
        return inline_nodes

    def _parse_node_definition(self, line: str) -> Optional[ParsedNode]:
        """Parse standalone node definitions"""
        patterns = [
            r'^(\w+)\s*\["([^"]+)"\]',
            r'^(\w+)\s*\{"([^"]+)"\}',
            r'^(\w+)\s*\("([^"]+)"\)',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                node_id, text = match.groups()
                clean_text = re.sub(r'<br\s*/?>', ' ', text).strip()
                
                node_type = self._determine_node_type(clean_text)
                label = self._generate_production_label(clean_text, node_type)
                segments, variables = self._segment_for_production(clean_text)
                
                return ParsedNode(
                    id=node_id,
                    original_text=clean_text,
                    node_type=node_type,
                    label=label,
                    segments=segments,
                    variables=variables,
                    connections=[]
                )
        return None

    def _determine_node_type(self, text: str) -> NodeType:
        """Determine node type based on content"""
        text_lower = text.lower()
        
        if 'welcome' in text_lower or 'this is an' in text_lower:
            return NodeType.WELCOME
        elif 'enter' in text_lower and 'pin' in text_lower:
            return NodeType.PIN_ENTRY
        elif 'press' in text_lower and ('1' in text_lower or '3' in text_lower):
            return NodeType.DECISION
        elif any(word in text_lower for word in ['accept', 'decline', 'not home', 'qualified']):
            return NodeType.RESPONSE
        elif 'goodbye' in text_lower or 'thank you' in text_lower:
            return NodeType.GOODBYE
        elif 'press any key' in text_lower or '30-second' in text_lower:
            return NodeType.SLEEP
        elif 'problem' in text_lower or 'error' in text_lower:
            return NodeType.ERROR
        else:
            return NodeType.ACTION

    def _generate_production_label(self, text: str, node_type: NodeType) -> str:
        """Generate production-style labels"""
        text_lower = text.lower()
        
        # Specific pattern matching for production labels
        if 'welcome' in text_lower or 'this is an' in text_lower:
            return "Live Answer"
        elif 'enter' in text_lower and 'pin' in text_lower:
            return "Enter PIN"
        elif 'employee not home' in text_lower:
            return "Not Home"
        elif 'accepted response' in text_lower:
            return "Accept"
        elif 'callout decline' in text_lower:
            return "Decline"
        elif 'qualified no' in text_lower:
            return "Qualified No"
        elif 'goodbye' in text_lower:
            return "Goodbye"
        elif 'disconnect' in text_lower:
            return "Disconnect"
        elif 'invalid' in text_lower:
            return "Invalid Entry"
        elif 'correct pin' in text_lower:
            return "Check PIN"
        elif 'available' in text_lower and 'callout' in text_lower:
            return "Offer"
        elif 'callout reason' in text_lower:
            return "Callout Reason"
        elif 'trouble location' in text_lower:
            return "Trouble Location"
        elif 'custom message' in text_lower:
            return "Custom Message"
        elif '30-second' in text_lower or 'press any key' in text_lower:
            return "Sleep"
        elif node_type == NodeType.ERROR:
            return "Problems"
        else:
            # Generate from meaningful words
            words = re.findall(r'\b[a-zA-Z]+\b', text)
            key_words = [w for w in words[:3] if len(w) > 2 and w.lower() not in ['the', 'and', 'for', 'are', 'you', 'this']]
            return ' '.join(key_words[:2]).title() if key_words else "Action"

    def _segment_for_production(self, text: str) -> Tuple[List[str], Dict[str, str]]:
        """Segment text following production patterns"""
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
        
        # Production segmentation patterns
        if 'this is an' in text.lower() and 'callout' in text.lower():
            # Handle main welcome message
            segments = self._segment_welcome_message(processed_text)
        elif 'press 1' in text.lower() and 'press' in text.lower():
            # Handle multi-press instructions
            segments = self._segment_press_instructions(processed_text)
        elif 'available' in text.lower() and 'callout' in text.lower():
            # Handle availability question
            segments = self._segment_availability_question(processed_text)
        else:
            # Simple segmentation
            segments = [processed_text]
        
        return segments, variables

    def _segment_welcome_message(self, text: str) -> List[str]:
        """Segment welcome message following production patterns"""
        segments = []
        
        # Extract "This is an"
        if 'this is an' in text.lower():
            segments.append("This is an")
            remaining = re.sub(r'this\s+is\s+an\s+', '', text, flags=re.IGNORECASE).strip()
        else:
            remaining = text
        
        # Extract callout type
        if 'callout' in remaining.lower():
            parts = re.split(r'\s+callout\s+', remaining, 1, flags=re.IGNORECASE)
            if len(parts) == 2:
                if parts[0].strip():
                    segments.append(parts[0].strip())
                segments.append("callout")
                if parts[1].strip():
                    # Further segment the rest
                    rest_segments = self._segment_press_instructions(parts[1].strip())
                    segments.extend(rest_segments)
            else:
                segments.append(remaining)
        else:
            segments.append(remaining)
        
        return segments

    def _segment_press_instructions(self, text: str) -> List[str]:
        """Segment press instructions following production patterns"""
        segments = []
        
        # Split by sentence boundaries and press instructions
        parts = re.split(r'(press\s+\d+[^.]*\.?)', text, flags=re.IGNORECASE)
        
        for part in parts:
            part = part.strip()
            if part:
                if 'press' in part.lower():
                    # Further split press instructions
                    press_parts = re.split(r'(press\s+\d+)', part, flags=re.IGNORECASE)
                    for p in press_parts:
                        p = p.strip()
                        if p and p != '.':
                            segments.append(p)
                else:
                    segments.append(part)
        
        return [s for s in segments if s and s.strip()]

    def _segment_availability_question(self, text: str) -> List[str]:
        """Segment availability question following production patterns"""
        # Production pattern for availability questions
        segments = []
        
        # Split on key phrases
        parts = re.split(r'(if\s+yes[^.]*\.?|if\s+no[^.]*\.?|press\s+\d+)', text, flags=re.IGNORECASE)
        
        for part in parts:
            part = part.strip()
            if part and part != '.':
                segments.append(part)
        
        return segments if segments else [text]

    def _generate_production_flow(self, nodes: Dict[str, ParsedNode], connections: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Generate production IVR flow following allflows patterns"""
        production_nodes = []
        used_labels = set()
        
        # Build connection map
        conn_map = {}
        for conn in connections:
            if conn['source'] not in conn_map:
                conn_map[conn['source']] = []
            conn_map[conn['source']].append(conn)
        
        # Find start node
        incoming = {conn['target'] for conn in connections}
        start_nodes = [node_id for node_id in nodes.keys() if node_id not in incoming]
        
        if not start_nodes and nodes:
            start_nodes = [sorted(nodes.keys())[0]]
        
        # Process nodes in production order
        processed = set()
        for start_node in start_nodes:
            self._process_production_node(start_node, nodes, conn_map, production_nodes, processed, used_labels)
        
        # Process remaining nodes
        for node_id in nodes.keys():
            if node_id not in processed:
                self._process_production_node(node_id, nodes, conn_map, production_nodes, processed, used_labels)
        
        # Ensure standard handlers exist
        self._ensure_standard_handlers(production_nodes, used_labels)
        
        return production_nodes

    def _process_production_node(self, node_id: str, nodes: Dict[str, ParsedNode], 
                                conn_map: Dict[str, List[Dict[str, str]]], 
                                production_nodes: List[Dict[str, Any]], 
                                processed: Set[str], used_labels: Set[str]):
        """Process node into production format"""
        if node_id in processed or node_id not in nodes:
            return
        
        processed.add(node_id)
        node = nodes[node_id]
        
        # Ensure unique label
        if node.label in used_labels:
            counter = 2
            while f"{node.label} {counter}" in used_labels:
                counter += 1
            node.label = f"{node.label} {counter}"
        used_labels.add(node.label)
        
        # Generate production nodes based on type
        node_connections = conn_map.get(node_id, [])
        generated_nodes = self._create_production_nodes(node, node_connections)
        
        for prod_node in generated_nodes:
            production_nodes.append(prod_node)
        
        # Process connected nodes
        for conn in node_connections:
            if conn['target'] in nodes:
                self._process_production_node(conn['target'], nodes, conn_map, production_nodes, processed, used_labels)

    def _create_production_nodes(self, node: ParsedNode, connections: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Create production nodes following allflows patterns"""
        text_lower = node.original_text.lower()
        
        # Main welcome message with decision logic
        if node.node_type == NodeType.WELCOME and 'press' in text_lower:
            return self._create_welcome_decision_nodes(node, connections)
        
        # Response handlers (split into multiple nodes)
        elif node.node_type == NodeType.RESPONSE:
            return self._create_response_handler_nodes(node, text_lower)
        
        # PIN entry
        elif node.node_type == NodeType.PIN_ENTRY:
            return self._create_pin_entry_nodes(node, connections)
        
        # Availability offer
        elif 'available' in text_lower and 'callout' in text_lower:
            return self._create_offer_nodes(node, connections)
        
        # Sleep/wait
        elif node.node_type == NodeType.SLEEP:
            return self._create_sleep_nodes(node, connections)
        
        # Standard single node
        else:
            return [self._create_standard_node(node, connections)]

    def _create_welcome_decision_nodes(self, node: ParsedNode, connections: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Create welcome message with decision logic following production patterns"""
        
        # Generate playLog and playPrompt
        play_log, play_prompt = self._generate_production_prompts(node.segments, node.variables)
        
        # Build branch mapping
        branch_map = {}
        valid_choices = []
        
        for conn in connections:
            label = conn['label'].lower()
            target = conn['target']
            
            if '1' in label or 'employee' in label:
                valid_choices.append('1')
                branch_map['1'] = target
            elif '3' in label or 'need more time' in label:
                valid_choices.append('3')
                branch_map['3'] = target
            elif '7' in label or 'not home' in label:
                valid_choices.append('7')
                branch_map['7'] = target
            elif '9' in label or 'repeat' in label:
                valid_choices.append('9')
                branch_map['9'] = target
            elif 'no input' in label or 'go to pg' in label:
                branch_map['none'] = target
            elif 'retry' in label or 'invalid' in label:
                branch_map['error'] = target
        
        # Set defaults
        if 'error' not in branch_map:
            branch_map['error'] = node.label  # Loop back to self
        if 'none' not in branch_map:
            branch_map['none'] = 'Sleep'
        
        if not valid_choices:
            valid_choices = ['1', '3', '7', '9']
        
        # Create the main node
        main_node = {
            "label": node.label,
            "maxLoop": ["Main", 3, "Problems"],  # Production pattern
        }
        
        # Add playLog/playPrompt
        if len(play_log) > 1:
            main_node["playLog"] = play_log
        else:
            main_node["log"] = play_log[0] if play_log else node.original_text
        
        main_node["playPrompt"] = play_prompt
        
        # Add getDigits with production settings
        main_node["getDigits"] = {
            "numDigits": 1,
            "maxTime": 1,  # Production uses 1 for main menu
            "validChoices": "|".join(sorted(valid_choices)),
            "errorPrompt": "callflow:1009"
        }
        
        main_node["branch"] = branch_map
        
        return [main_node]

    def _create_response_handler_nodes(self, node: ParsedNode, text_lower: str) -> List[Dict[str, Any]]:
        """Create response handler nodes (split pattern from production)"""
        nodes = []
        
        # Determine response type
        if 'accept' in text_lower:
            gosub_code = self.response_codes['accept']
            confirmation_prompt = "callflow:1167"
            confirmation_text = "An accepted response has been recorded."
        elif 'decline' in text_lower:
            gosub_code = self.response_codes['decline']
            confirmation_prompt = "callflow:1021"
            confirmation_text = "Your response is being recorded as a decline."
        elif 'not home' in text_lower:
            gosub_code = self.response_codes['not_home']
            confirmation_prompt = "callflow:1017"
            confirmation_text = "Please have"
        elif 'qualified' in text_lower:
            gosub_code = self.response_codes['qualified_no']
            confirmation_prompt = "callflow:1266"
            confirmation_text = "You may be called again on this callout if no one else accepts"
        else:
            gosub_code = self.response_codes['error']
            confirmation_prompt = "callflow:1351"
            confirmation_text = "Error occurred"
        
        # First node: gosub call
        gosub_node = {
            "label": node.label,
            "gosub": gosub_code
        }
        nodes.append(gosub_node)
        
        # Second node: confirmation message
        confirmation_node = {
            "log": confirmation_text,
            "playPrompt": confirmation_prompt,
            "nobarge": "1",
            "goto": "Goodbye"
        }
        nodes.append(confirmation_node)
        
        return nodes

    def _create_pin_entry_nodes(self, node: ParsedNode, connections: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Create PIN entry following production patterns"""
        return [{
            "label": node.label,
            "log": "Please enter your four digit PIN followed by the pound key",
            "playPrompt": "callflow:1008",
            "getDigits": {
                "numDigits": 5,  # Production uses 5 (4 digits + pound)
                "maxTries": 3,
                "maxTime": 7,
                "validChoices": "{{pin}}",
                "errorPrompt": "callflow:1009",
                "nonePrompt": "callflow:1009"
            },
            "branch": {
                "error": "Problems",
                "none": "Problems"
            }
        }]

    def _create_offer_nodes(self, node: ParsedNode, connections: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Create offer nodes following production patterns"""
        
        # Build branch mapping
        branch_map = {}
        valid_choices = ['1', '3']
        
        for conn in connections:
            label = conn['label'].lower()
            target = conn['target']
            
            if '1' in label or 'accept' in label:
                branch_map['1'] = target
            elif '3' in label or 'decline' in label:
                branch_map['3'] = target
            elif '9' in label or 'call back' in label:
                valid_choices.append('9')
                branch_map['9'] = target
        
        # Set defaults
        if 'error' not in branch_map:
            branch_map['error'] = 'Problems'
        if 'none' not in branch_map:
            branch_map['none'] = 'Problems'
        
        return [{
            "label": node.label,
            "log": "Are you available to work this callout?",
            "playPrompt": "callflow:1316",
            "getDigits": {
                "numDigits": 1,
                "maxTries": 3,
                "maxTime": 7,
                "validChoices": "|".join(valid_choices),
                "errorPrompt": "callflow:1009",
                "nonePrompt": "callflow:1009"
            },
            "branch": branch_map
        }]

    def _create_sleep_nodes(self, node: ParsedNode, connections: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Create sleep nodes following production patterns"""
        
        target = connections[0]['target'] if connections else "Live Answer"
        
        return [{
            "label": node.label,
            "log": "Press any key to continue..",
            "playPrompt": "callflow:1265",
            "getDigits": {
                "numDigits": 1
            },
            "maxLoop": ["Loop-B", 2, "Problems"],
            "branch": {
                "next": target,
                "none": target
            }
        }]

    def _create_standard_node(self, node: ParsedNode, connections: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create standard single node"""
        
        play_log, play_prompt = self._generate_production_prompts(node.segments, node.variables)
        
        prod_node = {
            "label": node.label
        }
        
        # Add log
        if len(play_log) > 1:
            prod_node["playLog"] = play_log
        else:
            prod_node["log"] = play_log[0] if play_log else node.original_text
        
        prod_node["playPrompt"] = play_prompt
        
        # Add flow control
        if len(connections) == 1:
            prod_node["goto"] = connections[0]['target']
        elif 'goodbye' in node.original_text.lower():
            prod_node["nobarge"] = "1"
            prod_node["goto"] = "hangup"
        
        return prod_node

    def _generate_production_prompts(self, segments: List[str], variables: Dict[str, str]) -> Tuple[List[str], List[str]]:
        """Generate production playLog and playPrompt"""
        play_log = []
        play_prompt = []
        
        for segment in segments:
            # Clean segment for log
            log_segment = segment
            for var_text, var_replacement in variables.items():
                log_segment = log_segment.replace(var_replacement, var_text)
            play_log.append(log_segment)
            
            # Generate production prompt
            if any(var in segment for var in variables.values()):
                # Contains variables - use as-is
                play_prompt.append(segment)
            else:
                # Generate production callflow ID
                callflow_id = self._get_production_callflow_id(segment)
                play_prompt.append(f"callflow:{callflow_id}")
        
        return play_log, play_prompt

    def _get_production_callflow_id(self, text: str) -> str:
        """Get production callflow ID following allflows patterns"""
        text_lower = text.lower()
        
        # Try to match known patterns
        for pattern, callflow_id in self.callflow_mappings.items():
            if pattern.replace('_', ' ') in text_lower:
                return callflow_id
        
        # Generate new ID
        self.callflow_counter += 1
        return str(self.callflow_counter)

    def _ensure_standard_handlers(self, production_nodes: List[Dict[str, Any]], used_labels: Set[str]):
        """Ensure standard handlers exist"""
        
        # Check if Goodbye exists
        if not any(node.get('label') == 'Goodbye' for node in production_nodes):
            production_nodes.append({
                "label": "Goodbye",
                "log": "Goodbye(1029)",
                "playPrompt": "callflow:1029",
                "nobarge": "1",
                "goto": "hangup"
            })
        
        # Check if Problems exists
        if not any(node.get('label') == 'Problems' for node in production_nodes):
            # Problems handler (multiple nodes following production pattern)
            problems_nodes = [
                {
                    "label": "Problems",
                    "gosub": ["SaveCallResult", 1198, "Error Out"]
                },
                {
                    "nobarge": "1",
                    "playLog": ["I'm sorry you are having problems.", "Please have", "Employee name"],
                    "playPrompt": ["callflow:1351", "callflow:1017", "names:{{contact_id}}"]
                },
                {
                    "log": "call the",
                    "playPrompt": "callflow:1174"
                },
                {
                    "nobarge": "1",
                    "playLog": ["location", "callout system", "at", "speak phone num"],
                    "playPrompt": ["location:{{level2_location}}", "callflow:1290", "callflow:1015", "digits:{{callback_number}}"],
                    "goto": "Goodbye"
                }
            ]
            production_nodes.extend(problems_nodes)

    def _create_fallback_flow(self) -> List[Dict[str, Any]]:
        """Create fallback flow when parsing fails"""
        return [
            {
                "label": "Live Answer",
                "log": "Welcome message",
                "playPrompt": "callflow:2001",
                "goto": "Problems"
            },
            {
                "label": "Problems",
                "log": "Error handler",
                "playPrompt": "callflow:1351",
                "goto": "hangup"
            }
        ]


def convert_mermaid_to_ivr(mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Main conversion function"""
    converter = ProductionMermaidIVRConverter()
    return converter.convert(mermaid_code)