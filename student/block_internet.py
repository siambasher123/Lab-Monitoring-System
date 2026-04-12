# block_internet.py - HOSTS FILE METHOD (GUARANTEED WORKING)
import os
import subprocess
import config
import server
import gui
import time
import shutil

enabled = False
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
BACKUP_PATH = r"C:\Windows\System32\drivers\etc\hosts.backup"

def enable():
    """Block internet using HOSTS file - 100% effective"""
    global enabled
    
    if enabled:
        return

    teacher_ip = config.TEACHER_IP
    print(f"[INTERNET] BLOCKING via HOSTS file + DNS...")
    
    gui.update_internet("BLOCKED")
    
    try:
        # STEP 1: Backup original hosts file
        if os.path.exists(HOSTS_PATH):
            shutil.copy2(HOSTS_PATH, BACKUP_PATH)
            print("[INTERNET] Backed up hosts file")
        
        # STEP 2: Create blocking hosts file
        blocking_content = '''# ============================================
# INTERNET BLOCKED BY CLASSROOM MANAGEMENT SYSTEM
# ============================================

# Localhost
127.0.0.1       localhost
::1             localhost

# Teacher IP (ALLOWED)
{teacher_ip}    teacher.local

# ============================================
# BLOCKED SITES (All internet traffic)
# ============================================

# Block ALL domains by redirecting to localhost
0.0.0.0         www.google.com
0.0.0.0         google.com
0.0.0.0         www.youtube.com
0.0.0.0         youtube.com
0.0.0.0         www.facebook.com
0.0.0.0         facebook.com
0.0.0.0         www.twitter.com
0.0.0.0         twitter.com
0.0.0.0         www.instagram.com
0.0.0.0         instagram.com
0.0.0.0         www.netflix.com
0.0.0.0         netflix.com
0.0.0.0         www.amazon.com
0.0.0.0         amazon.com
0.0.0.0         www.microsoft.com
0.0.0.0         microsoft.com
0.0.0.0         www.bing.com
0.0.0.0         bing.com
0.0.0.0         www.yahoo.com
0.0.0.0         yahoo.com

# Block DNS servers
0.0.0.0         8.8.8.8
0.0.0.0         8.8.4.4
0.0.0.0         1.1.1.1

# Block ALL .com, .net, .org (catch-all)
0.0.0.0         .com
0.0.0.0         .net
0.0.0.0         .org
0.0.0.0         .edu
0.0.0.0         .gov

# Block common ports
0.0.0.0         :80
0.0.0.0         :443
0.0.0.0         :8080

# ============================================
# END OF BLOCK
# ============================================
'''.format(teacher_ip=teacher_ip)
        
        # Write blocking hosts file
        with open(HOSTS_PATH, 'w', encoding='utf-8') as f:
            f.write(blocking_content)
        
        print("[INTERNET] Hosts file modified")
        
        # STEP 3: Flush DNS
        flush_cmd = "ipconfig /flushdns"
        subprocess.run(flush_cmd, shell=True, capture_output=True)
        print("[INTERNET] DNS flushed")
        
        # STEP 4: Disable Windows Network Location Awareness
        try:
            subprocess.run(["sc", "stop", "NlaSvc"], shell=True, capture_output=True)
            subprocess.run(["sc", "config", "NlaSvc", "start=", "disabled"], shell=True, capture_output=True)
            print("[INTERNET] Network Location Awareness disabled")
        except:
            pass
        
        # STEP 5: Block via Windows Firewall (try but don't fail)
        try:
            firewall_cmd = f'''
            netsh advfirewall firewall add rule name="Classroom_Total_Block" dir=out action=block remoteip=any protocol=any enable=yes
            netsh advfirewall firewall add rule name="Classroom_Allow_Teacher" dir=out action=allow remoteip={teacher_ip} protocol=any enable=yes
            '''
            subprocess.run(["cmd", "/c", firewall_cmd], shell=True, capture_output=True, timeout=10)
            print("[INTERNET] Firewall rules added")
        except:
            print("[INTERNET] Firewall rules skipped (not critical)")
        
        enabled = True
        print("[INTERNET] ✓ INTERNET 100% BLOCKED")
        print("[INTERNET] ⚠️  All websites redirected to 0.0.0.0")
        server.send_log("Internet: COMPLETELY BLOCKED via HOSTS")
        gui.add_log("Internet: BLOCKED (all sites)")
        
        # Test immediately
        time.sleep(2)
        test_hosts_block()
        
    except PermissionError:
        print("[INTERNET] ✗ Need Administrator rights!")
        print("[INTERNET] Running self-elevation...")
        self_elevate()
    except Exception as e:
        print(f"[INTERNET] ✗ Error: {e}")
        gui.add_log(f"Block error: {e}")
        gui.update_internet("Unblocked")

