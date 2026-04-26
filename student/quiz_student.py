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
        
        # GUI elements
        self.question_label = None
        self.options_vars = []
        self.timer_label = None
        self.progress_label = None
        self.submit_btn = None
        self.option_buttons = []
        
    def register_student(self):
        """Show registration window first"""
        reg_window = tk.Toplevel()
        reg_window.title("📝 Quiz Registration")
        reg_window.geometry("450x300")
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
        
        # Title
        ttk.Label(reg_window, text="📝 Quiz Registration", 
                 font=("Arial", 16, "bold")).pack(pady=20)
        
        # Instructions
        ttk.Label(reg_window, text="Please enter your details to begin the quiz",
                 font=("Arial", 10)).pack(pady=10)
        
        # Student number frame
        frame = ttk.Frame(reg_window, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Enter Your Roll Number / Student ID:",
                 font=("Arial", 11)).pack(pady=10)
        
        student_num_var = tk.StringVar()
        student_entry = ttk.Entry(frame, textvariable=student_num_var,
                                 font=("Arial", 12), width=25)
        student_entry.pack(pady=10)
        student_entry.focus()
        
        # Name (optional)
        ttk.Label(frame, text="Your Name (Optional):",
                 font=("Arial", 11)).pack(pady=5)
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(frame, textvariable=name_var,
                              font=("Arial", 12), width=25)
        name_entry.pack(pady=5)
        
        def submit_registration():
            student_num = student_num_var.get().strip()
            if not student_num:
                messagebox.showerror("Error", "Please enter your student number!")
                return
                
            self.student_number = student_num
            self.student_name = name_var.get().strip() or f"Student_{student_num}"
            self.registration_complete = True
            reg_window.destroy()
            
            # Send registration to teacher
            try:
                import server
                server.send_log(f"Student {student_num} registered for quiz")
            except:
                pass
                
        ttk.Button(frame, text="✅ Register & Start Quiz",
                  command=submit_registration, width=20).pack(pady=20)
        
        # Bind Enter key
        reg_window.bind('<Return>', lambda e: submit_registration())
        
        # Wait for registration
        reg_window.wait_window()
        
        return self.registration_complete
        
    def show_quiz(self, quiz_id, duration, q_per_student, marks_correct, marks_wrong):
        """Show quiz window"""
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
        
        # Close any existing window
        if self.window and self.window.winfo_exists():
            self.window.destroy()
            
        # Create window
        self.window = tk.Toplevel()
        self.window.title(f"📝 Quiz - {self.student_number}")
        self.window.geometry("900x700")
        
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
        
        # Main container
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Student info
        info_frame = ttk.Frame(header_frame)
        info_frame.pack(side="left")
        ttk.Label(info_frame, text=f"Student: {self.student_number}",
                 font=("Arial", 12, "bold")).pack(anchor="w")
        if hasattr(self, 'student_name'):
            ttk.Label(info_frame, text=f"Name: {self.student_name}",
                     font=("Arial", 10)).pack(anchor="w")
        
        # Timer
        self.timer_label = ttk.Label(header_frame, text="Time: --:--",
                                     font=("Arial", 14, "bold"), foreground="red")
        self.timer_label.pack(side="right")
        
        # Progress
        self.progress_label = ttk.Label(main_frame, text="Question 0/0",
                                        font=("Arial", 11))
        self.progress_label.pack(anchor="w", pady=(0, 10))
        
        # Question frame
        q_frame = ttk.LabelFrame(main_frame, text="Question", padding=15)
        q_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Question text
        self.question_label = tk.Text(q_frame, wrap="word", height=4,
                                     font=("Arial", 12), padx=10, pady=10)
        self.question_label.pack(fill="x", pady=(0, 15))
        self.question_label.config(state="disabled")
        
        # Options frame
        options_frame = ttk.Frame(q_frame)
        options_frame.pack(fill="x")
        
        self.options_vars = [tk.StringVar() for _ in range(4)]
        self.option_buttons = []
        
        for i, opt_var in enumerate(self.options_vars):
            rb = ttk.Radiobutton(options_frame, text="", variable=opt_var,
                                value=chr(65 + i),  # A, B, C, D
                                command=self.save_answer)
            rb.pack(anchor="w", pady=5)
            self.option_buttons.append(rb)
            
        # Navigation buttons
        nav_frame = ttk.Frame(main_frame)
        nav_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Button(nav_frame, text="◀ Previous", 
                  command=self.prev_question, width=15).pack(side="left", padx=5)
        
        ttk.Button(nav_frame, text="Next ▶", 
                  command=self.next_question, width=15).pack(side="left", padx=5)
        
        # Submit button
        self.submit_btn = ttk.Button(main_frame, text="✅ SUBMIT QUIZ", 
                                     command=self.submit_quiz, width=20)
        self.submit_btn.pack()
        
        # Instructions
        ttk.Label(main_frame, text="Note: You cannot exit until you submit the quiz",
                 font=("Arial", 9), foreground="red").pack(pady=10)
        
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
        self.question_label.insert(1.0, f"Q{q['number']}. {q['text']}")
        self.question_label.config(state="disabled")
        
        # Update options
        for i, opt_text in enumerate(q['options']):
            self.option_buttons[i].config(text=f"{chr(65 + i)}. {opt_text}")
            
        # Restore previous answer if any
        saved_answer = self.answers.get(q['number'])
        if saved_answer:
            for i, opt_var in enumerate(self.options_vars):
                opt_var.set(saved_answer if chr(65 + i) == saved_answer else "")
        else:
            for opt_var in self.options_vars:
                opt_var.set("")
                
        # Update progress
        self.progress_label.config(text=f"Question {index + 1}/{self.total_questions}")
        self.current_question = index
        
    def save_answer(self):
        """Save current answer"""
        if not self.questions:
            return
            
        q = self.questions[self.current_question]
        for opt_var in self.options_vars:
            answer = opt_var.get()
            if answer:
                self.answers[q['number']] = answer
                break
                
    def next_question(self):
        """Go to next question"""
        self.save_answer()
        if self.current_question < len(self.questions) - 1:
            self.display_question(self.current_question + 1)
            
    def prev_question(self):
        """Go to previous question"""
        self.save_answer()
        if self.current_question > 0:
            self.display_question(self.current_question - 1)
            
    def update_timer(self):
        """Update quiz timer"""
        while self.quiz_active and self.window and self.window.winfo_exists():
            elapsed = time.time() - self.start_time
            remaining = max(0, self.duration - elapsed)
            
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            
            # Update timer in main thread
            if self.window and self.window.winfo_exists():
                self.window.after(0, lambda: self.timer_label.config(
                    text=f"Time: {mins:02d}:{secs:02d}",
                    foreground="red" if remaining < 300 else "blue"
                ))
                
            if remaining <= 0:
                self.window.after(0, self.time_up)
                break
                
            time.sleep(1)
            
    def time_up(self):
        """Handle time up"""
        if self.quiz_active:
            messagebox.showinfo("Time's Up", "Your quiz time has ended. Submitting automatically...")
            self.submit_quiz()
            
    def submit_quiz(self):
        """Submit the quiz and exit"""
        if not messagebox.askyesno("Confirm", "Are you sure you want to submit? You cannot change answers after submission."):
            return
            
        # Save last answer
        self.save_answer()
        
        # Calculate summary
        answered = len(self.answers)
        total = self.total_questions
        unanswered = total - answered
        
        # Show submission confirmation
        submit_window = tk.Toplevel(self.window)
        submit_window.title("Submitting Quiz")
        submit_window.geometry("400x350")
        submit_window.transient(self.window)
        submit_window.grab_set()
        
        # Center
        submit_window.update_idletasks()
        x = (submit_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (submit_window.winfo_screenheight() // 2) - (350 // 2)
        submit_window.geometry(f'400x350+{x}+{y}')
        
        ttk.Label(submit_window, text="📤 Submitting Quiz", 
                 font=("Arial", 14, "bold")).pack(pady=20)
        
        ttk.Label(submit_window, text=f"Student: {self.student_number}",
                 font=("Arial", 11)).pack(pady=5)
        
        ttk.Label(submit_window, text=f"Questions Answered: {answered}/{total}",
                 font=("Arial", 11)).pack(pady=5)
        
        if unanswered > 0:
            ttk.Label(submit_window, text=f"Unanswered: {unanswered}",
                     font=("Arial", 11), foreground="orange").pack(pady=5)
        
        ttk.Label(submit_window, text="\nSending answers to teacher...",
                 font=("Arial", 10)).pack(pady=10)
        
        # Progress bar
        progress = ttk.Progressbar(submit_window, mode='indeterminate', length=300)
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
            ttk.Label(submit_window, text="✓ Submitted Successfully!", 
                     font=("Arial", 11, "bold"), foreground="green").pack(pady=10)
            submit_window.update()
            time.sleep(1.5)
            
        except Exception as e:
            progress.stop()
            ttk.Label(submit_window, text=f"✗ Error: {str(e)[:50]}", 
                     font=("Arial", 11), foreground="red").pack(pady=10)
            submit_window.update()
            time.sleep(2)
            
        finally:
            submit_window.destroy()
            self.quiz_active = False
            
            # Close quiz window and exit fullscreen
            if self.window:
                self.window.attributes('-fullscreen', False)
                self.window.destroy()
                self.window = None
                
            # Show completion message
            self.show_completion_message(answered, total)
            
    def show_completion_message(self, answered, total):
        """Show quiz completion message"""
        complete_window = tk.Toplevel()
        complete_window.title("Quiz Complete")
        complete_window.geometry("400x300")
        
        # Center
        complete_window.update_idletasks()
        x = (complete_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (complete_window.winfo_screenheight() // 2) - (300 // 2)
        complete_window.geometry(f'400x300+{x}+{y}')
        
        ttk.Label(complete_window, text="✅ Quiz Submitted!", 
                 font=("Arial", 16, "bold"), foreground="green").pack(pady=20)
        
        ttk.Label(complete_window, text=f"Thank you {self.student_number}",
                 font=("Arial", 12)).pack(pady=10)
        
        ttk.Label(complete_window, text=f"You answered {answered} out of {total} questions",
                 font=("Arial", 11)).pack(pady=5)
        
        ttk.Label(complete_window, text="\nYour results will be displayed by the teacher.",
                 font=("Arial", 10), foreground="blue").pack(pady=10)
        
        ttk.Button(complete_window, text="Close",
                  command=complete_window.destroy, width=15).pack(pady=20)
        
    def on_close(self):
        """Handle window close attempt"""
        if self.quiz_active:
            messagebox.showwarning("Warning", "You cannot exit during the quiz!\nPlease submit your answers first.")
            return

# Global instance
student_quiz = StudentQuiz()