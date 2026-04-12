# setup.py - FIRST-RUN SETUP (for when TEST_MODE = False)
import tkinter as tk
from tkinter import ttk, messagebox
import socket
import config

def show_setup_window():
    """Show setup window for first-time configuration"""
    
    def validate_ip(ip):
        """Validate IP address format"""
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False
    
    def on_save():
        teacher_ip = ip_entry.get().strip()
        machine_num = machine_entry.get().strip()
        
        # Validation
        if not teacher_ip:
            messagebox.showerror("Error", "Please enter Teacher IP address!")
            return False
        
        if not validate_ip(teacher_ip):
            messagebox.showerror("Error", f"Invalid IP address: {teacher_ip}")
            return False
        
        if not machine_num.isdigit():
            messagebox.showerror("Error", "Machine number must be a number!")
            return False
        
        machine_num = int(machine_num)
        if not (1 <= machine_num <= 30):
            messagebox.showerror("Error", "Machine number must be between 1 and 30!")
            return False
        
        # Save configuration
        if config.save_config(teacher_ip, machine_num):
            messagebox.showinfo("Success", 
                f"✅ Setup Complete!\n\n"
                f"Machine Number: {machine_num}\n"
                f"Teacher IP: {teacher_ip}\n\n"
                f"Student agent will now start.")
            return True
        else:
            messagebox.showerror("Error", "Failed to save configuration!")
            return False
    
    # Create setup window
    setup_win = tk.Tk()
    setup_win.title("Classroom Agent - First Time Setup")
    setup_win.geometry("450x350")
    setup_win.resizable(False, False)
    
    # Center window
    setup_win.eval('tk::PlaceWindow . center')
    
    # Title
    title = ttk.Label(setup_win, text="📋 First Time Setup", 
                     font=("Arial", 16, "bold"))
    title.pack(pady=20)
    
    # Teacher IP
    ttk.Label(setup_win, text="Teacher Computer IP Address:", 
             font=("Arial", 10)).pack(anchor="w", padx=40, pady=5)
    
    ip_var = tk.StringVar()
    ip_entry = ttk.Entry(setup_win, textvariable=ip_var, width=25,
                        font=("Arial", 10))
    ip_entry.pack()
    ttk.Label(setup_win, text="Example: 192.168.1.100", 
             font=("Arial", 8), foreground="gray").pack()
    
    # Machine Number
    ttk.Label(setup_win, text="Your Machine Number (1-30):", 
             font=("Arial", 10)).pack(anchor="w", padx=40, pady=15)
    
    machine_var = tk.StringVar()
    machine_entry = ttk.Entry(setup_win, textvariable=machine_var, width=10,
                             font=("Arial", 10))
    machine_entry.pack()
    
    # Save button
    btn_frame = ttk.Frame(setup_win)
    btn_frame.pack(pady=30)
    
    saved = [False]  # Using list to modify in nested function
    
    def save_and_close():
        if on_save():
            saved[0] = True
            setup_win.destroy()
    
    ttk.Button(btn_frame, text="🚀 Save & Start", 
              command=save_and_close, width=20).pack()
    
    # Set focus
    ip_entry.focus()
    
    # Run window
    setup_win.mainloop()
    
    return saved[0]