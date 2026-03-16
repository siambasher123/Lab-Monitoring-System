# message_popup.py - Student side message popup with file download support
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import base64
import config

class MessagePopup:
    def __init__(self, message, file_data=None, file_name=None):
        self.message = message
        self.file_data = file_data
        self.file_name = file_name
        self.window = None
        self.timer = None
        self.countdown_var = None
        self.countdown_label = None
        self.remaining_time = 30  # 30 seconds countdown
        self.has_file = file_data is not None
        
    def show(self):
        """Show the popup window"""
        # Create window in main thread
        def create_window():
            self.window = tk.Toplevel()
            self.window.title("📢 Message from Teacher")
            
            # Adjust window size based on content
            if self.has_file:
                self.window.geometry("500x350")  # Larger for file attachment
            else:
                self.window.geometry("450x300")
                
            self.window.resizable(False, False)
            self.window.configure(bg='white')
            
            # Make it always on top
            self.window.attributes('-topmost', True)
            
            # Center window
            self.center_window()
            
            # Title
            title_text = "📢 Message from Teacher"
            if self.has_file:
                title_text += " (with Attachment)"
                
            title_label = tk.Label(
                self.window,
                text=title_text,
                font=("Arial", 14, "bold"),
                bg='white',
                fg='#2c3e50'
            )
            title_label.pack(pady=(15, 10))
            
            # Main content frame
            main_content = tk.Frame(self.window, bg='white')
            main_content.pack(fill="both", expand=True, padx=20, pady=(0, 10))
            
            # Message text frame
            text_frame = tk.LabelFrame(main_content, text="Message", 
                                      bg='white', font=("Arial", 10, "bold"),
                                      padx=10, pady=10)
            text_frame.pack(fill="both", expand=True, pady=(0, 10))
            
            # Message text with scrollbar
            text_container = tk.Frame(text_frame, bg='white')
            text_container.pack(fill="both", expand=True)
            
            scrollbar = ttk.Scrollbar(text_container)
            scrollbar.pack(side="right", fill="y")
            
            message_text = tk.Text(
                text_container,
                wrap="word",
                height=5,
                font=("Arial", 11),
                bg='#f8f9fa',
                relief="flat",
                yscrollcommand=scrollbar.set,
                padx=10,
                pady=10
            )
            message_text.pack(side="left", fill="both", expand=True)
            message_text.insert("1.0", self.message)
            message_text.config(state="disabled")  # Make read-only
            scrollbar.config(command=message_text.yview)
            
            # File attachment section (if has file)
            if self.has_file:
                file_frame = tk.LabelFrame(main_content, text="Attachment", 
                                         bg='white', font=("Arial", 10, "bold"),
                                         padx=10, pady=10)
                file_frame.pack(fill="x", pady=(0, 10))
                
                # File info
                file_info_frame = tk.Frame(file_frame, bg='white')
                file_info_frame.pack(fill="x", pady=(0, 10))
                
                # File icon and name
                file_icon_label = tk.Label(
                    file_info_frame,
                    text="📎",
                    font=("Arial", 14),
                    bg='white'
                )
                file_icon_label.pack(side="left", padx=(0, 10))
                
                file_name_label = tk.Label(
                    file_info_frame,
                    text=self.file_name,
                    font=("Arial", 11, "bold"),
                    bg='white',
                    anchor="w"
                )
                file_name_label.pack(side="left", fill="x", expand=True)
                
                # File size
                file_size = len(self.file_data)
                if file_size < 1024:
                    size_str = f"{file_size} bytes"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                file_size_label = tk.Label(
                    file_info_frame,
                    text=f"Size: {size_str}",
                    font=("Arial", 9),
                    bg='white',
                    fg='gray'
                )
                file_size_label.pack(side="right")
                
                # Download button
                download_btn = ttk.Button(
                    file_frame,
                    text="⬇️ Download File",
                    command=self.download_file,
                    width=20
                )
                download_btn.pack()
            
            # Timer and button frame
            bottom_frame = tk.Frame(self.window, bg='white')
            bottom_frame.pack(fill="x", padx=20, pady=(0, 10))
            
            # Countdown timer
            self.countdown_var = tk.StringVar(value=f"Closing in: {self.remaining_time}s")
            self.countdown_label = tk.Label(
                bottom_frame,
                textvariable=self.countdown_var,
                font=("Arial", 10),
                bg='white',
                fg='#e74c3c'
            )
            self.countdown_label.pack(side="left")
            
            # Close button
            close_btn = ttk.Button(
                bottom_frame,
                text="OK (Close Now)",
                command=self.close_window,
                width=15
            )
            close_btn.pack(side="right")
            
            # Start countdown timer
            self.start_countdown()
            
            # Start auto-close timer (30 seconds)
            self.timer = threading.Timer(30.0, self.close_window)
            self.timer.start()
            
            # Bind escape key to close
            self.window.bind('<Escape>', lambda e: self.close_window())
            
            # Log the message
            import gui
            if self.has_file:
                gui.add_log(f"Received message with file: {self.file_name}")
            else:
                gui.add_log(f"Received message: {self.message[:50]}...")
        
        # Run in main thread
        if tk._default_root:
            tk._default_root.after(0, create_window)
    
    def center_window(self):
        """Center the window on screen"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def start_countdown(self):
        """Start the countdown timer"""
        def update_countdown():
            if self.remaining_time > 0 and self.window and self.window.winfo_exists():
                self.countdown_var.set(f"Closing in: {self.remaining_time}s")
                self.remaining_time -= 1
                # Schedule next update in 1 second
                if tk._default_root:
                    tk._default_root.after(1000, update_countdown)
            else:
                # Time's up, close window
                self.close_window()
        
        # Start the countdown
        if tk._default_root:
            tk._default_root.after(1000, update_countdown)
    
    def download_file(self):
        """Download the attached file"""
        if not self.file_data or not self.file_name:
            return
            
        # Ask user where to save the file
        file_path = filedialog.asksaveasfilename(
            title="Save File",
            initialfile=self.file_name,
            defaultextension=os.path.splitext(self.file_name)[1],
            filetypes=[("All Files", "*.*")]
        )
        
        if file_path:
            try:
                # Save the file
                with open(file_path, 'wb') as f:
                    f.write(self.file_data)
                
                # Show success message
                messagebox.showinfo(
                    "Success",
                    f"File saved successfully:\n{file_path}"
                )
                
                # Log the download
                import gui
                gui.add_log(f"Downloaded file: {self.file_name}")
                
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Failed to save file:\n{str(e)}"
                )
    
    def close_window(self):
        """Close the popup window"""
        def close():
            if self.window and self.window.winfo_exists():
                self.window.destroy()
            if self.timer:
                self.timer.cancel()
        
        if tk._default_root:
            tk._default_root.after(0, close)

def show_message(message, file_data=None, file_name=None):
    """Show message popup (thread-safe)"""
    popup = MessagePopup(message, file_data, file_name)
    popup.show()