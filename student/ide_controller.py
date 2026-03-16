# ide_controller.py - STUDENT SIDE IDE CONTROL
# UPDATED: Removes ALL close/minimize buttons - Student cannot close at all
import os
import subprocess
import time
import threading
import win32gui
import win32con
import win32process
import keyboard

class IDEController:
    def __init__(self):
        self.process = None
        self.process_pid = None
        self.session_active = False
        self.session_end_time = 0
        self.current_ide = None
        self.duration = 0
        self.monitor_thread = None
        
        # IDE paths for different editors
        self.ide_paths = {
            "VS Code": [
                r"C:\Program Files\Microsoft VS Code\Code.exe",
                r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe"
            ],
            "Code::Blocks": [
                r"C:\Program Files\CodeBlocks\codeblocks.exe",
                r"C:\Program Files (x86)\CodeBlocks\codeblocks.exe"
            ],
            "Spyder": [
                r"C:\ProgramData\Anaconda3\Scripts\spyder.exe",
                r"C:\Python39\Scripts\spyder.exe",
            ],
            "PyCharm": [
                r"C:\Program Files\JetBrains\PyCharm\bin\pycharm64.exe",
                r"C:\Program Files\JetBrains\PyCharm Community Edition\bin\pycharm64.exe"
            ],
            "IDLE": [
                r"C:\Python39\pythonw.exe",
                r"C:\Python310\pythonw.exe",
            ],
            "Sublime Text": [
                r"C:\Program Files\Sublime Text 3\sublime_text.exe",
                r"C:\Program Files\Sublime Text\sublime_text.exe"
            ]
        }
    
    def find_ide_path(self, ide_name):
        """Find IDE executable path"""
        if ide_name not in self.ide_paths:
            return None
        
        username = os.environ.get("USERNAME", "")
        for path in self.ide_paths[ide_name]:
            full_path = path.replace("%USERNAME%", username)
            if os.path.exists(full_path):
                return full_path
        return None
    
    def launch_ide(self, ide_name):
        """Launch the specified IDE"""
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
                    self.process = subprocess.Popen([ide_path])
                    self.process_pid = self.process.pid
                    return True
                except:
                    return False
        return False
    
    def remove_close_button(self):
        """REMOVE close, minimize, maximize buttons COMPLETELY"""
        if not self.process_pid:
            return
        
        try:
            def enum_callback(hwnd, _):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == self.process_pid:
                    # Get current window style
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    
                    # REMOVE all title bar elements:
                    # WS_CAPTION = Title bar
                    # WS_SYSMENU = System menu (close button)
                    # WS_MINIMIZEBOX = Minimize button
                    # WS_MAXIMIZEBOX = Maximize button
                    # WS_THICKFRAME = Resizable border
                    style = style & ~win32con.WS_CAPTION
                    style = style & ~win32con.WS_SYSMENU
                    style = style & ~win32con.WS_MINIMIZEBOX
                    style = style & ~win32con.WS_MAXIMIZEBOX
                    style = style & ~win32con.WS_THICKFRAME
                    
                    # Apply new style
                    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
                    
                    # Remove extended styles
                    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    ex_style = ex_style & ~win32con.WS_EX_DLGMODALFRAME
                    ex_style = ex_style & ~win32con.WS_EX_WINDOWEDGE
                    ex_style = ex_style & ~win32con.WS_EX_CLIENTEDGE
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
                    
                    # Force window to refresh
                    win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                         win32con.SWP_FRAMECHANGED | 
                                         win32con.SWP_NOMOVE | 
                                         win32con.SWP_NOSIZE | 
                                         win32con.SWP_NOZORDER)
                    
                    print(f"[IDE] Removed close button for window: {hwnd}")
                return True
            
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            print(f"[IDE] Error removing close button: {e}")
    
    def make_fullscreen(self):
        """Make IDE window fullscreen"""
        if not self.process_pid:
            return
        
        try:
            def enum_callback(hwnd, _):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == self.process_pid:
                    # Get monitor info
                    monitor = win32gui.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
                    monitor_info = win32gui.GetMonitorInfo(monitor)
                    monitor_rect = monitor_info['Monitor']
                    
                    # Set to fullscreen
                    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                                         monitor_rect[0], monitor_rect[1],
                                         monitor_rect[2] - monitor_rect[0],
                                         monitor_rect[3] - monitor_rect[1],
                                         win32con.SWP_FRAMECHANGED)
                    
                    print(f"[IDE] Made fullscreen: {hwnd}")
                return True
            
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            print(f"[IDE] Fullscreen error: {e}")
    
    def block_all_input(self):
        """Block ALL system keys"""
        keyboard.add_hotkey('alt+tab', lambda: None, suppress=True)
        keyboard.add_hotkey('alt+esc', lambda: None, suppress=True)
        keyboard.add_hotkey('windows', lambda: None, suppress=True)
        keyboard.add_hotkey('windows+d', lambda: None, suppress=True)
        keyboard.add_hotkey('windows+e', lambda: None, suppress=True)
        keyboard.add_hotkey('windows+r', lambda: None, suppress=True)
        keyboard.add_hotkey('ctrl+esc', lambda: None, suppress=True)
        keyboard.add_hotkey('alt+f4', lambda: None, suppress=True)
        
        # Block function keys
        for i in range(1, 13):
            keyboard.add_hotkey(f'f{i}', lambda: None, suppress=True)
        
        self.hide_taskbar()
    
    def hide_taskbar(self):
        """Hide Windows taskbar"""
        try:
            taskbar_hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
            if taskbar_hwnd:
                win32gui.ShowWindow(taskbar_hwnd, win32con.SW_HIDE)
        except:
            pass
    
    def show_taskbar(self):
        """Show Windows taskbar"""
        try:
            taskbar_hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
            if taskbar_hwnd:
                win32gui.ShowWindow(taskbar_hwnd, win32con.SW_SHOW)
        except:
            pass
    
    def monitor_session(self):
        """Main monitoring loop"""
        start_time = time.time()
        self.session_end_time = start_time + (self.duration * 60)
        
        # Block all input first
        self.block_all_input()
        time.sleep(2)
        
        # REMOVE CLOSE BUTTON and make fullscreen
        self.remove_close_button()
        self.make_fullscreen()
        
        print(f"[IDE] Session started for {self.duration} minutes - NO CLOSE BUTTON")
        
        try:
            last_check = 0
            while self.session_active and time.time() < self.session_end_time:
                current_time = time.time()
                
                # Every 5 seconds, ensure close button is still gone
                if current_time - last_check > 5:
                    self.remove_close_button()
                    self.make_fullscreen()
                    last_check = current_time
                
                time.sleep(1)
            
            print("[IDE] Session completed")
        except Exception as e:
            print(f"[IDE] Session error: {e}")
        finally:
            self.end_session()
    
    def start_session(self, ide_name, duration):
        """Start IDE session"""
        self.current_ide = ide_name
        self.duration = duration
        
        if self.launch_ide(ide_name):
            self.session_active = True
            self.monitor_thread = threading.Thread(target=self.monitor_session, daemon=True)
            self.monitor_thread.start()
            
            try:
                import gui
                gui.add_log(f"IDE launched: {ide_name} ({duration} min) - NO CLOSE BUTTON")
            except:
                pass
            return True
        
        try:
            import gui
            gui.add_log(f"Failed to launch {ide_name}")
        except:
            pass
        return False
    
    def end_session(self):
        """End IDE session"""
        self.session_active = False
        keyboard.unhook_all_hotkeys()
        self.show_taskbar()
        self.current_ide = None
        self.process = None
        self.process_pid = None
        
        try:
            import gui
            gui.add_log("IDE session ended")
        except:
            pass
        print("[IDE] Session ended")

# Global instance
ide_instance = IDEController()

def handle_launch_command(cmd, gui_module):
    """Handle LAUNCH_IDE command"""
    try:
        parts = cmd.split("|")
        if len(parts) >= 3 and parts[0] == "LAUNCH_IDE":
            ide_name = parts[1]
            duration = int(parts[2])
            
            print(f"[IDE] Launching: {ide_name} for {duration} min")
            
            threading.Thread(target=ide_instance.start_session, 
                           args=(ide_name, duration),
                           daemon=True).start()
            
            if gui_module:
                gui_module.add_log(f"IDE launching: {ide_name} ({duration} min)")
            return True
    except Exception as e:
        if gui_module:
            gui_module.add_log(f"IDE launch error: {e}")
        print(f"[IDE] Error: {e}")
    return False

def handle_end_command(gui_module):
    """Handle END_IDE_SESSION command"""
    ide_instance.end_session()
    if gui_module:
        gui_module.add_log("IDE session ended by teacher")