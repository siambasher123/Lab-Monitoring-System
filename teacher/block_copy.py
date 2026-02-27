# block_copy.py
import state

def enable():
    state.copy_blocked = True
    state.send_command("BLOCK")
    state.add_log("Teacher | Copy-Paste BLOCKED")

def disable():
    state.copy_blocked = False
    state.send_command("UNBLOCK")
    state.add_log("Teacher | Copy-Paste UNBLOCKED")