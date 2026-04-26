# ide_controller.py - STUDENT SIDE IDE CONTROL
# 100% WORKING - STABLE CONSOLE WITH INSTANT F9 RESPONSE
import os
import subprocess
import time
import threading
import win32gui
import win32con
import win32process
import keyboard
import win32api
import ctypes
import psutil

# Windows API constants
SW_HIDE = 0
SW_SHOW = 5
SW_RESTORE = 9
SW_SHOWMAXIMIZED = 3
SW_FORCEMINIMIZE = 11
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_OVERLAPPEDWINDOW = 0x00CF0000
GWL_STYLE = -16
GWL_EXSTYLE = -20

class IDEController:
    def __init__(self):
        self.process = None
        self.process_pid = None
        self.session_active = False
        self.current_ide = None
        self.duration = 0
        self.monitor_thread = None
        self.session_timer_thread = None
        self.hotkey_handles = []
        self.enforced_windows = set()
        self.post_session_lock_pin = None
        self.screen_width = 0
        self.screen_height = 0
        self.console_windows = set()
        self.last_enforce_time = 0
        self.enforce_interval = 2
        self.ide_main_hwnd = None
        self.original_styles = {}
        self.active_console = None  # Track currently active console
        self.console_bring_time = 0  # Track when console was last brought
        self.get_screen_dimensions()
        
        # IDE paths
        self.ide_paths = {
            "VS Code": [ r"C:\Program Files\Microsoft VS Code\Code.exe", r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe" ],
            "Code::Blocks": [ r"C:\Program Files\CodeBlocks\codeblocks.exe", r"C:\Program Files (x86)\CodeBlocks\codeblocks.exe" ],
            "Spyder": [ r"C:\ProgramData\Anaconda3\Scripts\spyder.exe", r"C:\Python39\Scripts\spyder.exe", ],
            "PyCharm": [ r"C:\Program Files\JetBrains\PyCharm\bin\pycharm64.exe", r"C:\Program Files\JetBrains\PyCharm Community Edition\bin\pycharm64.exe" ],
            "IDLE": [ r"C:\Python39\pythonw.exe", r"C:\Python310\pythonw.exe", ],
            "Sublime Text": [ r"C:\Program Files\Sublime Text 3\sublime_text.exe", r"C:\Program Files\Sublime Text\sublime_text.exe" ]
        }

    def get_screen_dimensions(self):
        try:
            self.screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            self.screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        except:
            self.screen_width = 1920
            self.screen_height = 1080

    def find_ide_path(self, ide_name):
        if ide_name not in self.ide_paths:
            return None
        username = os.environ.get("USERNAME", "")
        for path in self.ide_paths[ide_name]:
            full_path = path.replace("%USERNAME%", username)
            if os.path.exists(full_path):
                return full_path
        return None

    def launch_ide(self, ide_name):
        if ide_name == "IDLE":
            python_path = self.find_ide_path("IDLE")
            if python_path:
                try:
                    self.process = subprocess.Popen([python_path, "-m", "idlelib"])
                    self.process_pid = self.process.pid
                    return True
                except:
                    return False
        else:
            ide_path = self.find_ide_path(ide_name)
            if ide_path:
                try:
                    self.process = subprocess.Popen(ide_path)
                    self.process_pid = self.process.pid
                    return True
                except:
                    return False
        return False

    def find_ide_windows(self):
        """Find all windows belonging to IDE process"""
        windows = []
        def enum_callback(hwnd, _):
            try:
                _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                if window_pid == self.process_pid and win32gui.IsWindowVisible(hwnd):
                    parent = win32gui.GetParent(hwnd)
                    if parent == 0:
                        windows.append(hwnd)
            except:
                pass
            return True
        win32gui.EnumWindows(enum_callback, None)
        return windows

    def is_fullscreen(self, hwnd):
        """Check if window is already in fullscreen/kiosk mode"""
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return (rect[0] <= 0 and rect[1] <= 0 and 
                    rect[2] >= self.screen_width - 10 and 
                    rect[3] >= self.screen_height - 10)
        except:
            return False

    def store_original_style(self, hwnd):
        """Store original window style before modifying"""
        if hwnd not in self.original_styles:
            try:
                style = win32gui.GetWindowLong(hwnd, GWL_STYLE)
                self.original_styles[hwnd] = style
            except:
                pass

    def make_fullscreen_kiosk(self, hwnd):
        """Make window true fullscreen"""
        try:
            self.store_original_style(hwnd)
            
            if self.is_fullscreen(hwnd):
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
                return True
            
            style = WS_POPUP | WS_VISIBLE
            win32gui.SetWindowLong(hwnd, GWL_STYLE, style)
            
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 
                                 self.screen_width, self.screen_height, 
                                 win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW)
            
            win32gui.ShowWindow(hwnd, SW_SHOWMAXIMIZED)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            return False

    def restore_window(self, hwnd):
        """Restore window to original style and position"""
        try:
            if hwnd in self.original_styles:
                original_style = self.original_styles[hwnd]
                win32gui.SetWindowLong(hwnd, GWL_STYLE, original_style)
            
            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                 win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_FRAMECHANGED)
            
            win32gui.ShowWindow(hwnd, SW_RESTORE)
            win32gui.ShowWindow(hwnd, SW_SHOW)
            return True
        except:
            return False

    def find_console_windows(self):
        """Find console windows created by Code::Blocks"""
        console_windows = []
        
        def enum_callback(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                
                if hwnd == self.ide_main_hwnd:
                    return True
                    
                class_name = win32gui.GetClassName(hwnd)
                window_text = win32gui.GetWindowText(hwnd)
                
                # Detect console windows
                if class_name == "ConsoleWindowClass" or "Console" in class_name:
                    _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                    
                    if self.process_pid:
                        try:
                            parent = psutil.Process(self.process_pid)
                            children = parent.children(recursive=True)
                            child_pids = [c.pid for c in children]
                            child_pids.append(self.process_pid)
                            
                            if window_pid in child_pids:
                                console_windows.append(hwnd)
                                # Print only once per console
                                if hwnd not in self.console_windows:
                                    print(f"[CONSOLE] Detected: {win32gui.GetWindowText(hwnd)[:30]}")
                        except:
                            console_windows.append(hwnd)
            except:
                pass
            return True
        
        win32gui.EnumWindows(enum_callback, None)
        return console_windows

    def bring_console_to_front_instantly(self, console_hwnd):
        """Bring console to front IMMEDIATELY without delay"""
        try:
            # Get current foreground window
            foreground = win32gui.GetForegroundWindow()
            
            # If console is already foreground, just ensure it's on top
            if foreground == console_hwnd:
                win32gui.SetWindowPos(console_hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                return True
            
            # Position console in a good location (top-right corner)
            rect = win32gui.GetWindowRect(console_hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            
            # Only reposition if it's in a weird location
            if rect[0] < 50 or rect[1] < 50:
                new_x = self.screen_width - width - 20
                new_y = 50
                win32gui.SetWindowPos(console_hwnd, None, new_x, new_y, 0, 0,
                                     win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            
            # Make window visible and bring to front
            win32gui.ShowWindow(console_hwnd, SW_SHOW)
            win32gui.SetWindowPos(console_hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                 win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            win32gui.SetForegroundWindow(console_hwnd)
            
            # Store as active console
            self.active_console = console_hwnd
            self.console_bring_time = time.time()
            
            print(f"[CONSOLE] Brought to front instantly")
            return True
        except Exception as e:
            print(f"[CONSOLE] Error: {e}")
            return False

    def monitor_console_stability(self):
        """Keep console stable without flickering"""
        if not self.active_console:
            return
        
        try:
            # Check if active console still exists
            if not win32gui.IsWindow(self.active_console):
                self.active_console = None
                return
            
            # Only refresh console position if it's been more than 2 seconds
            # This prevents constant flickering
            current_time = time.time()
            if current_time - self.console_bring_time > 2:
                # Just ensure it's on top without forcing focus
                win32gui.SetWindowPos(self.active_console, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
        except:
            self.active_console = None

    def exit_kiosk_mode_gracefully(self):
        """Exit kiosk mode but keep IDE running"""
        print("\n[EXIT] Exiting kiosk mode...")
        
        self.unblock_all_keys()
        
        # Restore IDE windows
        windows = self.find_ide_windows()
        for hwnd in windows:
            self.restore_window(hwnd)
        
        # Restore consoles
        for console_hwnd in self.console_windows:
            try:
                win32gui.SetWindowPos(console_hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            except:
                pass
        
        self.show_taskbar()
        ctypes.windll.user32.PostMessageW(0xFFFF, 0x001A, 0, 0)
        time.sleep(0.2)
        
        print("[EXIT] Kiosk mode exited")
        
        if self.post_session_lock_pin:
            self.apply_screen_lock()

    def block_all_keys(self):
        """Block all escape keys - F9 is FREE"""
        keys = ['alt+tab', 'alt+esc', 'ctrl+alt+tab', 'ctrl+esc', 'windows', 'windows+d', 
                'windows+e', 'windows+r', 'alt+f4', 'ctrl+shift+esc', 'ctrl+alt+del', 
                'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f10', 'f11', 'f12']
        
        for key in keys:
            try:
                handle = keyboard.add_hotkey(key, lambda: None, suppress=True)
                self.hotkey_handles.append(handle)
            except:
                pass

    def unblock_all_keys(self):
        for handle in self.hotkey_handles:
            try:
                keyboard.remove_hotkey(handle)
            except:
                pass
        self.hotkey_handles.clear()

    def hide_taskbar(self):
        try:
            taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
            if taskbar:
                win32gui.ShowWindow(taskbar, SW_HIDE)
        except:
            pass

    def show_taskbar(self):
        try:
            taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
            if taskbar:
                win32gui.ShowWindow(taskbar, SW_SHOW)
        except:
            pass

    def apply_screen_lock(self):
        if self.post_session_lock_pin:
            try:
                print("[LOCK] Applying screen lock...")
                time.sleep(0.5)
                
                import screen_lock_student
                screen_lock_student.screen_lock.lock_screen(self.post_session_lock_pin)
                
                try:
                    import gui
                    gui.update_screen("Locked")
                except:
                    pass
            except Exception as e:
                print(f"[LOCK] Failed: {e}")

    def monitor_loop(self):
        """Stable monitor loop - doesn't interfere with console"""
        print("[MONITOR] Started")
        last_enforce_time = 0
        last_console_scan = 0
        
        while self.session_active:
            try:
                current_time = time.time()
                
                # Only enforce fullscreen every 2 seconds
                if current_time - last_enforce_time >= self.enforce_interval:
                    windows = self.find_ide_windows()
                    for hwnd in windows:
                        if self.ide_main_hwnd is None:
                            self.ide_main_hwnd = hwnd
                        
                        if not self.is_fullscreen(hwnd):
                            self.make_fullscreen_kiosk(hwnd)
                            self.enforced_windows.add(hwnd)
                    last_enforce_time = current_time
                
                # Scan for new consoles every 0.5 seconds
                if current_time - last_console_scan >= 0.5:
                    consoles = self.find_console_windows()
                    
                    for console_hwnd in consoles:
                        if console_hwnd not in self.console_windows:
                            # New console detected - bring it to front IMMEDIATELY
                            self.console_windows.add(console_hwnd)
                            self.bring_console_to_front_instantly(console_hwnd)
                    
                    last_console_scan = current_time
                
                # Stabilize existing console (prevent flicker)
                self.monitor_console_stability()
                
                time.sleep(0.1)  # Small sleep to prevent CPU overload
                
            except Exception as e:
                print(f"[MONITOR] Error: {e}")
                time.sleep(0.5)
        
        print("[MONITOR] Stopped")
        self.exit_kiosk_mode_gracefully()

    def timer_loop(self):
        """Session timer"""
        start_time = time.time()
        duration_sec = self.duration * 60
        session_end_time = start_time + duration_sec
        
        print(f"[TIMER] Session ends at {time.ctime(session_end_time)}")
        
        while self.session_active:
            if time.time() >= session_end_time:
                print(f"[TIMER] Time expired!")
                self.session_active = False
                break
            time.sleep(0.5)
        
        print("[TIMER] Stopped")

    def start_session(self, ide_name, duration, post_session_pin=None):
        """Start kiosk session"""
        if self.session_active:
            return False
        
        self.current_ide = ide_name
        self.duration = duration
        self.enforced_windows.clear()
        self.console_windows.clear()
        self.original_styles.clear()
        self.ide_main_hwnd = None
        self.active_console = None
        self.post_session_lock_pin = post_session_pin
        
        print(f"\n{'='*60}")
        print(f"[SESSION] Starting KIOSK MODE")
        print(f"[SESSION] IDE: {ide_name}")
        print(f"[SESSION] Duration: {duration} minutes")
        if post_session_pin:
            print(f"[SESSION] Lock PIN: {post_session_pin}")
        print(f"{'='*60}\n")
        
        self.hide_taskbar()
        time.sleep(0.2)
        
        if not self.launch_ide(ide_name):
            print("[SESSION] Failed to launch IDE!")
            self.show_taskbar()
            return False
        
        self.session_active = True
        time.sleep(3)
        
        windows = self.find_ide_windows()
        if windows:
            for hwnd in windows:
                self.make_fullscreen_kiosk(hwnd)
                self.enforced_windows.add(hwnd)
                if self.ide_main_hwnd is None:
                    self.ide_main_hwnd = hwnd
            print(f"[SESSION] Kiosk mode active")
        
        self.block_all_keys()
        
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.session_timer_thread = threading.Thread(target=self.timer_loop, daemon=True)
        self.session_timer_thread.start()
        
        try:
            import gui
            gui.add_log(f"🔒 KIOSK: {ide_name} ({duration} min)")
            gui.update_ide("Active")
        except:
            pass
        
        print(f"[SESSION] ✅ Ready! Press F9 to run code - console appears instantly\n")
        return True

    def end_session_early(self):
        if self.session_active:
            print("\n[SESSION] Early termination")
            self.session_active = False
            return True
        return False

# Global instance
ide_instance = IDEController()

def handle_launch_command(cmd, gui_module):
    try:
        parts = cmd.split("|")
        if len(parts) >= 3 and parts[0] == "LAUNCH_IDE":
            ide_name = parts[1]
            duration = int(parts[2])
            post_session_pin = None
            
            if len(parts) >= 4 and parts[3].startswith("LOCKPIN:"):
                pin_candidate = parts[3][8:].strip()
                if pin_candidate.isdigit() and len(pin_candidate) == 4:
                    post_session_pin = pin_candidate
            
            threading.Thread(target=ide_instance.start_session, args=(ide_name, duration, post_session_pin), daemon=True).start()
            return True
    except Exception as e:
        print(f"[CMD] Error: {e}")
    return False

def handle_end_command(gui_module):
    return ide_instance.end_session_early()