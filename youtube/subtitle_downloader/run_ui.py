#!/usr/bin/env python3
"""
Launch script for the YouTube Audio Processing Pipeline UI.
This script starts the Streamlit application with proper configuration.
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    ui_path = script_dir / "ui.py"
    
    # Check if ui.py exists
    if not ui_path.exists():
        print(f"Error: ui.py not found at {ui_path}")
        sys.exit(1)
    
    # Streamlit configuration
    streamlit_args = [
        "streamlit", "run", str(ui_path),
        "--server.port", "8501",
        "--server.address", "localhost",
        "--server.headless", "false",
        "--browser.serverAddress", "localhost",
        "--browser.gatherUsageStats", "false",
        "--server.fileWatcherType", "none"  # Disable file watching for better performance
    ]
    
    print("🚀 Starting YouTube Audio Processing Pipeline UI...")
    print(f"📁 Working directory: {script_dir}")
    print("🌐 The app will open in your browser at: http://localhost:8501")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        # Run Streamlit
        subprocess.run(streamlit_args, cwd=script_dir, check=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down the server...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Streamlit: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Streamlit not found. Please install it with: pip install streamlit")
        sys.exit(1)

if __name__ == "__main__":
    main()
