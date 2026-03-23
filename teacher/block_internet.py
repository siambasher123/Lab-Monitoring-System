# block_internet.py - TEACHER SIDE
import state

def enable():
    """Send command to block internet on all students"""
    state.send_command("BLOCK_INTERNET")
    state.add_log("Teacher | Internet COMPLETELY BLOCKED for all students")

def disable():
    """Send command to unblock internet on all students"""
    state.send_command("UNBLOCK_INTERNET")
    state.add_log("Teacher | Internet COMPLETELY RESTORED for all students")