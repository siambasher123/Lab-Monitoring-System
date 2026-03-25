# gui.py - TEACHER SIDE WITH 4-COLUMN LAYOUT (Basic + IDE + Students + Log)
# FIXED: Added safety checks for GUI updates
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import socket
import os
import base64
import state
import server
import block_copy
import block_internet
import sys
import threading
import time
import subprocess

def get_local_ip():
    """Get local IP address without internet dependency"""
    ips = []
    
    # Method 1: Hostname
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip and not local_ip.startswith('127.'):
            ips.append(("hostname", local_ip))
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
                ips.append(("ipconfig", ip))
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
            ips.append(("router", ip))
    except:
        pass
    
    # Method 4: Connect to internet (if available)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.'):
            ips.append(("internet", ip))
    except:
        pass
    
    # Return the first valid IP, or default
    if ips:
        # Prefer LAN IPs over others
        for method, ip in ips:
            if ip.startswith(('192.168.', '10.', '172.')):
                return ip
        # Otherwise return the first one
        return ips[0][1]
    
    return "127.0.0.1"  # Last resort fallback

def check_internet():
    """Check if internet is available"""
    try:
        socket.gethostbyname("www.google.com")
        return True
    except:
        return False

def get_network_status():
    """Get comprehensive network status"""
    internet = check_internet()
    local_ip = get_local_ip()
    
    if internet:
        mode = "Internet + LAN"
        color = "green"
    else:
        mode = "LAN Only"
        color = "orange"
    
    return {
        "internet": internet,
        "local_ip": local_ip,
        "mode": mode,
        "color": color
    }

class MessageBroadcastWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.file_path = None
        self.file_data = None
        self.file_name = None
        
    def show(self):
        """Show the message broadcast window"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
            
        self.window = tk.Toplevel(self.parent)
        self.window.title("📤 Send Message to Students")
        self.window.geometry("700x600")
        self.window.resizable(False, False)
        
        # Center window
        self.center_window()
        
        # Make it modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="📤 Send Message to All Students",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Network status indicator
        status = get_network_status()
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(status_frame, text="Network Mode:", 
                 font=("Arial", 9)).pack(side="left")
        ttk.Label(status_frame, text=f" {status['mode']}", 
                 font=("Arial", 9, "bold"),
                 foreground=status['color']).pack(side="left")
        ttk.Label(status_frame, text=f" | IP: {status['local_ip']}", 
                 font=("Arial", 9)).pack(side="left", padx=(10, 0))
        
        # Message frame
        message_frame = ttk.LabelFrame(main_frame, text="Your Message", padding=15)
        message_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Message text with scrollbar
        text_container = ttk.Frame(message_frame)
        text_container.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(text_container)
        scrollbar.pack(side="right", fill="y")
        
        self.message_text = tk.Text(
            text_container,
            wrap="word",
            height=10,
            font=("Arial", 11),
            yscrollcommand=scrollbar.set,
            padx=10,
            pady=10
        )
        self.message_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.message_text.yview)
        
        # Add placeholder text
        self.message_text.insert("1.0", "Type your message here...")
        self.message_text.config(foreground="gray")
        
        def on_focus_in(event):
            if self.message_text.get("1.0", "end-1c") == "Type your message here...":
                self.message_text.delete("1.0", tk.END)
                self.message_text.config(foreground="black")
        
        def on_focus_out(event):
            if not self.message_text.get("1.0", "end-1c").strip():
                self.message_text.insert("1.0", "Type your message here...")
                self.message_text.config(foreground="gray")
        
        self.message_text.bind('<FocusIn>', on_focus_in)
        self.message_text.bind('<FocusOut>', on_focus_out)
        
        # Attachment frame
        attachment_frame = ttk.LabelFrame(main_frame, text="File Attachment (Optional)", padding=15)
        attachment_frame.pack(fill="x", pady=(0, 20))
        
        # Attachment info frame
        self.attach_info_frame = ttk.Frame(attachment_frame)
        self.attach_info_frame.pack(fill="x", pady=(0, 10))
        
        # Initially show "No file attached" message
        self.no_file_label = ttk.Label(
            self.attach_info_frame,
            text="No file attached",
            font=("Arial", 10, "italic"),
            foreground="gray"
        )
        self.no_file_label.pack()
        
        # File info frame (hidden initially)
        self.file_info_frame = ttk.Frame(self.attach_info_frame)
        
        self.file_name_label = ttk.Label(
            self.file_info_frame,
            text="",
            font=("Arial", 10, "bold")
        )
        self.file_name_label.pack(anchor="w")
        
        self.file_size_label = ttk.Label(
            self.file_info_frame,
            text="",
            font=("Arial", 9),
            foreground="gray"
        )
        self.file_size_label.pack(anchor="w")
        
        # Attachment buttons frame
        attach_btn_frame = ttk.Frame(attachment_frame)
        attach_btn_frame.pack(fill="x")
        
        # Attachment button
        attach_icon = "📎"
        self.attach_btn = ttk.Button(
            attach_btn_frame,
            text=f"{attach_icon} Attach File",
            command=self.attach_file,
            width=15
        )
        self.attach_btn.pack(side="left", padx=(0, 10))
        
        # Remove attachment button
        self.remove_btn = ttk.Button(
            attach_btn_frame,
            text="❌ Remove",
            command=self.remove_attachment,
            width=10,
            state="disabled"
        )
        self.remove_btn.pack(side="left")
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        # Send button
        send_btn = ttk.Button(
            button_frame,
            text="🚀 Send to All Students",
            command=self.send_message,
            width=20
        )
        send_btn.pack(side="right", padx=(10, 0))
        
        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.close_window,
            width=10
        )
        cancel_btn.pack(side="right")
        
        # Bind Enter key to send
        self.window.bind('<Return>', lambda e: self.send_message())
        
        # Bind Escape key to close
        self.window.bind('<Escape>', lambda e: self.close_window())
        
    def center_window(self):
        """Center the window"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def attach_file(self):
        """Attach a file to the message"""
        file_path = filedialog.askopenfilename(
            title="Select File to Attach",
            filetypes=[
                ("All Files", "*.*"),
                ("PDF Files", "*.pdf"),
                ("Word Documents", "*.doc *.docx"),
                ("Text Files", "*.txt"),
                ("Image Files", "*.jpg *.jpeg *.png *.gif"),
                ("Excel Files", "*.xls *.xlsx"),
                ("PowerPoint Files", "*.ppt *.pptx")
            ]
        )
        
        if file_path:
            try:
                # Read file
                with open(file_path, 'rb') as f:
                    self.file_data = f.read()
                
                self.file_path = file_path
                self.file_name = os.path.basename(file_path)
                file_size = len(self.file_data)
                
                # Hide "no file" label
                self.no_file_label.pack_forget()
                
                # Update file info
                self.file_name_label.config(text=f"📄 {self.file_name}")
                
                # Format file size
                if file_size < 1024:
                    size_str = f"{file_size} bytes"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                self.file_size_label.config(text=f"Size: {size_str}")
                
                # Show file info
                self.file_info_frame.pack(fill="x")
                
                # Enable remove button
                self.remove_btn.config(state="normal")
                
                # Update log
                state.add_log(f"Attached file: {self.file_name} ({size_str})")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read file: {e}")
    
    def remove_attachment(self):
        """Remove the attached file"""
        self.file_path = None
        self.file_data = None
        self.file_name = None
        
        # Hide file info
        self.file_info_frame.pack_forget()
        
        # Show "no file" label
        self.no_file_label.pack()
        
        # Disable remove button
        self.remove_btn.config(state="disabled")
    
    def send_message(self):
        """Send the message to all students"""
        # Get message text
        message = self.message_text.get("1.0", "end-1c").strip()
        if message == "Type your message here...":
            message = ""
        
        if not message and not self.file_data:
            messagebox.showwarning(
                "Warning",
                "Please enter a message or attach a file to send."
            )
            return
        
        # Check file size if attached
        if self.file_data and len(self.file_data) > 50 * 1024 * 1024:  # 50MB limit
            messagebox.showerror(
                "Error",
                "File size too large! Maximum 50MB allowed."
            )
            return
        
        # Check if any students are connected
        if not state.students:
            result = messagebox.askyesno(
                "No Students Connected",
                "No students are currently connected.\n\nMessages will be sent when they connect.\n\nContinue anyway?"
            )
            if not result:
                return
        
        # Send to all students
        self.send_to_students(message, self.file_data, self.file_name)
        
        # Close window
        self.close_window()
    
    def send_to_students(self, message, file_data, file_name):
        """Send message with optional file to all students"""
        # Create the command
        if file_data and file_name:
            # Encode file in base64
            encoded_data = base64.b64encode(file_data).decode('utf-8')
            command = f"FILE_MESSAGE:{message}|||{file_name}|||{encoded_data}"
            log_msg = f"Teacher | Sent message with file: {file_name}"
        else:
            command = f"BROADCAST:{message}"
            log_msg = f"Teacher | Broadcast message: {message}"
        
        # Send command
        state.send_command(command)
        state.add_log(log_msg)
        
        # Show confirmation
        connected_count = len(state.students)
        if connected_count > 0:
            messagebox.showinfo(
                "Success",
                f"Message sent to {connected_count} connected student(s)!\n\nOthers will receive it when they connect."
            )
        else:
            messagebox.showinfo(
                "Queued",
                "Message saved. It will be sent when students connect."
            )
    
    def close_window(self):
        """Close the window"""
        if self.window:
            self.window.destroy()
            self.window = None


