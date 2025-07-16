"""
ARCOS-Integrated Streamlit App
Dual database loading with ARCOS foundation + client overrides
"""
import streamlit as st
import streamlit_mermaid as st_mermaid
import json
import tempfile
import os
import traceback

# Import the ARCOS-integrated converter
from mermaid_ivr_converter import convert_mermaid_to_ivr

# Page configuration
st.set_page_config(
    page_title="🎯 ARCOS-Integrated IVR Converter",
    page_icon="🔄",
    layout="wide"
)

# Constants
DEFAULT_FLOWS = {
    "Electric Callout (ARCOS Pattern)": '''flowchart TD
A["Welcome<br/>This is an electric callout from (Level 2).<br/>Press 1, if this is (employee).<br/>Press 3, if you need more time to get (employee) to the phone.<br/>Press 7, if (employee) is not home.<br/>Press 9, to repeat this message."] -->|"input"| B{"1 - this is employee"}
A -->|"no input - go to pg 3"| C["30-second message<br/>Press any key to continue..."]
A -->|"7 - not home"| D["Employee Not Home<br/>Please have<br/>(employee) call the<br/>(Level 2) Callout<br/>System at<br/>866-502-7267."]
A -->|"3 - need more time"| C
A -->|"9 - repeat"| A
B -->|"yes"| E["Enter Employee PIN<br/>Please enter your 4 digit PIN<br/>followed by the pound key."]
E --> F{"Correct PIN?"}
F -->|"yes"| G["Electric Callout<br/>This is an electric callout."]
F -->|"no"| H["Invalid PIN<br/>Please try again."]
H --> E
G --> I["Callout Reason<br/>The callout reason is (callout reason)."]
I --> J["Trouble Location<br/>The trouble location is (trouble location)."]
J --> K["Custom Message<br/>(Play custom message, if selected.)"]
K --> L{"Available For Callout<br/>Are you available to work this callout?<br/>If yes, press 1. If no, press 3.<br/>If no one else accepts, and you want to be called again, press 9."}
L -->|"1 - accept"| M["Accepted Response<br/>An accepted response has been recorded."]
L -->|"3 - decline"| N["Callout Decline<br/>Your response is being recorded as a decline."]
L -->|"9 - call back"| O["Qualified No<br/>You may be called again on this callout if no one accepts."]
M --> P["Goodbye<br/>Thank you.<br/>Goodbye."]
N --> P
O --> P
P --> Q["Disconnect"]
D --> Q''',

    "PIN Change": '''flowchart TD
A["Enter Current PIN<br/>Please enter your current 4 digit PIN followed by the pound key."] --> B{"Valid PIN?"}
B -->|"No"| C["Invalid Entry<br/>Invalid PIN. Please try again."]
B -->|"Yes"| D["New PIN<br/>Please enter your new 4 digit PIN followed by the pound key."]
C --> A
D --> E["Confirm PIN<br/>Please confirm your new PIN by entering it again."]
E --> F{"PIN Match?"}
F -->|"No"| D
F -->|"Yes"| G["PIN Changed<br/>Your PIN has been successfully updated."]
G --> H["Goodbye<br/>Thank you."]''',

    "Simple Availability": '''flowchart TD
A["Available For Callout<br/>Are you available to work this callout?<br/>Press 1 for yes, press 3 for no."] -->|"1"| B["Accept<br/>Thank you. Your response has been recorded."]
A -->|"3"| C["Decline<br/>Your decline has been recorded."]
A -->|"no input"| D["Problems<br/>I'm sorry you are having problems."]
B --> E["Goodbye<br/>Thank you."]
C --> E
D --> E'''
}

