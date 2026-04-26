# server.py - STUDENT SIDE with parallel command processing and PROPER SHUTDOWN
# UPDATED: Fixed quiz handling for working quiz_student.py  
# FIXED: Added graceful shutdown support
import socket
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import base64
import json
import subprocess
import os

import gui
import block_copy
import block_internet
import config
import message_popup
import screen_lock_student
import ide_controller  # Import IDE controller

# ===== SILENT REMOTE CONTROL IMPORT =====
try:
    import remote_control
    REMOTE_CONTROL_AVAILABLE = True
except ImportError:
    REMOTE_CONTROL_AVAILABLE = False
    print("[WARNING] Remote control module not found")

# ===== QUIZ MODULE IMPORT =====
try:
    import quiz_student
    QUIZ_AVAILABLE = True
except ImportError:
    QUIZ_AVAILABLE = False
    print("[WARNING] Quiz module not found")

connected = False
sock = None
# Thread pool for parallel command execution
executor = ThreadPoolExecutor(max_workers=4)
_reconnect_event = threading.Event()
_last_heartbeat = 0
HEARTBEAT_INTERVAL = 30

# Global shutdown flag
shutdown_flag = False

def handle_command_async(cmd: str):
    """Handle command in separate thread"""
    global shutdown_flag
    
    if shutdown_flag:
        print(f"[SERVER] Ignoring command during shutdown: {cmd[:50]}")
        return
    
    cmd = cmd.strip()
    
    # CRITICAL DEBUG - This will show EVERY command received
    print(f"\n{'='*60}")
    print(f"🔴🔴🔴 [STUDENT] RECEIVED COMMAND: '{cmd}'")
    print(f"🔴 Command length: {len(cmd)}")
    print(f"{'='*60}")
    
    if not cmd:
        print("[STUDENT] Empty command, ignoring")
        return
    
    # ===== IDE CONTROL COMMANDS =====
    if cmd.startswith("LAUNCH_IDE|"):
        print(f"\n💻 [STUDENT] IDE LAUNCH COMMAND RECEIVED")
        try:
            # Parse format:
            # LAUNCH_IDE|Code::Blocks|15
            # LAUNCH_IDE|Code::Blocks|15|LOCKPIN:1234
            parts = cmd.split("|")
            if len(parts) >= 3:
                ide_name = parts[1]
                duration_str = parts[2]
                post_session_pin = None

                if len(parts) >= 4 and parts[3].startswith("LOCKPIN:"):
                    pin_candidate = parts[3][8:].strip()
                    if pin_candidate.isdigit() and len(pin_candidate) == 4:
                        post_session_pin = pin_candidate
                    else:
                        print(f"[IDE] Invalid LOCKPIN value received: '{pin_candidate}'")
                
                # Parse duration safely
                try:
                    duration = int(duration_str)
                except:
                    duration = 30
                    print(f"[IDE] Invalid duration '{duration_str}', using 30")
                
                print(f"[IDE] Launching: {ide_name} for {duration} min")
                
                # Start IDE session (optional post-session lock PIN)
                threading.Thread(target=ide_controller.ide_instance.start_session,
                               args=(ide_name, duration, post_session_pin),
                               daemon=True).start()
                
                if post_session_pin:
                    gui.add_log(f"IDE launched: {ide_name} ({duration} min) | Post-lock enabled")
                else:
                    gui.add_log(f"IDE launched: {ide_name} ({duration} min)")
                return
        except Exception as e:
            print(f"[IDE] Error: {e}")
            gui.add_log(f"IDE launch error: {e}")
        return
        
    elif cmd == "END_IDE_SESSION":
        print(f"\n💻 [STUDENT] IDE END SESSION COMMAND RECEIVED")
        try:
            ide_controller.ide_instance.end_session()
            gui.add_log("IDE session ended by teacher")
        except Exception as e:
            print(f"[IDE] Error ending session: {e}")
        return
    
    # ===== SCREEN LOCK COMMANDS =====
    if cmd.startswith("LOCK_ALL_SCREENS:"):
        pin = cmd[17:]  # Extract PIN
        print(f"[STUDENT] SCREEN LOCK command received with PIN: {pin}")
        screen_lock_student.screen_lock.lock_screen(pin)
        gui.update_screen("Locked")
        return
        
    elif cmd == "UNLOCK_ALL_SCREENS":
        print("[STUDENT] UNLOCK ALL SCREENS command received")
        screen_lock_student.screen_lock.unlock_silently()
        gui.update_screen("Unlocked")
        return
    
    # ===== TEST COMMAND FOR DEBUGGING =====
    if cmd.startswith("TEST:"):
        print(f"\n🧪🧪🧪 [STUDENT] TEST COMMAND RECEIVED!")
        message = cmd[5:]
        print(f"🧪 Test message: '{message}'")
        gui.add_log(f"✅ Test received: {message}")
        send_log(f"Test acknowledgment: {message}")
        return
    
    # ===== SILENT REMOTE CONTROL =====
    if cmd.startswith("REMOTE_CONTROL:"):
        print(f"[STUDENT] Remote control command detected")
        action = cmd[15:]  # START or STOP
        
        if REMOTE_CONTROL_AVAILABLE:
            if action == "START":
                print("[STUDENT] Starting remote control")
                remote_control.remote_control.start()
            elif action == "STOP":
                print("[STUDENT] Stopping remote control")
                remote_control.remote_control.stop()
        else:
            print("[STUDENT] Remote control not available")
        return
    
    # ===== REMOTE INPUT EVENTS =====
    elif cmd.startswith("REMOTE_INPUT:"):
        if REMOTE_CONTROL_AVAILABLE:
            try:
                data = cmd[13:]
                parts = data.split('|')
                event_type = parts[0]
                
                if event_type == 'mouse_move':
                    x = int(parts[1])
                    y = int(parts[2])
                    remote_control.remote_control.queue_input_event('mouse_move', x=x, y=y)
                elif event_type == 'mouse_click':
                    button = parts[1]
                    down = parts[2] == '1'
                    remote_control.remote_control.queue_input_event('mouse_click', button=button, key_down=down)
                elif event_type == 'mouse_wheel':
                    delta = int(parts[1])
                    remote_control.remote_control.queue_input_event('mouse_wheel', wheel_delta=delta)
                elif event_type == 'key':
                    key_code = int(parts[1])
                    down = parts[2] == '1'
                    remote_control.remote_control.queue_input_event('key', key_code=key_code, key_down=down)
                elif event_type == 'key_char':
                    char = parts[1]
                    remote_control.remote_control.queue_input_event('key_char', key_char=char)
            except Exception as e:
                print(f"[STUDENT] Remote input error: {e}")
        return
    
    # In server.py, replace the quiz commands section with:

    # ===== QUIZ COMMANDS - FIXED FOR WORKING QUIZ_STUDENT.PY =====
    elif cmd.startswith("QUIZ_START:"):
        print(f"\n📝 [STUDENT] QUIZ_START command received")
        if QUIZ_AVAILABLE:
            try:
                # Format: QUIZ_START:quiz_id|duration|q_per_student|marks_correct|marks_wrong
                parts = cmd[11:].split('|')
                if len(parts) >= 5:
                    quiz_id = parts[0]
                    duration = int(parts[1])
                    q_per_student = int(parts[2])
                    marks_correct = int(parts[3])
                    marks_wrong = int(parts[4])
                    
                    print(f"[QUIZ] Starting quiz: {quiz_id}")
                    print(f"[QUIZ] Duration: {duration} min, Questions per student: {q_per_student}")
                    print(f"[QUIZ] Marks: +{marks_correct}/-{marks_wrong}")
                    
                    # IMPORTANT: Clear previous quiz data
                    if hasattr(quiz_student, 'student_quiz'):
                        quiz_student.student_quiz.questions = []
                        quiz_student.student_quiz.answers = {}
                    
                    # Show quiz in the main thread
                    if gui.root_window:
                        gui.root_window.after(0, lambda: quiz_student.student_quiz.show_quiz(
                            quiz_id, duration, q_per_student, marks_correct, marks_wrong
                        ))
                    
                    gui.add_log(f"Quiz started: {quiz_id}")
            except Exception as e:
                print(f"[QUIZ] Error starting quiz: {e}")
                import traceback
                traceback.print_exc()
        return
        
    elif cmd.startswith("QUIZ_QUESTION:"):
        if QUIZ_AVAILABLE:
            try:
                # Extract question data
                q_data = cmd[14:]  # Remove "QUIZ_QUESTION:"
                print(f"[QUIZ] Adding question: {q_data[:50]}...")
                
                # Pass directly to student_quiz
                if hasattr(quiz_student, 'student_quiz') and quiz_student.student_quiz:
                    quiz_student.student_quiz.add_question(q_data)
                else:
                    print(f"[QUIZ] Quiz object not initialized yet")
                    
            except Exception as e:
                print(f"[QUIZ] Error adding question: {e}")
        return
        
    elif cmd == "QUIZ_TIME_UP":
        if QUIZ_AVAILABLE:
            try:
                gui.add_log("Quiz time is up!")
                if hasattr(quiz_student, 'student_quiz') and quiz_student.student_quiz:
                    if quiz_student.student_quiz.quiz_active:
                        if gui.root_window:
                            # Force time up immediately
                            gui.root_window.after(0, quiz_student.student_quiz.force_time_up)
            except Exception as e:
                print(f"[QUIZ] Error handling time up: {e}")
        return
    
    # ===== PING COMMAND (Heartbeat) =====
    elif cmd == "PING":
        send_raw("PONG\n")
        return
    
    # ===== REGULAR COMMANDS =====
    print(f"\n📨 [STUDENT] Regular command: '{cmd[:50]}...'")
    
    # File message with attachment
    if cmd.startswith("FILE_MESSAGE:"):
        try:
            content = cmd[13:]
            parts = content.split("|||")
            
            if len(parts) == 3:
                message = parts[0]
                file_name = parts[1]
                encoded_data = parts[2]
                
                print(f"[FILE_MESSAGE] Received file: {file_name}")
                
                try:
                    file_data = base64.b64decode(encoded_data)
                    message_popup.show_message(message, file_data, file_name)
                    gui.add_log(f"Received file: {file_name} ({len(file_data)} bytes)")
                except Exception as decode_error:
                    print(f"[FILE_MESSAGE] Decode error: {decode_error}")
                    message_popup.show_message(message)
                    gui.add_log(f"Received message (file decode failed)")
            
            elif len(parts) == 1:
                message = parts[0]
                message_popup.show_message(message)
                gui.add_log(f"Message from teacher: {message[:30]}...")
        except Exception as e:
            print(f"[FILE_MESSAGE] Error: {e}")
    
    # Broadcast message
    elif cmd.startswith("BROADCAST:"):
        message = cmd[10:]
        print(f"[BROADCAST] Received message: {message}")
        try:
            message_popup.show_message(message)
            gui.add_log(f"Message from teacher: {message[:30]}...")
        except Exception as e:
            print(f"[BROADCAST] Error showing popup: {e}")
    
    # Screen streaming commands
    elif cmd.startswith("START_SCREEN_STREAM:"):
        teacher_ip = cmd[20:]
        print(f"[SCREEN] Starting screen stream to {teacher_ip}")
        try:
            import screen_stream
            screen_stream.screen_streamer.start_streaming(teacher_ip)
            gui.add_log("Screen streaming started")
        except ImportError:
            print("[SCREEN] ERROR: screen_stream module not found")
        except Exception as e:
            print(f"[SCREEN] Error starting stream: {e}")
        
    elif cmd.startswith("STOP_SCREEN_STREAM:"):
        print("[SCREEN] Stopping screen stream")
        try:
            import screen_stream
            screen_stream.screen_streamer.stop_streaming()
            gui.add_log("Screen streaming stopped")
        except ImportError:
            print("[SCREEN] ERROR: screen_stream module not found")
        except Exception as e:
            print(f"[SCREEN] Error stopping stream: {e}")
        
    elif cmd.startswith("REFRESH_SCREEN:"):
        print("[SCREEN] Refresh requested")
        gui.add_log("Screen refresh requested")

    elif cmd.startswith("SET_STREAM_QUALITY:"):
        payload = cmd[19:]
        try:
            quality_str, fps_str, width_str, height_str = payload.split('|', 3)
            quality = int(float(quality_str))
            fps = float(fps_str)
            width = int(float(width_str))
            height = int(float(height_str))

            import screen_stream
            screen_stream.screen_streamer.update_settings(
                quality=quality,
                fps=fps,
                width=width,
                height=height,
            )
            gui.add_log(f"Stream quality updated: {width}x{height}, Q{quality}, {fps} FPS")
        except Exception as e:
            print(f"[SCREEN] Invalid stream quality command: {payload} ({e})")
    
    # Copy-paste blocking
    elif cmd == "BLOCK":
        print("[STUDENT] BLOCK copy-paste command")
        block_copy.enable()
        gui.update_copy("Blocked")
        
    elif cmd == "UNBLOCK":
        print("[STUDENT] UNBLOCK copy-paste command")
        block_copy.disable()
        gui.update_copy("Unblocked")
    
    # Internet blocking    
    elif cmd == "BLOCK_INTERNET":
        print("[STUDENT] BLOCK_INTERNET command")
        block_internet.enable()
        gui.update_internet("Blocked")
        
    elif cmd == "UNBLOCK_INTERNET":
        print("[STUDENT] UNBLOCK_INTERNET command")
        block_internet.disable()
        gui.update_internet("Unblocked")
    
    else:
        print(f"[STUDENT] Unknown command: {cmd}")

