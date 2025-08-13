"""
Enhanced PDF processor that extracts text and vector content directly,
avoiding image conversion for better quality and performance.
"""

import fitz  # PyMuPDF
import io
import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw
from dataclasses import dataclass
from openai import OpenAI
import streamlit as st

logger = logging.getLogger(__name__)

@dataclass
class DiagramElement:
    """Represents an element in a flowchhart diagram"""
    type: str  # 'text', 'shape', 'line', 'image'
    content: str
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    properties: Dict[str, Any]

@dataclass
class FlowchartDiagram:
    """Represents a complete flowchart diagram"""
    page_number: int
    elements: List[DiagramElement]
    text_content: str
    bbox: Tuple[float, float, float, float]

class EnhancedPDFProcessor:
    """
    Advanced PDF processor that extracts vector content, text, and shapes
    directly from PDF without converting to images first.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize processor with OpenAI API key"""
        self.api_key = (
            api_key or 
            st.secrets.get("general", {}).get("OPENAI_API_KEY") or 
            st.secrets.get("OPENAI_API_KEY")
        )
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def extract_diagrams_from_pdf(self, pdf_file) -> List[FlowchartDiagram]:
        """
        Extract flowchart diagrams from PDF using vector analysis
        instead of image conversion.
        """
        diagrams = []
        
        try:
            # Read PDF from uploaded file
            pdf_bytes = pdf_file.read()
            pdf_file.seek(0)  # Reset file pointer
            
            # Open PDF document
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            logger.info(f"Processing PDF with {len(doc)} pages")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Extract structured content from page
                page_diagrams = self._extract_page_diagrams(page, page_num)
                diagrams.extend(page_diagrams)
            
            doc.close()
            
            logger.info(f"Extracted {len(diagrams)} diagrams from PDF")
            return diagrams
            
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            raise RuntimeError(f"PDF processing error: {str(e)}")
    
    def _extract_page_diagrams(self, page: fitz.Page, page_num: int) -> List[FlowchartDiagram]:
        """Extract diagrams from a single PDF page using vector analysis"""
        diagrams = []
        
        try:
            # Get page dimensions
            page_rect = page.rect
            
            # Extract text with positioning
            text_dict = page.get_text("dict")
            
            # Extract vector graphics (shapes, lines)
            drawing_commands = page.get_drawings()
            
            # Extract images
            image_list = page.get_images()
            
            # Analyze content to identify diagram regions
            diagram_regions = self._identify_diagram_regions(
                text_dict, drawing_commands, image_list, page_rect
            )
            
            # Process each diagram region
            for region_idx, region in enumerate(diagram_regions):
                elements = self._extract_elements_from_region(
                    page, region, text_dict, drawing_commands
                )
                
                # Create structured text representation
                text_content = self._create_text_representation(elements)
                
                diagram = FlowchartDiagram(
                    page_number=page_num + 1,
                    elements=elements,
                    text_content=text_content,
                    bbox=region
                )
                
                diagrams.append(diagram)
                
                logger.info(f"Page {page_num + 1}, Diagram {region_idx + 1}: "
                          f"{len(elements)} elements extracted")
        
        except Exception as e:
            logger.error(f"Error processing page {page_num}: {str(e)}")
            # Fallback to image-based processing for this page
            fallback_diagram = self._fallback_image_processing(page, page_num)
            if fallback_diagram:
                diagrams.append(fallback_diagram)
        
        return diagrams
    
    def _identify_diagram_regions(self, text_dict: Dict, drawings: List, 
                                images: List, page_rect: fitz.Rect) -> List[Tuple[float, float, float, float]]:
        """
        Identify regions of the page that contain flowchart diagrams
        by analyzing text density, drawing elements, and layout.
        """
        regions = []
        
        # Simple approach: if page has drawings or specific flowchart keywords,
        # treat entire page as one diagram region
        flowchart_keywords = [
            'flowchart', 'diagram', 'press', 'enter', 'welcome', 'callout',
            'employee', 'pin', 'accept', 'decline', 'invalid', 'goodbye'
        ]
        
        # Extract all text content
        all_text = ""
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        all_text += span.get("text", "") + " "
        
        all_text = all_text.lower()
        
        # Check if this looks like a flowchart page
        has_flowchart_content = any(keyword in all_text for keyword in flowchart_keywords)
        has_drawings = len(drawings) > 0
        
        if has_flowchart_content or has_drawings:
            # For now, treat entire page as one diagram
            # In future, could implement more sophisticated region detection
            regions.append((page_rect.x0, page_rect.y0, page_rect.x1, page_rect.y1))
        
        return regions or [(page_rect.x0, page_rect.y0, page_rect.x1, page_rect.y1)]
    
    def _extract_elements_from_region(self, page: fitz.Page, region: Tuple[float, float, float, float],
                                    text_dict: Dict, drawings: List) -> List[DiagramElement]:
        """Extract structured elements from a diagram region"""
        elements = []
        
        region_rect = fitz.Rect(region)
        
        # Extract text elements
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                block_rect = fitz.Rect(block["bbox"])
                if region_rect.intersects(block_rect):
                    text_content = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_content += span.get("text", "") + " "
                    
                    if text_content.strip():
                        element = DiagramElement(
                            type="text",
                            content=text_content.strip(),
                            bbox=block["bbox"],
                            properties={
                                "font_size": line["spans"][0].get("size", 12) if block["lines"] and block["lines"][0]["spans"] else 12,
                                "font": line["spans"][0].get("font", "Arial") if block["lines"] and block["lines"][0]["spans"] else "Arial"
                            }
                        )
                        elements.append(element)
        
        # Extract drawing elements (shapes, lines)
        for drawing in drawings:
            drawing_rect = fitz.Rect(drawing["rect"])
            if region_rect.intersects(drawing_rect):
                # Classify drawing type
                drawing_type = self._classify_drawing(drawing)
                
                element = DiagramElement(
                    type="shape",
                    content=drawing_type,
                    bbox=drawing["rect"],
                    properties={
                        "stroke_color": drawing.get("stroke", {}).get("color"),
                        "fill_color": drawing.get("fill", {}).get("color"),
                        "width": drawing.get("stroke", {}).get("width", 1)
                    }
                )
                elements.append(element)
        
        return elements
    
    def _classify_drawing(self, drawing: Dict) -> str:
        """Classify drawing element type based on properties"""
        # Simple classification - could be enhanced
        rect = drawing["rect"]
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        
        aspect_ratio = width / height if height > 0 else 1
        
        # Classify based on shape and aspect ratio
        if 0.8 <= aspect_ratio <= 1.2:
            return "diamond" if "diamond" in str(drawing).lower() else "rectangle"
        elif aspect_ratio > 3 or aspect_ratio < 0.33:
            return "line"
        else:
            return "rectangle"
    
    def _create_text_representation(self, elements: List[DiagramElement]) -> str:
        """Create a structured text representation of the diagram"""
        text_elements = [e for e in elements if e.type == "text"]
        shape_elements = [e for e in elements if e.type == "shape"]
        
        # Sort by position (top to bottom, left to right)
        text_elements.sort(key=lambda e: (e.bbox[1], e.bbox[0]))
        
        text_repr = []
        text_repr.append("=== FLOWCHART DIAGRAM ===\n")
        
        text_repr.append("TEXT ELEMENTS:")
        for i, element in enumerate(text_elements):
            text_repr.append(f"{i+1}. {element.content}")
        
        text_repr.append(f"\nSHAPES: {len(shape_elements)} elements")
        
        return "\n".join(text_repr)
    
    def _fallback_image_processing(self, page: fitz.Page, page_num: int) -> Optional[FlowchartDiagram]:
        """Fallback to image-based processing if vector extraction fails"""
        try:
            logger.info(f"Using fallback image processing for page {page_num + 1}")
            
            # Convert page to image
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(img_data))
            
            # Create a fallback diagram with image data
            element = DiagramElement(
                type="image",
                content="fallback_image",
                bbox=(0, 0, image.width, image.height),
                properties={"image_data": img_data}
            )
            
            return FlowchartDiagram(
                page_number=page_num + 1,
                elements=[element],
                text_content="Image-based fallback processing",
                bbox=(0, 0, image.width, image.height)
            )
            
        except Exception as e:
            logger.error(f"Fallback processing failed: {str(e)}")
            return None
    
    def convert_diagrams_to_mermaid(self, diagrams: List[FlowchartDiagram]) -> List[str]:
        """Convert extracted diagrams to Mermaid format using OpenAI"""
        mermaid_results = []
        
        for i, diagram in enumerate(diagrams):
            logger.info(f"Converting diagram {i+1}/{len(diagrams)} to Mermaid")
            
            try:
                if any(e.type == "image" for e in diagram.elements):
                    # Handle image-based fallback
                    mermaid_code = self._convert_image_diagram_to_mermaid(diagram)
                else:
                    # Handle structured vector data
                    mermaid_code = self._convert_structured_diagram_to_mermaid(diagram)
                
                mermaid_results.append(mermaid_code)
                
            except Exception as e:
                logger.error(f"Error converting diagram {i+1}: {str(e)}")
                mermaid_results.append(f"// Error converting diagram {i+1}: {str(e)}")
        
        return mermaid_results
    
    def _convert_structured_diagram_to_mermaid(self, diagram: FlowchartDiagram) -> str:
        """Convert structured diagram data to Mermaid using text analysis"""
        
        # Enhanced prompt for structured data
        prompt = f"""
Convert this extracted flowchart diagram to Mermaid.js format. The diagram has been extracted from PDF with structured content analysis.

DIAGRAM DATA:
Page: {diagram.page_number}
Elements extracted: {len(diagram.elements)}

TEXT CONTENT:
{diagram.text_content}

ELEMENT DETAILS:
"""
        
        for i, element in enumerate(diagram.elements[:10]):  # Limit to avoid token limits
            prompt += f"Element {i+1}: {element.type} - {element.content[:100]}\n"
        
        prompt += """

Create a Mermaid flowchart that represents this IVR call flow diagram. Include:
1. All text nodes exactly as written
2. Decision diamonds for questions/choices  
3. Process rectangles for actions/messages
4. All connection labels and flow paths
5. Proper Mermaid syntax

Format as: flowchart TD
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert at converting flowchart diagrams to Mermaid.js format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.1
            )
            
            mermaid_code = response.choices[0].message.content.strip()
            
            # Clean up the response
            if "```mermaid" in mermaid_code:
                mermaid_code = mermaid_code.split("```mermaid")[1].split("```")[0].strip()
            elif "```" in mermaid_code:
                mermaid_code = mermaid_code.split("```")[1].strip()
            
            return mermaid_code
            
        except Exception as e:
            logger.error(f"OpenAI conversion failed: {str(e)}")
            return f"// OpenAI conversion failed: {str(e)}"
    
    def _convert_image_diagram_to_mermaid(self, diagram: FlowchartDiagram) -> str:
        """Convert image-based diagram to Mermaid (fallback method)"""
        
        # Find the image element
        image_element = next((e for e in diagram.elements if e.type == "image"), None)
        if not image_element:
            return "// No image data found"
        
        # Convert image to base64 for OpenAI
        base64_image = base64.b64encode(image_element.properties["image_data"]).decode()
        
        prompt = """
