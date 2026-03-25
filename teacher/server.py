# server.py - TEACHER SIDE with quiz support
# UPDATED: Enhanced quiz handling with email and multiple question types
# FIXED: Removed noisy screen data warnings
import socket
import threading
import state
import json
import time
import subprocess
import os

PORT = 5000
HEARTBEAT_INTERVAL = 30

def check_network_status():
    """Check if internet is available"""
    try:
        # Try to reach Google DNS
        socket.gethostbyname("www.google.com")
        return "Internet + LAN"
    except:
        return "LAN Only"

def handle_student(conn, addr):
    ip = addr[0]
    state.students[ip] = conn
    last_heartbeat = time.time()
    
    # Update student list
    for callback in state.update_callbacks:
        try:
            callback()
        except:
            pass
    
    try:
        conn.settimeout(HEARTBEAT_INTERVAL + 5)
        
        while True:
            try:
                # First 4 bytes for data length
                length_bytes = conn.recv(4)
                if not length_bytes or len(length_bytes) < 4:
                    print(f"[TEACHER] No length bytes from {ip}")
                    break
                
                data_length = int.from_bytes(length_bytes, 'little')
                
                # Handle heartbeat (PING message)
                if data_length == 4:  # "PING".encode() is 4 bytes
                    ping_data = conn.recv(4)
                    if ping_data == b'PING':
                        conn.send(b'PONG\n')
                        last_heartbeat = time.time()
                        # Optional: Uncomment for heartbeat debugging
                        # print(f"[TEACHER] Heartbeat from {ip}")
                        continue
                
                # Handle screen data (between 1KB and 50KB)
                elif 1000 < data_length < 50000:
                    # Silent processing - no print statements
                    screen_data = b''
                    bytes_received = 0
                    while bytes_received < data_length:
                        chunk_size = min(4096, data_length - bytes_received)
                        chunk = conn.recv(chunk_size)
                        if not chunk:
                            break
                        screen_data += chunk
                        bytes_received += len(chunk)
                    
                    if len(screen_data) == data_length:
                        try:
                            import screen_dashboard
                            screen_dashboard.screen_dashboard.receive_screen_data(ip, screen_data)
                        except:
                            pass  # Silently ignore screen dashboard errors
                    continue
                
                # Handle suspicious large data - silently discard
                elif data_length >= 50000:
                    # Silently discard without printing warnings
                    try:
                        # Only read a small amount to clear the buffer
                        conn.recv(min(data_length, 4096))
                    except:
                        pass
                    continue
                
                # Regular message (text data) - small messages only
                elif data_length > 0 and data_length <= 4096:
                    msg_bytes = b''
                    bytes_received = 0
                    while bytes_received < data_length:
                        chunk = conn.recv(data_length - bytes_received)
                        if not chunk:
                            break
                        msg_bytes += chunk
                        bytes_received += len(chunk)
                    
                    if msg_bytes:
                        msg = msg_bytes.decode('utf-8', errors='ignore')
                        if msg:
                            if msg.startswith("LOG "):
                                content = msg[4:].strip()
                                
                                # Check for quiz submission
                                if content.startswith("QUIZ_SUBMIT:"):
                                    try:
                                        quiz_data = content[12:]
                                        parts = quiz_data.split('|', 2)
                                        if len(parts) == 3:
                                            quiz_id = parts[0]
                                            student_num = parts[1]
                                            answers_json = parts[2]
                                            
                                            print(f"[QUIZ] Received submission from {student_num} ({ip})")
                                            
                                            try:
                                                # Parse the submission (now contains student info + answers)
                                                submission = json.loads(answers_json)
                                                
                                                # Import quiz_teacher and forward to quiz panel
                                                try:
                                                    import quiz_teacher
                                                    if hasattr(quiz_teacher, 'quiz_teacher') and quiz_teacher.quiz_teacher:
                                                        # Forward to quiz panel
                                                        quiz_teacher.quiz_teacher.receive_submission(
                                                            ip, 
                                                            student_num, 
                                                            submission
                                                        )
                                                        state.add_log(
                                                            f"Quiz submission from {submission.get('student_num', student_num)} "
                                                            f"({submission.get('student_email', 'no email')}) - "
                                                            f"{len(submission.get('answers', {}))} answers"
                                                        )
                                                except Exception as e:
                                                    print(f"[QUIZ] Error in quiz panel: {e}")
                                                    state.add_log(f"Quiz panel error for {ip}")
                                                    
                                            except json.JSONDecodeError as json_error:
                                                print(f"[QUIZ] JSON parse error: {json_error}")
                                                state.add_log(f"Quiz JSON error from {ip}")
                                            except Exception as e:
                                                print(f"[QUIZ] Error processing submission: {e}")
                                                state.add_log(f"Quiz submission error from {ip}")
                                    except Exception as e:
                                        print(f"[QUIZ] Error in quiz submission handling: {e}")
                                
                                # Student registration for quiz
                                elif content.startswith("QUIZ_REGISTER:"):
                                    try:
                                        reg_data = content[14:]
                                        student_num, student_email, student_name = reg_data.split('|', 2)
                                        state.add_log(f"Student {student_num} ({student_email}) registered for quiz")
                                    except:
                                        pass
                                
                                # Regular log message
                                else:
                                    parts = content.split(":", 1)
                                    if len(parts) == 2:
                                        student_name = parts[0].strip()
                                        message = parts[1].strip()
                                        
                                        if "Student_" in student_name:
                                            machine_num = student_name.replace("Student_", "")
                                            state.add_log(f"Machine {machine_num}: {message}")
                                        else:
                                            state.add_log(f"{student_name}: {message}")
                
                # Check for timeout
                if time.time() - last_heartbeat > HEARTBEAT_INTERVAL * 3:
                    print(f"[TEACHER] Student {ip} heartbeat timeout")
                    break
                    
            except socket.timeout:
                # Check if still connected
                if time.time() - last_heartbeat > HEARTBEAT_INTERVAL * 3:
                    print(f"[TEACHER] Student {ip} connection timeout")
                    break
                continue
            except ConnectionError:
                print(f"[TEACHER] Connection error from {ip}")
                break
            except Exception as e:
                print(f"[TEACHER] Error from {ip}: {e}")
                break
    
    except Exception as e:
        print(f"[TEACHER] Connection error with {ip}: {e}")
    
    # Clean up disconnected student
    if ip in state.students:
        del state.students[ip]
        
        # Get network status for log
        net_status = check_network_status()
        state.add_log(f"Student disconnected: {ip} | Network: {net_status}")
        print(f"[TEACHER] Student disconnected: {ip}")
        
        # Stop screen monitoring
        try:
            import screen_dashboard
            screen_dashboard.screen_dashboard.stop_stream(ip)
        except:
            pass
        
        # Update quiz status
        try:
            import quiz_teacher
            if hasattr(quiz_teacher, 'quiz_teacher') and quiz_teacher.quiz_teacher:
                if ip in quiz_teacher.quiz_teacher.student_responses:
                    quiz_teacher.quiz_teacher.student_responses[ip]['status'] = 'disconnected'
                    quiz_teacher.quiz_teacher.refresh_progress()
        except:
            pass
        
        # Update GUI
        for callback in state.update_callbacks:
            try:
                callback()
            except:
                pass


