# screen_dashboard.py - Teacher dashboard for viewing all student screens
# FIXED: Proper indentation and method placement
import tkinter as tk
from tkinter import ttk
import threading
import queue
import io
from PIL import Image, ImageTk
import state
import math

class ScreenDashboard:
    def __init__(self):
        self.dashboard_window = None
        self.image_queues = {}  # student_ip -> queue of images
        self.screen_frames = {}  # student_ip -> frame widget
        self.screen_labels = {}  # student_ip -> label widget
        self.photo_images = {}  # student_ip -> PhotoImage reference
        self.active_streams = set()
        self.max_columns = 3  # 3 screens per row
        self.update_thread = None
        self.is_running = False
        self.screen_width = 600  # Fixed width for each screen
        self.screen_height = 300  # Fixed height for each screen
        self.remote_panels = {}  # Store remote control panel references

    # ============ REMOTE CONTROL METHODS ============
    
    def show_remote_control(self, student_ip):
        """Show remote control panel for a student"""
        if student_ip not in state.students:
            return
            
        # Get student name
        student_name = f"Student_{list(state.students.keys()).index(student_ip) + 1:02d}"
        
        # Import here to avoid circular imports
        try:
            import remote_control_panel
        except ImportError:
            state.add_log("ERROR: remote_control_panel module not found")
            return
        
        # Create and show remote control panel
        panel = remote_control_panel.RemoteControlPanel(
            self.dashboard_window,
            student_ip,
            student_name,
            self
        )
        panel.show()
        
        # Store reference
        self.remote_panels[student_ip] = panel

    # ============ CONTEXT MENU METHODS ============
    
    def show_context_menu(self, event, student_ip):
        """Show right-click context menu for student"""
        menu = tk.Menu(self.dashboard_window, tearoff=0)
        
        # Get student name
        if student_ip in self.screen_frames:
            student_name = f"Machine {self.screen_frames[student_ip]['machine_number']}"
        else:
            student_name = student_ip
        
        menu.add_command(label=f"🎮 Remote Control {student_name}", 
                        command=lambda: self.show_remote_control(student_ip))
        menu.add_separator()
        menu.add_command(label=f"📺 View Screen", 
                        command=lambda: self.show_zoom_window(student_ip, 
                            self.screen_frames[student_ip]['machine_number'] if student_ip in self.screen_frames else 0))
        menu.add_command(label=f"🔄 Refresh Stream", 
                        command=lambda: self.refresh_student_stream(student_ip))
        menu.add_separator()
        menu.add_command(label=f"🔒 Lock Student", 
                        command=lambda: self.lock_student(student_ip))
        menu.add_command(label=f"🔓 Unlock Student", 
                        command=lambda: self.unlock_student(student_ip))
        menu.add_separator()
        menu.add_command(label=f"⛔ Disconnect Student", 
                        command=lambda: self.disconnect_student(student_ip))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def refresh_student_stream(self, student_ip):
        """Refresh a single student's stream"""
        state.send_command(f"REFRESH_SCREEN:{student_ip}")
        state.add_log(f"Teacher | Refreshed stream for {student_ip}")

    def lock_student(self, student_ip):
        """Lock specific student (not broadcast)"""
        state.send_command(f"LOCK_SCREEN:{student_ip}")
        state.add_log(f"Teacher | Locked {student_ip}")

    def unlock_student(self, student_ip):
        """Unlock specific student"""
        state.send_command(f"UNLOCK_SCREEN:{student_ip}")
        state.add_log(f"Teacher | Unlocked {student_ip}")

    def disconnect_student(self, student_ip):
        """Force disconnect a student"""
        if student_ip in state.students:
            try:
                state.students[student_ip].close()
                del state.students[student_ip]
                state.add_log(f"Teacher | Disconnected {student_ip}")
                self.refresh_all()
            except:
                pass

    # ============ DASHBOARD METHODS ============
    
    def show_dashboard(self):
        """Show the dashboard window"""
        if self.dashboard_window and self.dashboard_window.winfo_exists():
            self.dashboard_window.lift()
            self.dashboard_window.focus_force()
            return
            
        self.dashboard_window = tk.Toplevel()
        self.dashboard_window.title("Student Screens Dashboard")
        self.dashboard_window.geometry("1400x800")
        
        # Configure window
        self.dashboard_window.protocol("WM_DELETE_WINDOW", self.close_dashboard)
        
        # Create main container
        main_container = ttk.Frame(self.dashboard_window, padding=10)
        main_container.pack(fill="both", expand=True)
        
        # Header with controls
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(header_frame, text="📺 Student Screens Dashboard", 
                 font=("Arial", 14, "bold")).pack(side="left")
        
        # Control buttons
        control_frame = ttk.Frame(header_frame)
        control_frame.pack(side="right")
        
        ttk.Button(control_frame, text="Start All", 
                  command=self.start_all_streams,
                  width=10).pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="Stop All", 
                  command=self.stop_all_streams,
                  width=10).pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="Refresh", 
                  command=self.refresh_all,
                  width=10).pack(side="left", padx=5)
        
        # Canvas with scrollbar for screens
        canvas_frame = ttk.Frame(main_container)
        canvas_frame.pack(fill="both", expand=True)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(canvas_frame, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # Configure canvas scrolling
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create frame inside canvas for screens
        screens_container = ttk.Frame(canvas, padding=5)
        canvas_window = canvas.create_window((0, 0), window=screens_container, anchor="nw")
        
        # Configure canvas to resize with window
        def configure_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width)
            screens_container.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        canvas.bind('<Configure>', configure_canvas)
        
        # Status bar
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill="x", pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var,
                 font=("Arial", 9)).pack(side="left")
        
        self.count_var = tk.StringVar(value="Connected: 0 | Streaming: 0")
        ttk.Label(status_frame, textvariable=self.count_var,
                 font=("Arial", 9)).pack(side="right")
        
        # Store references
        self.canvas = canvas
        self.screens_container = screens_container
        
        # Initialize queues for all connected students
        for student_ip in state.students:
            self.image_queues[student_ip] = queue.Queue(maxsize=3)
            print(f"[DASHBOARD] Created queue for {student_ip}")
        
        # Create screen grid
        self.create_screen_grid()
        
        # Start update thread
        self.is_running = True
        self.update_thread = threading.Thread(target=self.update_all_screens, daemon=True)
        self.update_thread.start()
        
        # Start streaming for all students
        self.start_all_streams()
        
        # Center window
        self.center_window()
    
    def center_window(self):
        """Center the dashboard window"""
        self.dashboard_window.update_idletasks()
        width = self.dashboard_window.winfo_width()
        height = self.dashboard_window.winfo_height()
        x = (self.dashboard_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dashboard_window.winfo_screenheight() // 2) - (height // 2)
        self.dashboard_window.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_screen_grid(self):
        """Create grid layout for student screens"""
        # Clear existing frames
        for widget in self.screens_container.winfo_children():
            widget.destroy()
        
        self.screen_frames.clear()
        self.screen_labels.clear()
        
        # Get all student IPs
        student_ips = list(state.students.keys())
        
        if not student_ips:
            ttk.Label(self.screens_container, text="No students connected",
                     font=("Arial", 12)).pack(pady=50)
            return
        
        # Calculate grid dimensions - 3 columns
        num_students = len(student_ips)
        rows = math.ceil(num_students / self.max_columns)
        
        # Configure grid weights for ALL rows and columns
        for i in range(self.max_columns):
            self.screens_container.columnconfigure(i, weight=1, minsize=200)
        for i in range(rows):
            self.screens_container.rowconfigure(i, weight=1, minsize=150)
        
        # Create screen frames in grid with PROPER sizes
        for idx, student_ip in enumerate(student_ips):
            row = idx // self.max_columns
            col = idx % self.max_columns
            
            # Create frame for each screen
            screen_frame = ttk.LabelFrame(self.screens_container, 
                                         text=f"Machine {idx+1} - {student_ip}",
                                         padding=5)
            screen_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            # Add right-click context menu
            screen_frame.bind('<Button-3>', lambda e, ip=student_ip: self.show_context_menu(e, ip))
            
            # Screen display label
            screen_label = tk.Label(screen_frame, bg="black", 
                                   text="Waiting for stream...",
                                   fg="white", font=("Arial", 11))
            screen_label.pack(fill="both", expand=True)
            screen_label.bind('<Button-3>', lambda e, ip=student_ip: self.show_context_menu(e, ip))
            
            # Controls frame
            controls_frame = ttk.Frame(screen_frame)
            controls_frame.pack(fill="x", pady=(10, 5))
            
            # Start/Stop button
            def make_start_stop_cmd(ip):
                def cmd():
                    if ip in self.active_streams:
                        self.stop_stream(ip)
                    else:
                        self.start_stream(ip)
                return cmd
            
            start_stop_btn = ttk.Button(controls_frame, text="Start",
                                       command=make_start_stop_cmd(student_ip),
                                       width=10)
            start_stop_btn.pack(side="left", padx=(0, 10))
            
            # Remote Control button
            def make_remote_cmd(ip):
                def cmd():
                    self.show_remote_control(ip)
                return cmd
            
            remote_btn = ttk.Button(controls_frame, text="🎮 Remote",
                                   command=make_remote_cmd(student_ip),
                                   width=10)
            remote_btn.pack(side="left", padx=(0, 10))
            
            # Zoom button
            def make_zoom_cmd(ip, machine_num):
                def cmd():
                    self.show_zoom_window(ip, machine_num)
                return cmd
            
            ttk.Button(controls_frame, text="Zoom",
                      command=make_zoom_cmd(student_ip, idx+1),
                      width=10).pack(side="right")
            
            # Store references
            self.screen_frames[student_ip] = {
                "frame": screen_frame,
                "label": screen_label,
                "start_stop_btn": start_stop_btn,
                "remote_btn": remote_btn,
                "machine_number": idx + 1,
                "status": "stopped"
            }
            
            # Initialize queue if not exists
            if student_ip not in self.image_queues:
                self.image_queues[student_ip] = queue.Queue(maxsize=3)
            
            print(f"[DASHBOARD] Created screen frame for {student_ip}")
    
    def start_stream(self, student_ip):
        """Start streaming from a student"""
        if student_ip not in state.students:
            return
            
        state.send_command(f"START_SCREEN_STREAM:{student_ip}")
        self.active_streams.add(student_ip)
        
        # Update button text
        if student_ip in self.screen_frames:
            self.screen_frames[student_ip]["start_stop_btn"].config(text="Stop")
            self.screen_frames[student_ip]["label"].config(text="Starting stream...")
        
        self.status_var.set(f"Started stream for {student_ip}")
        state.add_log(f"Teacher | Started screen stream for {student_ip}")
        print(f"[DASHBOARD] Started stream for {student_ip}")
    
    def stop_stream(self, student_ip):
        """Stop streaming from a student"""
        state.send_command(f"STOP_SCREEN_STREAM:{student_ip}")
        self.active_streams.discard(student_ip)
        
        # Update button text and clear screen
        if student_ip in self.screen_frames:
            self.screen_frames[student_ip]["start_stop_btn"].config(text="Start")
            self.screen_frames[student_ip]["label"].config(text="Stream stopped", 
                                                          image="")
            # Clear PhotoImage reference
            if student_ip in self.photo_images:
                del self.photo_images[student_ip]
        
        self.status_var.set(f"Stopped stream for {student_ip}")
        state.add_log(f"Teacher | Stopped screen stream for {student_ip}")
        print(f"[DASHBOARD] Stopped stream for {student_ip}")
    
    def start_all_streams(self):
        """Start streaming for all connected students"""
        for student_ip in state.students:
            if student_ip not in self.active_streams:
                self.start_stream(student_ip)
        
        self.status_var.set("Started all streams")
        print(f"[DASHBOARD] Started all streams")
    
    def stop_all_streams(self):
        """Stop all streams"""
        for student_ip in list(self.active_streams):
            self.stop_stream(student_ip)
        
        self.status_var.set("Stopped all streams")
        print(f"[DASHBOARD] Stopped all streams")
    
    def refresh_all(self):
        """Refresh all streams"""
        for student_ip in self.active_streams:
            state.send_command(f"REFRESH_SCREEN:{student_ip}")
        
        self.status_var.set("Refreshed all streams")
        print(f"[DASHBOARD] Refreshed all streams")
    
    def update_all_screens(self):
        """Update all screen displays"""
        while self.is_running and self.dashboard_window and self.dashboard_window.winfo_exists():
            try:
                # Update count display
                if hasattr(self, 'count_var'):
                    self.count_var.set(f"Connected: {len(state.students)} | Streaming: {len(self.active_streams)}")
                
                # Process each student's image queue
                for student_ip in list(self.image_queues.keys()):
                    if not self.is_running:
                        break
                        
                    try:
                        # Try to get image from queue (non-blocking)
                        image_data = self.image_queues[student_ip].get_nowait()
                        
                        # Update display if student has a frame
                        if student_ip in self.screen_frames:
                            self.update_screen_display(student_ip, image_data)
                            
                    except queue.Empty:
                        continue
                    except Exception as e:
                        print(f"[DASHBOARD] Error updating {student_ip}: {e}")
                
                # Small delay to prevent CPU hogging
                threading.Event().wait(0.1)
                
            except Exception as e:
                print(f"[DASHBOARD] Update thread error: {e}")
                break
    
    def update_screen_display(self, student_ip, image_data):
        """Update a specific screen display"""
        try:
            print(f"[DASHBOARD] Updating screen for {student_ip} with {len(image_data)} bytes")
            
            # Check if image data is valid
            if not image_data or len(image_data) < 100:
                print(f"[DASHBOARD] Invalid image data from {student_ip}")
                return
                
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            print(f"[DASHBOARD] Original image size: {image.size}")
            
            # Get screen frame info
            screen_info = self.screen_frames[student_ip]
            label = screen_info["label"]
            
            # Get the current size of the label
            label.update_idletasks()
            label_width = label.winfo_width()
            label_height = label.winfo_height()
            
            print(f"[DASHBOARD] Label size: {label_width}x{label_height}")
            
            if label_width > 10 and label_height > 10:
                # Resize image to fit the label while maintaining aspect ratio
                image.thumbnail((label_width, label_height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(image)
                
                # Update label
                label.config(image=photo, text="")
                label.image = photo  # Keep reference
                
                # Store reference
                self.photo_images[student_ip] = photo
                
                print(f"[DASHBOARD] Displayed image size: {image.size}")
            else:
                print(f"[DASHBOARD] Label too small: {label_width}x{label_height}")
            
            print(f"[DASHBOARD] Screen updated for {student_ip}")
            
        except Exception as e:
            print(f"[DASHBOARD] Display error for {student_ip}: {e}")
    
    def receive_screen_data(self, student_ip, image_data):
        """Receive screen data from student"""
        print(f"[DASHBOARD] Received {len(image_data)} bytes from {student_ip}")
        
        if student_ip in self.image_queues:
            try:
                # Put image in queue (non-blocking)
                self.image_queues[student_ip].put_nowait(image_data)
                print(f"[DASHBOARD] Queued image for {student_ip}")
            except queue.Full:
                # Remove old image and add new one
                try:
                    self.image_queues[student_ip].get_nowait()
                    self.image_queues[student_ip].put_nowait(image_data)
                    print(f"[DASHBOARD] Replaced image in queue for {student_ip}")
                except:
                    pass
        else:
            print(f"[DASHBOARD] No queue found for {student_ip}")
    
    def show_zoom_window(self, student_ip, machine_number):
        """Show zoomed window for a specific student"""
        ZoomWindow(self.dashboard_window, student_ip, machine_number, self)
    
    def close_dashboard(self):
        """Close the dashboard window"""
        self.is_running = False
        
        # Close all remote control panels
        for ip, panel in list(self.remote_panels.items()):
            try:
                if panel and hasattr(panel, 'close'):
                    panel.close()
            except:
                pass
        self.remote_panels.clear()
        
        # Stop all streams
        self.stop_all_streams()
        
        # Close window
        if self.dashboard_window:
            try:
                self.dashboard_window.destroy()
            except:
                pass
            self.dashboard_window = None
        
        # Clear queues
        self.image_queues.clear()
        self.screen_frames.clear()
        self.screen_labels.clear()
        self.photo_images.clear()
        self.active_streams.clear()
        
        state.add_log("Teacher | Closed screen dashboard")
        print(f"[DASHBOARD] Dashboard closed")


class ZoomWindow:
    """Zoomed window for viewing a single student screen"""
    def __init__(self, parent, student_ip, machine_number, dashboard):
        self.parent = parent
        self.student_ip = student_ip
        self.machine_number = machine_number
        self.dashboard = dashboard
        self.window = None
        self.photo_image = None
        self.is_running = True
        self.zoom_width = 1024
        self.zoom_height = 768
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"Zoomed View - Machine {machine_number} - {student_ip}")
        self.window.geometry(f"{self.zoom_width}x{self.zoom_height}")
        
        # Configure window
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        
        # Create main container
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(header_frame, text=f"🔍 Zoomed View - Machine {machine_number} - {student_ip}", 
                 font=("Arial", 12, "bold")).pack(side="left")
        
        # Controls
        controls_frame = ttk.Frame(header_frame)
        controls_frame.pack(side="right")
        
        ttk.Button(controls_frame, text="Refresh", 
                  command=self.refresh_screen,
                  width=10).pack(side="left", padx=5)
        
        ttk.Button(controls_frame, text="Full Screen", 
                  command=self.toggle_fullscreen,
                  width=10).pack(side="left", padx=5)
        
        ttk.Button(controls_frame, text="🎮 Remote Control", 
                  command=self.open_remote_control,
                  width=15).pack(side="left", padx=5)
        
        # Screen display
        self.screen_label = tk.Label(main_frame, bg="black", 
                                    text="Loading...",
                                    fg="white", font=("Arial", 12))
        self.screen_label.pack(fill="both", expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Streaming...")
        ttk.Label(main_frame, textvariable=self.status_var,
                 font=("Arial", 9)).pack(fill="x", pady=(10, 0))
        
        # Start update thread
        self.update_thread = threading.Thread(target=self.update_zoom_view, daemon=True)
        self.update_thread.start()
        
        # Center window
        self.center_window()
        print(f"[ZOOM] Created zoom window for {student_ip}")
    
    def center_window(self):
        """Center the zoom window"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def update_zoom_view(self):
        """Update the zoomed view"""
        while self.is_running and self.window and self.window.winfo_exists():
            try:
                if self.student_ip in self.dashboard.image_queues:
                    # Get latest image
                    try:
                        image_data = self.dashboard.image_queues[self.student_ip].get_nowait()
                        print(f"[ZOOM] Updating display for {self.student_ip}")
                        self.update_display(image_data)
                    except queue.Empty:
                        pass
                
                # Small delay
                threading.Event().wait(0.2)  # Update every 200ms
                
            except Exception as e:
                print(f"[ZOOM] Error: {e}")
                break
    
    def update_display(self, image_data):
        """Update the display with new image"""
        try:
            print(f"[ZOOM] Received {len(image_data)} bytes")
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            print(f"[ZOOM] Image size: {image.size}")
            
            # Resize to fit zoom window
            label_width = self.screen_label.winfo_width()
            label_height = self.screen_label.winfo_height()
            
            if label_width > 10 and label_height > 10:
                # Resize to fit label while maintaining aspect ratio
                image.thumbnail((label_width, label_height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(image)
                
                # Update label
                self.screen_label.config(image=photo, text="")
                self.screen_label.image = photo  # Keep reference
                self.photo_image = photo
                
                # Update status
                self.status_var.set(f"Updated: {image.width}x{image.height}")
                print(f"[ZOOM] Display updated: {image.width}x{image.height}")
                
        except Exception as e:
            self.status_var.set(f"Error: {str(e)[:50]}")
            print(f"[ZOOM] Error updating display: {e}")
    
    def refresh_screen(self):
        """Request screen refresh"""
        state.send_command(f"REFRESH_SCREEN:{self.student_ip}")
        self.status_var.set("Refresh requested...")
        print(f"[ZOOM] Requested refresh for {self.student_ip}")
    
    def open_remote_control(self):
        """Open remote control for this student"""
        self.dashboard.show_remote_control(self.student_ip)
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        current_state = self.window.attributes('-fullscreen')
        self.window.attributes('-fullscreen', not current_state)
        
        if not current_state:
            self.window.bind('<Escape>', lambda e: self.toggle_fullscreen())
        print(f"[ZOOM] Toggled fullscreen: {not current_state}")
    
    def close_window(self):
        """Close the zoom window"""
        self.is_running = False
        if self.window:
            try:
                self.window.destroy()
            except:
                pass
            self.window = None
        print(f"[ZOOM] Closed window for {self.student_ip}")


# Global instance
screen_dashboard = ScreenDashboard()