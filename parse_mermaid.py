"""
Enhanced Mermaid Parser for IVR Diagrams
Handles complex flowcharts with decision nodes, subgraphs, and IVR-specific patterns
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import re
from enum import Enum

class NodeType(Enum):
    """Types of nodes in IVR flowcharts"""
    START = "start"
    END = "end"
    ACTION = "action"
    DECISION = "decision"
    MENU = "menu"
    INPUT = "input"
    TRANSFER = "transfer"
    RECORDING = "recording"
    VALIDATION = "validation"

@dataclass
class Node:
    """Represents a node in the flowchart"""
    id: str
    raw_text: str
    node_type: NodeType
    
    @property
    def text(self):
        """Get cleaned text (removing HTML tags)"""
        # Remove HTML line breaks
        cleaned = re.sub(r'<br\s*/?\s*>', ' ', self.raw_text)
        # Remove other HTML tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        # Clean whitespace
        cleaned = ' '.join(cleaned.split())
        return cleaned
    
    @property
    def lines(self):
        """Get text split by line breaks"""
        # Split on HTML line breaks
        lines = re.split(r'<br\s*/?\s*>', self.raw_text)
        # Clean each line
        return [line.strip() for line in lines if line.strip()]

@dataclass
class Edge:
    """Represents an edge/connection in the flowchart"""
    from_id: str
    to_id: str
    label: Optional[str] = None
    style: Optional[str] = None

class MermaidParser:
    """
    Enhanced parser for Mermaid flowcharts
    Specifically designed for IVR call flow diagrams
    """
    
    def __init__(self):
        # IVR-specific node patterns
        self.node_patterns = {
            NodeType.MENU: [
                r'press\s+\d+',
                r'if\s+yes.*press',
                r'available\s+to\s+work',
                r'are\s+you\s+available'
            ],
            NodeType.INPUT: [
                r'enter.*pin',
                r'enter.*digits?',
                r'input.*number'
            ],
            NodeType.DECISION: [
                r'valid\s+pin\?',
                r'correct\s+pin\?',
                r'entered\s+digits?\?',
                r'transfer\s+available\?'
            ],
            NodeType.END: [
                r'goodbye',
                r'disconnect',
                r'end\s+of\s+call',
                r'thank\s+you.*goodbye'
            ],
            NodeType.START: [
                r'welcome',
                r'this\s+is\s+an?\s+\w+\s+callout'
            ],
            NodeType.RECORDING: [
                r'recording',
                r'leave.*message',
                r'record.*response'
            ],
            NodeType.TRANSFER: [
                r'transfer',
                r'connect',
                r'agent'
            ]
        }
        
        # Edge pattern mapping
        self.edge_patterns = {
            r'-->': 'arrow',
            r'==>': 'thick',
            r'-\.-': 'dotted',
            r'--\|(.+?)\|->': 'label',
            # Dotted connection for optional flows
            r'-\.->\s*': 'optional',
            # Thick connection for primary paths
            r'==+>': 'primary'
        }

    def parse(self, mermaid_text: str) -> Dict:
        """
        Parse Mermaid diagram text into structured format
        
        Args:
            mermaid_text: Raw Mermaid diagram text
            
        Returns:
            Dict containing parsed nodes, edges, and metadata
        """
        lines = [line.strip() for line in mermaid_text.split('\n') if line.strip()]
        
        nodes = {}
        edges = []
        subgraphs = {}
        metadata = {
            'title': None,
            'direction': 'TD',
            'styles': {}
        }
        
        current_subgraph = None
        
        try:
            for line in lines:
                # Skip comments and directives
                if line.startswith('%%') or line.startswith('%'):
                    continue
                
                # Parse flowchart direction
                if line.startswith('flowchart') or line.startswith('graph'):
                    direction_match = re.match(r'(?:flowchart|graph)\s+(\w+)', line)
                    if direction_match:
                        metadata['direction'] = direction_match.group(1)
                    continue
                
                # Handle subgraphs
                if line.startswith('subgraph'):
                    subgraph_match = re.match(r'subgraph\s+(\w+)(?:\s*\[(.*?)\])?', line)
                    if subgraph_match:
                        current_subgraph = subgraph_match.group(1)
                        title = subgraph_match.group(2) or current_subgraph
                        subgraphs[current_subgraph] = {
                            'id': current_subgraph,
                            'title': title,
                            'nodes': set()
                        }
                    continue
                
                if line == 'end':
                    current_subgraph = None
                    continue
                
                # Parse nodes
                node_match = self._parse_node(line)
                if node_match:
                    node_id, node = node_match
                    nodes[node_id] = node
                    if current_subgraph:
                        subgraphs[current_subgraph]['nodes'].add(node_id)
                    continue
                
                # Parse edges
                edge = self._parse_edge(line)
                if edge:
                    edges.append(edge)
                    continue
                
                # Parse styles
                style_match = self._parse_style(line)
                if style_match:
                    class_name, styles = style_match
                    metadata['styles'][class_name] = styles
            
            return {
                'nodes': nodes,
                'edges': edges,
                'subgraphs': subgraphs,
                'metadata': metadata
            }
            
        except Exception as e:
            raise ValueError(f"Failed to parse Mermaid diagram: {str(e)}")

    def _parse_node(self, line: str) -> Optional[tuple]:
        """Parse node definition"""
        # Match node patterns with various syntax forms
        node_patterns = [
            # ["text"] form
            r'^\s*(\w+)\s*\["([^"]+)"\]',
            # {"text"} form for decisions
            r'^\s*(\w+)\s*\{"([^"]+)"\}',
            # ("text") form
            r'^\s*(\w+)\s*\("([^"]+)"\)',
            # [("text")] form
            r'^\s*(\w+)\s*\[\("([^"]+)"\)\]'
        ]
        
        for pattern in node_patterns:
            match = re.match(pattern, line)
            if match:
                node_id, text = match.groups()
                node_type = self._determine_node_type(text)
                return node_id, Node(
                    id=node_id,
                    raw_text=text,
                    node_type=node_type
                )
        return None

    def _parse_edge(self, line: str) -> Optional[Edge]:
        """Parse edge definition"""
        for pattern, style in self.edge_patterns.items():
            # Use raw string for regex pattern
            match = re.search(rf'(\w+)\s*{pattern}\s*(\w+)', line)
            if match:
                from_id, to_id = match.groups()
                label = None
                if 'label' in style and len(match.groups()) > 2:
                    label = match.group(2)
                return Edge(
                    from_id=from_id,
                    to_id=to_id,
                    label=label,
                    style=style
                )
        return None

    def _parse_style(self, line: str) -> Optional[tuple]:
        """Parse style definition"""
        style_match = re.match(r'classDef\s+(\w+)\s+(.*?)$', line)
        if style_match:
            class_name, styles = style_match.groups()
            return class_name, styles
        return None

    def _determine_node_type(self, text: str) -> NodeType:
        """Determine node type from text content"""
        text_lower = text.lower()
        
        for node_type, patterns in self.node_patterns.items():
            if any(re.search(pattern, text_lower) for pattern in patterns):
                return node_type
        
        return NodeType.ACTION

def parse_mermaid(mermaid_text: str) -> Dict:
    """Convenience wrapper for parsing Mermaid diagrams"""
    parser = MermaidParser()
    return parser.parse(mermaid_text)

# Command-line testing
if __name__ == "__main__":
    test_diagram = """
    flowchart TD
        A["Welcome<br/>This is an electric callout from Level 2.<br/>Press 1 if this is employee."]
        B{"Valid PIN?"}
        C["Enter PIN<br/>Please enter your 4 digit PIN<br/>followed by the pound key."]
        D["Goodbye<br/>Thank you.<br/>Goodbye."]
        
        A -->|"1"| C
        C --> B
        B -->|"yes"| D
        B -->|"no"| C
    """
    
    parser = MermaidParser()
    result = parser.parse(test_diagram)
    
    print("Nodes:")
    for node_id, node in result['nodes'].items():
        print(f"  {node_id}: {node.node_type.value} - {node.text[:50]}...")
    
    print("\nEdges:")
    for edge in result['edges']:
        print(f"  {edge.from_id} --> {edge.to_id} ({edge.label or 'no label'})")