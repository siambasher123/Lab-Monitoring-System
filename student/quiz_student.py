# quiz_student.py - Student quiz interface with proper exit on submit
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import config

class StudentQuiz:
    def __init__(self):
        self.window = None
        self.questions = []
        self.current_question = 0
        self.answers = {}
        self.quiz_active = False
        self.quiz_id = None
        self.duration = 0
        self.start_time = None
        self.marks_correct = 4
        self.marks_wrong = 1
        self.total_questions = 0
        self.student_number = None
        self.registration_complete = False
        self.auto_submit_triggered = False
        
        # GUI elements
        self.question_label = None
        self.options_vars = []
        self.timer_label = None
        self.progress_label = None
        self.submit_btn = None
        self.option_buttons = []
        self.main_frame = None
        self.question_frame = None
        self.options_frame = None
        self.next_btn = None
        
    def register_student(self):
        """Show registration window - only asks for roll number"""
        reg_window = tk.Toplevel()
        reg_window.title("📝 Quiz Registration")
        reg_window.geometry("600x600")
        reg_window.resizable(False, False)
        
        # Make it modal
        reg_window.transient()
        reg_window.grab_set()
        reg_window.focus_force()
        
        # Center window
        reg_window.update_idletasks()
        width = reg_window.winfo_width()
        height = reg_window.winfo_height()
        x = (reg_window.winfo_screenwidth() // 2) - (width // 2)
        y = (reg_window.winfo_screenheight() // 2) - (height // 2)
        reg_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Set style
        style = ttk.Style()
        style.configure('Register.TLabel', font=('Segoe UI', 11))
        style.configure('RegisterHeader.TLabel', font=('Segoe UI', 18, 'bold'))
        style.configure('Register.TButton', font=('Segoe UI', 11, 'bold'))
        
        # Main container with padding
        main_container = ttk.Frame(reg_window, padding=30)
        main_container.pack(fill="both", expand=True)
        
        # Header with icon
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(header_frame, text="📋", 
                 font=("Segoe UI", 40)).pack()
        
        ttk.Label(header_frame, text="Quiz Registration", 
                 style='RegisterHeader.TLabel').pack(pady=(10, 5))
        
        ttk.Label(header_frame, text="Please enter your roll number to begin",
                 font=("Segoe UI", 10), foreground="#666666").pack()
        
        # Separator
        ttk.Separator(main_container, orient='horizontal').pack(fill='x', pady=20)
        
        # Form frame
        form_frame = ttk.Frame(main_container)
        form_frame.pack(fill="both", expand=True)
        
        # Roll number (required)
        ttk.Label(form_frame, text="Roll Number / Student ID", 
                 style='Register.TLabel').pack(anchor="w", pady=(0, 5))
        
        student_num_var = tk.StringVar()
        student_entry = ttk.Entry(form_frame, textvariable=student_num_var,
                                 font=("Segoe UI", 12), width=30)
        student_entry.pack(fill="x", pady=(0, 20))
        student_entry.focus()
        
        # Info note
        info_frame = ttk.Frame(form_frame)
        info_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(info_frame, text="⚠️", font=("Segoe UI", 12)).pack(side="left", padx=(0, 5))
        ttk.Label(info_frame, text="You cannot exit the quiz once started", 
                 font=("Segoe UI", 9), foreground="#FF6B6B").pack(side="left")
        
        def submit_registration(event=None):
            student_num = student_num_var.get().strip()
            if not student_num:
                messagebox.showerror("Error", "Please enter your roll number!")
                return
                
            self.student_number = student_num
            self.student_name = f"Student_{student_num}"
            self.registration_complete = True
            reg_window.destroy()
            
            # Send registration to teacher
            try:
                import server
                server.send_log(f"Student {student_num} registered for quiz")
            except:
                pass
        
        # Button frame
        button_frame = ttk.Frame(form_frame)
        button_frame.pack(fill="x", pady=10)
        
        register_btn = ttk.Button(button_frame, text="✅ ENTER QUIZ",
                                 command=submit_registration, style='Register.TButton')
        register_btn.pack()
        
        # Bind Enter key to submit
        reg_window.bind('<Return>', submit_registration)
        student_entry.bind('<Return>', submit_registration)
        
        # Wait for registration
        reg_window.wait_window()
        
        return self.registration_complete
        
    def show_quiz(self, quiz_id, duration, q_per_student, marks_correct, marks_wrong):
        """Show quiz window with professional UI"""
        # First register if not done
        if not self.registration_complete:
            if not self.register_student():
                return False
                
        self.quiz_id = quiz_id
        self.duration = duration * 60  # Convert to seconds
        self.marks_correct = marks_correct
        self.marks_wrong = marks_wrong
        self.start_time = time.time()
        self.quiz_active = True
        self.auto_submit_triggered = False
        
        # Close any existing window
        if self.window and self.window.winfo_exists():
            self.window.destroy()
            
        # Create window
        self.window = tk.Toplevel()
        self.window.title(f"📝 Quiz - {self.student_number}")
        self.window.geometry("1000x700")
        
        # Make it fullscreen and always on top
        self.window.attributes('-fullscreen', True)
        self.window.attributes('-topmost', True)
        
        # Configure window to block alt+tab and other windows
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Bind keys to prevent leaving
        self.window.bind('<Alt-Tab>', lambda e: 'break')
        self.window.bind('<Alt-F4>', lambda e: 'break')
        self.window.bind('<Control-w>', lambda e: 'break')
        self.window.bind('<Control-q>', lambda e: 'break')
        self.window.bind('<Escape>', lambda e: 'break')
        self.window.bind('<F11>', lambda e: 'break')
        self.window.bind('<F4>', lambda e: 'break')
        
        # Configure styles
        style = ttk.Style()
        style.configure('Header.TLabel', font=('Segoe UI', 12))
        style.configure('Timer.TLabel', font=('Segoe UI', 16, 'bold'))
        style.configure('Question.TLabel', font=('Segoe UI', 14, 'bold'))
        style.configure('Option.TRadiobutton', font=('Segoe UI', 12), padding=5)
        style.configure('Submit.TButton', font=('Segoe UI', 14, 'bold'))
        style.configure('Next.TButton', font=('Segoe UI', 12, 'bold'))
        
        # Main container with padding
        self.main_frame = ttk.Frame(self.window, padding=30)
        self.main_frame.pack(fill="both", expand=True)
        
        # Header with gradient effect (simulated with frames)
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill="x", pady=(0, 25))
        
        # Left side - Student info
        info_frame = ttk.Frame(header_frame)
        info_frame.pack(side="left")
        
        ttk.Label(info_frame, text=f"Roll No: {self.student_number}",
                 style='Header.TLabel').pack(anchor="w")
        
        # Right side - Timer with background
        timer_container = ttk.Frame(header_frame)
        timer_container.pack(side="right")
        
        # Timer background frame
        timer_bg = tk.Frame(timer_container, bg="#2c3e50", bd=0, highlightthickness=2, highlightbackground="#3498db")
        timer_bg.pack(padx=10, pady=5)
        
        self.timer_label = ttk.Label(timer_bg, text="Time: 00:00",
                                     style='Timer.TLabel', foreground="#e74c3c")
        self.timer_label.pack(padx=20, pady=10)
        
        # Separator
        ttk.Separator(self.main_frame, orient='horizontal').pack(fill='x', pady=(0, 20))
        
        # Progress bar container
        progress_container = ttk.Frame(self.main_frame)
        progress_container.pack(fill="x", pady=(0, 20))
        
        # Progress label with styling
        self.progress_label = ttk.Label(progress_container, 
                                        text="Question 0/0",
                                        font=("Segoe UI", 12, "bold"),
                                        foreground="#2980b9")
        self.progress_label.pack(side="left")
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_container, 
                                           mode='determinate',
                                           length=200)
        self.progress_bar.pack(side="right")
        
        # Question frame with border
        self.question_frame = tk.Frame(self.main_frame, 
                                       bg="white",
                                       highlightbackground="#bdc3c7",
                                       highlightthickness=1,
                                       bd=0)
        self.question_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Question header
        q_header = tk.Frame(self.question_frame, bg="#f8f9fa", height=40)
        q_header.pack(fill="x")
        q_header.pack_propagate(False)
        
        tk.Label(q_header, text="QUESTION", 
                font=("Segoe UI", 11, "bold"),
                bg="#f8f9fa", fg="#2c3e50").pack(side="left", padx=15, pady=10)
        
        # Question number badge
        self.q_badge = tk.Label(q_header, text="1", 
                                font=("Segoe UI", 10, "bold"),
                                bg="#3498db", fg="white",
                                width=3, height=1)
        self.q_badge.pack(side="right", padx=15, pady=8)
        
        # Question content frame
        q_content = tk.Frame(self.question_frame, bg="white", padx=20, pady=20)
        q_content.pack(fill="both", expand=True)
        
        # Question text
        self.question_label = tk.Text(q_content, wrap="word", height=4,
                                     font=("Segoe UI", 13), 
                                     bg="white", fg="#2c3e50",
                                     bd=0, padx=10, pady=10)
        self.question_label.pack(fill="x", pady=(0, 20))
        self.question_label.config(state="disabled")
        
        # Options frame
        self.options_frame = tk.Frame(q_content, bg="white")
        self.options_frame.pack(fill="x")
        
        self.options_vars = [tk.StringVar() for _ in range(4)]
        self.option_buttons = []
        
        # Style for option buttons
        option_style = {
            'font': ('Segoe UI', 12),
            'bg': 'white',
            'activebackground': '#e8f4fd',
            'selectcolor': 'white'
        }
        
        for i, opt_var in enumerate(self.options_vars):
            # Create a frame for each option with hover effect
            opt_frame = tk.Frame(self.options_frame, bg="white")
            opt_frame.pack(fill="x", pady=5)
            
            # Radio button
            rb = tk.Radiobutton(opt_frame, text="", variable=opt_var,
                               value=chr(65 + i),  # A, B, C, D
                               command=self.save_answer,
                               **option_style)
            rb.pack(side="left", padx=10)
            
            # Option letter badge
            letter_badge = tk.Label(opt_frame, text=chr(65 + i),
                                   font=("Segoe UI", 10, "bold"),
                                   bg="#3498db" if i == 0 else "#2ecc71" if i == 1 else "#e74c3c" if i == 2 else "#f39c12",
                                   fg="white", width=2, height=1)
            letter_badge.pack(side="left", padx=(0, 10))
            
            self.option_buttons.append(rb)
        
        # Navigation and Submit frame
        nav_frame = ttk.Frame(self.main_frame)
        nav_frame.pack(fill="x", pady=(10, 0))
        
        # Next button (always visible)
        self.next_btn = ttk.Button(nav_frame, text="⏭️ NEXT QUESTION", 
                                   command=self.next_question,
                                   style='Next.TButton',
                                   width=20)
        self.next_btn.pack(side="right", padx=5)
        
        # Submit button (initially hidden, shown on last question)
        self.submit_btn = ttk.Button(nav_frame, text="✅ SUBMIT QUIZ", 
                                     command=self.submit_quiz,
                                     style='Submit.TButton',
                                     width=20)
        self.submit_btn.pack_forget()
        
        # Instructions
        ttk.Label(self.main_frame, 
                 text="⚠️ Note: Click NEXT to skip a question. You cannot go back to previous questions.",
                 font=("Segoe UI", 9), 
                 foreground="#e74c3c").pack(pady=(15, 0))
        
        # Start timer thread
        self.timer_thread = threading.Thread(target=self.update_timer, daemon=True)
        self.timer_thread.start()
        
        return True
        
    def add_question(self, q_data):
        """Add a question to the quiz"""
        parts = q_data.split('|')
        if len(parts) == 6:
            q_num = parts[0]
            q_text = parts[1]
            options = parts[2:6]
            
            question = {
                'number': q_num,
                'text': q_text,
                'options': options,
                'correct': None  # Student doesn't know correct answer
            }
            self.questions.append(question)
            self.total_questions = len(self.questions)
            
            # If this is the first question, display it
            if len(self.questions) == 1 and self.window and self.window.winfo_exists():
                self.display_question(0)
                
    def display_question(self, index):
        """Display a specific question"""
        if not self.questions or index >= len(self.questions):
            return
            
        q = self.questions[index]
        
        # Update question text
        self.question_label.config(state="normal")
        self.question_label.delete(1.0, tk.END)
        self.question_label.insert(1.0, f"{q['text']}")
        self.question_label.config(state="disabled")
        
        # Update question badge
        self.q_badge.config(text=str(index + 1))
        
        # Update options
        for i, opt_text in enumerate(q['options']):
            self.option_buttons[i].config(text=f" {opt_text}")
            
        # Restore previous answer if any
        saved_answer = self.answers.get(q['number'])
        if saved_answer:
            for i, opt_var in enumerate(self.options_vars):
                opt_var.set(saved_answer if chr(65 + i) == saved_answer else "")
        else:
            for opt_var in self.options_vars:
                opt_var.set("")
                
        # Update progress
        self.progress_label.config(text=f"Question {index + 1} of {self.total_questions}")
        self.progress_bar['value'] = ((index + 1) / self.total_questions) * 100
        
        # Show/hide submit button based on last question
        if index == self.total_questions - 1:
            self.submit_btn.pack(side="right", padx=5)
            self.next_btn.config(text="⏭️ FINAL QUESTION", state="disabled")
        else:
            self.submit_btn.pack_forget()
            self.next_btn.config(text="⏭️ NEXT QUESTION", state="normal")
            
        self.current_question = index
        
    def save_answer(self):
        """Save current answer"""
        if not self.questions or self.auto_submit_triggered:
            return
            
        q = self.questions[self.current_question]
        for opt_var in self.options_vars:
            answer = opt_var.get()
            if answer:
                self.answers[q['number']] = answer
                break
                
    def next_question(self):
        """Go to next question (skip if no answer)"""
        self.save_answer()  # Save if answered
        
        if self.current_question < len(self.questions) - 1:
            self.display_question(self.current_question + 1)
                
    def update_timer(self):
        """Update quiz timer"""
        while self.quiz_active and self.window and self.window.winfo_exists():
            elapsed = time.time() - self.start_time
            remaining = max(0, self.duration - elapsed)
            
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            
            # Update timer in main thread
            if self.window and self.window.winfo_exists():
                # Change color based on time remaining
                if remaining < 60:  # Last minute
                    color = "#e74c3c"  # Red
                elif remaining < 300:  # Last 5 minutes
                    color = "#f39c12"  # Orange
                else:
                    color = "#27ae60"  # Green
                    
                self.window.after(0, lambda: self.timer_label.config(
                    text=f"Time: {mins:02d}:{secs:02d}",
                    foreground=color
                ))
                
            if remaining <= 0 and not self.auto_submit_triggered:
                self.window.after(0, self.time_up)
                break
                
            time.sleep(1)
            
    def time_up(self):
        """Handle time up - auto submit and exit"""
        if self.quiz_active and not self.auto_submit_triggered:
            self.auto_submit_triggered = True
            
            # Save last answer
            self.save_answer()
            
            # Show time up message
            timeup_window = tk.Toplevel(self.window)
            timeup_window.title("Time's Up!")
            timeup_window.geometry("400x250")
            timeup_window.transient(self.window)
            timeup_window.grab_set()
            
            # Center window
            timeup_window.update_idletasks()
            x = (timeup_window.winfo_screenwidth() // 2) - (400 // 2)
            y = (timeup_window.winfo_screenheight() // 2) - (250 // 2)
            timeup_window.geometry(f'400x250+{x}+{y}')
            
            # Style
            tk.Label(timeup_window, text="⏰", 
                    font=("Segoe UI", 40)).pack(pady=20)
            
            tk.Label(timeup_window, text="TIME'S UP!", 
                    font=("Segoe UI", 16, "bold"),
                    fg="#e74c3c").pack()
            
            tk.Label(timeup_window, text="Your quiz time has ended.\nSubmitting answers automatically...",
                    font=("Segoe UI", 11),
                    fg="#666666").pack(pady=10)
            
            # Progress bar
            progress = ttk.Progressbar(timeup_window, mode='indeterminate', length=300)
            progress.pack(pady=20)
            progress.start(10)
            
            # Update UI
            timeup_window.update()
            
            # Wait a moment for user to see
            time.sleep(2)
            
            timeup_window.destroy()
            
            # Submit quiz
            self.submit_quiz(auto_submit=True)
            
    def submit_quiz(self, auto_submit=False):
        """Submit the quiz and exit"""
        if self.auto_submit_triggered and not auto_submit:
            return
            
        if not auto_submit:
            if not messagebox.askyesno("Confirm Submission", 
                                       "Are you sure you want to submit?\n\n"
                                       f"Answered: {len(self.answers)}/{self.total_questions}\n"
                                       "You cannot change answers after submission."):
                return
        
        self.auto_submit_triggered = True
        self.quiz_active = False
            
        # Save last answer
        self.save_answer()
        
        # Calculate summary
        answered = len(self.answers)
        total = self.total_questions
        unanswered = total - answered
        
        # Show submission confirmation
        submit_window = tk.Toplevel(self.window)
        submit_window.title("Submitting Quiz")
        submit_window.geometry("450x400")
        submit_window.transient(self.window)
        submit_window.grab_set()
        
        # Center window
        submit_window.update_idletasks()
        x = (submit_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (submit_window.winfo_screenheight() // 2) - (400 // 2)
        submit_window.geometry(f'450x400+{x}+{y}')
        
        # Style
        tk.Label(submit_window, text="📤", 
                font=("Segoe UI", 50)).pack(pady=20)
        
        tk.Label(submit_window, text="Submitting Quiz", 
                font=("Segoe UI", 16, "bold"),
                fg="#2980b9").pack()
        
        # Summary frame
        summary_frame = tk.Frame(submit_window, bg="#f8f9fa", padx=20, pady=20)
        summary_frame.pack(fill="x", padx=30, pady=20)
        
        tk.Label(summary_frame, text=f"Roll Number: {self.student_number}",
                font=("Segoe UI", 11),
                bg="#f8f9fa").pack(anchor="w", pady=2)
        
        tk.Label(summary_frame, text=f"Questions Answered: {answered}/{total}",
                font=("Segoe UI", 11),
                bg="#f8f9fa",
                fg="#27ae60" if answered == total else "#e74c3c").pack(anchor="w", pady=2)
        
        if unanswered > 0:
            tk.Label(summary_frame, text=f"Skipped: {unanswered}",
                    font=("Segoe UI", 11),
                    bg="#f8f9fa",
                    fg="#f39c12").pack(anchor="w", pady=2)
        
        tk.Label(submit_window, text="Sending answers to teacher...",
                font=("Segoe UI", 10),
                fg="#666666").pack(pady=10)
        
        # Progress bar
        progress = ttk.Progressbar(submit_window, mode='indeterminate', length=350)
        progress.pack(pady=10)
        progress.start(10)
        
        # Update UI
        submit_window.update()
        
        # Send answers to teacher
        try:
            import server
            import json
            answers_json = json.dumps(self.answers)
            server.send_quiz_submission(self.quiz_id, self.student_number, answers_json)
            
            # Success
            progress.stop()
            tk.Label(submit_window, text="✓ Submitted Successfully!", 
                    font=("Segoe UI", 12, "bold"),
                    fg="#27ae60").pack(pady=10)
            submit_window.update()
            time.sleep(1.5)
            
        except Exception as e:
            progress.stop()
            tk.Label(submit_window, text=f"⚠️ Error: {str(e)[:50]}", 
                    font=("Segoe UI", 10),
                    fg="#e74c3c").pack(pady=10)
            submit_window.update()
            time.sleep(2)
            
        finally:
            submit_window.destroy()
            
            # Close quiz window and exit fullscreen
            if self.window and self.window.winfo_exists():
                self.window.attributes('-fullscreen', False)
                self.window.destroy()
                self.window = None
                
            # Show completion message
            self.show_completion_message(answered, total)
            
    def show_completion_message(self, answered, total):
        """Show quiz completion message"""
        complete_window = tk.Toplevel()
        complete_window.title("Quiz Complete")
        complete_window.geometry("450x350")
        
        # Center window
        complete_window.update_idletasks()
        x = (complete_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (complete_window.winfo_screenheight() // 2) - (350 // 2)
        complete_window.geometry(f'450x350+{x}+{y}')
        
        # Style
        tk.Label(complete_window, text="✅", 
                font=("Segoe UI", 60)).pack(pady=20)
        
        tk.Label(complete_window, text="Quiz Submitted!", 
                font=("Segoe UI", 18, "bold"),
                fg="#27ae60").pack()
        
        tk.Label(complete_window, text=f"Thank you, {self.student_number}",
                font=("Segoe UI", 12),
                fg="#2980b9").pack(pady=10)
        
        tk.Label(complete_window, text=f"You answered {answered} out of {total} questions",
                font=("Segoe UI", 11)).pack(pady=5)
        
        tk.Label(complete_window, text="\nYour results will be displayed by the teacher.",
                font=("Segoe UI", 10),
                fg="#666666").pack(pady=10)
        
        ttk.Button(complete_window, text="Close",
                  command=complete_window.destroy, width=20).pack(pady=20)
        
        # Auto close after 5 seconds
        complete_window.after(5000, complete_window.destroy)
        
    def on_close(self):
        """Handle window close attempt"""
        if self.quiz_active and not self.auto_submit_triggered:
            messagebox.showwarning("Warning", 
                                 "You cannot exit during the quiz!\n\n"
                                 "Please complete all questions and click SUBMIT QUIZ.\n")
                             
            return

# Global instance
student_quiz = StudentQuiz()