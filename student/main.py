# main.py - STUDENT with cleanup and network monitoring
# UPDATED: Universal - Works with/without internet, shows network status
import sys
import threading
import atexit
import time
import config

def network_monitor():
    """Monitor network changes and update GUI"""
    last_status = None
    last_ip = None
    
    while True:
        try:
            # Get current network status
            status = config.get_network_status()
            current_status = status['connection_type']
            current_ip = status['local_ip']
            
            # Log changes
            if current_status != last_status or current_ip != last_ip:
                print(f"\n🌐 Network Status Changed:")
                print(f"   ├─ Mode: {current_status}")
                print(f"   ├─ Local IP: {current_ip}")
                print(f"   └─ Teacher: {'✅ Reachable' if status['teacher_reachable'] else '❌ Not Reachable'}")
                
                try:
                    import gui
                    gui.add_log(f"Network: {current_status} | IP: {current_ip}")
                    
                    # Update status in GUI if teacher reachability changes
                    if status['teacher_reachable']:
                        gui.update_status("trying")  # Will try to connect/reconnect
                    else:
                        gui.update_status("disconnected")
                except:
                    pass
                
                last_status = current_status
                last_ip = current_ip
            
            time.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"[NETWORK MONITOR] Error: {e}")
            time.sleep(10)

def check_prerequisites():
    """Check if all prerequisites are met before starting"""
    print("\n🔍 Checking prerequisites...")
    
    # Check Python version
    import sys
    print(f"   ├─ Python version: {sys.version.split()[0]}")
    
    # Check if running as admin (for Windows features)
    if sys.platform == 'win32':
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if is_admin:
                print("   ├─ ✓ Running as Administrator")
            else:
                print("   ├─ ⚠️ Not running as Administrator")
                print("   │  Some features may not work (Internet blocking, Screen lock)")
        except:
            pass
    
    # Check firewall (basic check)
    try:
        import socket
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(1)
        result = test_sock.connect_ex(('127.0.0.1', config.PORT))
        test_sock.close()
        if result == 0:
            print(f"   ├─ ⚠️ Port {config.PORT} is already in use")
        else:
            print(f"   ├─ ✓ Port {config.PORT} is available")
    except:
        pass
    
    print("   └─ Done\n")

def show_startup_banner():
    """Show fancy startup banner"""
    print("=" * 70)
    print("🎓  CLASSROOM MONITORING SYSTEM - STUDENT AGENT  🎓")
    print("=" * 70)
    
    # Get network status
    status = config.get_network_status()
    
    # Show status in a nice format
    print(f"\n📡 NETWORK STATUS:")
    print(f"   ├─ Mode: {status['connection_type']}")
    print(f"   ├─ Local IP: {status['local_ip']}")
    print(f"   ├─ Teacher IP: {config.TEACHER_IP}")
    print(f"   ├─ Teacher Reachable: {'✅ Yes' if status['teacher_reachable'] else '❌ No'}")
    print(f"   └─ Port: {config.PORT}")
    
    # Show student info
    print(f"\n👤 STUDENT INFO:")
    print(f"   ├─ Name: {config.STUDENT_NAME}")
    print(f"   ├─ Machine: {config.MACHINE_NUMBER}")
    print(f"   └─ Mode: {config.CURRENT_MODE.upper()}")
    
    print("\n" + "=" * 70)

