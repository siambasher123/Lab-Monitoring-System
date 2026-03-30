# main.py - TEACHER with PROPER CLEANUP AND GRACEFUL SHUTDOWN
import threading
import server
import gui
import atexit
import signal
import sys

# Global references for cleanup
server_thread = None
server_shutdown_event = None
gui_window = None

def cleanup_resources():
    """Cleanup function called at shutdown"""
    print("\n[SHUTDOWN] Closing application gracefully...")
    
    # Signal server to stop
    if server_shutdown_event:
        print("[SHUTDOWN] Stopping server...")
        server_shutdown_event.set()
    
    # Wait for server thread with timeout
    if server_thread and server_thread.is_alive():
        print("[SHUTDOWN] Waiting for server thread to finish...")
        server_thread.join(timeout=3)
        if server_thread.is_alive():
            print("[WARNING] Server thread still running after timeout")
    
    print("[SHUTDOWN] Cleanup complete")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n[SIGNAL] Received interrupt signal")
    if gui_window:
        try:
            gui_window.quit()
        except:
            pass
    sys.exit(0)

# Register cleanup handlers
atexit.register(cleanup_resources)
signal.signal(signal.SIGINT, signal_handler)

# Create shutdown event for server
server_shutdown_event = threading.Event()
server.shutdown_event = server_shutdown_event  # Pass to server module

# Start server as NON-DAEMON thread (important!)
server_thread = threading.Thread(target=server.start_server, daemon=False)
server_thread.start()

print("[MAIN] Starting GUI...")

# Start GUI (blocking)
gui_window = gui.start_gui(server_shutdown_event)

# Program continues here after GUI closes
print("[MAIN] GUI closed, shutting down...")
cleanup_resources()
print("[MAIN] Goodbye!") 
