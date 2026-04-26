# screen_stream.py - Student side screen streaming
import threading
import time
import io
import queue
from PIL import Image, ImageGrab
import mss
import mss.tools
import config
import server

class ScreenStreamer:
    def __init__(self):
        self.streaming = False
        self.target_ip = None
        self.stream_thread = None
        self.image_queue = queue.Queue(maxsize=2)
        self.capture_thread = None
        self.quality = 85  # HD-friendly JPEG quality
        self.fps = 2.0  # 2 frames per second for smoother preview
        self.screen_width = 1280
        self.screen_height = 720

    def update_settings(self, quality=None, fps=None, width=None, height=None):
        """Update streaming settings at runtime."""
        if quality is not None:
            self.quality = max(30, min(95, int(quality)))
        if fps is not None:
            self.fps = max(0.5, min(5.0, float(fps)))
        if width is not None:
            self.screen_width = max(640, min(1920, int(width)))
        if height is not None:
            self.screen_height = max(360, min(1080, int(height)))

        print(
            f"[SCREEN STREAM] Settings updated: "
            f"{self.screen_width}x{self.screen_height}, "
            f"Q{self.quality}, {self.fps} FPS"
        )
        
    def start_streaming(self, teacher_ip):
        """Start streaming screen to teacher"""
        if self.streaming:
            return False
            
        self.streaming = True
        self.target_ip = teacher_ip
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self.capture_screen, daemon=True)
        self.capture_thread.start()
        
        # Start stream thread
        self.stream_thread = threading.Thread(target=self.stream_to_teacher, daemon=True)
        self.stream_thread.start()
        
        print(f"[SCREEN STREAM] Started streaming {self.screen_width}x{self.screen_height} to {teacher_ip}")
        import gui
        gui.add_log("Screen streaming started")
        return True
    
    def stop_streaming(self):
        """Stop screen streaming"""
        if not self.streaming:
            return
            
        self.streaming = False
        
        # Wait for threads to finish
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        if self.stream_thread:
            self.stream_thread.join(timeout=2.0)
            
        print("[SCREEN STREAM] Stopped streaming")
        import gui
        gui.add_log("Screen streaming stopped")
    
    def capture_screen(self):
        """Capture screen at regular intervals"""
        frame_interval = 1.0 / max(self.fps, 0.1)

        while self.streaming:
            frame_start = time.time()
            try:
                # mss is faster/more stable for continuous capture on Windows.
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    raw = sct.grab(monitor)
                    screenshot = Image.frombytes("RGB", raw.size, raw.rgb)

                screenshot = screenshot.resize((self.screen_width, self.screen_height), Image.Resampling.LANCZOS)

                img_bytes = io.BytesIO()
                screenshot.save(
                    img_bytes,
                    format='JPEG',
                    quality=self.quality,
                    optimize=True,
                    progressive=False
                )
                image_data = img_bytes.getvalue()

                # Keep only latest frame in queue.
                try:
                    self.image_queue.put_nowait(image_data)
                except queue.Full:
                    try:
                        self.image_queue.get_nowait()
                        self.image_queue.put_nowait(image_data)
                    except:
                        pass

            except Exception as e:
                print(f"[SCREEN] Capture error: {e}")

            elapsed = time.time() - frame_start
            sleep_time = max(0.05, frame_interval - elapsed)
            time.sleep(sleep_time)
    
    def stream_to_teacher(self):
        """Stream captured images to teacher"""
        while self.streaming:
            try:
                # Get image from queue
                image_data = self.image_queue.get(timeout=5.0)
                
                if not self.streaming:
                    break
                
                # Send to teacher
                self.send_screen_data(image_data)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[SCREEN] Streaming error: {e}")
                break
    
    def send_screen_data(self, image_data):
        """Send screen data to teacher - FIXED VERSION"""
        if server.connected and server.sock:
            try:
                data_length = len(image_data)
                
                # CRITICAL FIX: Use LITTLE ENDIAN (Windows standard)
                length_bytes = data_length.to_bytes(4, 'little', signed=False)
                
                # Send length THEN image
                server.sock.sendall(length_bytes)  # Use sendall for reliability
                server.sock.sendall(image_data)
                
            except Exception as e:
                print(f"[SCREEN] Send error: {e}")
                self.stop_streaming()

# Global instance
screen_streamer = ScreenStreamer()