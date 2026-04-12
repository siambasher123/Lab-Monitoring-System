# ide_controller.py - IDE CONTROL LOGIC (SEPARATE FROM GUI)
import state

# IDE to command mapping
IDE_COMMANDS = {
    "VS Code": "LAUNCH_VSCODE",
    "Code::Blocks": "LAUNCH_CODEBLOCKS",
    "Spyder": "LAUNCH_SPYDER",
    "PyCharm": "LAUNCH_PYCHARM",
    "IDLE": "LAUNCH_IDLE",
    "Sublime Text": "LAUNCH_SUBLIME"
}

# Callbacks
status_callback = None

def set_status_callback(callback):
    """Set callback for status updates"""
    global status_callback
    status_callback = callback

def launch_ide(ide_name, duration, force_lock=True, reopen=True):
    """Launch IDE on all student PCs"""
    
    # Get command
    cmd = IDE_COMMANDS.get(ide_name, "LAUNCH_VSCODE")
    
    # Build command with options
    full_cmd = f"{cmd}:{duration}"
    if force_lock:
        full_cmd += ":LOCK"
    if reopen:
        full_cmd += ":REOPEN"
    
    # Send to all students
    state.send_command(full_cmd)
    
    # Log
    state.add_log(f"Teacher | Launched {ide_name} ({duration} min)")
    
    # Update status
    if status_callback:
        status_callback(f"Active: {ide_name} ({duration} min)", "green")

def end_ide_session():
    """End IDE session early"""
    state.send_command("END_IDE_SESSION")
    state.add_log("Teacher | Ended IDE session")
    
    if status_callback:
        status_callback("No active session", "gray")