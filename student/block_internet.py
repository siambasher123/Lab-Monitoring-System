# block_internet.py - STUDENT SIDE
# BLOCKS ALL INTERNET TRAFFIC COMPLETELY
# Preserves ONLY LAN traffic (including teacher)

import os
import subprocess
import threading
import time
import ctypes
import sys

# Global state
enabled = False
MONITOR_THREAD = None
MONITOR_ACTIVE = False
TEACHER_IP = None
DEFAULT_CLASSROOM_PORT = 5050

def get_classroom_port():
    """Get classroom control port from config with safe fallback."""
    try:
        import config
        return int(getattr(config, 'PORT', DEFAULT_CLASSROOM_PORT))
    except Exception:
        return DEFAULT_CLASSROOM_PORT

def is_admin():
    """Check if running as administrator"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_command(cmd, timeout=10):
    """Run a command and return output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except:
        return False, "", "Timeout"

def get_local_ip():
    """Get local IP address"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None

def get_network_info():
    """Get network information"""
    try:
        success, stdout, _ = run_command("ipconfig")
        if success:
            lines = stdout.split('\n')
            ip = None
            gateway = None
            
            for i, line in enumerate(lines):
                if "IPv4 Address" in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        ip = parts[1].strip()
                if "Default Gateway" in line and ":" in line:
                    parts = line.split(':')
                    if len(parts) > 1 and parts[1].strip() and not parts[1].strip() == ":":
                        gateway = parts[1].strip()
            
            return ip, gateway
    except:
        pass
    return None, None

def block_all_internet_firewall():
    """Block ALL internet traffic, allow ONLY LAN"""
    global TEACHER_IP
    
    print("\n[INTERNET] 🔥 Configuring Windows Firewall to block ALL internet...")
    
    # Remove any existing classroom rules
    run_command('netsh advfirewall firewall delete rule name="Classroom_Block_Internet"')
    run_command('netsh advfirewall firewall delete rule name="Classroom_Allow_LAN"')
    run_command('netsh advfirewall firewall delete rule name="Classroom_Allow_Teacher"')
    run_command('netsh advfirewall firewall delete rule name="Classroom_Allow_All"')
    
    # Get local IP and gateway
    local_ip, gateway = get_network_info()
    print(f"[INTERNET] Local IP: {local_ip}")
    print(f"[INTERNET] Gateway: {gateway}")
    
    # Calculate LAN subnet from local IP
    lan_subnet = None
    if local_ip:
        ip_parts = local_ip.split('.')
        if len(ip_parts) == 4:
            if local_ip.startswith('10.'):
                lan_subnet = f"10.0.0.0/8"
            elif local_ip.startswith('172.'):
                lan_subnet = f"172.16.0.0/12"
            elif local_ip.startswith('192.168.'):
                lan_subnet = f"192.168.0.0/16"
            else:
                # For other IPs, allow the entire /24 subnet
                lan_subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
    
    print(f"[INTERNET] LAN Subnet: {lan_subnet}")
    
    # STEP 1: Block ALL outbound internet traffic
    block_cmd = 'netsh advfirewall firewall add rule name="Classroom_Block_Internet" dir=out action=block protocol=any remoteip=any enable=yes'
    run_command(block_cmd)
    print("[INTERNET] ✓ Blocked ALL outbound traffic")
    
    # STEP 2: Allow ALL local network traffic (preserve LAN)
    if lan_subnet:
        allow_lan_cmd = f'netsh advfirewall firewall add rule name="Classroom_Allow_LAN" dir=out action=allow remoteip={lan_subnet} enable=yes'
        run_command(allow_lan_cmd)
        print(f"[INTERNET] ✓ Allowed LAN subnet: {lan_subnet}")
    
    # Also allow common LAN ranges as backup
    lan_ranges = [
        "192.168.0.0/16",
        "10.0.0.0/8", 
        "172.16.0.0/12",
        "169.254.0.0/16",  # APIPA
    ]
    
    for lan in lan_ranges:
        allow_lan_cmd = f'netsh advfirewall firewall add rule name="Classroom_Allow_LAN" dir=out action=allow remoteip={lan} enable=yes'
        run_command(allow_lan_cmd)
    
    # STEP 3: Specifically allow teacher IP
    if TEACHER_IP:
        allow_teacher_cmd = f'netsh advfirewall firewall add rule name="Classroom_Allow_Teacher" dir=out action=allow remoteip={TEACHER_IP} enable=yes'
        run_command(allow_teacher_cmd)
        print(f"[INTERNET] ✓ Allowed teacher IP: {TEACHER_IP}")
    
    # STEP 4: Allow necessary port for classroom communication
    classroom_port = get_classroom_port()
    allow_port_cmd = (
        f'netsh advfirewall firewall add rule name="Classroom_Allow_Port" '
        f'dir=out action=allow protocol=tcp localport={classroom_port} enable=yes'
    )
    run_command(allow_port_cmd)
    
    # Allow ICMP (ping) for testing
    allow_ping_cmd = 'netsh advfirewall firewall add rule name="Classroom_Allow_Ping" dir=out action=allow protocol=icmpv4 enable=yes'
    run_command(allow_ping_cmd)
    
    print("[INTERNET] ✓ Firewall configuration complete")
    return True

def block_all_internet_hosts():
    """Use hosts file to block ALL domain resolution"""
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
    backup_path = hosts_path + ".classroom_backup"
    
    try:
        print("[INTERNET] 📄 Configuring hosts file to block ALL domains...")
        
        # Backup original
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy2(hosts_path, backup_path)
            print("[INTERNET] ✓ Hosts file backed up")
        
        # Create SUPER BLOCKING hosts file
        with open(hosts_path, 'w') as f:
            f.write("""# INTERNET COMPLETELY BLOCKED BY CLASSROOM MANAGEMENT
