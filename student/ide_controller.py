# ide_controller.py - STUDENT SIDE IDE CONTROL
# UPDATED: Removes ALL close/minimize buttons - Student cannot close at all
import os
import subprocess
import time
import threading
import ctypes
import argparse
import win32gui
import win32con
import win32process
import win32api
import keyboard
import ctypes.wintypes
import sys

def check_and_elevate_if_needed(ide_name=None):
    """Elevate script to admin if using Code::Blocks for proper window manipulation"""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if is_admin:
            print("[IDE] Running with admin privileges ✓")
            return True
        
        # If NOT admin and using Code::Blocks, elevate
        if ide_name and "code::blocks" in ide_name.lower():
            print("[IDE] Code::Blocks requires admin privileges, elevating script...")
            # Re-run the script with admin privileges
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                " ".join(['"%s"' % arg if ' ' in arg else arg for arg in sys.argv]),
                None,
                1  # SW_SHOW
            )
            sys.exit(0)
        else:
            print("[IDE] Running in standard mode")
            return False
    except Exception as e:
        print(f"[IDE] Privilege check: {e}")
        return False

class IDEController:
    def __init__(self):
        try:
            # Avoid DPI scaling offsets that can leave a visible edge in fullscreen.
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

        self.process = None
        self.process_pid = None
        self.target_exe_name = None
        self.target_window_hwnd = None  # Only lock this specific window
        self.session_active = False
        self.session_end_time = 0
        self.current_ide = None
        self.duration = 0
        self.monitor_thread = None
        self.hidden_taskbars = []
        self.known_ide_exes = {
            "code.exe",
            "codeblocks.exe",
            "spyder.exe",
            "pycharm64.exe",
            "pythonw.exe",
            "sublime_text.exe",
        }
        
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
        """Find IDE executable path from configured locations or system PATH"""
        if ide_name not in self.ide_paths:
            print(f"[IDE] IDE '{ide_name}' not configured")
            return None
        
        username = os.environ.get("USERNAME", "")
        
        # First, try configured paths
        for path in self.ide_paths[ide_name]:
            full_path = path.replace("%USERNAME%", username)
            if os.path.exists(full_path):
                print(f"[IDE] Found {ide_name} at: {full_path}")
                return full_path
        
        # If not found, search system PATH
        print(f"[IDE] Not found in configured paths, searching system PATH...")
        try:
            result = subprocess.run(
                ["where", self._get_exe_name(ide_name)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                exe_path = result.stdout.strip().split('\n')[0]  # Get first match
                print(f"[IDE] Found {ide_name} in PATH: {exe_path}")
                return exe_path
        except Exception as e:
            print(f"[IDE] PATH search failed: {e}")
        
        print(f"[IDE] ERROR: Could not find {ide_name}")
        return None
    
    def _get_exe_name(self, ide_name):
        """Get executable name for the IDE"""
        exe_map = {
            "VS Code": "code.exe",
            "Code::Blocks": "codeblocks.exe",
            "Spyder": "spyder.exe",
            "PyCharm": "pycharm64.exe",
            "IDLE": "pythonw.exe",
            "Sublime Text": "sublime_text.exe"
        }
        return exe_map.get(ide_name, ide_name.lower() + ".exe")
    
    def _launch_elevated(self, exe_path):
        """Launch executable with elevated privileges (admin)"""
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                exe_path,
                None,
                None,
                1  # SW_SHOW
            )
            # Get the newly spawned process by searching for it
            time.sleep(0.5)
            for _ in range(10):  # Try up to 10 times
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {os.path.basename(exe_path)}"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if os.path.basename(exe_path) in result.stdout:
                    # Extract PID from tasklist output
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if os.path.basename(exe_path) in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                try:
                                    pid = int(parts[1])
                                    return pid
                                except:
                                    pass
                time.sleep(0.2)
            return None
        except Exception as e:
            print(f"[IDE] Elevation error: {e}")
            return None
    
    def launch_ide(self, ide_name):
        """Launch the specified IDE"""
        if ide_name == "IDLE":
            python_path = self.find_ide_path("IDLE")
            if python_path:
                try:
                    self.process = subprocess.Popen([python_path, "-m", "idlelib"])
                    self.process_pid = self.process.pid
                    self.target_exe_name = os.path.basename(python_path).lower()
                    print(f"[IDE] Launched IDLE with PID {self.process_pid}")
                    return True
                except Exception as e:
                    print(f"[IDE] IDLE launch error: {e}")
                    return False
        else:
            ide_path = self.find_ide_path(ide_name)
            if ide_path:
                try:
                    launch_cmd = [ide_path]
                    if ide_name == "VS Code":
                        launch_cmd.extend(["--new-window", "--kiosk"])
                    print(f"[IDE] Launching: {' '.join(launch_cmd)}")
                    self.process = subprocess.Popen(launch_cmd)
                    self.process_pid = self.process.pid
                    self.target_exe_name = os.path.basename(ide_path).lower()
                    print(f"[IDE] Launched {ide_name} with PID {self.process_pid}")
                    return True
                except OSError as e:
                    if "elevation" in str(e).lower() or "740" in str(e):
                        print(f"[IDE] Admin elevation required, trying elevated launch...")
                        pid = self._launch_elevated(ide_path)
                        if pid:
                            self.process_pid = pid
                            self.target_exe_name = os.path.basename(ide_path).lower()
                            print(f"[IDE] Launched {ide_name} elevated with PID {self.process_pid}")
                            return True
                        else:
                            print(f"[IDE] Failed to launch elevated")
                            return False
                    else:
                        print(f"[IDE] {ide_name} launch error: {e}")
                        import traceback
                        traceback.print_exc()
                        return False
                except Exception as e:
                    print(f"[IDE] {ide_name} launch error: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                print(f"[IDE] Could not find path for {ide_name}")
                return False

    def _get_process_exe_name(self, pid):
        """Get executable name for a PID."""
        process_handle = None
        try:
            query_flag = getattr(win32con, "PROCESS_QUERY_LIMITED_INFORMATION", 0x1000)
            process_handle = win32api.OpenProcess(query_flag | win32con.PROCESS_VM_READ, False, pid)
            image_path = win32process.GetModuleFileNameEx(process_handle, 0)
            return os.path.basename(image_path).lower() if image_path else ""
        except Exception:
            return ""
        finally:
            if process_handle:
                try:
                    win32api.CloseHandle(process_handle)
                except Exception:
                    pass

    def _find_main_window(self, timeout_seconds=10):
        """Find the main window of the launched process or its children.
        Some apps (like VS Code) spawn helper processes, so we look for visible windows
        with the right exe name rather than just the original PID.
        """
        start_time = time.time()
        found_window = None
        target_exe = self.target_exe_name.lower() if self.target_exe_name else ""
        
        while time.time() - start_time < timeout_seconds:
            def enum_callback(hwnd, _):
                nonlocal found_window
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                
                # Check 1: Direct PID match (primary process)
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid == self.process_pid:
                        found_window = hwnd
                        return False  # Stop enumeration
                except Exception:
                    pass
                
                # Check 2: If no direct match, look for windows with matching exe name
                # (handles VS Code child processes)
                if target_exe and found_window is None:
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        process_handle = win32api.OpenProcess(0x0400 | 0x0010, False, pid)  # QUERY | VM_READ
                        exe_path = win32process.GetModuleFileNameEx(process_handle, 0)
                        current_exe = os.path.basename(exe_path).lower()
                        if current_exe == target_exe:
                            found_window = hwnd
                            # Don't stop - keep looking for main process window first
                    except Exception:
                        pass
                
                return True  # Keep enumerating
            
            try:
                win32gui.EnumWindows(enum_callback, None)
                if found_window is not None:
                    self.target_window_hwnd = found_window
                    print(f"[IDE] Found target window: {found_window} (exe: {target_exe})")
                    return True
            except Exception as e:
                print(f"[IDE] Error during window enumeration: {e}")
            
            time.sleep(0.2)
        
        print(f"[IDE] Failed to find window for PID {self.process_pid} or exe {target_exe}")
        return False

    def _is_target_window(self, hwnd):
        """Check whether a window belongs to the controlled IDE.
        STRICT MATCHING: Only match explicit target window handle to prevent collateral damage.
        """
        # If we have a specific window handle, ONLY match that exact window
        if self.target_window_hwnd is not None:
            return hwnd == self.target_window_hwnd
        
        # If target handle not set yet, don't match anything to prevent accidental locks
        # on other windows. The _find_main_window method will set target_window_hwnd.
        return False

    def _restore_window_style(self, hwnd):
        """Restore a normal resizable desktop window style and maximize to fill screen."""
        try:
            # First, make sure window is visible and not minimized
            if not win32gui.IsWindowVisible(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            else:
                # If it's minimized, restore it first
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            time.sleep(0.1)
            
            normal_style = (
                win32con.WS_OVERLAPPED
                | win32con.WS_CAPTION
                | win32con.WS_SYSMENU
                | win32con.WS_THICKFRAME
                | win32con.WS_MINIMIZEBOX
                | win32con.WS_MAXIMIZEBOX
                | win32con.WS_VISIBLE
            )
            try:
                win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, normal_style)
            except Exception:
                pass  # May fail if IDE is elevated - that's okay
            
            try:
                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                ex_style = (ex_style | win32con.WS_EX_APPWINDOW) & ~win32con.WS_EX_TOOLWINDOW
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
            except Exception:
                pass  # May fail if IDE is elevated - that's okay

            # Reset any modified system menu and clear any custom clipping region.
            try:
                win32gui.GetSystemMenu(hwnd, True)
            except Exception:
                pass
            try:
                win32gui.SetWindowRgn(hwnd, 0, True)
            except Exception:
                pass

            try:
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_NOTOPMOST,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_FRAMECHANGED | win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
                )
            except Exception:
                pass  # May fail if IDE is elevated - that's okay
                
            # Maximize window to fill screen in normal mode
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            print(f"[IDE] Restored window to normal full-screen maximized mode: {hwnd}")
        except Exception as e:
            print(f"[IDE] Error restoring window {hwnd}: {e}")

    def restore_target_windows(self):
        """Restore windows belonging to the current session target process."""
        if not self.process_pid and not self.target_exe_name:
            return

        def enum_callback(hwnd, _):
            if self._is_target_window(hwnd):
                self._restore_window_style(hwnd)
            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception:
            pass

    def restore_any_known_ide_windows(self):
        """Restore only the target IDE window that was locked - DO NOT touch other IDE windows."""
        # Only restore our specific target window, nothing else
        if self.target_window_hwnd is not None:
            try:
                if win32gui.IsWindow(self.target_window_hwnd):
                    self._restore_window_style(self.target_window_hwnd)
                    print(f"[IDE] Safely restored only target window: {self.target_window_hwnd}")
            except Exception as e:
                print(f"[IDE] Error restoring target window: {e}")
    
    def remove_close_button(self):
        """Apply kiosk-like window style to remove all chrome and resize paths."""
        if not self.process_pid and not self.target_window_hwnd:
            print("[IDE] WARNING: No process or window to lock")
            return
        
        try:
            affected_count = 0
            def enum_callback(hwnd, _):
                nonlocal affected_count
                if self._is_target_window(hwnd):
                    affected_count += 1
                    print(f"[IDE] Locking window {hwnd}")
                    
                    try:
                        # Force exact style instead of patching bits to prevent residual frame.
                        style = win32con.WS_POPUP | win32con.WS_VISIBLE | win32con.WS_CLIPCHILDREN | win32con.WS_CLIPSIBLINGS
                        
                        # Apply new style (may fail if IDE is elevated)
                        try:
                            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
                        except Exception:
                            pass
                        
                        # Remove extended styles (may fail if IDE is elevated)
                        try:
                            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                            ex_style = ex_style & ~win32con.WS_EX_DLGMODALFRAME
                            ex_style = ex_style & ~win32con.WS_EX_WINDOWEDGE
                            ex_style = ex_style & ~win32con.WS_EX_CLIENTEDGE
                            ex_style = ex_style & ~win32con.WS_EX_STATICEDGE
                            ex_style = ex_style & ~win32con.WS_EX_OVERLAPPEDWINDOW
                            ex_style = ex_style & ~win32con.WS_EX_APPWINDOW
                            ex_style = ex_style & ~win32con.WS_EX_TOOLWINDOW
                            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
                        except Exception:
                            pass

                        # Disable system-menu close/minimize/restore paths if menu exists.
                        try:
                            hmenu = win32gui.GetSystemMenu(hwnd, False)
                            if hmenu:
                                win32gui.EnableMenuItem(hmenu, win32con.SC_CLOSE, win32con.MF_BYCOMMAND | win32con.MF_GRAYED)
                                win32gui.EnableMenuItem(hmenu, win32con.SC_MINIMIZE, win32con.MF_BYCOMMAND | win32con.MF_GRAYED)
                                win32gui.EnableMenuItem(hmenu, win32con.SC_MAXIMIZE, win32con.MF_BYCOMMAND | win32con.MF_GRAYED)
                                win32gui.EnableMenuItem(hmenu, win32con.SC_RESTORE, win32con.MF_BYCOMMAND | win32con.MF_GRAYED)
                                win32gui.EnableMenuItem(hmenu, win32con.SC_SIZE, win32con.MF_BYCOMMAND | win32con.MF_GRAYED)
                        except Exception:
                            pass
                        
                        # Force window to refresh (may fail if IDE is elevated)
                        try:
                            win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                                 win32con.SWP_FRAMECHANGED | 
                                                 win32con.SWP_NOMOVE | 
                                                 win32con.SWP_NOSIZE | 
                                                 win32con.SWP_NOZORDER)
                        except Exception:
                            pass
                        
                        print(f"[IDE] Locked window {hwnd} successfully")
                    except Exception as e:
                        # Keyboard blocking is still in effect, so IDE is still locked
                        print(f"[IDE] Note: Locked via keyboard (window style changes may be limited)")
                        
                return True
            
            win32gui.EnumWindows(enum_callback, None)
            print(f"[IDE] Affected {affected_count} window(s)")
        except Exception as e:
            print(f"[IDE] Error removing close button: {e}")
    
    def make_fullscreen(self):
        """Force IDE window into topmost monitor-sized fullscreen."""
        if not self.process_pid:
            return
        
        try:
            window_count = 0
            def enum_callback(hwnd, _):
                nonlocal window_count
                if self._is_target_window(hwnd):
                    window_count += 1
                    try:
                        # Get monitor info
                        monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
                        monitor_info = win32api.GetMonitorInfo(monitor)
                        monitor_rect = monitor_info['Monitor']
                        x = monitor_rect[0]
                        y = monitor_rect[1]
                        width = monitor_rect[2] - monitor_rect[0]
                        height = monitor_rect[3] - monitor_rect[1]

                        print(f"[IDE] Positioning window {hwnd} to fullscreen: ({x}, {y}, {width}, {height})")

                        # Restore from minimized state
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        
                        # Single efficient fullscreen positioning call
                        result = win32gui.SetWindowPos(
                            hwnd,
                            win32con.HWND_TOPMOST,
                            x, y, width, height,
                            win32con.SWP_SHOWWINDOW
                        )
                        
                        if result:
                            print(f"[IDE] Successfully set fullscreen for window {hwnd}")
                        else:
                            print(f"[IDE] SetWindowPos returned False for {hwnd} (may be elevated process)")
                        
                        # bring to focus
                        try:
                            win32gui.SetForegroundWindow(hwnd)
                        except Exception as e:
                            pass
                    except Exception as e:
                        print(f"[IDE] Error positioning window {hwnd}: {e}")
                return True
            
            win32gui.EnumWindows(enum_callback, None)
            if window_count == 0:
                print("[IDE] WARNING: No target window found for fullscreen positioning")
        except Exception as e:
            print(f"[IDE] Error in make_fullscreen: {e}")
    
    def block_all_input(self):
        """Block ALL system keys and common close/minimize shortcuts"""
        # Block system navigation
        keyboard.add_hotkey('alt+tab', lambda: None, suppress=True)
        keyboard.add_hotkey('alt+esc', lambda: None, suppress=True)
        keyboard.add_hotkey('alt+space', lambda: None, suppress=True)
        keyboard.add_hotkey('windows', lambda: None, suppress=True)
        keyboard.add_hotkey('windows+tab', lambda: None, suppress=True)
        keyboard.add_hotkey('windows+d', lambda: None, suppress=True)
        keyboard.add_hotkey('windows+m', lambda: None, suppress=True)
        keyboard.add_hotkey('windows+e', lambda: None, suppress=True)
        keyboard.add_hotkey('windows+r', lambda: None, suppress=True)
        keyboard.add_hotkey('ctrl+esc', lambda: None, suppress=True)
        keyboard.add_hotkey('ctrl+shift+esc', lambda: None, suppress=True)
        keyboard.add_hotkey('alt+f4', lambda: None, suppress=True)
        
        # Block close/minimize shortcuts in applications
        keyboard.add_hotkey('ctrl+w', lambda: None, suppress=True)  # Close tab/window in many apps
        keyboard.add_hotkey('ctrl+q', lambda: None, suppress=True)  # Close app in many apps
        keyboard.add_hotkey('alt+F4', lambda: None, suppress=True)  # Redundant but explicit
        
        # Block function keys
        for i in range(1, 13):
            keyboard.add_hotkey(f'f{i}', lambda: None, suppress=True)
        
        self.hide_taskbar()
    
    def hide_taskbar(self):
        """Hide Windows taskbar(s) on all monitors."""
        try:
            self.hidden_taskbars = []

            def enum_callback(hwnd, _):
                class_name = win32gui.GetClassName(hwnd)
                if class_name in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd") and win32gui.IsWindowVisible(hwnd):
                    self.hidden_taskbars.append(hwnd)
                    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                    print(f"[IDE] Hid taskbar window: {hwnd}")
                return True

            win32gui.EnumWindows(enum_callback, None)
            print(f"[IDE] Taskbar: Found and hid {len(self.hidden_taskbars)} taskbar window(s)")
        except Exception as e:
            print(f"[IDE] Error hiding taskbar: {e}")
    
    def show_taskbar(self):
        """Restore previously hidden Windows taskbar(s) and bring to foreground."""
        try:
            print(f"[IDE] Restoring taskbar: {len(self.hidden_taskbars)} window(s) to restore")
            for hwnd in self.hidden_taskbars:
                if win32gui.IsWindow(hwnd):
                    # Show the taskbar window
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    print(f"[IDE] Showed taskbar window: {hwnd}")
                    # Short delay between show and positioning
                    time.sleep(0.1)
                    # Force it to the top of the Z-order
                    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                         win32con.SWP_NOSIZE | win32con.SWP_NOMOVE)
                    # Try to set focus to taskbar to make it active
                    try:
                        win32gui.SetForegroundWindow(hwnd)
                    except:
                        pass
                    # Redraw to ensure visibility
                    win32gui.InvalidateRect(hwnd, None, True)
                    # Force a refresh
                    win32gui.UpdateWindow(hwnd)
                    time.sleep(0.1)
                else:
                    print(f"[IDE] Taskbar window {hwnd} is no longer valid")
            self.hidden_taskbars = []
            # Longer delay to allow taskbar to render properly
            time.sleep(0.5)
            print(f"[IDE] Taskbar restoration complete")
        except Exception as e:
            print(f"[IDE] Error showing taskbar: {e}")
    
    def monitor_session(self):
        """Main monitoring loop"""
        start_time = time.time()
        self.session_end_time = start_time + (self.duration * 60)
        
        # Block all input first
        self.block_all_input()
        
        # Wait longer for IDE to fully initialize all windows before applying kiosk.
        # This prevents flickering during startup.
        print("[IDE] Waiting 6 seconds for IDE to fully initialize...")
        time.sleep(6)
        
        # Find the main window of the launched process (only this one will be locked)
        print("[IDE] Finding main window...")
        if not self._find_main_window(timeout_seconds=5):
            print("[IDE] WARNING: Could not find main window after 5 seconds")
        else:
            print(f"[IDE] Found target window: {self.target_window_hwnd}")
        
        # REMOVE CLOSE BUTTON and make fullscreen - only for the newly launched window
        self.remove_close_button()
        self.make_fullscreen()
        
        print(f"[IDE] Session started for {self.duration} minutes - NO CLOSE BUTTON - FULLSCREEN LOCKED")
        
        try:
            last_check = 0
            while self.session_active and time.time() < self.session_end_time:
                current_time = time.time()
                
                # Only check if window needs re-enforcement if minimized or moved.
                # Avoid constant reapplication to prevent flickering.
                if current_time - last_check > 15:
                    # Check if window was minimized and restore it
                    def check_minimized(hwnd, _):
                        if self._is_target_window(hwnd):
                            if not win32gui.IsWindowVisible(hwnd):
                                # Window hidden, restore it
                                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                        return True
                    try:
                        win32gui.EnumWindows(check_minimized, None)
                    except:
                        pass
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
    
    def end_session(self, force_close_ide=False):
        """End IDE session"""
        self.session_active = False

        # FIRST: Restore window styles and show in normal mode (BEFORE closing process)
        print("[IDE] Restoring IDE windows to normal mode...")
        self.restore_target_windows()
        self.restore_any_known_ide_windows()
        
        time.sleep(0.2)

        # SECOND: Close IDE process if requested (give it time to exit)
        if force_close_ide and self.process is not None:
            try:
                if self.process.poll() is None:
                    self.process.terminate()
                    time.sleep(0.8)
                    if self.process.poll() is None:
                        self.process.kill()
                        time.sleep(0.5)
                print("[IDE] IDE process closed successfully")
            except Exception as e:
                print(f"[IDE] Error closing process: {e}")

        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        
        # FINALLY: Show taskbar and bring it to focus
        self.show_taskbar()
        
        # Try multiple approaches to ensure desktop is visible
        try:
            # Approach 1: Find and activate Progman (desktop window class)
            progman = win32gui.FindWindow("Progman", "Program Manager")
            if progman:
                try:
                    win32gui.SetForegroundWindow(progman)
                    print("[IDE] Activated desktop via Progman")
                except:
                    pass
        except:
            pass
        
        try:
            # Approach 2: Find and activate Shell_TrayWnd (taskbar)
            taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
            if taskbar:
                try:
                    win32gui.SetForegroundWindow(taskbar)
                    print("[IDE] Activated taskbar window")
                except:
                    pass
        except:
            pass
        
        self.current_ide = None
        self.process = None
        self.process_pid = None
        self.target_exe_name = None
        self.target_window_hwnd = None  # Clear target window handle
        
        try:
            import gui
            gui.add_log("IDE session ended")
        except:
            pass
        print("[IDE] Session ended")

