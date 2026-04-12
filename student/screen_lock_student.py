# screen_lock_student.py - Student side screen lock with PIN entry
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import config
import server

class ScreenLock:
    def __init__(self):
        self.lock_window = None
        self.locked = False
        self.correct_pin = None
        self.attempts = 0
        self.max_attempts = 5
        self.lock_active = False
        
    def lock_screen(self, pin):
        """Lock the student's screen with fullscreen PIN entry"""
        self.correct_pin = pin
        self.locked = True
        self.lock_active = True
        self.attempts = 0
        
        # Close any existing lock window
        if self.lock_window and self.lock_window.winfo_exists():
            self.lock_window.destroy()
            
        # Create lock window in main thread
        if tk._default_root:
            tk._default_root.after(0, self._create_lock_window)
        else:
            # If no root exists, create one in a new thread
            threading.Thread(target=self._create_lock_window_thread, daemon=True).start()
            
        # Log to teacher (optional - can be removed if you want silent)
        server.send_log("Screen locked - PIN required")
        
    def _create_lock_window_thread(self):
        """Create lock window in a new thread with its own Tk instance"""
        root = tk.Tk()
        root.withdraw()  # Hide the root
        self._create_lock_window(root)
        root.mainloop()
        
    def _create_lock_window(self, parent=None):
        """Create the actual lock window"""
        if parent is None:
            parent = tk._default_root
            
        self.lock_window = tk.Toplevel(parent)
        self.lock_window.title("🔒 Screen Locked")
        
        # Get screen dimensions
        screen_width = self.lock_window.winfo_screenwidth()
        screen_height = self.lock_window.winfo_screenheight()
        
        # Make it fullscreen and always on top
        self.lock_window.geometry(f"{screen_width}x{screen_height}+0+0")
        self.lock_window.attributes('-fullscreen', True)
        self.lock_window.attributes('-topmost', True)
        
        # Prevent closing
        self.lock_window.protocol("WM_DELETE_WINDOW", self.on_close_attempt)
        
        # Bind keys to prevent leaving
        self.lock_window.bind('<Alt-Tab>', lambda e: 'break')
        self.lock_window.bind('<Alt-F4>', lambda e: 'break')
        self.lock_window.bind('<Control-w>', lambda e: 'break')
        self.lock_window.bind('<Control-q>', lambda e: 'break')
        self.lock_window.bind('<Escape>', lambda e: 'break')
        self.lock_window.bind('<Tab>', lambda e: 'break')
        
        # Set background color
        self.lock_window.configure(bg='#2c3e50')
        
        # Main frame
        main_frame = tk.Frame(self.lock_window, bg='#2c3e50')
        main_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Lock icon
        lock_icon = tk.Label(main_frame, text="🔒", 
                            font=("Arial", 80), 
                            bg='#2c3e50', fg='#e74c3c')
        lock_icon.pack(pady=(0, 20))
        
        # Title
        title = tk.Label(main_frame, text="SCREEN LOCKED", 
                        font=("Arial", 24, "bold"), 
                        bg='#2c3e50', fg='white')
        title.pack(pady=(0, 10))
        
        # Message
        message = tk.Label(main_frame, 
                          text="Enter the 4-digit PIN to unlock", 
                          font=("Arial", 12), 
                          bg='#2c3e50', fg='#bdc3c7')
        message.pack(pady=(0, 30))
        
        # PIN Entry Frame
        pin_frame = tk.Frame(main_frame, bg='#2c3e50')
        pin_frame.pack(pady=(0, 20))
        
        # PIN Entry
        self.pin_var = tk.StringVar()
        self.pin_entry = tk.Entry(pin_frame, textvariable=self.pin_var,
                                 font=("Arial", 24), width=6,
                                 show="●", justify='center',
                                 bg='#34495e', fg='white',
                                 insertbackground='white',
                                 relief='flat', bd=10)
        self.pin_entry.pack()
        
        # Attempts remaining
        self.attempts_var = tk.StringVar(value=f"Attempts remaining: {self.max_attempts}")
        attempts_label = tk.Label(main_frame, textvariable=self.attempts_var,
                                 font=("Arial", 10), 
                                 bg='#2c3e50', fg='#e74c3c')
        attempts_label.pack(pady=(10, 20))
        
        # Unlock button
        unlock_btn = tk.Button(main_frame, text="UNLOCK", 
                              command=self.check_pin,
                              font=("Arial", 12, "bold"),
                              bg='#3498db', fg='white',
                              activebackground='#2980b9',
                              activeforeground='white',
                              relief='flat', padx=20, pady=10,
                              cursor='hand2')
        unlock_btn.pack()
        
        # Instructions
        instructions = tk.Label(main_frame, 
                               text="Contact your teacher for the PIN", 
                               font=("Arial", 9), 
                               bg='#2c3e50', fg='#7f8c8d')
        instructions.pack(pady=(20, 0))
        
        # Bind Enter key
        self.pin_entry.bind('<Return>', lambda e: self.check_pin())
        self.pin_entry.focus()
        
        # Start update thread for attempts
        self.update_attempts()
        
        # Log
        import gui
        gui.add_log("🔒 Screen locked - PIN required")
        
    def check_pin(self):
        """Check if entered PIN is correct"""
        entered_pin = self.pin_var.get().strip()
        
        if not entered_pin.isdigit() or len(entered_pin) != 4:
            self.show_error("PIN must be exactly 4 digits!")
            self.pin_var.set("")
            self.pin_entry.focus()
            return
            
        if entered_pin == self.correct_pin:
            # Correct PIN - unlock
            self.unlock_screen()
        else:
            # Wrong PIN
            self.attempts += 1
            remaining = self.max_attempts - self.attempts
            self.attempts_var.set(f"Attempts remaining: {remaining}")
            
            if remaining <= 0:
                self.show_error("Too many failed attempts!\nRestart required.")
                # Could add additional punishment here
                self.attempts = 0
                self.attempts_var.set(f"Attempts remaining: {self.max_attempts}")
            
            self.show_error("Incorrect PIN!")
            self.pin_var.set("")
            self.pin_entry.focus()
            
    def show_error(self, message):
        """Show error message (non-blocking)"""
        if self.lock_window and self.lock_window.winfo_exists():
            # Create error label that disappears
            error_label = tk.Label(self.lock_window, text=message,
                                  font=("Arial", 10),
                                  bg='#2c3e50', fg='#e74c3c')
            error_label.place(relx=0.5, rely=0.85, anchor='center')
            self.lock_window.after(2000, error_label.destroy)
            
    def unlock_screen(self):
        """Unlock the screen"""
        self.locked = False
        self.lock_active = False
        
        # Close lock window
        if self.lock_window and self.lock_window.winfo_exists():
            self.lock_window.attributes('-fullscreen', False)
            self.lock_window.destroy()
            self.lock_window = None
            
        # Notify teacher that student unlocked
        server.send_log("Screen unlocked - Correct PIN entered")
        
        # Log
        import gui
        gui.add_log("🔓 Screen unlocked")
        
        # Notify server that this student is unlocked
        try:
            import server
            server.send_log("STUDENT_UNLOCKED")
        except:
            pass
            
    def on_close_attempt(self):
        """Handle attempts to close the window"""
        # Just ignore - window cannot be closed
        pass
        
    def update_attempts(self):
        """Update attempts counter"""
        if self.lock_active and self.lock_window and self.lock_window.winfo_exists():
            remaining = self.max_attempts - self.attempts
            self.attempts_var.set(f"Attempts remaining: {remaining}")
            self.lock_window.after(1000, self.update_attempts)
            
    def unlock_silently(self):
        """Unlock without logging (used when teacher unlocks)"""
        self.locked = False
        self.lock_active = False
        
        if self.lock_window and self.lock_window.winfo_exists():
            self.lock_window.attributes('-fullscreen', False)
            self.lock_window.destroy()
            self.lock_window = None
            
        import gui
        gui.add_log("🔓 Screen unlocked by teacher")


# Global instance
screen_lock = ScreenLock()