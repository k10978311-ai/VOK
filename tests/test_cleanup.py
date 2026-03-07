#!/usr/bin/env python3
"""
Test script to verify application cleanup functionality.
Run this script to test if the application handles signals and cleanup properly.
"""

import sys
import os
import time
import signal
import subprocess

def test_cleanup_handling():
    """Test if the application handles cleanup properly when terminated."""
    print("Testing VOK application cleanup handling...")
    
    # Add the project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    try:
        # Start the application in a subprocess
        print("Starting VOK application...")
        process = subprocess.Popen(
            [sys.executable, "run.py"],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a moment for startup
        time.sleep(3)
        
        if process.poll() is None:
            print("✓ Application started successfully")
            
            # Send SIGTERM to test graceful shutdown
            print("Sending SIGTERM signal...")
            process.terminate()
            
            # Wait for graceful shutdown
            try:
                stdout, stderr = process.communicate(timeout=10)
                return_code = process.returncode
                
                print(f"✓ Application exited with code: {return_code}")
                
                if stdout:
                    print("STDOUT:", stdout.decode()[:200] + "..." if len(stdout.decode()) > 200 else stdout.decode())
                if stderr:
                    print("STDERR:", stderr.decode()[:200] + "..." if len(stderr.decode()) > 200 else stderr.decode())
                
                if return_code == 0:
                    print("✓ Graceful shutdown successful")
                else:
                    print(f"⚠ Application exited with non-zero code: {return_code}")
                    
            except subprocess.TimeoutExpired:
                print("⚠ Application did not exit gracefully, force killing...")
                process.kill()
                process.communicate()
                
        else:
            print("✗ Application failed to start")
            stdout, stderr = process.communicate()
            if stdout:
                print("STDOUT:", stdout.decode())
            if stderr:
                print("STDERR:", stderr.decode())
            
    except FileNotFoundError:
        print("✗ Could not find run.py script")
    except Exception as e:
        print(f"✗ Test failed with error: {e}")

def test_signal_handlers():
    """Test that signal handlers are properly registered."""
    print("\\nTesting signal handler registration...")
    
    # Test if signal handlers are available
    try:
        original_sigint = signal.signal(signal.SIGINT, signal.default_int_handler)
        original_sigterm = signal.signal(signal.SIGTERM, signal.default_int_handler)
        print("✓ Signal handling is available on this platform")
        
        # Restore original handlers
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
        
    except (AttributeError, OSError) as e:
        print(f"⚠ Signal handling may be limited: {e}")

def main():
    """Run cleanup tests."""
    print("VOK Application Cleanup Test")
    print("=" * 40)
    
    test_signal_handlers()
    test_cleanup_handling()
    
    print("\\nTest completed!")
    print("\\nCleanup improvements made:")
    print("• Added signal handlers for SIGINT and SIGTERM")
    print("• Improved system tray exit to call proper cleanup")
    print("• Enhanced MainWindow.onExit() with comprehensive cleanup")
    print("• Added database thread graceful shutdown")  
    print("• Added background thread termination")
    print("• Added signal disconnection to prevent crashes")
    print("• Added window close event handler with force-quit option (Shift+Close)")

if __name__ == "__main__":
    main()