def run_local_kiosk_test(ide_name="VS Code", seconds=30):
    """Run a local kiosk test on the current laptop without teacher/LAN."""
    # Check and elevate if needed (for Code::Blocks)
    check_and_elevate_if_needed(ide_name)
    
    print(f"[IDE TEST] Starting local kiosk test for {seconds} seconds using {ide_name}")
    duration_minutes = max(seconds, 1) / 60.0
    if not ide_instance.start_session(ide_name, duration_minutes):
        print("[IDE TEST] Failed to launch IDE. Check IDE path in ide_paths.")
        return False

    end_time = time.time() + seconds
    try:
        while time.time() < end_time and ide_instance.session_active:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("[IDE TEST] Interrupted by user")
    finally:
        # For local testing, close only the launched IDE so desktop is guaranteed to restore.
        ide_instance.end_session(force_close_ide=True)

    print("[IDE TEST] Completed")
    return True

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Student IDE kiosk controller local test")
    parser.add_argument("--test", action="store_true", help="Run local offline kiosk test")
    parser.add_argument("--restore", action="store_true", help="Emergency: restore normal desktop/window state")
    parser.add_argument("--ide", default="VS Code", help="IDE name to test (default: VS Code)")
    parser.add_argument("--seconds", type=int, default=30, help="Test duration in seconds (default: 30)")
    args = parser.parse_args()

    if args.test:
        run_local_kiosk_test(args.ide, args.seconds)
    elif args.restore:
        ide_instance.restore_any_known_ide_windows()
        ide_instance.show_taskbar()
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        print("[IDE RESTORE] Attempted emergency restore of desktop and IDE windows")