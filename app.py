"""
Enhanced Streamlit app for IVR flow conversion with the new enhanced converter
that follows Andres's conventions and generates production-ready IVR code.
"""
import streamlit as st
import streamlit_mermaid as st_mermaid
import json
import tempfile
import os
from PIL import Image
import traceback

# Import the enhanced converter
from mermaid_ivr_converter import convert_mermaid_to_ivr
from parse_mermaid import MermaidParser
from openai_converter import process_flow_diagram

# Page configuration
st.set_page_config(
    page_title="Enhanced Mermaid-to-IVR Converter",
    page_icon="🔄",
    layout="wide"
)

# Constants and examples
DEFAULT_FLOWS = {
    "Electric Callout": '''flowchart TD
A["Welcome<br/>This is an electric callout from (Level 2).<br/>Press 1, if this is (employee).<br/>Press 3, if you need more time to get (employee) to the phone.<br/>Press 7, if (employee) is not home.<br/>Press 9, to repeat this message."] -->|"1"| B{"1 - this is employee"}
A -->|"no input - go to pg 3"| C["30-second message<br/>Press any key to continue..."]
A -->|"7 - not home"| D["Employee Not Home"]
A -->|"3 - need more time"| C
A -->|"9 - repeat"| A
B -->|"yes"| E["Enter Employee PIN"]
E --> F{"Correct PIN?"}
F -->|"yes"| G["Available For Callout<br/>Are you available to work this callout?<br/>If yes, press 1. If no, press 3."]
F -->|"no"| H["Invalid PIN<br/>Please try again."]
H --> E
G -->|"1 - accept"| I["Accepted Response<br/>An accepted response has been recorded."]
G -->|"3 - decline"| J["Callout Decline<br/>Your response is being recorded as a decline."]
I --> K["Goodbye<br/>Thank you.<br/>Goodbye."]
J --> K''',

    "PIN Change": '''flowchart TD
A["Enter PIN"] --> B{"Valid PIN?"}
B -->|"No"| C["Invalid Entry<br/>Please try again."]
B -->|"Yes"| D["PIN Changed<br/>Your PIN has been updated."]
C --> A
D --> E["Goodbye<br/>Thank you."]''',

    "Simple Availability": '''flowchart TD
A["Available For Callout<br/>Are you available to work this callout?<br/>Press 1 for yes, press 3 for no."] -->|"1"| B["Accept<br/>Thank you. Your response has been recorded."]
A -->|"3"| C["Decline<br/>Your decline has been recorded."]
A -->|"no input"| D["Problems<br/>I'm sorry you are having problems."]
B --> E["Goodbye"]
C --> E
D --> E'''
}

def save_temp_file(content: str, suffix: str = '.js') -> str:
    """Save content to a temporary file and return the path"""
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
        f.write(content)
        return f.name

def validate_mermaid(mermaid_text: str) -> str:
    """Validate Mermaid diagram syntax"""
    try:
        parser = MermaidParser()
        parser.parse(mermaid_text)
        return None
    except Exception as e:
        return f"Diagram Validation Error: {str(e)}"

def show_code_diff(original: str, converted: str):
    """Show comparison of original and converted code"""
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Original Mermaid")
        st.code(original, language="mermaid")
    with col2:
        st.subheader("Generated IVR Code")
        st.code(converted, language="javascript")

def render_mermaid_safely(mermaid_text: str):
    """Safely render Mermaid diagram with error handling"""
    try:
        st_mermaid.st_mermaid(mermaid_text, height=500)
    except Exception as e:
        st.error(f"Preview Error: {str(e)}")
        st.code(mermaid_text, language="mermaid")

def format_ivr_output(ivr_dict: list) -> str:
    """Format IVR dictionary as JavaScript module"""
    return "module.exports = " + json.dumps(ivr_dict, indent=2) + ";"

