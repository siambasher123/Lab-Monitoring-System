# state.py - Global state (UPDATED with enhanced quiz session)
students = {}  # ip -> socket
copy_blocked = False
screen_lock_active = False
current_lock_pin = None
locked_students = {}  # ip -> locked status

# Callback lists
log_callbacks = []
status_callbacks = []
update_callbacks = []

def add_log_callback(callback):
    """Add callback for log messages"""
    if callback not in log_callbacks:
        log_callbacks.append(callback)

def add_status_callback(callback):
    """Add callback for status updates"""
    if callback not in status_callbacks:
        status_callbacks.append(callback)

def add_update_callback(callback):
    """Add callback for student list updates"""
    if callback not in update_callbacks:
        update_callbacks.append(callback)

def send_command(command):
    """Send command to ALL connected students with proper separation"""
    disconnected = []
    
    print(f"[TEACHER] Sending command: '{command}'")
    
    # Ensure command ends with newline for proper separation
    if not command.endswith('\n'):
        command = command + '\n'
    
    for ip, sock in list(students.items()):
        try:
            sock.send(command.encode())
        except:
            disconnected.append(ip)
            print(f"[TEACHER] Failed to send to {ip}")
    
    # Remove disconnected students
    for ip in disconnected:
        if ip in students:
            del students[ip]
    
    # Update student list in GUI
    for callback in update_callbacks:
        try:
            callback()
        except:
            pass

def send_command_to_all(command):
    """Send command to all connected students"""
    disconnected = []
    for ip, sock in list(students.items()):
        try:
            sock.send(command.encode())
        except:
            disconnected.append(ip)
    
    # Remove disconnected
    for ip in disconnected:
        if ip in students:
            del students[ip]
    
    # Update UI
    for callback in update_callbacks:
        try:
            callback()
        except:
            pass

def add_log(message):
    """Add log message to all registered callbacks"""
    print(f"[TEACHER LOG] {message}")
    
    # Highlight PINs in the message
    if "PIN:" in message:
        # Extract and format PIN for better visibility
        import re
        pin_match = re.search(r'PIN: (\d{4})', message)
        if pin_match:
            pin = pin_match.group(1)
            # Create a highlighted version (just for display, not changing callback)
            highlighted = message.replace(f"PIN: {pin}", f"PIN: {pin} 🔑")
            for callback in log_callbacks:
                try:
                    callback(highlighted)
                except:
                    pass
            return
    
    for callback in log_callbacks:
        try:
            callback(message)
        except:
            pass

def update_status(message):
    """Update status message in all registered callbacks"""
    for callback in status_callbacks:
        try:
            callback(message)
        except:
            pass

def get_student_count():
    """Get number of connected students"""
    return len(students)

def clear_students():
    """Clear all student connections (for reset)"""
    students.clear()
    for callback in update_callbacks:
        try:
            callback()
        except:
            pass

def send_command_to_student(student_ip, command):
    """Send command to a specific student only"""
    if student_ip in students:
        try:
            if not command.endswith('\n'):
                command = command + '\n'
            students[student_ip].send(command.encode())
            return True
        except:
            # Remove disconnected student
            if student_ip in students:
                del students[student_ip]
            for callback in update_callbacks:
                try:
                    callback()
                except:
                    pass
    return False

def lock_all_students(pin):
    """Lock all connected students with given PIN"""
    global screen_lock_active, current_lock_pin
    screen_lock_active = True
    current_lock_pin = pin
    
    # Send lock command to all students with PIN
    send_command(f"LOCK_ALL_SCREENS:{pin}")
    add_log(f"Teacher | Locked ALL screens with PIN: {pin}")
    
    # Mark all students as locked
    for ip in students:
        locked_students[ip] = True

def unlock_all_students():
    """Unlock all students"""
    global screen_lock_active, current_lock_pin
    screen_lock_active = False
    current_lock_pin = None
    
    # Send unlock command to all students
    send_command("UNLOCK_ALL_SCREENS")
    add_log("Teacher | Unlocked ALL screens")
    
    # Clear all locked status
    locked_students.clear()

