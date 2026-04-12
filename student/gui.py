# gui.py - STUDENT GUI (UPDATED with IDE status)
import tkinter as tk
from tkinter import ttk
import config

# Global GUI elements - MUST be initialized to None
status_label = None
copy_label = None
internet_label = None
screen_label = None
ide_label = None  # NEW: IDE status label
log_box = None
root_window = None

# GUI update functions that can be called from other threads
def update_status(state):
    """Update connection status - must run in main thread"""
    if not status_label:
        print("[GUI] status_label not initialized!")
        return

    def _update():
        if state == "connected":
            status_label.config(text="● Connected", foreground="green")
            add_log("Connected to teacher")
        elif state == "trying":
            status_label.config(text="● Trying to connect...", foreground="red")
        elif state == "disconnected":
            status_label.config(text="● Disconnected", foreground="red")
            add_log("Connection lost, retrying...")
    
    # Schedule update in main thread
    if root_window:
        root_window.after(0, _update)

def update_copy(status):
    """Update copy-paste status - must run in main thread"""
    if not copy_label:
        print("[GUI] copy_label not initialized!")
        return

    def _update():
        color = "red" if status == "Blocked" else "green"
        copy_label.config(text=f"Copy-Paste: {status}", foreground=color)
        add_log(f"Copy-Paste {status}")
    
    if root_window:
        root_window.after(0, _update)

def update_internet(status):
    """Update internet status - must run in main thread"""
    if not internet_label:
        print("[GUI] internet_label not initialized!")
        return

    def _update():
        color = "red" if status == "Blocked" else "green"
        internet_label.config(text=f"Internet: {status}", foreground=color)
        add_log(f"Internet {status}")
    
    if root_window:
        root_window.after(0, _update)

def update_screen(status):
    """Update screen status - must run in main thread"""
    if not screen_label:
        print("[GUI] screen_label not initialized!")
        return

    def _update():
        # Handle different status formats
        if "Locked" in str(status):
            screen_label.config(text="Screen: Locked 🔒", foreground="red")
            add_log("🔒 Screen locked - PIN required")
        else:
            screen_label.config(text="Screen: Unlocked 🔓", foreground="green")
            add_log("🔓 Screen unlocked")
    
    if root_window:
        root_window.after(0, _update)

def update_ide(status):
    """Update IDE status - must run in main thread (NEW)"""
    if not ide_label:
        print("[GUI] ide_label not initialized!")
        return

    def _update():
        if status == "Active":
            ide_label.config(text="IDE: Active 💻", foreground="purple")
        else:
            ide_label.config(text="IDE: Inactive", foreground="gray")
    
    if root_window:
        root_window.after(0, _update)

def add_log(message):
    """Add log message - must run in main thread"""
    if not log_box:
        print("[GUI] log_box not initialized!")
        return

    def _add():
        import time
        timestamp = time.strftime("%H:%M:%S")
        log_box.insert(tk.END, f"[{timestamp}] {message}\n")
        log_box.see(tk.END)
    
    if root_window:
        root_window.after(0, _add)

def start_gui():
    """Start the student GUI"""
    global status_label, copy_label, internet_label, screen_label, ide_label, log_box, root_window

    root = tk.Tk()
    root_window = root  # Store reference for thread-safe updates
    
    root.title(f"Student Agent - {config.STUDENT_NAME}")
    root.geometry("500x480")  # Slightly taller for IDE status
    root.resizable(False, False)

    # Main frame
    main_frame = ttk.Frame(root, padding=20)
    main_frame.pack(fill="both", expand=True)

    # Title
    title_label = ttk.Label(
        main_frame,
        text="Student Control Agent",
        font=("Segoe UI", 14, "bold")
    )
    title_label.pack(pady=(0, 10))

    # Student info
    info_frame = ttk.Frame(main_frame)
    info_frame.pack(fill="x", pady=5)
    
    ttk.Label(info_frame, text=f"Student: {config.STUDENT_NAME}", 
              font=("Segoe UI", 10)).pack(side="left")
    ttk.Label(info_frame, text=f"IP: {config.get_my_ip()}", 
              font=("Segoe UI", 10)).pack(side="right")

    # Connection status
    status_label = ttk.Label(
        main_frame,
        text="● Trying to connect...",
        foreground="red",
        font=("Segoe UI", 10, "bold")
    )
    status_label.pack(anchor="w", pady=(10, 5))

    # Feature status frame
    status_frame = ttk.LabelFrame(main_frame, text="Feature Status", padding=15)
    status_frame.pack(fill="x", pady=10)

    # Initialize status labels
    copy_label = ttk.Label(status_frame, text="Copy-Paste: Unblocked", 
                          foreground="green", font=("Segoe UI", 10))
    copy_label.pack(anchor="w", pady=3)

    internet_label = ttk.Label(status_frame, text="Internet: Unblocked", 
                              foreground="green", font=("Segoe UI", 10))
    internet_label.pack(anchor="w", pady=3)

    screen_label = ttk.Label(status_frame, text="Screen: Unlocked 🔓", 
                            foreground="green", font=("Segoe UI", 10))
    screen_label.pack(anchor="w", pady=3)

    # NEW: IDE status label
    ide_label = ttk.Label(status_frame, text="IDE: Inactive", 
                         foreground="gray", font=("Segoe UI", 10))
    ide_label.pack(anchor="w", pady=3)

    # Activity log
    log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding=10)
    log_frame.pack(fill="both", expand=True, pady=10)

    # Log container with scrollbar
    log_container = ttk.Frame(log_frame)
    log_container.pack(fill="both", expand=True)

    # Scrollbar
    scrollbar = ttk.Scrollbar(log_container)
    scrollbar.pack(side="right", fill="y")

    # Text widget for logs
    log_box = tk.Text(
        log_container,
        height=10,
        wrap="word",
        font=("Consolas", 9),
        yscrollcommand=scrollbar.set
    )
    log_box.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=log_box.yview)

    # Initial log messages
    add_log("Student agent started")
    add_log(f"Teacher IP: {config.TEACHER_IP}")
    add_log("Waiting for teacher commands...")

    return root