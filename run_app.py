#!/usr/bin/env python3
"""
Script to run the PaMerB Streamlit app on port 8502
"""

import subprocess
import sys
import os

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import streamlit
        import streamlit_mermaid
        import openai
        from PIL import Image
        print("[OK] All dependencies found")
        return True
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("[TIP] Run: pip install -r requirements.txt")
        return False

def run_app():
    """Run the Streamlit app"""
    if not check_dependencies():
        return False
    
    print("[STARTING] PaMerB IVR Converter...")
    print("[INFO] App will be available at: http://localhost:8502")
    print("[INFO] Press Ctrl+C to stop the app")
    print("-" * 50)
    
    try:
        # Run streamlit on port 8502 to avoid conflicts
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8502",
            "--server.address", "localhost"
        ], check=True)
    except KeyboardInterrupt:
        print("\n[INFO] App stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error running app: {e}")
        return False
    except FileNotFoundError:
        print("[ERROR] Streamlit not found. Install with: pip install streamlit")
        return False
    
    return True

if __name__ == "__main__":
    print("PaMerB - IVR Converter Web App")
    print("=" * 40)
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    success = run_app()
    
    if not success:
        print("\n[TROUBLESHOOTING]:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Check if app.py exists in current directory")
        print("3. Ensure Python and Streamlit are properly installed")