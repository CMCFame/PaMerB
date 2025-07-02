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
        try:
            # Parse the mermaid diagram
            parsed_nodes, connections = self._parse_mermaid(mermaid_code)
            
            # Generate IVR flow
            ivr_nodes = self._generate_ivr_flow(parsed_nodes, connections)
            
            # Convert to dictionary format for JSON serialization
            ivr_dict = [self._node_to_dict(node) for node in ivr_nodes]
            
            return ivr_dict, []
            
        except Exception as e:
            # Return error handler if conversion fails
            error_node = {
                "label": "Problems",
                "log": f"Conversion error: {str(e)}",
                "playPrompt": "callflow:ErrorHandler",
                "goto": "hangup"
            }
            return [error_node], [f"Conversion failed: {str(e)}"]

    def _parse_mermaid(self, mermaid_code: str) -> Tuple[Dict[str, ParsedNode], List[Dict[str, str]]]:
        """Parse mermaid code into structured nodes and connections"""
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        
        nodes = {}
        connections = []
        
        for line in lines:
            # Skip flowchart definition and comments
            if line.startswith('flowchart') or line.startswith('%%'):
                continue
            
            # Parse connections
            if '-->' in line:
                conn = self._parse_connection(line)
                if conn:
                    connections.append(conn)
            else:
                # Parse node definitions
                node = self._parse_node_definition(line)
                if node:
                    nodes[node.id] = node
        
        return nodes, connections

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
        # Pattern: A -->|"label"| B or A --> B
        pattern = r'^(\w+)\s*-->\s*(?:\|"([^"]+)"\|\s*)?(\w+)'
        match = re.match(pattern, line)
        
        if match:
            source, label, target = match.groups()
            return {
                'source': source.strip(),
                'target': target.strip(),
                'label': label.strip() if label else ''
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
        
        if node_type == NodeType.WELCOME:
            return "Live Answer"
        elif node_type == NodeType.PIN_ENTRY:
            return "Enter PIN"
        elif node_type == NodeType.GOODBYE:
            return "Goodbye"
        elif node_type == NodeType.ERROR:
            return "Problems"
        elif node_type == NodeType.SLEEP:
            return "Sleep"
        elif node_type == NodeType.DECISION:
            # Extract key decision words
            if re.search(r'available.*work.*callout', text.lower()):
                return "Available For Callout"
            elif re.search(r'correct.*pin', text.lower()):
                return "Check PIN"
            elif re.search(r'this\s+is.*employee', text.lower()):
                return "Employee Verification"
            else:
                return "Decision Point"
        elif node_type == NodeType.RESPONSE:
            if re.search(r'accept', text.lower()):
                return "Accept"
            elif re.search(r'decline', text.lower()):
                return "Decline"
            elif re.search(r'not\s+home', text.lower()):
                return "Not Home"
            elif re.search(r'qualified.*no', text.lower()):
                return "Qualified No"
            else:
                return "Response Handler"
        else:
            # Generate label from key words in text
            words = re.findall(r'\w+', text)
            key_words = [w for w in words[:3] if len(w) > 2]
            return ' '.join(key_words[:2]).title() if key_words else "Action"

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
        # Common segmentation patterns following Andres's approach
        segments = []
        
        # Handle common callout patterns
        if re.search(r'this\s+is\s+an?\s+.*callout', text.lower()):
            # Pattern: "This is an electric callout from Level 2"
            parts = re.split(r'(this\s+is\s+an?)', text, flags=re.IGNORECASE)
            if len(parts) > 2:
                segments.append(parts[0] + parts[1])  # "This is an"
                remaining = parts[2].strip()
                
                # Further split callout type and location
                callout_parts = re.split(r'(callout)', remaining, flags=re.IGNORECASE)
                if len(callout_parts) > 1:
                    segments.append(callout_parts[0].strip())  # callout type
                    segments.append(callout_parts[1])  # "callout"
                    if len(callout_parts) > 2:
                        segments.append(callout_parts[2].strip())  # remaining
                else:
                    segments.append(remaining)
            else:
                segments.append(text)
        
        # Handle press instructions
        elif re.search(r'press\s+\d+', text.lower()):
            # Split on "Press X"
            parts = re.split(r'(press\s+\d+)', text, flags=re.IGNORECASE)
            segments.extend([part.strip() for part in parts if part.strip()])
        
        # Handle simple sentences
        else:
            # Split on natural breaks (periods, commas followed by space)
            parts = re.split(r'[.,]\s+', text)
            segments.extend([part.strip() for part in parts if part.strip()])
        
        # If no segmentation happened, return the whole text
        if not segments:
            segments = [text]
        
        return segments

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
        
        # Process nodes in order, starting with start nodes
        processed = set()
        for start_node in start_nodes:
            self._process_node_recursive(start_node, nodes, conn_map, ivr_nodes, processed)
        
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
        ivr_node = self._create_ivr_node(node, conn_map.get(node_id, []))
        ivr_nodes.append(ivr_node)
        
        # Process connected nodes
        for conn in conn_map.get(node_id, []):
            self._process_node_recursive(conn['target'], nodes, conn_map, ivr_nodes, processed)

    def _create_ivr_node(self, node: ParsedNode, connections: List[Dict[str, str]]) -> IVRNode:
        """Create IVR node following Andres's patterns"""
        
        # Generate playLog and playPrompt from segments
        play_log = []
        play_prompt = []
        
        for i, segment in enumerate(node.segments):
            if any(var in segment for var in node.variables.values()):
                # This segment contains a variable
                play_log.append(self._clean_log_text(segment))
                play_prompt.append(segment)  # Keep variable syntax
            else:
                # Regular voice file segment
                clean_segment = self._clean_log_text(segment)
                play_log.append(clean_segment)
                callflow_id = self._generate_callflow_id(clean_segment)
                play_prompt.append(f"callflow:{callflow_id}")
        
        # Create base IVR node
        ivr_node = IVRNode(
            label=node.label,
            playLog=play_log if len(play_log) > 1 else play_log[0] if play_log else node.original_text,
            playPrompt=play_prompt if len(play_prompt) > 1 else play_prompt[0] if play_prompt else f"callflow:{node.label}"
        )
        
        # Add type-specific properties
        if node.node_type == NodeType.DECISION:
            self._add_decision_properties(ivr_node, connections)
        elif node.node_type == NodeType.PIN_ENTRY:
            self._add_pin_entry_properties(ivr_node)
        elif node.node_type == NodeType.RESPONSE:
            self._add_response_properties(ivr_node, node.original_text)
        elif node.node_type == NodeType.GOODBYE:
            ivr_node.nobarge = "1"
            ivr_node.goto = "hangup"
        elif node.node_type == NodeType.SLEEP:
            self._add_sleep_properties(ivr_node, connections)
        elif len(connections) == 1:
            # Simple goto for single connection
            ivr_node.goto = connections[0]['target']
        
        return ivr_node

    def _add_decision_properties(self, ivr_node: IVRNode, connections: List[Dict[str, str]]):
        """Add decision node properties (getDigits and branch)"""
        # Extract valid choices from connection labels
        valid_choices = []
        branch_map = {}
        
        for conn in connections:
            label = conn['label'].lower()
            if re.search(r'\b1\b', label):
                valid_choices.append('1')
                branch_map['1'] = conn['target']
            elif re.search(r'\b2\b', label):
                valid_choices.append('2')
                branch_map['2'] = conn['target']
            elif re.search(r'\b3\b', label):
                valid_choices.append('3')
                branch_map['3'] = conn['target']
            elif re.search(r'\b7\b', label):
                valid_choices.append('7')
                branch_map['7'] = conn['target']
            elif re.search(r'\b9\b', label):
                valid_choices.append('9')
                branch_map['9'] = conn['target']
            elif 'no input' in label or 'timeout' in label:
                branch_map['none'] = conn['target']
            elif 'error' in label or 'invalid' in label:
                branch_map['error'] = conn['target']
        
        # Set default error handling
        if 'error' not in branch_map:
            branch_map['error'] = 'Problems'
        if 'none' not in branch_map:
            branch_map['none'] = 'Problems'
        
        ivr_node.getDigits = {
            "numDigits": 1,
            "maxTries": 3,
            "maxTime": 7,
            "validChoices": "|".join(sorted(valid_choices)) if valid_choices else "1|3|7|9",
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
        # Remove variable syntax and clean up
        cleaned = re.sub(r'\{\{[^}]+\}\}', '[Variable]', text)
        return cleaned.strip()

    def _generate_callflow_id(self, text: str) -> str:
        """Generate callflow ID from text"""
        # Extract meaningful words and create camelCase ID
        words = re.findall(r'\w+', text)
        meaningful_words = [w for w in words if len(w) > 2 and w.lower() not in ['the', 'and', 'for', 'are', 'you']]
        
        if meaningful_words:
            # CamelCase the words
            callflow_id = meaningful_words[0].lower()
            for word in meaningful_words[1:3]:  # Limit to 3 words max
                callflow_id += word.capitalize()
            return callflow_id
        else:
            # Fallback to first few chars
            return re.sub(r'\W', '', text)[:10]

    def _node_to_dict(self, node: IVRNode) -> Dict[str, Any]:
        """Convert IVRNode to dictionary for JSON serialization"""
        result = {
            "label": node.label,
        }
        
        # Add log (use different property names based on type)
        if isinstance(node.playLog, list):
            result["playLog"] = node.playLog
        else:
            result["log"] = node.playLog
        
        # Add playPrompt
        result["playPrompt"] = node.playPrompt
        
        # Add optional properties
        if node.getDigits:
            result["getDigits"] = node.getDigits
        if node.branch:
            result["branch"] = node.branch
        if node.goto:
            result["goto"] = node.goto
        if node.gosub:
            result["gosub"] = node.gosub
        if node.nobarge:
            result["nobarge"] = node.nobarge
        if node.maxLoop:
            result["maxLoop"] = node.maxLoop
            
        return result


def convert_mermaid_to_ivr(mermaid_code: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Main conversion function - wrapper for the enhanced converter"""
    converter = EnhancedMermaidIVRConverter()
    return converter.convert(mermaid_code)

# Also provide the function expected by the current app structure
def convert_mermaid_to_ivr_legacy(mermaid_text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Legacy wrapper for backward compatibility"""
    return convert_mermaid_to_ivr(mermaid_text)