def is_student_locked(student_ip):
    """Check if a specific student is locked"""
    return locked_students.get(student_ip, False)

def student_unlocked(student_ip):
    """Mark student as unlocked (when they enter correct PIN)"""
    if student_ip in locked_students:
        del locked_students[student_ip]
        add_log(f"Student {student_ip} unlocked screen with correct PIN")


# Enhanced Quiz session storage
quiz_session = {
    'questions': [],           # List of question objects
    'file_path': None,         # Path to original PDF
    'total': 0,                # Total number of questions
    'timestamp': None,         # When the session was created
    'teacher_email': None,     # Teacher's email for sending results
    'quiz_name': None,         # Name of the quiz
    'settings': {              # Quiz settings
        'marks_correct': 4,
        'marks_wrong': 1,
        'duration': 30,
        'code_threshold': 50
    }
}

def save_quiz_session(questions, file_path, teacher_email=None, quiz_name=None, settings=None):
    """Save quiz session globally with enhanced information"""
    global quiz_session
    import time
    
    quiz_session = {
        'questions': questions,
        'file_path': file_path,
        'total': len(questions),
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
        'teacher_email': teacher_email,
        'quiz_name': quiz_name or f"Quiz_{time.strftime('%Y%m%d_%H%M%S')}",
        'settings': settings or {
            'marks_correct': 4,
            'marks_wrong': 1,
            'duration': 30,
            'code_threshold': 50
        }
    }
    
    # Log question type breakdown
    counts = {
        'mcq': 0,
        'truefalse': 0,
        'short': 0,
        'short_with_sample': 0,
        'code': 0
    }
    
    for q in questions:
        q_type = q.get('type', 'short')
        if q_type in counts:
            counts[q_type] += 1
        else:
            counts['short'] += 1
    
    summary = f"MCQ:{counts['mcq']} TF:{counts['truefalse']} Short:{counts['short'] + counts['short_with_sample']} Code:{counts['code']}"
    
    print(f"[STATE] Quiz session saved: {len(questions)} questions ({summary})")
    if teacher_email:
        print(f"[STATE] Teacher email: {teacher_email}")

def load_quiz_session():
    """Load quiz session"""
    global quiz_session
    return quiz_session

def update_quiz_settings(marks_correct=None, marks_wrong=None, duration=None, code_threshold=None):
    """Update quiz settings"""
    global quiz_session
    
    if marks_correct is not None:
        quiz_session['settings']['marks_correct'] = marks_correct
    if marks_wrong is not None:
        quiz_session['settings']['marks_wrong'] = marks_wrong
    if duration is not None:
        quiz_session['settings']['duration'] = duration
    if code_threshold is not None:
        quiz_session['settings']['code_threshold'] = code_threshold
    
    print(f"[STATE] Quiz settings updated: {quiz_session['settings']}")

def clear_quiz_session():
    """Clear quiz session"""
    global quiz_session
    quiz_session = {
        'questions': [],
        'file_path': None,
        'total': 0,
        'timestamp': None,
        'teacher_email': None,
        'quiz_name': None,
        'settings': {
            'marks_correct': 4,
            'marks_wrong': 1,
            'duration': 30,
            'code_threshold': 50
        }
    }
    print("[STATE] Quiz session cleared")

def get_quiz_statistics():
    """Get statistics about current quiz"""
    if not quiz_session['questions']:
        return None
    
    questions = quiz_session['questions']
    
    # Count by type
    type_counts = {}
    for q in questions:
        q_type = q.get('type', 'short')
        type_counts[q_type] = type_counts.get(q_type, 0) + 1
    
    # Calculate difficulty distribution (if available)
    difficulties = {}
    for q in questions:
        diff = q.get('difficulty', 'medium')
        difficulties[diff] = difficulties.get(diff, 0) + 1
    
    return {
        'total': len(questions),
        'by_type': type_counts,
        'by_difficulty': difficulties,
        'settings': quiz_session['settings'],
        'teacher_email': quiz_session['teacher_email'],
        'quiz_name': quiz_session['quiz_name'],
        'timestamp': quiz_session['timestamp']
    }