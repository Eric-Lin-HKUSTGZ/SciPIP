#!/usr/bin/env python3
"""
Startup script for SciPIP API Service
"""

import os
import sys
import subprocess
from pathlib import Path

def check_environment():
    """Check if required environment variables and files exist."""
    print("🔍 Checking environment...")
    
    # Check required configuration files
    required_files = [
        "./configs/datasets.yaml",
        "./assets/data/example.json",
        "./scripts/env.sh"
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"⚠️  Warning: File not found: {file_path}")
            print(f"   The service may not work correctly without this file.")
    
    # Check environment variables (MODEL_NAME, NEO4J_URL, etc.)
    # These are loaded from scripts/env.sh automatically
    
    print("✅ Environment check completed!")
    return True

def start_api_service():
    """Start the API service."""
    print("🚀 Starting SciPIP API Service...")
    
    try:
        # Change to the project directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # Start the API service
        subprocess.run([
            sys.executable, "api_service.py"
        ], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start API service: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  API service stopped by user")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function."""
    print("=" * 60)
    print("🔬 SciPIP API Service Startup")
    print("=" * 60)
    
    if not check_environment():
        print("\n❌ Environment check failed. Please fix the issues above.")
        sys.exit(1)
    
    # Get port from config
    from api_config import API_PORT
    
    print("\n📋 Service Information:")
    print(f"   - API URL: http://localhost:{API_PORT}")
    print(f"   - Generate Endpoint: POST http://localhost:{API_PORT}/generate")
    print(f"   - Health Check: http://localhost:{API_PORT}/health")
    print(f"   - Documentation: http://localhost:{API_PORT}/docs")
    print("\n💡 To test the service, run:")
    print("   python python_client_example.py")
    print("\n" + "=" * 60)
    
    if not start_api_service():
        sys.exit(1)

if __name__ == "__main__":
    main()