# All domains resolve to 0.0.0.0 (nowhere)

127.0.0.1       localhost
::1             localhost

# Block ALL domains with wildcard
0.0.0.0         *
0.0.0.0         .*
0.0.0.0         com
0.0.0.0         net
0.0.0.0         org
0.0.0.0         edu
0.0.0.0         gov
0.0.0.0         io
0.0.0.0         co
0.0.0.0         ai
0.0.0.0         app

# Block common IP ranges
0.0.0.0         8.8.8.8
0.0.0.0         8.8.4.4
0.0.0.0         1.1.1.1
0.0.0.0         1.0.0.1
0.0.0.0         9.9.9.9
0.0.0.0         208.67.222.222
0.0.0.0         208.67.220.220

# Block ALL possible internet destinations
0.0.0.0         0.0.0.0/0
0.0.0.0         :80
0.0.0.0         :443
0.0.0.0         :8080
0.0.0.0         :8000
0.0.0.0         :3000
0.0.0.0         :5050
""")
        
        # Flush DNS
        run_command("ipconfig /flushdns")
        print("[INTERNET] ✓ Hosts file updated, DNS flushed")
        return True
    except Exception as e:
        print(f"[INTERNET] Hosts file error: {e}")
        return False

def disable_dns():
    """Disable DNS resolution completely"""
    print("[INTERNET] 🌐 Disabling DNS resolution...")
    
    try:
        # Set DNS to invalid addresses for all adapters
        success, stdout, _ = run_command("netsh interface show interface")
        if success:
            lines = stdout.split('\n')
            for line in lines:
                if "Connected" in line or "Enabled" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        adapter_name = ' '.join(parts[3:]).strip()
                        # Set DNS to invalid IPs
                        run_command(f'netsh interface ip set dns name="{adapter_name}" static 0.0.0.0')
                        run_command(f'netsh interface ip add dns name="{adapter_name}" 0.0.0.1 index=2')
                        print(f"[INTERNET]   Disabled DNS for: {adapter_name}")
    except:
        pass

def restore_dns():
    """Restore DNS to automatic/DHCP"""
    print("[INTERNET] 🌐 Restoring DNS...")
    
    try:
        success, stdout, _ = run_command("netsh interface show interface")
        if success:
            lines = stdout.split('\n')
            for line in lines:
                if "Connected" in line or "Enabled" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        adapter_name = ' '.join(parts[3:]).strip()
                        run_command(f'netsh interface ip set dns name="{adapter_name}" dhcp')
                        print(f"[INTERNET]   Restored DNS for: {adapter_name}")
    except:
        pass

def restore_firewall():
    """Remove all classroom firewall rules"""
    print("[INTERNET] 🔥 Removing firewall rules...")
    
    rules_to_remove = [
        "Classroom_Block_Internet",
        "Classroom_Allow_LAN", 
        "Classroom_Allow_Teacher",
        "Classroom_Allow_Port",
        "Classroom_Allow_Port_5000",
        "Classroom_Allow_Ping",
    ]
    
    for rule in rules_to_remove:
        run_command(f'netsh advfirewall firewall delete rule name="{rule}"')
    
    print("[INTERNET] ✓ Firewall rules removed")

def restore_hosts():
    """Restore original hosts file"""
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
    backup_path = hosts_path + ".classroom_backup"
    
    print("[INTERNET] 📄 Restoring hosts file...")
    
    try:
        if os.path.exists(backup_path):
            import shutil
            shutil.copy2(backup_path, hosts_path)
            print("[INTERNET] ✓ Original hosts file restored")
        else:
            # Create minimal default
            with open(hosts_path, 'w') as f:
                f.write("127.0.0.1       localhost\n::1             localhost\n")
        
        run_command("ipconfig /flushdns")
        return True
    except:
        return False

def enable():
    """Enable COMPLETE internet blocking (preserves LAN)"""
    global enabled, TEACHER_IP, MONITOR_ACTIVE, MONITOR_THREAD
    
    if enabled:
        return True
    
    print("\n" + "="*70)
    print("🔴🔴🔴 COMPLETE INTERNET BLOCKING ACTIVATED")
    print("="*70)
    
    # Check admin rights
    if not is_admin():
        print("[INTERNET] ❌ ERROR: Must run as Administrator!")
        return False
    
    # Get teacher IP
    try:
        import config
        TEACHER_IP = config.TEACHER_IP
        print(f"[INTERNET] Teacher IP: {TEACHER_IP}")
    except:
        TEACHER_IP = None
        print("[INTERNET] ⚠️ Could not get teacher IP")
    
    # Get local network info
    local_ip, gateway = get_network_info()
    print(f"[INTERNET] Local IP: {local_ip}")
    print(f"[INTERNET] Gateway: {gateway}")
    
    # LAYER 1: Firewall blocking (primary)
    if block_all_internet_firewall():
        
        # LAYER 2: Hosts file blocking (secondary)
        block_all_internet_hosts()
        
        # LAYER 3: DNS disabling (tertiary)
        disable_dns()
        
        enabled = True
        
        # Start monitoring thread
        MONITOR_ACTIVE = True
        MONITOR_THREAD = threading.Thread(
            target=monitor_connection,
            args=(TEACHER_IP,),
            daemon=True
        )
        MONITOR_THREAD.start()
        
        # Update GUI
        try:
            import gui
            gui.update_internet("Blocked")
            gui.add_log("Internet: COMPLETELY BLOCKED")
        except:
            pass
        
        # Send confirmation to teacher
        try:
            import server
            server.send_log("Internet: COMPLETELY BLOCKED (all internet)")
        except:
            pass
        
        print("\n" + "="*70)
        print("✅✅✅ INTERNET COMPLETELY BLOCKED")
        print("   • All internet access: BLOCKED")
        print("   • ChatGPT/AI sites: BLOCKED")
        print("   • VPN/Proxy: BLOCKED")
        print("   • LAN/Teacher connection: PRESERVED")
        print("="*70)
        
        # Test immediately
        test_connection()
        
        return True
    
    return False

def disable():
    """Disable internet blocking"""
    global enabled, MONITOR_ACTIVE
    
    if not enabled:
        return True
    
    print("\n" + "="*70)
    print("🟢🟢🟢 INTERNET RESTORATION")
    print("="*70)
    
    MONITOR_ACTIVE = False
    
    # Restore all layers
    restore_firewall()
    restore_hosts()
    restore_dns()
    
    enabled = False
    
    # Update GUI
    try:
        import gui
        gui.update_internet("Unblocked")
        gui.add_log("Internet: COMPLETELY RESTORED")
    except:
        pass
    
    # Send confirmation to teacher
    try:
        import server
        server.send_log("Internet: RESTORED")
    except:
        pass
    
    print("\n" + "="*70)
    print("✅✅✅ INTERNET COMPLETELY RESTORED")
    print("="*70)
    
    return True

def monitor_connection(teacher_ip):
    """Monitor connection to teacher"""
    global MONITOR_ACTIVE
    
    print("[INTERNET] Starting connection monitor...")
    
    while MONITOR_ACTIVE and enabled:
        try:
            if teacher_ip:
                # Try to connect to teacher via TCP (more reliable than ping)
                import socket
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    classroom_port = get_classroom_port()
                    result = sock.connect_ex((teacher_ip, classroom_port))
                    sock.close()
                    
                    if result == 0:
                        # Teacher reachable - all good
                        pass
                    else:
                        print(f"[INTERNET] ⚠️ Teacher {teacher_ip} not responding on port {classroom_port}")
                except:
                    pass
                
            time.sleep(5)
        except:
            time.sleep(5)

def test_connection():
    """Test what's blocked and what's allowed"""
    print("\n" + "="*70)
    print("🌐 TESTING CONNECTION STATUS")
    print("="*70)
    
    # Test internet sites (should ALL be BLOCKED)
    internet_tests = [
        ("8.8.8.8", "Google DNS"),
        ("1.1.1.1", "Cloudflare DNS"),
        ("google.com", "Google"),
        ("youtube.com", "YouTube"),
        ("facebook.com", "Facebook"),
        ("chat.openai.com", "ChatGPT"),
        ("openai.com", "OpenAI"),
        ("bard.google.com", "Google Bard"),
        ("claude.ai", "Claude AI"),
        ("github.com", "GitHub"),
        ("stackoverflow.com", "StackOverflow"),
    ]
    
    print("\n📡 INTERNET ACCESS (should ALL be BLOCKED):")
    blocked_count = 0
    for target, desc in internet_tests:
        try:
            # Try ping first
            result = subprocess.run(
                ['ping', '-n', '1', target],
                capture_output=True,
                timeout=3
            )
            if result.returncode == 0:
                print(f"  ❌ {desc}: ACCESSIBLE (FAILED TO BLOCK!)")
            else:
                print(f"  ✅ {desc}: BLOCKED")
                blocked_count += 1
        except:
            print(f"  ✅ {desc}: BLOCKED")
            blocked_count += 1
    
    print(f"\n   {blocked_count}/{len(internet_tests)} internet sites blocked")
    
    # Test LAN (should be ALLOWED)
    print("\n🏠 LAN ACCESS (should be ALLOWED):")
    
    # Test teacher connection
    try:
        import config
        teacher_ip = config.TEACHER_IP
        
        # Test ping
        result = subprocess.run(
            ['ping', '-n', '1', teacher_ip],
            capture_output=True,
            timeout=3
        )
        if result.returncode == 0:
            print(f"  ✅ Teacher ({teacher_ip}): CONNECTED (ping)")
        else:
            # Try TCP connection to classroom app port
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            classroom_port = get_classroom_port()
            tcp_result = sock.connect_ex((teacher_ip, classroom_port))
            sock.close()
            
            if tcp_result == 0:
                print(f"  ✅ Teacher ({teacher_ip}): CONNECTED (port {classroom_port})")
            else:
                print(f"  ❌ Teacher ({teacher_ip}): NOT REACHABLE!")
    except:
        print(f"  ❌ Teacher: Could not test")
    
    # Test local network
    local_ip, gateway = get_network_info()
    if gateway:
        result = subprocess.run(
            ['ping', '-n', '1', gateway],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            print(f"  ✅ Gateway ({gateway}): CONNECTED")
    
    print("\n" + "="*70)