def handle_command(cmd: str):
    """Schedule command for async execution"""
    if cmd.strip():
        print(f"[STUDENT] Scheduling command: '{cmd[:50]}...'")
        executor.submit(handle_command_async, cmd.strip())

def send_raw(data):
    """Send raw data without logging"""
    global connected, sock
    if connected and sock:
        try:
            sock.send(data.encode() if isinstance(data, str) else data)
        except:
            pass

def monitor_connection():
    """Monitor connection health with heartbeat"""
    global connected, _last_heartbeat
    
    while True:
        if connected and sock:
            try:
                time.sleep(HEARTBEAT_INTERVAL)
                if connected:
                    # Send heartbeat
                    send_raw("PING\n")
                    _last_heartbeat = time.time()
                    print("[CONNECTION] Heartbeat sent")
            except:
                print("[CONNECTION] Heartbeat failed")
                connected = False
                gui.update_status("disconnected")
        else:
            time.sleep(1)

def check_teacher_reachable():
    """Check if teacher is reachable on LAN (without internet)"""
    try:
        # Try ping first (fastest)
        param = '-n' if os.name == 'nt' else '-c'
        result = subprocess.run(['ping', param, '1', config.TEACHER_IP], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            return True, "LAN"
        
        # Try TCP connection
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(1)
        result = test_sock.connect_ex((config.TEACHER_IP, config.PORT))
        test_sock.close()
        
        if result == 0:
            return True, "TCP"
        else:
            return False, f"Error {result}"
    except:
        return False, "Check failed"

def connect_to_teacher():
    """Connect to teacher with auto-reconnect and network change detection"""
    global connected, sock, shutdown_flag
    
    # Show network status at start
    network_status = config.get_network_status()
    print(f"\n🌐 Initial Network: {network_status['connection_type']}")
    print(f"📡 Local IP: {network_status['local_ip']}")
    print(f"🎯 Teacher IP: {config.TEACHER_IP}")
    
    while not shutdown_flag:
        if not connected and not shutdown_flag:
            try:
                # First check if teacher is reachable
                reachable, method = check_teacher_reachable()
                if not reachable:
                    if not shutdown_flag:
                        print(f"\n[CONNECTION] ⚠️ Teacher {config.TEACHER_IP} not reachable")
                        print("[CONNECTION] Make sure:")
                        print("  1. Teacher PC is on and running the app")
                        print("  2. Both PCs are on the same network")
                        print("  3. Firewall allows port 5000")
                    
                    # Wait before retry
                    for i in range(5, 0, -1):
                        if shutdown_flag:
                            print("[CONNECTION] Shutdown during retry wait")
                            return
                        print(f"[CONNECTION] Retrying in {i} seconds...", end='\r')
                        time.sleep(1)
                    print()
                    continue
                
                if shutdown_flag:
                    print("[CONNECTION] Shutdown requested during connection attempt")
                    return
                
                gui.update_status("trying")
                print(f"\n[CONNECTION] Connecting to teacher at {config.TEACHER_IP}:{config.PORT}...")
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((config.TEACHER_IP, config.PORT))
                
                connected = True
                gui.update_status("connected")
                print(f"[CONNECTION] ✓ Connected successfully via {method}!")
                print(f"[CONNECTION] Local socket: {sock.getsockname()}")
                
                # Send connection info with network status
                status = config.get_network_status()
                send_log(f"Connected via {status['connection_type']} | IP: {status['local_ip']}")
                
                # Start heartbeat monitor
                threading.Thread(target=monitor_connection, daemon=True).start()
                
                # Buffer for incomplete messages
                buffer = ""
                
                while connected and not shutdown_flag:
                    try:
                        data = sock.recv(8192)
                        if not data:
                            print("[CONNECTION] No data received, connection closed")
                            raise ConnectionError("Disconnected")
                        
                        received_text = data.decode('utf-8', errors='ignore')
                        
                        # Handle heartbeat response
                        if received_text.strip() == "PONG":
                            print("[CONNECTION] Heartbeat received")
                            continue
                        
                        print(f"\n[CONNECTION] Received raw data ({len(data)} bytes)")
                        if len(received_text) > 0 and len(received_text) < 200:
                            print(f"[CONNECTION] Raw data preview: {received_text[:100]}")
                        
                        buffer += received_text
                        
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if line and line != "PONG":
                                print(f"[CONNECTION] Processing line: '{line}'")
                                handle_command(line)
                        
                    except socket.timeout:
                        if shutdown_flag:
                            print("[CONNECTION] Shutdown during socket read")
                            break
                        continue
                    except Exception as e:
                        if not shutdown_flag:
                            connected = False
                            gui.update_status("disconnected")
                            print(f"[CONNECTION] ✗ Connection lost: {e}")
                            
                            # Check if teacher is still reachable
                            reachable, _ = check_teacher_reachable()
                            if reachable and not shutdown_flag:
                                print("[CONNECTION] Teacher still reachable, reconnecting...")
                            else:
                                print("[CONNECTION] Teacher not reachable, waiting...")
                        
                        try:
                            sock.close()
                        except:
                            pass
                        break
                        
            except Exception as e:
                if not shutdown_flag:
                    connected = False
                    gui.update_status("trying")
                    print(f"[CONNECTION] ✗ Connection failed: {e}")
                try:
                    if sock:
                        sock.close()
                except:
                    pass
            
            if shutdown_flag:
                print("[CONNECTION] Shutdown requested, exiting connection loop")
                break
            
            # Progressive backoff retry
            for i in range(3, 0, -1):
                if shutdown_flag:
                    print("[CONNECTION] Shutdown during backoff")
                    return
                print(f"[CONNECTION] Retrying in {i} seconds...", end='\r')
                time.sleep(1)
            print()
    
    # Cleanup on shutdown
    print("[CONNECTION] Closing connection...")
    if sock:
        try:
            sock.close()
        except:
            pass
    connected = False
    print("[CONNECTION] Connection thread stopped")

def send_log(message):
    """Send log message to teacher"""
    if connected and sock:
        try:
            full_message = f"LOG {config.STUDENT_NAME}: {message}\n"
            sock.send(full_message.encode())
            print(f"[STUDENT] Sent log: {message[:50]}...")
        except Exception as e:
            print(f"[STUDENT] Failed to send log: {e}")

def send_quiz_submission(quiz_id, student_roll, answers_json):
    """Send quiz answers to teacher"""
    if connected and sock:
        try:
            full_message = f"LOG QUIZ_SUBMIT:{quiz_id}|{student_roll}|{answers_json}\n"
            sock.send(full_message.encode())
            print(f"[QUIZ] Submitted answers for student {student_roll}")
            return True
        except Exception as e:
            print(f"[QUIZ] Error submitting: {e}")
            return False
    return False

def cleanup():
    """Cleanup resources"""
    global executor, shutdown_flag, sock, connected
    
    print("\n[STUDENT SERVER] Cleaning up...")
    shutdown_flag = True
    
    # CRITICAL: End IDE session FIRST - this is most important
    try:
        if ide_controller.ide_instance and ide_controller.ide_instance.session_active:
            print("[STUDENT SERVER] ⚠️ IDE session active, ending gracefully...")
            ide_controller.ide_instance.end_session_early()  # Use early end to ensure cleanup
            # Give it time to finish
            import time
            time.sleep(0.5)
            print("[STUDENT SERVER] ✓ IDE session ended")
    except Exception as e:
        print(f"[STUDENT SERVER] Error ending IDE session: {e}")
    
    # Stop remote control if active
    if REMOTE_CONTROL_AVAILABLE:
        try:
            remote_control.remote_control.stop()
            print("[STUDENT SERVER] ✓ Remote control stopped")
        except:
            pass
    
    # Close quiz if active
    if QUIZ_AVAILABLE:
        try:
            if hasattr(quiz_student, 'student_quiz') and quiz_student.student_quiz:
                if quiz_student.student_quiz.quiz_active:
                    if (hasattr(quiz_student.student_quiz, 'window') and 
                        quiz_student.student_quiz.window and 
                        quiz_student.student_quiz.window.winfo_exists()):
                        quiz_student.student_quiz.window.quit()
                        quiz_student.student_quiz.window.destroy()
            print("[STUDENT SERVER] ✓ Quiz closed")
        except:
            pass
    
    # Close socket
    if sock:
        try:
            sock.close()
            print("[STUDENT SERVER] ✓ Socket closed")
        except:
            pass
    
    connected = False
    
    # Shutdown thread pool
    try:
        print("[STUDENT SERVER] Shutting down thread pool...")
        executor.shutdown(wait=False)
        print("[STUDENT SERVER] ✓ Thread pool shut down")
    except:
        pass
    
    print("[STUDENT SERVER] Cleanup complete")