class MainApplication:
    def __init__(self, root):
        self.root = root
        self.teacher_ip = get_local_ip()
        self.current_page = "main"
        
        # Store frames
        self.main_frame = None
        self.quiz_frame = None
        self.content_frame = None
        
        # Initialize quiz panel reference
        self.quiz_panel = None
        
        # Network monitoring
        self.network_status = get_network_status()
        
        # Flag to track if GUI is alive
        self.gui_alive = True
        
        # Setup main container
        self.setup_container()
        
        # Show main page
        self.show_main_page()
        
        # Setup callbacks
        self.setup_callbacks()
        
        # Start network monitor
        self.start_network_monitor()
        
        # Center window
        self.center_window()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def on_closing(self):
        """Handle window closing"""
        self.gui_alive = False
        self.root.destroy()
        
    def start_network_monitor(self):
        """Start monitoring network status"""
        def monitor():
            while self.gui_alive:
                try:
                    new_status = get_network_status()
                    
                    # Check if status changed
                    if (new_status['internet'] != self.network_status['internet'] or
                        new_status['local_ip'] != self.network_status['local_ip']):
                        
                        self.network_status = new_status
                        
                        # Update UI in main thread only if GUI still exists
                        if self.gui_alive:
                            self.root.after(0, self.update_network_display)
                            
                            # Log the change
                            state.add_log(f"Network changed to: {new_status['mode']} | IP: {new_status['local_ip']}")
                    
                    time.sleep(5)  # Check every 5 seconds
                    
                except:
                    time.sleep(10)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def update_network_display(self):
        """Update network status in UI"""
        if not self.gui_alive:
            return
            
        try:
            if hasattr(self, 'network_label') and self.network_label.winfo_exists():
                self.network_label.config(
                    text=f"🌐 {self.network_status['mode']} | IP: {self.network_status['local_ip']}",
                    foreground=self.network_status['color']
                )
        except:
            pass
            
        try:
            if hasattr(self, 'status_var'):
                self.status_var.set(f"Server running on {self.teacher_ip}:5000 ({self.network_status['mode']})")
        except:
            pass
        
    def setup_container(self):
        """Setup the main container that will hold all pages"""
        # Configure root grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Create a container frame that fills the entire window
        self.container = ttk.Frame(self.root)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        # Create a content frame that will be swapped
        self.content_frame = ttk.Frame(self.container)
        self.content_frame.grid(row=0, column=0, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
    def clear_content(self):
        """Clear all widgets from content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
    def show_main_page(self):
        """Show the main control page with 4 columns"""
        self.clear_content()
        self.current_page = "main"
        
        # Create main page frame
        main_frame = ttk.Frame(self.content_frame)
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid for main_frame - 4 columns now!
        main_frame.columnconfigure(0, weight=1)  # Basic Controls
        main_frame.columnconfigure(1, weight=1)  # IDE Control (NEW)
        main_frame.columnconfigure(2, weight=1)  # Connected Students
        main_frame.columnconfigure(3, weight=1)  # Event Log
        main_frame.rowconfigure(0, weight=1)
        
        # ================= COLUMN 1: BASIC CONTROLS =================
        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create scrollable frame for left panel
        left_canvas = tk.Canvas(left_panel, highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=left_canvas.yview)
        left_scrollable = ttk.Frame(left_canvas)
        
        left_scrollable.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        
        left_canvas.create_window((0, 0), window=left_scrollable, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        left_canvas.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")
        
        # Teacher IP and Network Status at top
        info_frame = ttk.Frame(left_scrollable)
        info_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(info_frame, text=f"Teacher IP:", 
                  font=("Arial", 9)).pack(anchor="w")
        ttk.Label(info_frame, text=f"{self.teacher_ip}", 
                  font=("Arial", 12, "bold"), foreground="blue").pack(anchor="w")
        
        # Network status
        self.network_label = ttk.Label(
            info_frame,
            text=f"🌐 {self.network_status['mode']} | IP: {self.network_status['local_ip']}",
            font=("Arial", 9),
            foreground=self.network_status['color']
        )
        self.network_label.pack(anchor="w", pady=(5, 0))
        
        # ===== 1. COPY-PASTE CONTROL =====
        copy_frame = ttk.LabelFrame(left_scrollable, text="📋 Copy-Paste Control", padding=20)
        copy_frame.pack(fill="x", pady=(0, 20))
        
        self.copy_var = tk.StringVar(value="UNBLOCKED")
        
        def copy_changed():
            if self.copy_var.get() == "BLOCKED":
                block_copy.enable()
            else:
                block_copy.disable()
        
        ttk.Radiobutton(copy_frame, text="🔴 Block Copy-Paste", 
                        variable=self.copy_var, value="BLOCKED",
                        command=copy_changed).pack(anchor="w", pady=2)
        ttk.Radiobutton(copy_frame, text="🟢 Allow Copy-Paste", 
                        variable=self.copy_var, value="UNBLOCKED",
                        command=copy_changed).pack(anchor="w", pady=2)
        
        # ===== 2. INTERNET CONTROL =====
        internet_frame = ttk.LabelFrame(left_scrollable, text="🌐 Internet Control", padding=10)
        internet_frame.pack(fill="x", pady=(0, 10))
        
        self.internet_var = tk.StringVar(value="UNBLOCKED")
        
        def internet_changed():
            if self.internet_var.get() == "BLOCKED":
                block_internet.enable()
            else:
                block_internet.disable()
        
        ttk.Radiobutton(internet_frame, text="🔴 Block Internet", 
                        variable=self.internet_var, value="BLOCKED",
                        command=internet_changed).pack(anchor="w", pady=2)
        ttk.Radiobutton(internet_frame, text="🟢 Allow Internet", 
                        variable=self.internet_var, value="UNBLOCKED",
                        command=internet_changed).pack(anchor="w", pady=2)
        
        # Add note about internet blocking
        ttk.Label(internet_frame, text="Note: Blocks ALL internet access",
                  font=("Arial", 8), foreground="gray").pack(anchor="w")
        
        # ===== 3. SCREEN LOCK CONTROL =====
        lock_frame = ttk.LabelFrame(left_scrollable, text="🔒 Screen Lock Control", padding=10)
        lock_frame.pack(fill="x", pady=(0, 10))
        
        # PIN Entry
        pin_row = ttk.Frame(lock_frame)
        pin_row.pack(fill="x", pady=(0, 10))
        
        ttk.Label(pin_row, text="4-Digit PIN:", 
                  font=("Arial", 9)).pack(side="left", padx=(0, 5))
        
        self.pin_var = tk.StringVar()
        self.pin_entry = ttk.Entry(pin_row, textvariable=self.pin_var,
                                   width=6, font=("Arial", 12), show="●")
        self.pin_entry.pack(side="left")
        
        # Lock/Unlock buttons
        lock_btn_frame = ttk.Frame(lock_frame)
        lock_btn_frame.pack(fill="x", pady=(0, 10))
        
        self.lock_all_btn = ttk.Button(
            lock_btn_frame,
            text="🔒 Lock All",
            command=self.lock_all_screens,
            width=12
        )
        self.lock_all_btn.pack(side="left", padx=(0, 5))
        
        self.unlock_all_btn = ttk.Button(
            lock_btn_frame,
            text="🔓 Unlock All",
            command=self.unlock_all_screens,
            width=12
        )
        self.unlock_all_btn.pack(side="left")
        
        # Status indicator
        self.screen_lock_status = ttk.Label(
            lock_frame,
            text="● Screens Unlocked",
            foreground="green",
            font=("Arial", 9, "bold")
        )
        self.screen_lock_status.pack(anchor="w")
        
        # ===== 4. MESSAGE BROADCAST =====
        msg_frame = ttk.LabelFrame(left_scrollable, text="📢 Message Broadcast", padding=10)
        msg_frame.pack(fill="x", pady=(0, 10))
        
        # Create message broadcast window instance
        self.message_window = MessageBroadcastWindow(self.root)
        
        broadcast_btn = ttk.Button(
            msg_frame,
            text="📤 Open Message Window",
            command=self.message_window.show,
            width=25
        )
        broadcast_btn.pack(pady=5)
        
        ttk.Label(msg_frame, text="Send messages & files to all students",
                  font=("Arial", 8), foreground="gray").pack()
        
        # Student count indicator
        self.student_count_indicator = ttk.Label(
            msg_frame,
            text="Students connected: 0",
            font=("Arial", 8, "bold"),
            foreground="blue"
        )
        self.student_count_indicator.pack()
        
        # ===== 5. SCREEN MONITORING =====
        monitor_frame = ttk.LabelFrame(left_scrollable, text="📺 Screen Monitoring", padding=10)
        monitor_frame.pack(fill="x", pady=(0, 10))
        
        def show_screens_dashboard():
            """Show the screens dashboard"""
            try:
                import screen_dashboard
                screen_dashboard.screen_dashboard.show_dashboard()
                state.add_log("Teacher | Opened screens dashboard")
            except ImportError:
                state.add_log("ERROR: Screen dashboard module not found")
                messagebox.showerror("Error", "Screen dashboard module not found!")
            except Exception as e:
                state.add_log(f"ERROR: Could not open dashboard: {e}")
                messagebox.showerror("Error", f"Could not open dashboard: {e}")
        
        monitor_btn = ttk.Button(
            monitor_frame,
            text="📺 View All Student Screens",
            command=show_screens_dashboard,
            width=25
        )
        monitor_btn.pack(pady=5)
        
        ttk.Label(monitor_frame, text="Monitor all connected students",
                  font=("Arial", 8), foreground="gray").pack()
        
        # ===== 6. QUIZ MODE =====
        quiz_frame = ttk.LabelFrame(left_scrollable, text="📝 Quiz Mode", padding=10)
        quiz_frame.pack(fill="x", pady=(0, 10))
        
        quiz_btn = ttk.Button(
            quiz_frame,
            text="📝 Open Quiz Master",
            command=self.show_quiz_page,
            width=25
        )
        quiz_btn.pack(pady=5)
        
        ttk.Label(quiz_frame, text="Create and manage quizzes",
                  font=("Arial", 8), foreground="gray").pack()
        
        # ===== 7. NETWORK INFO =====
        network_frame = ttk.LabelFrame(left_scrollable, text="📡 Network Information", padding=10)
        network_frame.pack(fill="x", pady=(0, 10))
        
        # Live network stats
        self.network_stats = ttk.Label(
            network_frame,
            text="Monitoring network...",
            font=("Arial", 9)
        )
        self.network_stats.pack(anchor="w")
        
        # Start network stats update
        self.update_network_stats()
        
        # ================= COLUMN 2: IDE CONTROL =================
        ide_panel = ttk.Frame(main_frame)
        ide_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Create scrollable frame for IDE panel
        ide_canvas = tk.Canvas(ide_panel, highlightthickness=0)
        ide_scrollbar = ttk.Scrollbar(ide_panel, orient="vertical", command=ide_canvas.yview)
        ide_scrollable = ttk.Frame(ide_canvas)
        
        ide_scrollable.bind(
            "<Configure>",
            lambda e: ide_canvas.configure(scrollregion=ide_canvas.bbox("all"))
        )
        
        ide_canvas.create_window((0, 0), window=ide_scrollable, anchor="nw")
        ide_canvas.configure(yscrollcommand=ide_scrollbar.set)
        
        ide_canvas.pack(side="left", fill="both", expand=True)
        ide_scrollbar.pack(side="right", fill="y")
        
        # IDE Control Main Frame
        ide_control_frame = ttk.LabelFrame(ide_scrollable, text="💻 IDE CONTROL CENTER", padding=15)
        ide_control_frame.pack(fill="x", pady=(0, 15))
        
        # Title
        title_frame = ttk.Frame(ide_control_frame)
        title_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(title_frame, text="🚀 Launch IDE (Fullscreen Lock)", 
                  font=("Arial", 12, "bold"), foreground="purple").pack()
        
        # ===== IDE SELECTION =====
        select_frame = ttk.LabelFrame(ide_control_frame, text="1. Select Editor", padding=10)
        select_frame.pack(fill="x", pady=(0, 10))
        
        editor_row = ttk.Frame(select_frame)
        editor_row.pack(fill="x", pady=5)
        
        ttk.Label(editor_row, text="Editor:", font=("Arial", 9)).pack(side="left", padx=(0, 10))
        
        self.ide_var = tk.StringVar(value="VS Code")
        ide_combo = ttk.Combobox(editor_row, textvariable=self.ide_var,
                                 values=["VS Code", "Code::Blocks", "Spyder", 
                                        "PyCharm", "IDLE", "Sublime Text"],
                                 state="readonly", width=15)
        ide_combo.pack(side="left")
        
        # Common paths info
        paths_frame = ttk.Frame(select_frame)
        paths_frame.pack(fill="x", pady=(5, 0))
        
        self.path_info_label = ttk.Label(
            paths_frame,
            text="VS Code: C:\\Program Files\\Microsoft VS Code\\Code.exe",
            font=("Arial", 7),
            foreground="gray",
            wraplength=200
        )
        self.path_info_label.pack(anchor="w")
        
        def update_path_info(*args):
            ide = self.ide_var.get()
            paths = {
                "VS Code": "VS Code: C:\\Program Files\\Microsoft VS Code\\Code.exe",
                "Code::Blocks": "Code::Blocks: C:\\Program Files\\CodeBlocks\\codeblocks.exe",
                "Spyder": "Spyder: C:\\ProgramData\\Anaconda3\\Scripts\\spyder.exe",
                "PyCharm": "PyCharm: C:\\Program Files\\JetBrains\\PyCharm\\bin\\pycharm64.exe",
                "IDLE": "IDLE: C:\\Python39\\pythonw.exe -m idlelib",
                "Sublime Text": "Sublime: C:\\Program Files\\Sublime Text 3\\sublime_text.exe"
            }
            self.path_info_label.config(text=paths.get(ide, "Common install path"))
        
        self.ide_var.trace('w', update_path_info)
        update_path_info()
        
        # ===== DURATION SETTING =====
        duration_frame = ttk.LabelFrame(ide_control_frame, text="2. Set Duration", padding=10)
        duration_frame.pack(fill="x", pady=(0, 10))
        
        time_row = ttk.Frame(duration_frame)
        time_row.pack(fill="x", pady=5)
        
        ttk.Label(time_row, text="Time:", font=("Arial", 9)).pack(side="left", padx=(0, 10))
        
        self.ide_duration_var = tk.StringVar(value="30")
        duration_spin = ttk.Spinbox(time_row, from_=5, to=120,
                                   textvariable=self.ide_duration_var, width=5)
        duration_spin.pack(side="left")
        ttk.Label(time_row, text="minutes").pack(side="left", padx=5)
        
        # Preset buttons
        preset_frame = ttk.Frame(duration_frame)
        preset_frame.pack(fill="x", pady=(5, 0))
        
        def set_duration(mins):
            self.ide_duration_var.set(str(mins))
        
        # ===== INFO TEXT =====
        info_frame = ttk.Frame(ide_control_frame)
        info_frame.pack(fill="x", pady=(5, 10))
        
        # ===== ACTION BUTTONS =====
        action_frame = ttk.Frame(ide_control_frame)
        action_frame.pack(fill="x", pady=(5, 5))
        
        def launch_ide():
            """Launch IDE on all students - SIMPLIFIED"""
            ide = self.ide_var.get()
            
            # Get duration safely
            duration_str = self.ide_duration_var.get().strip()
            
            # Validate duration
            if not duration_str or not duration_str.isdigit():
                duration = 30
                self.ide_duration_var.set("30")
                messagebox.showwarning("Warning", "Invalid duration! Using default 30 minutes.")
            else:
                duration = int(duration_str)
                if duration < 5 or duration > 120:
                    duration = 30
                    self.ide_duration_var.set("30")
                    messagebox.showwarning("Warning", "Duration must be 5-120 minutes. Using default 30.")
            
            # Simple command - just IDE and duration (no options)
            cmd = f"LAUNCH_IDE|{ide}|{duration}"
            
            # Send to all students
            state.send_command(cmd)
            state.add_log(f"Teacher | Launched {ide} ({duration} min) - FULLSCREEN MODE")
            
            # Update status
            self.ide_status_label.config(
                text=f"● Active: {ide} ({duration} min)",
                foreground="green"
            )
            
            messagebox.showinfo("IDE Launched", 
                               f"{ide} launched on all students\nDuration: {duration} minutes\n\nFULLSCREEN MODE - Students cannot exit")
        
        def end_ide():
            """End IDE session"""
            state.send_command("END_IDE_SESSION")
            state.add_log("Teacher | Ended IDE session")
            
            self.ide_status_label.config(
                text="● No active session",
                foreground="gray"
            )
            
            messagebox.showinfo("Session Ended", "IDE session ended for all students")
        
        # Create buttons with styling
        launch_btn = tk.Button(
            action_frame,
            text="🚀 LAUNCH IDE (FULLSCREEN)",
            font=("Arial", 10, "bold"),
            bg="#4CAF50",
            fg="white",
            command=launch_ide,
            padx=10,
            pady=8,
            relief="raised",
            cursor="hand2"
        )
        launch_btn.pack(fill="x", pady=3)
        
        end_btn = tk.Button(
            action_frame,
            text="🔚 END SESSION",
            font=("Arial", 10, "bold"),
            bg="#f44336",
            fg="white",
            command=end_ide,
            padx=10,
            pady=8,
            relief="raised",
            cursor="hand2"
        )
        end_btn.pack(fill="x", pady=3)
        
        # Status indicator
        self.ide_status_label = ttk.Label(
            ide_control_frame,
            text="● No active session",
            foreground="gray",
            font=("Arial", 9)
        )
        self.ide_status_label.pack(anchor="w", pady=(10, 0))
        
        # ===== FUTURE CONTROLS =====
        future_frame = ttk.LabelFrame(ide_scrollable, text="🚫 Other Controls", padding=15)
        future_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(future_frame, text="More features coming soon...",
                  font=("Arial", 9, "italic"), foreground="gray").pack(pady=10)
        
        # ===== QUICK STATS =====
        stats_frame = ttk.LabelFrame(ide_scrollable, text="📊 Quick Stats", padding=15)
        stats_frame.pack(fill="x", pady=(0, 10))
        
        self.ide_student_count = ttk.Label(
            stats_frame,
            text="Connected Students: 0",
            font=("Arial", 9)
        )
        self.ide_student_count.pack(anchor="w", pady=2)
        
        # ================= COLUMN 3: CONNECTED STUDENTS =================
        students_frame = ttk.LabelFrame(main_frame, text="👥 Connected Students", padding=10)
        students_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        # Header with count
        header_frame = ttk.Frame(students_frame)
        header_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(header_frame, text="Student List", font=("Arial", 9, "bold")).pack(side="left")
        
        self.student_count_var = tk.StringVar(value="Count: 0")
        ttk.Label(header_frame, textvariable=self.student_count_var, 
                  font=("Arial", 9), foreground="blue").pack(side="right")
        
        # Student list with scrollbar
        list_container = ttk.Frame(students_frame)
        list_container.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")
        
        self.student_list = tk.Listbox(list_container, yscrollcommand=scrollbar.set,
                                 font=("Consolas", 9), height=25)
        self.student_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.student_list.yview)
        
        # Individual student control buttons
        student_control_frame = ttk.Frame(students_frame)
        student_control_frame.pack(fill="x", pady=(10, 0))
        
        def lock_selected_student():
            selected = self.student_list.curselection()
            if selected:
                display_text = self.student_list.get(selected[0])
                student_ip = display_text.replace("🔒 ", "").replace("  ", "").strip()
                pin = self.pin_var.get().strip()
                if not pin.isdigit() or len(pin) != 4:
                    messagebox.showerror("Error", "PIN must be exactly 4 digits!")
                    return
                state.send_command_to_student(student_ip, f"LOCK_ALL_SCREENS:{pin}")
                state.add_log(f"Teacher | Locked {student_ip} with PIN: {pin}")
        
        def unlock_selected_student():
            selected = self.student_list.curselection()
            if selected:
                display_text = self.student_list.get(selected[0])
                student_ip = display_text.replace("🔒 ", "").replace("  ", "").strip()
                state.send_command_to_student(student_ip, "UNLOCK_ALL_SCREENS")
                state.add_log(f"Teacher | Unlocked {student_ip}")
        
        ttk.Button(student_control_frame, text="🔒 Lock Selected", 
                  command=lock_selected_student, width=14).pack(side="left", padx=2)
        ttk.Button(student_control_frame, text="🔓 Unlock Selected", 
                  command=unlock_selected_student, width=14).pack(side="left", padx=2)
        
        # Refresh button
        def refresh_students():
            self.update_student_list()
            state.add_log("Teacher | Refreshed student list")
        
        ttk.Button(students_frame, text="🔄 Refresh List", 
                   command=refresh_students).pack(pady=(10, 0))
        
        # ================= COLUMN 4: EVENT LOG =================
        log_frame = ttk.LabelFrame(main_frame, text="📋 Event Log", padding=10)
        log_frame.grid(row=0, column=3, sticky="nsew", padx=5, pady=5)
        
        # Log controls
        log_controls = ttk.Frame(log_frame)
        log_controls.pack(fill="x", pady=(0, 5))
        ttk.Label(log_controls, text="System Events", 
                  font=("Arial", 9, "bold")).pack(side="left")
        
        def clear_log():
            self.log_box.delete(1.0, tk.END)
            state.add_log("Log cleared")
        
        ttk.Button(log_controls, text="Clear", 
                   command=clear_log, width=8).pack(side="right")
        
        # Log text area
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill="both", expand=True)
        
        log_scrollbar = ttk.Scrollbar(log_container)
        log_scrollbar.pack(side="right", fill="y")
        
        self.log_box = tk.Text(log_container, wrap="word", 
                         font=("Consolas", 9), height=25,
                         yscrollcommand=log_scrollbar.set)
        self.log_box.pack(side="left", fill="both", expand=True)
        log_scrollbar.config(command=self.log_box.yview)
        
        # ================= STATUS BAR =================
        status_bar = ttk.Frame(main_frame, relief="sunken")
        status_bar.grid(row=1, column=0, columnspan=4, sticky="ew", padx=5, pady=(0, 5))
        
        self.status_var = tk.StringVar(value=f"Server running on {self.teacher_ip}:5000 ({self.network_status['mode']})")
        ttk.Label(status_bar, textvariable=self.status_var, 
                  font=("Arial", 9)).pack(side="left", padx=10, pady=2)
        
        # Server status indicator
        server_status = ttk.Label(status_bar, text="● Online", 
                                 foreground="green", font=("Arial", 9, "bold"))
        server_status.pack(side="right", padx=(0, 10))
        
        # Network indicator in status bar
        self.network_indicator = ttk.Label(
            status_bar,
            text=f"● {self.network_status['mode']}",
            foreground=self.network_status['color'],
            font=("Arial", 9, "bold")
        )
        self.network_indicator.pack(side="right", padx=(0, 10))
        
        # Initial logs
        state.add_log("✅ Teacher application started")
        state.add_log(f"📡 Server IP: {self.teacher_ip}")
        state.add_log(f"🌐 Network mode: {self.network_status['mode']}")
        state.add_log("👥 Waiting for student connections...")
        state.add_log("📢 Use Message Broadcast to send messages")
        state.add_log("🔒 Screen Lock: Enter PIN and click Lock All")
        state.add_log("💻 IDE Control: Launch editors from column 2")
    
    def update_network_stats(self):
        """Update network statistics display"""
        if not self.gui_alive:
            return
            
        try:
            if hasattr(self, 'network_stats') and self.network_stats.winfo_exists():
                connected = len(state.students)
                status = get_network_status()
                
                stats = f"Mode: {status['mode']}\n"
                stats += f"Students: {connected}\n"
                stats += f"IP: {status['local_ip']}"
                
                self.network_stats.config(text=stats)
        except:
            pass
            
        try:
            # Update IDE student count
            if hasattr(self, 'ide_student_count') and self.ide_student_count.winfo_exists():
                connected = len(state.students)
                self.ide_student_count.config(text=f"Connected Students: {connected}")
        except:
            pass
        
        # Schedule next update only if GUI is still alive
        if self.gui_alive:
            self.root.after(5000, self.update_network_stats)
    
    def lock_all_screens(self):
        """Lock all student screens with the entered PIN"""
        pin = self.pin_var.get().strip()
        
        # Validate PIN
        if not pin:
            messagebox.showerror("Error", "Please enter a 4-digit PIN!")
            return
            
        if not pin.isdigit() or len(pin) != 4:
            messagebox.showerror("Error", "PIN must be exactly 4 digits!")
            return
            
        if not state.students:
            messagebox.showwarning("Warning", "No students connected!")
            return
            
        # Lock all screens
        state.lock_all_students(pin)
        
        # Update UI
        self.screen_lock_status.config(text="● Screens Locked 🔒", foreground="red")
        self.pin_entry.config(state="disabled")
        self.lock_all_btn.config(state="disabled")
        self.unlock_all_btn.config(state="normal")
        
        # Add to log
        state.add_log(f"🔒 ALL SCREENS LOCKED with PIN: {pin}")
        
    def unlock_all_screens(self):
        """Unlock all student screens"""
        if not state.students:
            messagebox.showwarning("Warning", "No students connected!")
            return
            
        # Unlock all screens
        state.unlock_all_students()
        
        # Update UI
        self.screen_lock_status.config(text="● Screens Unlocked 🔓", foreground="green")
        self.pin_entry.config(state="normal")
        self.lock_all_btn.config(state="normal")
        
        # Add to log
        state.add_log("🔓 ALL SCREENS UNLOCKED")
        
    def show_quiz_page(self):
        """Show the quiz page (replaces main page)"""
        try:
            import quiz_teacher
            
            self.clear_content()
            self.current_page = "quiz"
            
            # Create quiz page frame
            quiz_page = ttk.Frame(self.content_frame)
            quiz_page.grid(row=0, column=0, sticky="nsew")
            quiz_page.columnconfigure(0, weight=1)
            quiz_page.rowconfigure(1, weight=1)
            
            # Header with back button
            header_frame = ttk.Frame(quiz_page, style='Header.TFrame')
            header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
            header_frame.columnconfigure(1, weight=1)
            
            # Style for header
            style = ttk.Style()
            style.configure('Header.TFrame', relief='raised', borderwidth=1)
            
            # Back button (left)
            back_btn = ttk.Button(
                header_frame,
                text="← Back to Main",
                command=self.show_main_page,
                width=15
            )
            back_btn.grid(row=0, column=0, padx=10, pady=10)
            
            # Title (center)
            title_label = ttk.Label(
                header_frame,
                text="📝 Quiz Master",
                font=("Arial", 16, "bold")
            )
            title_label.grid(row=0, column=1, padx=10, pady=10)
            
            # Network status in header
            status = get_network_status()
            network_label = ttk.Label(
                header_frame,
                text=f"🌐 {status['mode']}",
                font=("Arial", 9),
                foreground=status['color']
            )
            network_label.grid(row=0, column=2, padx=10, pady=10)
            
            # Content frame for quiz panel
            quiz_content = ttk.Frame(quiz_page)
            quiz_content.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
            quiz_content.columnconfigure(0, weight=1)
            quiz_content.rowconfigure(0, weight=1)
            
            # Create and embed quiz panel
            self.quiz_panel = quiz_teacher.QuizTeacherPanel(self.root)
            self.quiz_panel.embed_in_frame(quiz_content)
            
            state.add_log("Teacher | Opened quiz page")
            
        except ImportError as e:
            messagebox.showerror("Error", f"Quiz module not found: {e}")
            state.add_log("ERROR: Quiz module not found")
            self.show_main_page()
        except Exception as e:
            messagebox.showerror("Error", f"Could not open quiz page: {e}")
            state.add_log(f"ERROR: Could not open quiz page: {e}")
            self.show_main_page()
            
    def update_student_list(self):
        """Update the student list display"""
        if not self.gui_alive:
            return
            
        try:
            if hasattr(self, 'student_list') and self.student_list.winfo_exists():
                self.student_list.delete(0, tk.END)
                for ip in state.students:
                    # Add lock indicator if student is locked
                    if state.is_student_locked(ip):
                        self.student_list.insert(tk.END, f"🔒 {ip}")
                    else:
                        self.student_list.insert(tk.END, f"   {ip}")
                
                count = len(state.students)
                self.student_count_var.set(f"Count: {count}")
                
                # Update student count indicator
                if hasattr(self, 'student_count_indicator') and self.student_count_indicator.winfo_exists():
                    if count > 0:
                        self.student_count_indicator.config(
                            text=f"Students connected: {count}",
                            foreground="green"
                        )
                    else:
                        self.student_count_indicator.config(
                            text="Students connected: 0",
                            foreground="blue"
                        )
        except:
            pass
    
    def add_log(self, text):
        """Add log message to log box"""
        if not self.gui_alive:
            return
            
        try:
            if hasattr(self, 'log_box') and self.log_box.winfo_exists():
                self.log_box.insert(tk.END, text + "\n")
                self.log_box.see(tk.END)
        except:
            pass
    
    def update_status(self, message):
        """Update status message"""
        if not self.gui_alive:
            return
            
        try:
            if hasattr(self, 'status_var'):
                self.status_var.set(message)
        except:
            pass
    
    def setup_callbacks(self):
        """Setup the callback functions"""
        # Clear existing callbacks
        state.log_callbacks.clear()
        state.status_callbacks.clear()
        state.update_callbacks.clear()
        
        # Add new callbacks
        state.add_log_callback(self.add_log)
        state.add_status_callback(self.update_status)
        state.add_update_callback(self.update_student_list)
    
    def center_window(self):
        """Center the window"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')


def start_gui():
    root = tk.Tk()
    
    local_ip = get_local_ip()
    status = get_network_status()
    
    root.title(f"Classroom Control - Teacher ({local_ip}) [{status['mode']}]")
    
    # Open like real software, full screen size with title bar
    root.state("zoomed")
    
    root.resizable(True, True)
    
    app = MainApplication(root)
    
    root.mainloop()

if __name__ == "__main__":
    start_gui()