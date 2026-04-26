# screen_stream.py - Student side screen streaming
import threading
import time
import io
import queue
from PIL import ImageGrab
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
        self.quality = 15  # VERY LOW quality
        self.fps = 0.5  # 1 frame every 2 seconds
        self.screen_width = 600
        self.screen_height = 300
        
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
        try:
            from PIL import ImageGrab
            
            while self.streaming:
                try:
                    # SIMPLE CAPTURE: Use ImageGrab directly
                    screenshot = ImageGrab.grab()
                    
                    # Resize to 600x300
                    screenshot = screenshot.resize((self.screen_width, self.screen_height))
                    
                    # Convert to bytes with VERY LOW quality
                    img_bytes = io.BytesIO()
                    screenshot.save(img_bytes, format='JPEG', quality=self.quality, optimize=True)
                    image_data = img_bytes.getvalue()
                    
                    print(f"[SCREEN] Captured {len(image_data)} bytes")
                    
                    # Put in queue
                    try:
                        self.image_queue.put_nowait(image_data)
                    except queue.Full:
                        try:
                            self.image_queue.get_nowait()
                            self.image_queue.put_nowait(image_data)
                        except:
                            pass
                    
                    # Wait 2 seconds
                    time.sleep(2.0)
                    
                except Exception as e:
                    print(f"[SCREEN] Capture error: {e}")
                    time.sleep(2.0)
                    
        except ImportError:
            print("[SCREEN] ImageGrab not available")
    
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
                print(f"[SCREEN] Sending image: {data_length} bytes")
                
                # CRITICAL FIX: Use LITTLE ENDIAN (Windows standard)
                length_bytes = data_length.to_bytes(4, 'little', signed=False)
                
                # DEBUG: Verify bytes
                print(f"[SCREEN DEBUG] Length bytes hex: {length_bytes.hex()}")
                print(f"[SCREEN DEBUG] What teacher will read: {int.from_bytes(length_bytes, 'little')}")
                
                # Send length THEN image
                server.sock.sendall(length_bytes)  # Use sendall for reliability
                server.sock.sendall(image_data)
                
                print(f"[SCREEN] Sent successfully")
                
            except Exception as e:
                print(f"[SCREEN] Send error: {e}")
                self.stop_streaming()

# Global instance
screen_streamer = ScreenStreamer()