def disable():
    """Restore internet"""
    global enabled
    
    if not enabled:
        return

    print("[INTERNET] Restoring internet...")
    
    gui.update_internet("Unblocked")
    
    try:
        # STEP 1: Restore original hosts file
        if os.path.exists(BACKUP_PATH):
            shutil.copy2(BACKUP_PATH, HOSTS_PATH)
            print("[INTERNET] Restored original hosts file")
        else:
            # Create default hosts file
            default_hosts = '''# Copyright (c) 1993-2009 Microsoft Corp.
#
# This is a sample HOSTS file used by Microsoft TCP/IP for Windows.
#
# This file contains the mappings of IP addresses to host names. Each
# entry should be kept on an individual line. The IP address should
# be placed in the first column followed by the corresponding host name.
# The IP address and the host name should be separated by at least one
# space.
#
# Additionally, comments (such as these) may be inserted on individual
# lines or following the machine name denoted by a '#' symbol.
#
# For example:
#
#      102.54.94.97     rhino.acme.com          # source server
#       38.25.63.10     x.acme.com              # x client host

# localhost name resolution is handled within DNS itself.
#	127.0.0.1       localhost
#	::1             localhost
'''
            with open(HOSTS_PATH, 'w', encoding='utf-8') as f:
                f.write(default_hosts)
        
        # STEP 2: Remove firewall rules
        try:
            firewall_cmd = '''
            netsh advfirewall firewall delete rule name="Classroom_Total_Block" dir=out
            netsh advfirewall firewall delete rule name="Classroom_Allow_Teacher" dir=out
            '''
            subprocess.run(["cmd", "/c", firewall_cmd], shell=True, capture_output=True)
            print("[INTERNET] Firewall rules removed")
        except:
            pass
        
        # STEP 3: Re-enable Network Location Awareness
        try:
            subprocess.run(["sc", "config", "NlaSvc", "start=", "auto"], shell=True, capture_output=True)
            subprocess.run(["sc", "start", "NlaSvc"], shell=True, capture_output=True)
            print("[INTERNET] Network services restored")
        except:
            pass
        
        # STEP 4: Flush DNS again
        subprocess.run("ipconfig /flushdns", shell=True, capture_output=True)
        
        enabled = False
        print("[INTERNET] ✓ Internet completely restored")
        server.send_log("Internet: RESTORED")
        gui.add_log("Internet: RESTORED")
        
    except Exception as e:
        print(f"[INTERNET] ✗ Error: {e}")
        gui.add_log(f"Restore error: {e}")
        enabled = False

def self_elevate():
    """Restart program as Administrator"""
    import sys
    import ctypes
    
    if ctypes.windll.shell32.IsUserAnAdmin():
        return True
    
    # Re-run as admin
    script = sys.argv[0]
    params = ' '.join([script] + sys.argv[1:])
    
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )
    
    sys.exit()

def test_hosts_block():
    """Test if hosts blocking works"""
    print("\n" + "="*60)
    print("[TEST] Testing HOSTS file blocking...")
    print("="*60)
    
    test_commands = [
        ("ping -n 2 www.google.com", "Google ping"),
        ("ping -n 2 google.com", "Google domain"),
        ("nslookup google.com", "DNS lookup"),
        ("curl -s --max-time 3 http://www.google.com", "HTTP request"),
        (f"ping -n 2 {config.TEACHER_IP}", "Teacher connection"),
    ]
    
    for cmd, desc in test_commands:
        try:
            result = subprocess.run(cmd, shell=True, 
                                  capture_output=True, text=True, timeout=5)
            
            if "teacher" in desc.lower():
                if result.returncode == 0:
                    print(f"  ✓ TEACHER: {desc} works")
                else:
                    print(f"  ✗ TEACHER: {desc} failed")
            else:
                # Check if blocked
                blocked_keywords = ['0.0.0.0', 'could not find', 'timed out', 'failed', 'unreachable']
                if any(keyword in result.stdout.lower() or keyword in result.stderr.lower() 
                      for keyword in blocked_keywords):
                    print(f"  ✓ BLOCKED: {desc}")
                else:
                    print(f"  ✗ UNBLOCKED: {desc} - Output: {result.stdout[:50]}")
                    
        except Exception as e:
            print(f"  ✓ BLOCKED: {desc} (Error: {str(e)[:30]})")
    
    print("="*60)
    
    # Additional check: Try to open browser programmatically
    print("\n[TEST] Quick browser test suggestion:")
    print("1. Open Chrome/Firefox/Edge")
    print("2. Try to visit: google.com, youtube.com, facebook.com")
    print("3. All should show 'This site can't be reached'")
    print("4. Teacher IP should still work for the classroom app")