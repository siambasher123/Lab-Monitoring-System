# block_copy.py - COPY-PASTE BLOCKING (UPDATED)
import keyboard
import win32clipboard
import win32con
import time
import threading
import config

import server

MAX_CHARS = 50
enabled = False
last_seq = 0

def block_keyboard_shortcuts():
    """Block all copy-paste keyboard shortcuts"""
    keyboard.add_hotkey("ctrl+c", lambda: log_copy_attempt(), suppress=True)
    keyboard.add_hotkey("ctrl+v", lambda: log_copy_attempt(), suppress=True)
    keyboard.add_hotkey("ctrl+x", lambda: log_copy_attempt(), suppress=True)
    keyboard.add_hotkey("ctrl+insert", lambda: log_copy_attempt(), suppress=True)
    keyboard.add_hotkey("shift+insert", lambda: log_copy_attempt(), suppress=True)
    keyboard.add_hotkey("print screen", lambda: log_copy_attempt(), suppress=True)
    keyboard.add_hotkey("windows+v", lambda: log_copy_attempt(), suppress=True)  # Clipboard history

def unblock_keyboard_shortcuts():
    """Remove all keyboard blocks"""
    keyboard.unhook_all_hotkeys()

def log_copy_attempt():
    """Log copy attempt to teacher - SIMPLIFIED VERSION"""
    server.send_log("Copy attempt blocked")

def manage_clipboard():
    """Monitor and limit clipboard - SILENT VERSION"""
    global last_seq
    
    while True:
        if enabled:
            try:
                seq = win32clipboard.GetClipboardSequenceNumber()
                if seq != last_seq:
                    last_seq = seq
                    win32clipboard.OpenClipboard()
                    
                    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                        text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                        if len(text) > MAX_CHARS:
                            # Limit clipboard size (silently)
                            win32clipboard.EmptyClipboard()
                            win32clipboard.SetClipboardText(text[:MAX_CHARS])
                    else:
                        win32clipboard.EmptyClipboard()
                    
                    win32clipboard.CloseClipboard()
            except Exception:
                pass  # Silently continue
        
        time.sleep(0.05)

def enable():
    """Enable copy-paste blocking"""
    global enabled
    if not enabled:
        enabled = True
        block_keyboard_shortcuts()
        print(f"[{config.STUDENT_NAME}] Copy-paste blocking ENABLED")

def disable():
    """Disable copy-paste blocking"""
    global enabled
    if enabled:
        enabled = False
        unblock_keyboard_shortcuts()
        print(f"[{config.STUDENT_NAME}] Copy-paste blocking DISABLED")
        # NO log to teacher

clipboard_thread = threading.Thread(target=manage_clipboard, daemon=True)
clipboard_thread.start()