def show_database_status(arcos_csv, client_csv):
    """Show database loading status"""
    st.subheader("📊 Database Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if arcos_csv:
            st.success("✅ ARCOS Foundation Database Loaded")
            st.info(f"📁 {arcos_csv.name} ({arcos_csv.size:,} bytes)")
            st.caption("🏗️ Provides core ARCOS callflow recordings")
        else:
            st.warning("⚠️ Using ARCOS Fallback Database")
            st.caption("🔧 Limited to basic callflow patterns")
    
    with col2:
        if client_csv:
            st.success("✅ Client Override Database Loaded")
            st.info(f"📁 {client_csv.name} ({client_csv.size:,} bytes)")
            st.caption("🎯 Client-specific recordings override ARCOS")
        else:
            st.info("ℹ️ No Client Database")
            st.caption("🏗️ Using ARCOS foundation only")

def analyze_arcos_integration(ivr_flow: list):
    """Analyze ARCOS integration in the conversion results"""
    
    st.subheader("🔍 ARCOS Integration Analysis")
    
    # Count voice file sources
    arcos_prompts = 0
    client_prompts = 0
    variable_prompts = 0
    missing_prompts = 0
    
    for node in ivr_flow:
        play_prompts = node.get('playPrompt', [])
        if isinstance(play_prompts, list):
            for prompt in play_prompts:
                if isinstance(prompt, str):
                    if prompt.startswith('callflow:'):
                        # Check if it's a standard ARCOS ID
                        callflow_id = prompt.replace('callflow:', '')
                        if callflow_id.isdigit() and len(callflow_id) == 4:
                            arcos_prompts += 1
                        else:
                            client_prompts += 1
                    elif ':{{' in prompt:  # Variable like names:{{contact_id}}
                        variable_prompts += 1
                    elif '[VOICE FILE NEEDED]' in prompt:
                        missing_prompts += 1
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏗️ ARCOS Foundation", arcos_prompts)
    with col2:
        st.metric("🎯 Client Override", client_prompts)
    with col3:
        st.metric("🔧 Variables", variable_prompts)
    with col4:
        st.metric("❓ Missing", missing_prompts)
    
    # Coverage analysis
    total_prompts = arcos_prompts + client_prompts + variable_prompts + missing_prompts
    if total_prompts > 0:
        coverage = ((arcos_prompts + client_prompts + variable_prompts) / total_prompts) * 100
        st.metric("📊 Total Coverage", f"{coverage:.1f}%")
        
        if missing_prompts > 0:
            st.warning(f"⚠️ {missing_prompts} voice files need to be created")
    
    # Show ARCOS pattern examples
    if arcos_prompts > 0:
        st.success("✅ ARCOS Integration Working!")
        with st.expander("🔍 ARCOS Pattern Examples"):
            for node in ivr_flow[:3]:  # Show first 3 nodes
                if 'playPrompt' in node:
                    st.write(f"**{node.get('label', 'Unknown')}:**")
                    st.code(json.dumps(node['playPrompt'], indent=2), language="json")

def show_code_diff(mermaid_text: str, js_output: str):
    """Show before/after comparison"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📝 Input: Mermaid Diagram")
        st.code(mermaid_text, language="mermaid")
        
        # Show Mermaid visualization
        try:
            st.markdown("### 🎨 Mermaid Visualization")
            st_mermaid.st_mermaid(mermaid_text, height="400px")
        except:
            st.info("Mermaid visualization not available")
    
    with col2:
        st.markdown("### ⚡ Output: ARCOS-Integrated IVR")
        st.code(js_output, language="javascript")

def main():
    st.title("🎯 ARCOS-Integrated IVR Converter")
    st.markdown("**Foundation + Override System**: ARCOS recordings as foundation with client-specific overrides")
    
    # Dual Database Upload Section
    st.sidebar.header("📁 Dual Database System")
    
    with st.sidebar:
        st.markdown("### 🏗️ ARCOS Foundation")
        arcos_csv = st.file_uploader(
            "Upload ARCOS Database", 
            type=['csv'],
            key="arcos_upload",
            help="ARCOS recordings provide the foundation layer (callflow:1191, 1274, etc.)"
        )
        
        st.markdown("### 🎯 Client Overrides")
        client_csv = st.file_uploader(
            "Upload cf_general_structure.csv", 
            type=['csv'],
            key="client_upload",
            help="Client-specific recordings that override ARCOS when available"
        )
        
        if arcos_csv and client_csv:
            st.success("🚀 Dual Database Mode")
            st.caption("Best possible voice file matching")
        elif arcos_csv:
            st.info("🏗️ ARCOS Foundation Mode")
            st.caption("Using ARCOS recordings only")
        elif client_csv:
            st.warning("⚠️ Client Only Mode")
            st.caption("Missing ARCOS foundation")
        else:
            st.error("❌ Fallback Mode")
            st.caption("Limited voice file coverage")
    
    # Show database status
    show_database_status(arcos_csv, client_csv)
    
    st.markdown("""
    **🎯 ARCOS Integration Benefits:**
    - ✅ **Foundation Layer**: Core ARCOS callflow recordings (1191, 1274, 1589, etc.)
    - ✅ **Client Overrides**: Company-specific recordings take priority when available
    - ✅ **Variable Support**: ARCOS patterns like `names:{{contact_id}}`, `location:{{level2_location}}`
    - ✅ **Production Patterns**: Matches allflows LITE structure exactly
    - ✅ **Automatic Prioritization**: Best match selection with fallback chain
    """)

    # Initialize session state
    if 'last_mermaid_code' not in st.session_state:
        st.session_state.last_mermaid_code = ""
    if 'last_ivr_code' not in st.session_state:
        st.session_state.last_ivr_code = ""

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("🎯 Integration Status")
        if arcos_csv and client_csv:
            st.success("✅ Dual Database Mode")
            st.success("✅ ARCOS Foundation")
            st.success("✅ Client Overrides")
        elif arcos_csv:
            st.success("✅ ARCOS Foundation")
            st.info("ℹ️ No Client Overrides")
        else:
            st.warning("⚠️ Fallback Mode Only")
        
        st.subheader("Advanced Settings")
        validate_syntax = st.checkbox("Validate Diagram", value=True)
        show_debug = st.checkbox("Show Debug Info", value=False)
        show_analysis = st.checkbox("Show ARCOS Analysis", value=True)

    # Main content area
    st.subheader("📝 Mermaid Diagram Input")
    
    # Example selector
    selected_example = st.selectbox("Load Example Flow", ["Custom"] + list(DEFAULT_FLOWS.keys()))
    initial_text = DEFAULT_FLOWS.get(selected_example, st.session_state.last_mermaid_code)
    
    # Text area for Mermaid code
    mermaid_text = st.text_area(
        "Mermaid Diagram Code", 
        initial_text, 
        height=300, 
        help="Paste your Mermaid flowchart code here or select an example above"
    )
    st.session_state.last_mermaid_code = mermaid_text
    
    # Conversion button
    if st.button("🔄 Convert with ARCOS Integration", type="primary", use_container_width=True):
        if not mermaid_text.strip():
            st.error("❌ Please enter Mermaid diagram code")
            return
        
        with st.spinner("🔄 Converting with ARCOS-integrated approach..."):
            try:
                # Convert using ARCOS-integrated converter
                ivr_flow_dict, js_output = convert_mermaid_to_ivr(
                    mermaid_text, 
                    cf_general_csv=client_csv, 
                    arcos_csv=arcos_csv
                )
                
                # Store results
                st.session_state.last_ivr_code = js_output
                
                # Show success message
                st.success(f"✅ **ARCOS-INTEGRATED CONVERSION SUCCESSFUL!** Generated {len(ivr_flow_dict)} IVR nodes")
                
                # Critical fix verification
                welcome_node = next((node for node in ivr_flow_dict if node.get('label') == 'Live Answer'), None)
                if welcome_node and welcome_node.get('branch', {}).get('1'):
                    st.success(f"🎯 **CRITICAL FIX VERIFIED**: Choice '1' maps to '{welcome_node['branch']['1']}'")
                
                # Show results
                st.subheader("📋 Generated ARCOS-Integrated IVR Configuration")
                
                # Download button
                st.download_button(
                    label="💾 Download IVR Code",
                    data=js_output,
                    file_name="arcos_integrated_ivr_flow.js",
                    mime="application/javascript"
                )
                
                # Display the JavaScript output
                st.code(js_output, language="javascript")
                
                # Show ARCOS integration analysis
                if show_analysis:
                    analyze_arcos_integration(ivr_flow_dict)
                
                # Show comparison
                if st.checkbox("📊 Show Before & After Comparison", value=True):
                    st.subheader("🔍 Before & After Comparison")
                    show_code_diff(mermaid_text, js_output)
                    
                # Show individual nodes for debugging
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
    
    else:
        st.info("👈 Enter or select a Mermaid diagram above, then click 'Convert with ARCOS Integration'")

    # Footer
    st.markdown("---")
    st.markdown("""
    **🎯 ARCOS Integration Features:**
    - 🏗️ **ARCOS Foundation**: Core callflow recordings (1191="This is an", 1274="callout", 1589="from")
    - 🎯 **Smart Prioritization**: Client recordings override ARCOS when available
    - 🔧 **Variable Support**: ARCOS patterns like `names:{{contact_id}}`, `current: dow, date, time`
    - 📋 **Production Matching**: Generates allflows LITE-compatible code
    - 🔄 **Automatic Fallback**: Graceful degradation when voice files are missing
    - ✅ **Critical Fix Applied**: Choice "1" employee verification now works correctly
    """)

    # ARCOS-specific test section
    if show_debug:
        st.markdown("---")
        st.subheader("🧪 ARCOS Integration Test")
        
        if st.button("🧪 Test ARCOS Integration"):
            with st.spinner("Testing ARCOS integration..."):
                try:
                    # Test with the electric callout example
                    test_mermaid = DEFAULT_FLOWS["Electric Callout (ARCOS Pattern)"]
                    test_flow, test_js = convert_mermaid_to_ivr(
                        test_mermaid, 
                        cf_general_csv=client_csv, 
                        arcos_csv=arcos_csv
                    )
                    
                    if test_flow:
                        st.success("✅ ARCOS integration test successful!")
                        
                        # Check for ARCOS patterns
                        arcos_patterns_found = []
                        for node in test_flow:
                            prompts = node.get('playPrompt', [])
                            for prompt in prompts:
                                if isinstance(prompt, str):
                                    if prompt.startswith('callflow:') and prompt.replace('callflow:', '').isdigit():
                                        arcos_patterns_found.append(prompt)
                                    elif ':{{' in prompt:
                                        arcos_patterns_found.append(prompt)
                        
                        if arcos_patterns_found:
                            st.success(f"🎯 Found {len(set(arcos_patterns_found))} ARCOS patterns:")
                            st.code("\n".join(set(arcos_patterns_found)), language="text")
                        
                        # Check critical fix
                        welcome_node = next((node for node in test_flow if node.get('label') == 'Live Answer'), None)
                        if welcome_node and welcome_node.get('branch', {}).get('1'):
                            st.success(f"✅ **TEST VERIFIED**: Choice '1' maps to '{welcome_node['branch']['1']}'")
                        else:
                            st.error("❌ Test failed - Choice '1' mapping missing!")
                    else:
                        st.error("❌ ARCOS integration test failed!")
                        
                except Exception as e:
                    st.error(f"❌ Test error: {e}")


if __name__ == "__main__":
    main()