def main():
    st.title("🔄 Enhanced Mermaid-to-IVR Converter")
    st.markdown("""
    **Production-Ready IVR Code Generator**
    
    This enhanced tool converts Mermaid flowcharts into production-ready IVR configurations following Andres's conventions:
    - ✅ Descriptive labels based on node purpose
    - ✅ Proper variable detection and replacement
    - ✅ Intelligent text segmentation for voice files
    - ✅ Standard IVR flow patterns (getDigits, branch, goto, gosub)
    - ✅ Error handling and timeout management
    """)

    # Initialize session state
    if 'last_mermaid_code' not in st.session_state:
        st.session_state.last_mermaid_code = ""
    if 'last_ivr_code' not in st.session_state:
        st.session_state.last_ivr_code = ""

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        conversion_method = st.radio("Input Method", ["Mermaid Editor", "Image Upload"])
        
        st.subheader("🎯 Enhanced Features")
        st.success("✅ Descriptive Labels")
        st.success("✅ Variable Detection")
        st.success("✅ Text Segmentation")
        st.success("✅ Andres's Patterns")
        
        st.subheader("Advanced Settings")
        validate_syntax = st.checkbox("Validate Diagram", value=True)
        show_debug = st.checkbox("Show Debug Info", value=False)
        show_analysis = st.checkbox("Show Analysis Details", value=True)
        
        st.subheader("API Configuration")
        openai_api_key = st.text_input("OpenAI API Key", type="password", help="Required for image processing")

    mermaid_text = ""
    
    if conversion_method == "Mermaid Editor":
        st.subheader("📝 Mermaid Diagram Editor")
        selected_example = st.selectbox("Load Example Flow", ["Custom"] + list(DEFAULT_FLOWS.keys()))
        initial_text = DEFAULT_FLOWS.get(selected_example, st.session_state.last_mermaid_code)
        mermaid_text = st.text_area("Mermaid Diagram Code", initial_text, height=300, 
                                   help="Paste your Mermaid flowchart code here or select an example above")
        st.session_state.last_mermaid_code = mermaid_text
        
    else:
        st.subheader("📷 Image Upload")
        col1, col2 = st.columns(2)
        with col1:
            uploaded_file = st.file_uploader("Upload Flowchart", type=['pdf', 'png', 'jpg', 'jpeg'])
        with col2:
            if uploaded_file:
                try:
                    image = Image.open(uploaded_file)
                    st.image(image, caption="Uploaded Flowchart", use_column_width=True)
                except Exception as e:
                    st.error(f"Error loading image: {str(e)}")
        
        if uploaded_file and openai_api_key:
            if st.button("🔄 Convert Image to Mermaid"):
                with st.spinner("Converting image..."):
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            mermaid_text = process_flow_diagram(tmp_file.name, openai_api_key)
                            st.session_state.last_mermaid_code = mermaid_text
                        st.success("Image converted successfully!")
                        st.subheader("Generated Mermaid Code")
                        st.code(mermaid_text, language="mermaid")
                    except Exception as e:
                        st.error(f"Conversion Error: {str(e)}")
                        if show_debug: 
                            st.exception(e)
                    finally:
                        if 'tmp_file' in locals(): 
                            os.unlink(tmp_file.name)
        else:
            if not openai_api_key: 
                st.info("Please provide an OpenAI API key in the sidebar for image conversion.")
            if not uploaded_file: 
                st.info("Please upload an image or PDF for conversion.")
        
        mermaid_text = st.session_state.last_mermaid_code

    # Display Mermaid preview
    if mermaid_text and mermaid_text.strip():
        st.subheader("👁️ Mermaid Diagram Preview")
        render_mermaid_safely(mermaid_text)
    else:
        st.warning("No Mermaid code to display. Paste code in the editor or convert an image.")

    # Main conversion section
    if mermaid_text and mermaid_text.strip():
        st.subheader("🚀 Convert to Production-Ready IVR")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            convert_button = st.button("🔄 Generate IVR Code", type="primary", use_container_width=True)
        with col2:
            if st.button("📋 Copy Example", help="Copy one of the example flows to get started"):
                st.session_state.last_mermaid_code = DEFAULT_FLOWS["Electric Callout"]
                st.rerun()
        
        if convert_button:
            with st.spinner("🔧 Converting to production-ready IVR code..."):
                try:
                    # Validate syntax if requested
                    if validate_syntax:
                        error = validate_mermaid(mermaid_text)
                        if error:
                            st.error(error)
                            return

                    # Convert using enhanced converter
                    ivr_flow_dict, notes = convert_mermaid_to_ivr(mermaid_text)
                    
                    # Format for display and download
                    js_output = format_ivr_output(ivr_flow_dict)
                    st.session_state.last_ivr_code = js_output

                    # Success message
                    st.success("✅ IVR code generated successfully!")
                    
                    # Analysis section
                    if show_analysis:
                        st.subheader("📊 Conversion Analysis")
                        
                        analysis_col1, analysis_col2, analysis_col3 = st.columns(3)
                        with analysis_col1:
                            st.metric("Nodes Generated", len(ivr_flow_dict))
                        with analysis_col2:
                            decision_nodes = sum(1 for node in ivr_flow_dict if "getDigits" in node)
                            st.metric("Decision Points", decision_nodes)
                        with analysis_col3:
                            variables_detected = sum(1 for node in ivr_flow_dict 
                                                   if any("{{" in str(prompt) for prompt in 
                                                         (node.get("playPrompt", []) if isinstance(node.get("playPrompt"), list) 
                                                          else [node.get("playPrompt", "")])))
                            st.metric("Variables Detected", variables_detected)
                        
                        # Show detected patterns
                        st.write("**🎯 Detected Patterns:**")
                        patterns = []
                        for node in ivr_flow_dict:
                            if "getDigits" in node:
                                patterns.append(f"• **{node['label']}**: Decision point with input validation")
                            elif "gosub" in node:
                                patterns.append(f"• **{node['label']}**: Response handler with database call")
                            elif "{{" in str(node.get("playPrompt", "")):
                                patterns.append(f"• **{node['label']}**: Dynamic content with variables")
                        
                        if patterns:
                            for pattern in patterns[:5]:  # Show first 5
                                st.write(pattern)
                        else:
                            st.write("• Simple linear flow detected")

                    # Display the generated code
                    st.subheader("📤 Generated IVR Configuration")
                    st.code(js_output, language="javascript")

                    # Display extracted notes if any
                    if notes:
                        st.warning("⚠️ Conversion Notes")
                        for note in notes:
                            st.info(f"📝 {note}")

                    # Download section
                    st.subheader("💾 Download Options")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        tmp_file = save_temp_file(js_output)
                        with open(tmp_file, 'rb') as f:
                            st.download_button(
                                "⬇️ Download IVR Configuration", 
                                f, 
                                file_name="callflow_config.js", 
                                mime="application/javascript",
                                use_container_width=True
                            )
                        os.unlink(tmp_file)
                    
                    with col2:
                        # Also offer JSON format
                        json_output = json.dumps(ivr_flow_dict, indent=2)
                        st.download_button(
                            "⬇️ Download as JSON", 
                            json_output, 
                            file_name="callflow_config.json", 
                            mime="application/json",
                            use_container_width=True
                        )

                    # Show comparison
                    st.subheader("🔍 Before & After Comparison")
                    show_code_diff(mermaid_text, js_output)
                    
                    # Show individual nodes for debugging if requested
                    if show_debug:
                        st.subheader("🐛 Debug Information")
                        st.write("**Generated Nodes:**")
                        for i, node in enumerate(ivr_flow_dict):
                            with st.expander(f"Node {i+1}: {node.get('label', 'Unknown')}"):
                                st.json(node)

                except Exception as e:
                    st.error(f"❌ Conversion Error: {str(e)}")
                    if show_debug:
                        st.subheader("🐛 Debug Information")
                        st.exception(e)
                        st.text(traceback.format_exc())
                        
                        # Show partial results if available
                        if 'ivr_flow_dict' in locals():
                            st.write("**Partial Results:**")
                            st.json(ivr_flow_dict)
    else:
        st.info("👈 Enter or upload Mermaid code to begin conversion")

    # Footer
    st.markdown("---")
    st.markdown("""
    **Enhanced Converter Features:**
    - 🎯 **Smart Label Generation**: Creates descriptive labels like "Live Answer", "Enter PIN", "Available For Callout"
    - 🔄 **Variable Detection**: Automatically converts (Level 2) → {{level2_location}}, (employee) → {{contact_id}}
    - 📝 **Text Segmentation**: Breaks complex messages into voice file components following Andres's patterns
    - 🎛️ **Flow Control**: Generates proper getDigits, branch, goto, and gosub structures
    - ⚡ **Production Ready**: Creates deployable JavaScript that follows IVR system conventions
    """)

if __name__ == "__main__":
    main()