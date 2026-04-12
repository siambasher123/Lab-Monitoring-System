# config.py - UNIVERSAL (Works with or without internet)
import json
import os
import socket
import time
import subprocess
import threading

# Set TEST_MODE = True -> hardcoded values for testing
TEST_MODE = True                   
TEST_TEACHER_IP = "192.168.0.102"   
TEST_MACHINE_NUM = 1              

DEFAULT_PORT = 5000
CONFIG_FILE = "student_config.json"
INTERNET_CHECK_INTERVAL = 30  # Check internet status every 30 seconds

# Global internet status
_internet_available = None
_last_internet_check = 0

def load_config():
    """Load configuration"""
    if TEST_MODE:
        print(f"⚙️ TEST MODE: Teacher IP = {TEST_TEACHER_IP}, Machine = {TEST_MACHINE_NUM}")
        return {
            "teacher_ip": TEST_TEACHER_IP,
            "machine_number": TEST_MACHINE_NUM,
            "port": DEFAULT_PORT,
            "student_name": f"Student_{TEST_MACHINE_NUM:02d}",
            "setup_complete": True,
            "mode": "test"
        }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                config["mode"] = "popup"
                return config
        except:
            pass
    
    return {
        "teacher_ip": None,
        "machine_number": None,
        "port": DEFAULT_PORT,
        "student_name": None,
        "setup_complete": False,
        "mode": "popup"
    }

def save_config(teacher_ip, machine_num):
    """Save configuration to file"""
    config = {
        "teacher_ip": teacher_ip.strip(),
        "machine_number": int(machine_num),
        "port": DEFAULT_PORT,
        "student_name": f"Student_{int(machine_num):02d}",
        "setup_complete": True,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "popup"
    }
    
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False

_config = load_config()

TEACHER_IP = _config["teacher_ip"]
MACHINE_NUMBER = _config["machine_number"]
PORT = _config["port"]
STUDENT_NAME = _config["student_name"]
SETUP_COMPLETE = _config["setup_complete"]
CURRENT_MODE = _config["mode"]

def check_internet():
    """Check if internet is available (cached to avoid constant checks)"""
    global _internet_available, _last_internet_check
    
    current_time = time.time()
    if _internet_available is not None and (current_time - _last_internet_check) < INTERNET_CHECK_INTERVAL:
        return _internet_available
    
    # Try multiple methods
    methods = [
        lambda: _check_dns("8.8.8.8"),
        lambda: _check_dns("1.1.1.1"),
        lambda: _check_http("http://www.google.com"),
        lambda: _check_http("http://www.microsoft.com"),
        lambda: _check_ping("8.8.8.8")
    ]
    
    for method in methods:
        try:
            if method():
                _internet_available = True
                _last_internet_check = current_time
                return True
        except:
            continue
    
    _internet_available = False
    _last_internet_check = current_time
    return False

def _check_dns(ip):
    """Check if DNS is reachable"""
    try:
        socket.gethostbyaddr(ip)
        return True
    except:
        return False

def _check_http(url):
    """Check if HTTP request works"""
    try:
        import urllib.request
        urllib.request.urlopen(url, timeout=3)
        return True
    except:
        return False

def _check_ping(ip):
    """Check if ping works"""
    try:
        param = '-n' if os.name == 'nt' else '-c'
        result = subprocess.run(['ping', param, '1', ip], 
                              capture_output=True, timeout=3)
        return result.returncode == 0
    except:
        return False

def get_my_ip():
    """Get local IP address - WORKS WITH OR WITHOUT INTERNET"""
    ips = []
    
    # Method 1: Get from hostname (always works)
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip and not local_ip.startswith('127.'):
            ips.append(("hostname", local_ip))
    except:
        pass
    
    # Method 2: Use ipconfig (Windows)
    try:
        result = subprocess.run(['ipconfig'], capture_output=True, text=True)
        output = result.stdout
        
        import re
        ip_pattern = r'IPv4 Address[ .]+: (\d+\.\d+\.\d+\.\d+)'
        matches = re.findall(ip_pattern, output)
        
        for ip in matches:
            if ip.startswith(('192.168.', '10.', '172.')):
                ips.append(("ipconfig", ip))
    except:
        pass
    
    # Method 3: Connect to router (works offline)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        router_ips = ["192.168.1.1", "192.168.0.1", "10.0.0.1"]
        for router_ip in router_ips:
            try:
                s.connect((router_ip, 80))
                ip = s.getsockname()[0]
                s.close()
                if ip and not ip.startswith('127.'):
                    ips.append(("router", ip))
                break
            except:
                continue
    except:
        pass
    
    # Method 4: Connect to internet (if available)
    if check_internet():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith('127.'):
                ips.append(("internet", ip))
        except:
            pass
    
    # Method 5: Use netifaces if available
    try:
        import netifaces2 as netifaces
        interfaces = netifaces.interfaces()
        for iface in interfaces:
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    if ip.startswith(('192.168.', '10.', '172.')):
                        ips.append(("netifaces", ip))
    except ImportError:
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

def get_network_status():
    """Get comprehensive network status"""
    status = {
        "internet": check_internet(),
        "local_ip": get_my_ip(),
        "teacher_reachable": False,
        "connection_type": "Unknown"
    }
    
    # Check if teacher is reachable (LAN)
    try:
        result = subprocess.run(['ping', '-n', '1', TEACHER_IP], 
                              capture_output=True, text=True, timeout=2)
        status["teacher_reachable"] = "Reply from" in result.stdout
    except:
        pass
    
    # Determine connection type
    if status["internet"]:
        status["connection_type"] = "Internet + LAN"
    elif status["teacher_reachable"]:
        status["connection_type"] = "LAN Only"
    else:
        status["connection_type"] = "No Connection"
    
    return status

def validate_config():
    """Check if configuration is valid"""
    if not SETUP_COMPLETE:
        return False, "Setup not complete"
    
    if not TEACHER_IP:
        return False, "Teacher IP not set"
    
    if not MACHINE_NUMBER:
        return False, "Machine number not set"
    
    try:
        socket.inet_aton(TEACHER_IP)
    except socket.error:
        return False, f"Invalid teacher IP: {TEACHER_IP}"
    
    if not (1 <= MACHINE_NUMBER <= 30):
        return False, f"Invalid machine number: {MACHINE_NUMBER} (must be 1-30)"
    
    return True, "Configuration valid"

def print_config_summary():
    """Print current configuration with network status"""
    print("=" * 60)
    print("STUDENT CONFIGURATION")
    print("=" * 60)
    print(f"Mode: {CURRENT_MODE.upper()}")
    print(f"Teacher IP: {TEACHER_IP}")
    print(f"Machine Number: {MACHINE_NUMBER}")
    print(f"Student Name: {STUDENT_NAME}")
    print(f"Port: {PORT}")
    
    # Get network status
    status = get_network_status()
    print(f"\n📡 NETWORK STATUS:")
    print(f"   Local IP: {status['local_ip']}")
    print(f"   Internet: {'✅ Connected' if status['internet'] else '❌ Disconnected'}")
    print(f"   Teacher Reachable: {'✅ Yes' if status['teacher_reachable'] else '❌ No'}")
    print(f"   Connection Type: {status['connection_type']}")
    print("=" * 60)

# Print config when module loads
if __name__ == "__main__":
    print_config_summary()
    valid, msg = validate_config()
    print(f"Valid: {valid} - {msg}")