def get_local_ip():
    """Get local IP address without internet dependency"""
    ips = []
    
    # Method 1: Hostname
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip and not local_ip.startswith('127.'):
            ips.append(local_ip)
    except:
        pass
    
    # Method 2: ipconfig
    try:
        result = subprocess.run(['ipconfig'], capture_output=True, text=True)
        import re
        ip_pattern = r'IPv4 Address[ .]+: (\d+\.\d+\.\d+\.\d+)'
        matches = re.findall(ip_pattern, result.stdout)
        for ip in matches:
            if ip.startswith(('192.168.', '10.', '172.')):
                ips.append(ip)
    except:
        pass
    
    # Method 3: Connect to router
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("192.168.1.1", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.'):
            ips.append(ip)
    except:
        pass
    
    # Return first valid IP or localhost
    return ips[0] if ips else "127.0.0.1"

def start_server():
    import socket as sock_lib
    
    # Get teacher IP using multiple methods
    teacher_ip = get_local_ip()
    
    # Check network status
    net_status = check_network_status()
    
    # Start server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("", PORT))
    server.listen()

    state.update_status(f"Server: {teacher_ip}:{PORT} ({net_status})")
    state.add_log(f"Teacher server started on {teacher_ip}:{PORT}")
    state.add_log(f"Network mode: {net_status}")
    print(f"\n{'='*60}")
    print(f"📡 TEACHER SERVER STARTED")
    print(f"{'='*60}")
    print(f"📍 Local IP: {teacher_ip}")
    print(f"🔌 Port: {PORT}")
    print(f"🌐 Mode: {net_status}")
    print(f"👥 Waiting for student connections...")
    print(f"{'='*60}\n")

    while True:
        try:
            conn, addr = server.accept()
            conn.settimeout(10.0)
            state.add_log(f"New connection from {addr[0]}")
            print(f"\n✅ New student connected: {addr[0]}")
            threading.Thread(
                target=handle_student,
                args=(conn, addr),
                daemon=True
            ).start()
        except Exception as e:
            state.add_log(f"Server error: {e}")
            print(f"[TEACHER] Server error: {e}")