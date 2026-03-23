# teacher_config.py - Teacher side configuration with email settings
import json
import os
import socket
import time

CONFIG_FILE = "teacher_config.json"

# ===== TEST MODE FLAG =====
# Set TEST_MODE = True to bypass email configuration for testing
# Set TEST_MODE = False for production use with real emails
TEST_MODE = True  # Change to False when deploying

# Default email configuration (will be overridden by saved config)
DEFAULT_EMAIL_CONFIG = {
    "sender_email": "",
    "sender_password": "",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "configured": False
}

def load_config():
    """Load teacher configuration"""
    config = {
        "email": DEFAULT_EMAIL_CONFIG.copy(),
        "last_updated": None,
        "first_run": True
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved_config = json.load(f)
                config.update(saved_config)
                config["first_run"] = False
                print(f"✅ Loaded teacher config from {CONFIG_FILE}")
        except Exception as e:
            print(f"⚠️ Error loading config: {e}")
    
    return config

def save_email_config(sender_email, sender_password, smtp_server="smtp.gmail.com", smtp_port=587):
    """Save email configuration"""
    config = {
        "email": {
            "sender_email": sender_email,
            "sender_password": sender_password,
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "configured": True
        },
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "first_run": False
    }
    
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        print(f"✅ Email configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"❌ Failed to save config: {e}")
        return False

def get_email_config():
    """Get email configuration"""
    config = load_config()
    return config.get("email", DEFAULT_EMAIL_CONFIG.copy())

def is_configured():
    """Check if email is configured - respects TEST_MODE"""
    if TEST_MODE:
        # In test mode, pretend email is always configured
        return True
    config = load_config()
    return config.get("email", {}).get("configured", False)

def clear_config():
    """Clear saved configuration"""
    if os.path.exists(CONFIG_FILE):
        try:
            os.remove(CONFIG_FILE)
            print("✅ Configuration cleared")
            return True
        except:
            pass
    return False

def get_test_mode_status():
    """Get test mode status"""
    return TEST_MODE

# Load config on module import
_config = load_config()
EMAIL_CONFIG = _config.get("email", DEFAULT_EMAIL_CONFIG.copy())
FIRST_RUN = _config.get("first_run", True)

def print_config_summary():
    """Print current configuration"""
    print("=" * 60)
    print("TEACHER CONFIGURATION")
    print("=" * 60)
    
    # Show test mode status
    if TEST_MODE:
        print("🔧 TEST MODE: ACTIVE")
        print("   Email checks bypassed for testing\n")
    
    if EMAIL_CONFIG.get("configured"):
        print("📧 Email Configuration:")
        print(f"   Sender Email: {EMAIL_CONFIG['sender_email']}")
        print(f"   SMTP Server: {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
        print(f"   Status: ✅ Configured")
    else:
        print("📧 Email Configuration: ❌ Not configured")
        if not TEST_MODE:
            print("   Run teacher app to configure email settings")
        else:
            print("   (Test mode active - emails not required)")
    
    if _config.get("last_updated"):
        print(f"\n🕒 Last Updated: {_config['last_updated']}")
    
    print("=" * 60)

# Print config when module loads
if __name__ == "__main__":
    print_config_summary()