Convert this IVR flowchart diagram to Mermaid.js format. Focus on:

1. Extract all text content exactly as written
2. Identify shapes: rectangles for processes, diamonds for decisions
3. Follow all flow lines and connections
4. Include all DTMF options and labels
5. Preserve the logical flow structure

Create a complete Mermaid flowchart starting with 'flowchart TD'
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=3000,
                temperature=0.1
            )
            
            mermaid_code = response.choices[0].message.content.strip()
            
            # Clean up the response
            if "```mermaid" in mermaid_code:
                mermaid_code = mermaid_code.split("```mermaid")[1].split("```")[0].strip()
            elif "```" in mermaid_code:
                mermaid_code = mermaid_code.split("```")[1].strip()
            
            return mermaid_code
            
        except Exception as e:
            logger.error(f"Image-based conversion failed: {str(e)}")
            return f"// Image-based conversion failed: {str(e)}"
    
    def process_pdf_file(self, pdf_file) -> List[str]:
        """
        Main entry point: process PDF file and return list of Mermaid diagrams
        """
        try:
            # Extract diagrams using vector analysis
            diagrams = self.extract_diagrams_from_pdf(pdf_file)
            
            if not diagrams:
                raise ValueError("No diagrams found in PDF")
            
            # Convert to Mermaid format
            mermaid_results = self.convert_diagrams_to_mermaid(diagrams)
            
            logger.info(f"Successfully processed PDF: {len(diagrams)} diagrams converted")
            
            return mermaid_results
            
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            raise RuntimeError(f"PDF processing error: {str(e)}")