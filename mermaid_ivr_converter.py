"""
Enhanced Mermaid to IVR Converter
Follows Andres's conventions and generates production-ready IVR code
with descriptive labels, proper variable handling, and text segmentation.
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

@dataclass
class IVRNode:
    label: str
    playLog: List[str]
    playPrompt: List[str]
    getDigits: Optional[Dict[str, Any]] = None
    branch: Optional[Dict[str, str]] = None
    goto: Optional[str] = None
    gosub: Optional[List[Any]] = None
    nobarge: Optional[str] = None
    maxLoop: Optional[List[Any]] = None

class EnhancedMermaidIVRConverter:
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
        
        # Node type detection patterns
        self.node_type_patterns = {
            NodeType.WELCOME: [
                r'welcome', r'this\s+is\s+an?\s+.*callout', r'greeting', r'introduction'
            ],
            NodeType.PIN_ENTRY: [
                r'enter.*pin', r'pin.*entry', r'enter.*password', r'4\s*digit.*pin'
            ],
            NodeType.DECISION: [
                r'press\s+\d+.*if', r'available.*to.*work', r'correct.*pin', 
                r'is\s+this', r'are\s+you', r'do\s+you'
            ],
            NodeType.RESPONSE: [
                r'accept', r'decline', r'not\s+home', r'qualified.*no', r'response.*recorded'
            ],
            NodeType.GOODBYE: [
                r'goodbye', r'thank\s+you', r'disconnect', r'end\s+call'
            ],
            NodeType.ERROR: [
                r'problem', r'error', r'invalid', r'retry', r'sorry'
            ],
            NodeType.SLEEP: [
                r'press\s+any\s+key', r'continue', r'wait', r'more\s+time'
            ]
        }
        
        # Common IVR flow structures
        self.standard_responses = {
            'accept': ['SaveCallResult', 1001, 'Accept'],
            'decline': ['SaveCallResult', 1002, 'Decline'],
            'not_home': ['SaveCallResult', 1006, 'NotHome'],
            'qualified_no': ['SaveCallResult', 1145, 'QualNo'],
            'error': ['SaveCallResult', 1198, 'Error Out']
        }

    def convert(self, mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Main conversion method"""
        notes = []
        
        try:
            # Parse the mermaid diagram
            parsed_nodes, connections = self._parse_mermaid(mermaid_code)
            
            # Debug: Check if we parsed anything
            if not parsed_nodes:
                notes.append("No nodes were parsed from the Mermaid diagram")
                return self._create_fallback_flow(), notes
            
            if not connections:
                notes.append("No connections were parsed from the Mermaid diagram")
            
            notes.append(f"Parsed {len(parsed_nodes)} nodes and {len(connections)} connections")
            
            # Generate IVR flow
            ivr_nodes = self._generate_ivr_flow(parsed_nodes, connections)
            
            # Check if we generated any nodes
            if not ivr_nodes:
                notes.append("No IVR nodes were generated")
                return self._create_fallback_flow(), notes
            
            notes.append(f"Generated {len(ivr_nodes)} IVR nodes")
            
            # Convert to dictionary format for JSON serialization
            ivr_dict = [self._node_to_dict(node) for node in ivr_nodes]
            
            return ivr_dict, notes
            
        except Exception as e:
            # Return error handler if conversion fails
            notes.append(f"Conversion failed with error: {str(e)}")
            return self._create_fallback_flow(), notes

    def _create_fallback_flow(self) -> List[Dict[str, Any]]:
        """Create a basic fallback flow when parsing fails"""
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
                "playPrompt": "callflow:ErrorMessage",
                "goto": "hangup"
            }
        ]

    def _parse_mermaid(self, mermaid_code: str) -> Tuple[Dict[str, ParsedNode], List[Dict[str, str]]]:
        """Parse mermaid code into structured nodes and connections"""
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        
        nodes = {}
        connections = []
        
        for line in lines:
            # Skip flowchart definition and comments
            if line.startswith('flowchart') or line.startswith('%%'):
                continue
            
            # Parse connections (may contain inline node definitions)
            if '-->' in line:
                conn = self._parse_connection(line)
                if conn:
                    connections.append(conn)
                
                # Also extract any inline node definitions from the connection line
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

    def _extract_inline_nodes(self, line: str) -> List[ParsedNode]:
        """Extract node definitions that appear inline in connection lines"""
        inline_nodes = []
        
        # Pattern to find nodes like: A["text"] or B{"text"} in connection lines
        node_patterns = [
            r'(\w+)\s*\["([^"]+)"\]',  # A["text"]
            r'(\w+)\s*\{"([^"]+)"\}',  # A{"text"}
            r'(\w+)\s*\("([^"]+)"\)',  # A("text")
        ]
        
        for pattern in node_patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                node_id, text = match.groups()
                
                # Clean up text
                clean_text = re.sub(r'<br\s*/?>', ' ', text).strip()
                
                # Determine node type
                node_type = self._determine_node_type(clean_text)
                
                # Generate descriptive label
                label = self._generate_descriptive_label(clean_text, node_type)
                
                # Segment text and detect variables
                segments, variables = self._segment_and_detect_variables(clean_text)
                
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
        """Parse individual node definition"""
        # Match various node syntax patterns
        patterns = [
            r'^(\w+)\s*\["([^"]+)"\]',  # ["text"]
            r'^(\w+)\s*\{"([^"]+)"\}',  # {"text"}
            r'^(\w+)\s*\("([^"]+)"\)',  # ("text")
            r'^(\w+)\s*\[\("([^"]+)"\)\]'  # [("text")]
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                node_id, text = match.groups()
                
                # Clean up text (replace <br/> with spaces)
                clean_text = re.sub(r'<br\s*/?>', ' ', text).strip()
                
                # Determine node type
                node_type = self._determine_node_type(clean_text)
                
                # Generate descriptive label
                label = self._generate_descriptive_label(clean_text, node_type)
                
                # Segment text and detect variables
                segments, variables = self._segment_and_detect_variables(clean_text)
                
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

    def _parse_connection(self, line: str) -> Optional[Dict[str, str]]:
        """Parse connection between nodes"""
        # Handle multiple connection patterns
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

    def _determine_node_type(self, text: str) -> NodeType:
        """Determine node type based on text content"""
        text_lower = text.lower()
        
        for node_type, patterns in self.node_type_patterns.items():
            if any(re.search(pattern, text_lower) for pattern in patterns):
                return node_type
        
        # Default to action if no specific type detected
        return NodeType.ACTION

    def _generate_descriptive_label(self, text: str, node_type: NodeType) -> str:
        """Generate descriptive label following Andres's conventions"""
        
        text_lower = text.lower()
        
        # Handle specific patterns from the mermaid code
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
        elif 'goodbye' in text_lower or 'thank you' in text_lower:
            return "Goodbye"
        elif 'invalid' in text_lower or 'retry' in text_lower:
            return "Invalid Entry"
        elif 'correct pin' in text_lower:
            return "Check PIN"
        elif 'available' in text_lower and 'callout' in text_lower:
            return "Available For Callout"
        elif 'custom message' in text_lower:
            return "Custom Message"
        elif 'callout reason' in text_lower:
            return "Callout Reason"
        elif 'trouble location' in text_lower:
            return "Trouble Location"
        elif 'disconnect' in text_lower:
            return "Disconnect"
        elif '30-second message' in text_lower or 'press any key' in text_lower:
            return "Sleep"
        elif node_type == NodeType.ERROR or 'problem' in text_lower:
            return "Problems"
        elif node_type == NodeType.DECISION:
            # Extract key decision words for unknown decision points
            if re.search(r'press\s+\d+', text_lower):
                return "User Input"
            else:
                return "Decision Point"
        else:
            # Generate label from first meaningful words
            words = re.findall(r'\b[a-zA-Z]+\b', text)
            meaningful_words = [w for w in words[:4] if len(w) > 2 and w.lower() not in ['the', 'and', 'for', 'are', 'you', 'this', 'that']]
            
            if meaningful_words:
                return ' '.join(meaningful_words[:2]).title()
            else:
                return "Action"

    def _segment_and_detect_variables(self, text: str) -> Tuple[List[str], Dict[str, str]]:
        """Segment text and detect variables following Andres's patterns"""
        segments = []
        variables = {}
        remaining_text = text
        
        # First, detect and replace variables
        for pattern, replacement in self.variable_patterns.items():
            matches = list(re.finditer(pattern, remaining_text, re.IGNORECASE))
            for match in reversed(matches):  # Process in reverse to maintain positions
                var_text = match.group(0)
                variables[var_text] = replacement
                remaining_text = remaining_text[:match.start()] + replacement + remaining_text[match.end():]
        
        # Now segment the text into logical voice file components
        segments = self._segment_text_for_voice_files(remaining_text)
        
        return segments, variables

    def _segment_text_for_voice_files(self, text: str) -> List[str]:
        """Segment text into logical voice file components"""
        segments = []
        
        # Handle common callout patterns
        if re.search(r'this\s+is\s+an?\s+.*callout', text.lower()):
            # Pattern: "This is an electric callout from Level 2"
            # Split into components following Andres's approach
            parts = []
            
            # Extract "This is an/a"
            intro_match = re.search(r'(this\s+is\s+an?\s+)', text, re.IGNORECASE)
            if intro_match:
                parts.append(intro_match.group(1).strip())
                remaining = text[intro_match.end():].strip()
            else:
                remaining = text
            
            # Extract callout type and remaining
            if 'callout' in remaining.lower():
                callout_parts = re.split(r'\s+callout\s+', remaining, 1, flags=re.IGNORECASE)
                if len(callout_parts) == 2:
                    # Before "callout"
                    if callout_parts[0].strip():
                        parts.append(callout_parts[0].strip())
                    parts.append("callout")
                    # After "callout"
                    if callout_parts[1].strip():
                        parts.append(callout_parts[1].strip())
                else:
                    parts.append(remaining)
            else:
                parts.append(remaining)
            
            segments = parts
        
        # Handle multi-line press instructions
        elif 'press' in text.lower() and ('\n' in text or '<br' in text):
            # Split by line breaks and periods
            lines = re.split(r'<br\s*/?>\s*|\n\s*', text)
            for line in lines:
                line = line.strip()
                if line:
                    # Further split long lines with press instructions
                    if 'press' in line.lower() and '.' in line:
                        press_parts = re.split(r'\.(?:\s+press|\s+if)', line, flags=re.IGNORECASE)
                        for part in press_parts:
                            part = part.strip()
                            if part:
                                segments.append(part)
                    else:
                        segments.append(line)
        
        # Handle simple sentences
        else:
            # Split on natural breaks (periods, commas followed by space)
            if '.' in text or ',' in text:
                parts = re.split(r'[.,]\s+', text)
                segments = [part.strip() for part in parts if part.strip()]
            else:
                segments = [text]
        
        # Clean up segments
        clean_segments = []
        for segment in segments:
            clean_segment = segment.strip()
            if clean_segment and clean_segment != '.':
                clean_segments.append(clean_segment)
        
        # If no segmentation happened, return the whole text
        return clean_segments if clean_segments else [text]

    def _generate_ivr_flow(self, nodes: Dict[str, ParsedNode], connections: List[Dict[str, str]]) -> List[IVRNode]:
        """Generate IVR flow following Andres's structure"""
        ivr_nodes = []
        
        # Build connection map
        conn_map = {}
        for conn in connections:
            if conn['source'] not in conn_map:
                conn_map[conn['source']] = []
            conn_map[conn['source']].append(conn)
        
        # Find start node (no incoming connections)
        incoming = {conn['target'] for conn in connections}
        start_nodes = [node_id for node_id in nodes.keys() if node_id not in incoming]
        
        # If no clear start node, use the first node alphabetically
        if not start_nodes and nodes:
            start_nodes = [sorted(nodes.keys())[0]]
        
        # Process all nodes, starting with start nodes
        processed = set()
        
        # First, process start nodes and their descendants
        for start_node in start_nodes:
            self._process_node_recursive(start_node, nodes, conn_map, ivr_nodes, processed)
        
        # Then process any remaining unprocessed nodes (in case of disconnected subgraphs)
        for node_id in nodes.keys():
            if node_id not in processed:
                self._process_node_recursive(node_id, nodes, conn_map, ivr_nodes, processed)
        
        # Add standard error handler if not present
        if not any(node.label == "Problems" for node in ivr_nodes):
            ivr_nodes.append(self._create_error_handler())
        
        return ivr_nodes

    def _process_node_recursive(self, node_id: str, nodes: Dict[str, ParsedNode], 
                               conn_map: Dict[str, List[Dict[str, str]]], 
                               ivr_nodes: List[IVRNode], processed: Set[str]):
        """Recursively process nodes to build IVR flow"""
        if node_id in processed or node_id not in nodes:
            return
        
        processed.add(node_id)
        node = nodes[node_id]
        
        # Create IVR node based on type
        node_connections = conn_map.get(node_id, [])
        ivr_node = self._create_ivr_node(node, node_connections)
        ivr_nodes.append(ivr_node)
        
        # Process connected nodes
        for conn in node_connections:
            if conn['target'] in nodes:  # Only process if target node exists
                self._process_node_recursive(conn['target'], nodes, conn_map, ivr_nodes, processed)

    def _create_ivr_node(self, node: ParsedNode, connections: List[Dict[str, str]]) -> IVRNode:
        """Create IVR node following Andres's patterns"""
        
        # Generate playLog and playPrompt from segments
        play_log = []
        play_prompt = []
        
        for segment in node.segments:
            # Clean segment for logging
            clean_segment = self._clean_log_text(segment)
            play_log.append(clean_segment)
            
            # Generate appropriate prompt
            if any(var in segment for var in node.variables.values()):
                # Keep variable syntax for prompts that contain variables
                prompt_segment = segment
                for original, replacement in node.variables.items():
                    prompt_segment = prompt_segment.replace(original, replacement)
                play_prompt.append(prompt_segment)
            else:
                # Generate callflow ID for regular segments
                callflow_id = self._generate_callflow_id(clean_segment)
                play_prompt.append(f"callflow:{callflow_id}")
        
        # Create base IVR node
        ivr_node = IVRNode(
            label=node.label,
            playLog=play_log if len(play_log) > 1 else (play_log[0] if play_log else node.original_text),
            playPrompt=play_prompt if len(play_prompt) > 1 else (play_prompt[0] if play_prompt else f"callflow:{self._generate_callflow_id(node.original_text)}")
        )
        
        # Add type-specific properties based on node content and connections
        text_lower = node.original_text.lower()
        
        if 'press 1' in text_lower and 'press 3' in text_lower and len(connections) > 1:
            # Main welcome/decision node
            self._add_main_decision_properties(ivr_node, connections, node.original_text)
        elif 'enter' in text_lower and 'pin' in text_lower:
            self._add_pin_entry_properties(ivr_node, connections)
        elif 'correct pin' in text_lower or ('pin' in text_lower and len(connections) > 1):
            self._add_pin_validation_properties(ivr_node, connections)
        elif 'available' in text_lower and 'callout' in text_lower and 'press' in text_lower:
            self._add_availability_decision_properties(ivr_node, connections)
        elif node.node_type == NodeType.RESPONSE or any(word in text_lower for word in ['accept', 'decline', 'not home', 'qualified']):
            self._add_response_properties(ivr_node, text_lower)
        elif 'press any key' in text_lower or '30-second' in text_lower:
            self._add_sleep_properties(ivr_node, connections)
        elif 'goodbye' in text_lower or 'thank you' in text_lower:
            ivr_node.nobarge = "1"
            ivr_node.goto = "hangup"
        elif 'disconnect' in text_lower:
            ivr_node.nobarge = "1"
            ivr_node.goto = "hangup"
        elif len(connections) == 1:
            # Simple goto for single connection
            target_node = connections[0]['target']
            ivr_node.goto = target_node
        
        return ivr_node

    def _add_main_decision_properties(self, ivr_node: IVRNode, connections: List[Dict[str, str]], text: str):
        """Add main decision properties for welcome message with multiple options"""
        valid_choices = []
        branch_map = {}
        
        # Parse the text to find mentioned options
        text_lower = text.lower()
        if 'press 1' in text_lower:
            valid_choices.append('1')
        if 'press 3' in text_lower:
            valid_choices.append('3')
        if 'press 7' in text_lower:
            valid_choices.append('7')
        if 'press 9' in text_lower:
            valid_choices.append('9')
        
        # Map connections to choices
        for conn in connections:
            label = conn['label'].lower()
            target = conn['target']
            
            if '1' in label or 'employee' in label:
                branch_map['1'] = target
            elif '3' in label or 'need more time' in label:
                branch_map['3'] = target
            elif '7' in label or 'not home' in label:
                branch_map['7'] = target
            elif '9' in label or 'repeat' in label or 'retry' in label:
                branch_map['9'] = target
            elif 'no input' in label or 'go to pg' in label:
                branch_map['none'] = target
        
        # Set defaults if missing
        if 'error' not in branch_map:
            branch_map['error'] = 'Problems'
        if 'none' not in branch_map:
            branch_map['none'] = 'Sleep'  # Follow the pattern from Mermaid
        
        ivr_node.getDigits = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "|".join(sorted(valid_choices)) if valid_choices else "1|3|7|9",
            "errorPrompt": "callflow:InvalidInput"
        }
        
        ivr_node.branch = branch_map

    def _add_pin_validation_properties(self, ivr_node: IVRNode, connections: List[Dict[str, str]]):
        """Add PIN validation properties"""
        branch_map = {}
        
        for conn in connections:
            label = conn['label'].lower()
            if 'yes' in label or 'valid' in label:
                branch_map['valid'] = conn['target']
            elif 'no' in label or 'invalid' in label:
                branch_map['invalid'] = conn['target']
        
        # Set defaults
        if 'valid' not in branch_map and connections:
            branch_map['valid'] = connections[0]['target']
        if 'invalid' not in branch_map:
            branch_map['invalid'] = 'Invalid Entry'
        
        ivr_node.getDigits = {
            "numDigits": 4,
            "maxTries": 3,
            "maxTime": 10,
            "errorPrompt": "callflow:InvalidPIN"
        }
        
        ivr_node.branch = branch_map

    def _add_availability_decision_properties(self, ivr_node: IVRNode, connections: List[Dict[str, str]]):
        """Add availability decision properties"""
        valid_choices = ['1', '3']
        branch_map = {}
        
        for conn in connections:
            label = conn['label'].lower()
            target = conn['target']
            
            if '1' in label or 'accept' in label:
                branch_map['1'] = target
            elif '3' in label or 'decline' in label:
                branch_map['3'] = target
            elif '0' in label or '9' in label or 'call back' in label:
                valid_choices.append('9')
                branch_map['9'] = target
            elif 'invalid' in label or 'no input' in label:
                branch_map['error'] = target
                branch_map['none'] = target
        
        # Set defaults
        if 'error' not in branch_map:
            branch_map['error'] = 'Problems'
        if 'none' not in branch_map:
            branch_map['none'] = 'Problems'
        
        ivr_node.getDigits = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "|".join(sorted(valid_choices)),
            "errorPrompt": "callflow:InvalidInput",
            "nonePrompt": "callflow:NoInput"
        }
        
        ivr_node.branch = branch_map

    def _add_decision_properties(self, ivr_node: IVRNode, connections: List[Dict[str, str]]):
        """Add decision node properties (getDigits and branch)"""
        # Extract valid choices from connection labels
        valid_choices = []
        branch_map = {}
        
        for conn in connections:
            label = conn['label'].lower()
            target = conn['target']
            
            # Look for specific digit patterns
            if re.search(r'\b1\b', label) or 'accept' in label:
                valid_choices.append('1')
                branch_map['1'] = target
            elif re.search(r'\b2\b', label):
                valid_choices.append('2')
                branch_map['2'] = target
            elif re.search(r'\b3\b', label) or 'decline' in label or 'need more time' in label:
                valid_choices.append('3')
                branch_map['3'] = target
            elif re.search(r'\b7\b', label) or 'not home' in label:
                valid_choices.append('7')
                branch_map['7'] = target
            elif re.search(r'\b9\b', label) or 'repeat' in label or 'retry' in label:
                valid_choices.append('9')
                branch_map['9'] = target
            elif 'no input' in label or 'timeout' in label or 'go to pg' in label:
                branch_map['none'] = target
            elif 'error' in label or 'invalid' in label:
                branch_map['error'] = target
            elif 'yes' in label and '1' not in branch_map:
                valid_choices.append('1')
                branch_map['1'] = target
            elif 'no' in label and '2' not in branch_map:
                valid_choices.append('2')
                branch_map['2'] = target
            else:
                # If no specific pattern, try to extract any digit
                digit_match = re.search(r'\b(\d)\b', label)
                if digit_match:
                    digit = digit_match.group(1)
                    valid_choices.append(digit)
                    branch_map[digit] = target
        
        # Set default error handling if not specified
        if 'error' not in branch_map:
            branch_map['error'] = 'Problems'
        if 'none' not in branch_map:
            branch_map['none'] = 'Problems'
        
        # Default valid choices if none detected
        if not valid_choices:
            valid_choices = ['1', '3', '7', '9']
        
        ivr_node.getDigits = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "|".join(sorted(set(valid_choices))),
            "errorPrompt": "callflow:InvalidInput",
            "nonePrompt": "callflow:NoInput"
        }
        
        ivr_node.branch = branch_map

    def _add_pin_entry_properties(self, ivr_node: IVRNode):
        """Add PIN entry properties"""
        ivr_node.getDigits = {
            "numDigits": 4,
            "maxTries": 3,
            "maxTime": 10,
            "errorPrompt": "callflow:InvalidPIN",
            "nonePrompt": "callflow:NoInput"
        }
        
        ivr_node.branch = {
            "valid": "PIN Accepted",
            "invalid": "Invalid PIN",
            "error": "Problems",
            "none": "Problems"
        }

    def _add_response_properties(self, ivr_node: IVRNode, text: str):
        """Add response handling properties"""
        text_lower = text.lower()
        
        if 'accept' in text_lower:
            ivr_node.gosub = self.standard_responses['accept']
        elif 'decline' in text_lower:
            ivr_node.gosub = self.standard_responses['decline']
        elif 'not home' in text_lower:
            ivr_node.gosub = self.standard_responses['not_home']
        elif 'qualified' in text_lower:
            ivr_node.gosub = self.standard_responses['qualified_no']
        
        ivr_node.goto = "Goodbye"

    def _add_sleep_properties(self, ivr_node: IVRNode, connections: List[Dict[str, str]]):
        """Add sleep/wait properties"""
        ivr_node.getDigits = {"numDigits": 1}
        ivr_node.maxLoop = ["Loop-B", 2, "Problems"]
        
        if connections:
            target = connections[0]['target']
            ivr_node.branch = {
                "next": target,
                "none": target
            }

    def _create_error_handler(self) -> IVRNode:
        """Create standard error handler following Andres's pattern"""
        return IVRNode(
            label="Problems",
            playLog=["I'm sorry you are having problems.", "Please have", "Employee name"],
            playPrompt=["callflow:ErrorMessage", "callflow:PleaseHave", "names:{{contact_id}}"],
            nobarge="1",
            goto="Goodbye"
        )

    def _clean_log_text(self, text: str) -> str:
        """Clean text for log entries"""
        # Replace variables with placeholder text for logs
        cleaned = text
        for pattern, replacement in self.variable_patterns.items():
            # Replace with descriptive text for logs
            if '{{level2_location}}' in replacement:
                cleaned = re.sub(pattern, 'Level 2', cleaned, flags=re.IGNORECASE)
            elif '{{contact_id}}' in replacement:
                cleaned = re.sub(pattern, 'Employee', cleaned, flags=re.IGNORECASE)
            elif '{{callout_type}}' in replacement:
                cleaned = re.sub(pattern, 'Callout Type', cleaned, flags=re.IGNORECASE)
            elif '{{callout_reason}}' in replacement:
                cleaned = re.sub(pattern, 'Callout Reason', cleaned, flags=re.IGNORECASE)
            elif '{{callout_location}}' in replacement:
                cleaned = re.sub(pattern, 'Trouble Location', cleaned, flags=re.IGNORECASE)
            elif '{{callback_number}}' in replacement:
                cleaned = re.sub(pattern, 'Phone Number', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()

    def _add_response_properties(self, ivr_node: IVRNode, text: str):
        """Add response handling properties"""
        text_lower = text.lower()
        
        if 'accept' in text_lower:
            ivr_node.gosub = self.standard_responses['accept']
        elif 'decline' in text_lower:
            ivr_node.gosub = self.standard_responses['decline']
        elif 'not home' in text_lower:
            ivr_node.gosub = self.standard_responses['not_home']
        elif 'qualified' in text_lower:
            ivr_node.gosub = self.standard_responses['qualified_no']
        
        ivr_node.goto = "Goodbye"

    def _generate_unique_label(self, base_label: str, existing_labels: Set[str]) -> str:
        """Generate unique label to avoid duplicates"""
        if base_label not in existing_labels:
            return base_label
        
        # Add suffix to make unique
        counter = 2
        while f"{base_label} {counter}" in existing_labels:
            counter += 1
        
        return f"{base_label} {counter}"

    def _generate_callflow_id(self, text: str) -> str:
        """Generate callflow ID from text"""
        # Extract meaningful words and create camelCase ID
        words = re.findall(r'\w+', text)
        meaningful_words = [w for w in words if len(w) > 2 and w.lower() not in ['the', 'and', 'for', 'are', 'you', 'this', 'that', 'with']]
        
        if meaningful_words:
            # CamelCase the words
            callflow_id = meaningful_words[0].lower()
            for word in meaningful_words[1:3]:  # Limit to 3 words max
                callflow_id += word.capitalize()
            return callflow_id
        else:
            # Fallback to first few chars, cleaned
            cleaned = re.sub(r'\W', '', text)
            return cleaned[:10] if cleaned else "prompt"

    def _add_pin_entry_properties(self, ivr_node: IVRNode, connections: List[Dict[str, str]]):
        """Add PIN entry properties"""
        ivr_node.getDigits = {
            "numDigits": 4,
            "maxTries": 3,
            "maxTime": 10,
            "errorPrompt": "callflow:InvalidPIN",
            "nonePrompt": "callflow:NoInput"
        }
        
        # Simple branch logic for PIN entry
        if connections:
            ivr_node.branch = {
                "next": connections[0]['target'],
                "error": "Invalid Entry",
                "none": "Invalid Entry"
            }
        else:
            ivr_node.branch = {
                "next": "Check PIN",
                "error": "Invalid Entry", 
                "none": "Invalid Entry"
            }

    def _generate_ivr_flow(self, nodes: Dict[str, ParsedNode], connections: List[Dict[str, str]]) -> List[IVRNode]:
        """Generate IVR flow following Andres's structure"""
        ivr_nodes = []
        used_labels = set()
        
        # Build connection map
        conn_map = {}
        for conn in connections:
            if conn['source'] not in conn_map:
                conn_map[conn['source']] = []
            conn_map[conn['source']].append(conn)
        
        # Find start node (no incoming connections)
        incoming = {conn['target'] for conn in connections}
        start_nodes = [node_id for node_id in nodes.keys() if node_id not in incoming]
        
        # If no clear start node, use the first node alphabetically
        if not start_nodes and nodes:
            start_nodes = [sorted(nodes.keys())[0]]
        
        # Remove the old method call references and update
        processed = set()
        
        # First, process start nodes and their descendants
        for start_node in start_nodes:
            self._process_node_recursive_with_unique_labels(start_node, nodes, conn_map, ivr_nodes, processed, used_labels)
        
        # Then process any remaining unprocessed nodes
        for node_id in nodes.keys():
            if node_id not in processed:
                self._process_node_recursive_with_unique_labels(node_id, nodes, conn_map, ivr_nodes, processed, used_labels)
        
        # Add standard error handler if not present
        if not any(node.label == "Problems" for node in ivr_nodes):
            problems_node = self._create_error_handler()
            problems_node.label = self._generate_unique_label("Problems", used_labels)
            ivr_nodes.append(problems_node)
        
        return ivr_nodes

    def _process_node_recursive_with_unique_labels(self, node_id: str, nodes: Dict[str, ParsedNode], 
                               conn_map: Dict[str, List[Dict[str, str]]], 
                               ivr_nodes: List[IVRNode], processed: Set[str], used_labels: Set[str]):
        """Recursively process nodes with unique label generation"""
        if node_id in processed or node_id not in nodes:
            return
        
        processed.add(node_id)
        node = nodes[node_id]
        
        # Ensure unique label
        node.label = self._generate_unique_label(node.label, used_labels)
        used_labels.add(node.label)
        
        # Create IVR node based on type
        node_connections = conn_map.get(node_id, [])
        ivr_node = self._create_ivr_node(node, node_connections)
        ivr_nodes.append(ivr_node)
        
        # Process connected nodes
        for conn in node_connections:
            if conn['target'] in nodes:
                self._process_node_recursive_with_unique_labels(conn['target'], nodes, conn_map, ivr_nodes, processed, used_labels)

    def _node_to_dict(self, node: IVRNode) -> Dict[str, Any]:
        """Convert IVRNode to dictionary for JSON serialization"""
        result = {
            "label": node.label,
        }
        
        # Add log (use different property names based on type)
        if isinstance(node.playLog, list) and len(node.playLog) > 1:
            result["playLog"] = node.playLog
        else:
            log_text = node.playLog[0] if isinstance(node.playLog, list) else node.playLog
            result["log"] = log_text
        
        # Add playPrompt
        result["playPrompt"] = node.playPrompt
        
        # Add optional properties in the order that matches allflows lite
        if node.getDigits:
            result["getDigits"] = node.getDigits
        if node.branch:
            result["branch"] = node.branch
        if node.maxLoop:
            result["maxLoop"] = node.maxLoop
        if node.gosub:
            result["gosub"] = node.gosub
        if node.goto:
            result["goto"] = node.goto
        if node.nobarge:
            result["nobarge"] = node.nobarge
            
        return result


def convert_mermaid_to_ivr(mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Main conversion function - wrapper for the enhanced converter"""
    converter = EnhancedMermaidIVRConverter()
    return converter.convert(mermaid_code)

# Also provide the function expected by the current app structure
def convert_mermaid_to_ivr_legacy(mermaid_text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Legacy wrapper for backward compatibility"""
    return convert_mermaid_to_ivr(mermaid_text)