def main():
    # Show startup banner
    show_startup_banner()
    
    # Check prerequisites
    check_prerequisites()
    
    # Validate configuration
    valid, message = config.validate_config()
    if not valid:
        print(f"\n❌ CONFIGURATION ERROR: {message}")
        if config.CURRENT_MODE == "popup" and not config.SETUP_COMPLETE:
            print("📋 Opening setup wizard...")
            import setup
            if not setup.show_setup_window():
                print("❌ Setup cancelled. Exiting.")
                input("\nPress Enter to exit...")
                sys.exit(1)
        else:
            print("\n💡 Tips:")
            print("   • Check teacher IP in config.py")
            print("   • Make sure teacher app is running")
            print("   • Check network connection")
            input("\nPress Enter to exit...")
            sys.exit(1)
    
    print(f"\n🚀 Starting student agent...")
    print(f"   ├─ Target: {config.TEACHER_IP}:{config.PORT}")
    print(f"   └─ Student: {config.STUDENT_NAME}")
    print("-" * 70)
    
    # Import modules
    try:
        import gui
        print("   ✓ GUI module loaded")
    except ImportError as e:
        print(f"   ❌ Failed to load GUI module: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    try:
        import server
        print("   ✓ Server module loaded")
    except ImportError as e:
        print(f"   ❌ Failed to load server module: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Register cleanup function
    def cleanup():
        print("\n🧹 Cleaning up student application...")
        try:
            server.cleanup()
            print("   ✓ Server cleanup complete")
        except Exception as e:
            print(f"   ✗ Cleanup error: {e}")
        
        try:
            import block_internet
            if block_internet.enabled:
                print("   ⚠️ Internet was blocked, restoring...")
                block_internet.disable()
        except:
            pass
        
        print("   ✓ Cleanup complete")
    
    atexit.register(cleanup)
    
    # Start GUI
    print("\n🖥️  Starting GUI...")
    try:
        root = gui.start_gui()
        print("   ✓ GUI started successfully")
    except Exception as e:
        print(f"   ❌ Failed to start GUI: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Start network monitor thread
    print("📡 Starting network monitor...")
    monitor_thread = threading.Thread(target=network_monitor, daemon=True)
    monitor_thread.start()
    print("   ✓ Network monitor started")
    
    # Start connection thread
    print("🔌 Starting connection manager...")
    connection_thread = threading.Thread(target=server.connect_to_teacher, daemon=True)
    connection_thread.start()
    print("   ✓ Connection manager started")
    
    # Import other modules (they auto-start threads)
    try:
        import block_copy
        print("   ✓ Copy-paste blocker loaded")
    except ImportError as e:
        print(f"   ⚠️ Copy-paste blocker not available: {e}")
    
    try:
        import block_internet
        print("   ✓ Internet blocker loaded")
    except ImportError as e:
        print(f"   ⚠️ Internet blocker not available: {e}")
    
    try:
        import screen_stream
        print("   ✓ Screen streamer loaded")
    except ImportError as e:
        print(f"   ⚠️ Screen streamer not available: {e}")
    
    try:
        import screen_lock_student
        print("   ✓ Screen lock module loaded")
    except ImportError as e:
        print(f"   ⚠️ Screen lock module not available: {e}")
    
    try:
        import message_popup
        print("   ✓ Message popup module loaded")
    except ImportError as e:
        print(f"   ⚠️ Message popup module not available: {e}")
    
    try:
        import remote_control
        print("   ✓ Remote control module loaded")
    except ImportError as e:
        print(f"   ⚠️ Remote control module not available: {e}")
    
    try:
        import quiz_student
        print("   ✓ Quiz module loaded")
    except ImportError as e:
        print(f"   ⚠️ Quiz module not available: {e}")
    
    print("\n" + "=" * 70)
    print("✅ ALL SYSTEMS READY!")
    print("📡 Waiting for teacher commands...")
    print("💡 Press Ctrl+C to exit")
    print("=" * 70 + "\n")
    
    # Add startup log to GUI
    try:
        status = config.get_network_status()
        gui.add_log(f"Started in {status['connection_type']} mode")
        gui.add_log(f"Local IP: {status['local_ip']}")
        if status['teacher_reachable']:
            gui.add_log("Teacher is reachable on network")
        else:
            gui.add_log("Waiting for teacher to be reachable...")
    except:
        pass
    
    # Start main loop with exception handling
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n\n⚠️ Shutdown requested by user...")
    except Exception as e:
        print(f"\n❌ GUI error: {e}")
    finally:
        print("🛑 Shutting down...")
        cleanup()
        print("👋 Goodbye!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)