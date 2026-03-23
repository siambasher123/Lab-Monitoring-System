# quiz_teacher.py - Teacher quiz control panel
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import random
import json
import os
import time
import threading
import state  # Import state
import quiz_parser
from datetime import datetime

class QuizTeacherPanel:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.questions = []
        self.active_quiz = False
        self.quiz_id = None
        self.quiz_session = {}  # Store current quiz session data
        self.student_responses = {}  # student_ip -> {answers: {}, score: int, status: str, student_num: str}
        self.quiz_start_time = None
        self.quiz_duration = 0
        self.notebook = None  # Store notebook reference
        self.current_quiz_file = None  # Store current quiz file path
        
    def embed_in_frame(self, parent_frame):
        """Embed quiz panel in existing frame (for page navigation)"""
        # Clear any existing content
        for widget in parent_frame.winfo_children():
            widget.destroy()
            
        # Main container
        main_frame = ttk.Frame(parent_frame, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Tab 1: Quiz Setup
        setup_frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(setup_frame, text="📋 Quiz Setup")
        self.create_setup_tab(setup_frame)
        
        # Tab 2: Active Quiz
        self.active_frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.active_frame, text="▶️ Active Quiz")
        self.create_active_tab(self.active_frame)
        
        # Tab 3: Results
        self.results_frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.results_frame, text="📊 Results")
        self.create_results_tab(self.results_frame)
        
        # Load any saved quiz session from global state
        self.load_quiz_session()
        
    def create_setup_tab(self, parent):
        """Create quiz setup tab"""
        # Upload PDF section
        pdf_frame = ttk.LabelFrame(parent, text="1. Upload Question Bank", padding=15)
        pdf_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(pdf_frame, text="Upload PDF with MCQs (Format: Q1. Question? A. Opt1 B. Opt2 C. Opt3 D. Opt4 Answer: A)",
                 font=("Arial", 9)).pack(anchor="w", pady=(0, 10))
        
        btn_frame = ttk.Frame(pdf_frame)
        btn_frame.pack(fill="x")
        
        self.pdf_path_var = tk.StringVar(value="No file selected")
        ttk.Label(btn_frame, textvariable=self.pdf_path_var,
                 font=("Arial", 9), foreground="gray").pack(side="left", padx=(0, 10))
        
        ttk.Button(btn_frame, text="📂 Browse PDF", 
                  command=self.browse_pdf, width=15).pack(side="left")
        
        ttk.Button(btn_frame, text="🔄 Parse Questions", 
                  command=self.parse_questions, width=15).pack(side="left", padx=10)
        
        # Question count display
        self.q_count_var = tk.StringVar(value="Questions loaded: 0")
        ttk.Label(pdf_frame, textvariable=self.q_count_var,
                 font=("Arial", 10, "bold"), foreground="blue").pack(anchor="w", pady=(10, 0))
        
        # Current session info
        session_frame = ttk.LabelFrame(parent, text="Current Quiz Session", padding=15)
        session_frame.pack(fill="x", pady=(0, 20))
        
        self.session_var = tk.StringVar(value="No active session")
        ttk.Label(session_frame, textvariable=self.session_var,
                 font=("Arial", 10)).pack(anchor="w")
        
        # Quiz settings
        settings_frame = ttk.LabelFrame(parent, text="2. Quiz Settings", padding=15)
        settings_frame.pack(fill="x", pady=(0, 20))
        
        # Questions per student
        q_per_row = ttk.Frame(settings_frame)
        q_per_row.pack(fill="x", pady=5)
        ttk.Label(q_per_row, text="Questions per student:", width=35).pack(side="left")
        self.q_per_student_var = tk.IntVar(value=30)
        ttk.Spinbox(q_per_row, from_=5, to=100, textvariable=self.q_per_student_var,
                   width=10).pack(side="left")
        
        # Marks per question
        marks_row = ttk.Frame(settings_frame)
        marks_row.pack(fill="x", pady=5)
        ttk.Label(marks_row, text="Marks per correct answer:", width=35).pack(side="left")
        self.marks_correct_var = tk.IntVar(value=4)
        ttk.Spinbox(marks_row, from_=1, to=10, textvariable=self.marks_correct_var,
                   width=10).pack(side="left")
        
        # Negative marking
        neg_row = ttk.Frame(settings_frame)
        neg_row.pack(fill="x", pady=5)
        ttk.Label(neg_row, text="Negative marks per wrong answer:", width=35).pack(side="left")
        self.marks_wrong_var = tk.IntVar(value=1)
        ttk.Spinbox(neg_row, from_=0, to=5, textvariable=self.marks_wrong_var,
                   width=10).pack(side="left")
        
        # Quiz duration
        time_row = ttk.Frame(settings_frame)
        time_row.pack(fill="x", pady=5)
        ttk.Label(time_row, text="Quiz duration (minutes):", width=35).pack(side="left")
        self.duration_var = tk.IntVar(value=30)
        ttk.Spinbox(time_row, from_=5, to=180, textvariable=self.duration_var,
                   width=10).pack(side="left")
        
        # Randomize questions
        random_row = ttk.Frame(settings_frame)
        random_row.pack(fill="x", pady=5)
        self.randomize_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(random_row, text="Randomize questions for each student",
                       variable=self.randomize_var).pack(anchor="w")
        
        # Start quiz button
        start_frame = ttk.Frame(parent)
        start_frame.pack(fill="x", pady=20)
        
        self.start_btn = ttk.Button(start_frame, text="🚀 START QUIZ", 
                                    command=self.start_quiz, width=20)
        
        # Check if we have questions from global state
        if state.quiz_session['questions']:
            self.questions = state.quiz_session['questions']
            self.q_count_var.set(f"Questions loaded: {len(self.questions)}")
            self.session_var.set(f"Session active: {os.path.basename(state.quiz_session['file_path'] or 'Unknown')} ({len(self.questions)} questions)")
            self.start_btn.config(state="normal")
        else:
            self.start_btn.config(state="disabled")
            
        self.start_btn.pack()
        
        # Clear session button
        ttk.Button(start_frame, text="🗑️ Clear Session", 
                  command=self.clear_session, width=25).pack(pady=10)
        
    def create_active_tab(self, parent):
        """Create active quiz monitoring tab"""
        # Quiz status
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="x", pady=(0, 20))
        
        self.quiz_status_var = tk.StringVar(value="No active quiz")
        ttk.Label(status_frame, textvariable=self.quiz_status_var,
                 font=("Arial", 12, "bold"), foreground="red").pack(side="left")
        
        self.timer_var = tk.StringVar(value="Time remaining: --:--")
        ttk.Label(status_frame, textvariable=self.timer_var,
                 font=("Arial", 12), foreground="blue").pack(side="right")
        
        # Student progress
        progress_frame = ttk.LabelFrame(parent, text="Student Progress", padding=10)
        progress_frame.pack(fill="both", expand=True)
        
        # Treeview for student progress
        columns = ('Student Num', 'IP', 'Status', 'Questions', 'Score')
        self.progress_tree = ttk.Treeview(progress_frame, columns=columns, show='headings', height=15)
        
        # Define headings
        self.progress_tree.heading('Student Num', text='Student Num')
        self.progress_tree.heading('IP', text='IP Address')
        self.progress_tree.heading('Status', text='Status')
        self.progress_tree.heading('Questions', text='Questions')
        self.progress_tree.heading('Score', text='Score')
        
        # Set column widths
        self.progress_tree.column('Student Num', width=100)
        self.progress_tree.column('IP', width=120)
        self.progress_tree.column('Status', width=100)
        self.progress_tree.column('Questions', width=80)
        self.progress_tree.column('Score', width=80)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(progress_frame, orient="vertical", command=self.progress_tree.yview)
        self.progress_tree.configure(yscrollcommand=scrollbar.set)
        
        self.progress_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Control buttons
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(control_frame, text="🔄 Refresh Progress", 
                  command=self.refresh_progress, width=20).pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="⏹️ END QUIZ", 
                  command=self.end_quiz, width=15).pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="📊 Auto-Grade", 
                  command=self.grade_quiz, width=15).pack(side="left", padx=5)
        
    def create_results_tab(self, parent):
        """Create results tab"""
        # Summary frame
        summary_frame = ttk.LabelFrame(parent, text="Quiz Summary", padding=10)
        summary_frame.pack(fill="x", pady=(0, 20))
        
        self.summary_var = tk.StringVar(value="No results available")
        ttk.Label(summary_frame, textvariable=self.summary_var,
                 font=("Arial", 11)).pack(anchor="w")
        
        # Results tree
        results_frame = ttk.LabelFrame(parent, text="Detailed Results", padding=10)
        results_frame.pack(fill="both", expand=True)
        
        columns = ('Rank', 'Student Num', 'Score', 'Correct', 'Wrong', 'Percentage', 'Status')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=15)
        
        # Define headings
        self.results_tree.heading('Rank', text='Rank')
        self.results_tree.heading('Student Num', text='Student Num')
        self.results_tree.heading('Score', text='Score')
        self.results_tree.heading('Correct', text='Correct')
        self.results_tree.heading('Wrong', text='Wrong')
        self.results_tree.heading('Percentage', text='Percentage')
        self.results_tree.heading('Status', text='Status')
        
        # Set column widths
        self.results_tree.column('Rank', width=50)
        self.results_tree.column('Student Num', width=100)
        self.results_tree.column('Score', width=80)
        self.results_tree.column('Correct', width=70)
        self.results_tree.column('Wrong', width=70)
        self.results_tree.column('Percentage', width=80)
        self.results_tree.column('Status', width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Export buttons
        export_frame = ttk.Frame(parent)
        export_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(export_frame, text="📄 Export as CSV", 
                  command=self.export_csv, width=20).pack(side="left", padx=5)
        
        ttk.Button(export_frame, text="📊 Show Statistics", 
                  command=self.show_statistics, width=20).pack(side="left", padx=5)
        
        ttk.Button(export_frame, text="🔄 New Quiz", 
                  command=self.new_quiz, width=15).pack(side="right", padx=5)
        
    def browse_pdf(self):
        """Browse for PDF file"""
        file_path = filedialog.askopenfilename(
            title="Select PDF with Questions",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.pdf_path_var.set(file_path)
            self.current_quiz_file = file_path
            
    def parse_questions(self):
        """Parse questions from PDF"""
        file_path = self.pdf_path_var.get()
        if file_path == "No file selected":
            messagebox.showwarning("Warning", "Please select a PDF file first!")
            return
            
        # Show parsing message
        self.q_count_var.set("Parsing PDF... Please wait")
        if hasattr(self, 'window') and self.window:
            self.window.update()
        
        self.questions = quiz_parser.QuizParser.parse_pdf(file_path)
        
        if self.questions:
            self.q_count_var.set(f"Questions loaded: {len(self.questions)}")
            
            # Save to global state
            state.save_quiz_session(self.questions, file_path)
            
            self.session_var.set(f"Session active: {os.path.basename(file_path)} ({len(self.questions)} questions)")
            
            # Enable start button only after successful parsing
            self.start_btn.config(state="normal")
            
            messagebox.showinfo("Success", f"Loaded {len(self.questions)} questions from PDF!\nSession saved globally.")
        else:
            self.q_count_var.set("Questions loaded: 0")
            messagebox.showerror("Error", "No questions found in PDF. Check the format!")
            
    def load_quiz_session(self):
        """Load saved quiz session from global state"""
        session = state.load_quiz_session()
        if session['questions']:
            self.questions = session['questions']
            self.q_count_var.set(f"Questions loaded: {len(self.questions)}")
            self.session_var.set(f"Session active: {os.path.basename(session['file_path'] or 'Unknown')} ({len(self.questions)} questions)")
            self.start_btn.config(state="normal")
            state.add_log(f"Loaded quiz session with {len(self.questions)} questions")
            
    def clear_session(self):
        """Clear current quiz session"""
        if messagebox.askyesno("Confirm", "Clear current quiz session?"):
            self.questions = []
            self.quiz_session = {}
            self.q_count_var.set("Questions loaded: 0")
            self.session_var.set("No active session")
            self.start_btn.config(state="disabled")
            self.pdf_path_var.set("No file selected")
            
            # Clear global state
            state.clear_quiz_session()
            
            state.add_log("Quiz session cleared")
            
    def start_quiz(self):
        """Start the quiz"""
        if not self.questions:
            messagebox.showwarning("Warning", "Please load questions first!")
            return
            
        if not state.students:
            messagebox.showwarning("Warning", "No students connected!")
            return
            
        # Get settings
        q_per_student = self.q_per_student_var.get()
        marks_correct = self.marks_correct_var.get()
        marks_wrong = self.marks_wrong_var.get()
        duration = self.duration_var.get()
        
        # Validate
        if q_per_student > len(self.questions):
            messagebox.showwarning("Warning", 
                f"Only {len(self.questions)} questions available. Reducing to {len(self.questions)} per student.")
            q_per_student = len(self.questions)
            self.q_per_student_var.set(q_per_student)
        
        # Generate quiz ID
        self.quiz_id = f"QUIZ_{int(time.time())}"
        self.active_quiz = True
        self.quiz_start_time = time.time()
        self.quiz_duration = duration * 60  # Convert to seconds
        
        # Clear previous responses
        self.student_responses = {}
        
        # Update status
        self.quiz_status_var.set(f"▶️ Active Quiz: {self.quiz_id}")
        
        # Send quiz start command to all students
        for student_ip in state.students:
            if self.randomize_var.get():
                student_questions = random.sample(self.questions, q_per_student)
            else:
                student_questions = self.questions[:q_per_student]
                
            # Store student's questions
            self.student_responses[student_ip] = {
                'questions': student_questions,
                'answers': {},
                'score': 0,
                'status': 'in_progress',
                'start_time': time.time(),
                'student_num': 'Unknown'
            }
            
            # Send to student
            command = f"QUIZ_START:{self.quiz_id}|{duration}|{q_per_student}|{marks_correct}|{marks_wrong}"
            state.send_command_to_student(student_ip, command)
            
            # Send questions one by one
            for q in student_questions:
                q_data = f"QUIZ_QUESTION:{q['number']}|{q['text']}|{q['options']['A']}|{q['options']['B']}|{q['options']['C']}|{q['options']['D']}"
                state.send_command_to_student(student_ip, q_data)
        
        # Start timer thread
        self.timer_thread = threading.Thread(target=self.update_timer, daemon=True)
        self.timer_thread.start()
        
        # Switch to active tab using notebook reference
        if self.notebook:
            self.notebook.select(1)  # Select the second tab (index 1)
        
        state.add_log(f"Quiz started: {self.quiz_id} with {len(state.students)} students")
        messagebox.showinfo("Quiz Started", f"Quiz {self.quiz_id} has started!\nDuration: {duration} minutes")
        
    def update_timer(self):
        """Update quiz timer"""
        while self.active_quiz:
            elapsed = time.time() - self.quiz_start_time
            remaining = max(0, self.quiz_duration - elapsed)
            
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            
            # Update timer in main thread
            if hasattr(self, 'timer_var'):
                try:
                    if hasattr(self, 'window') and self.window:
                        self.window.after(0, lambda: self.timer_var.set(f"Time remaining: {mins:02d}:{secs:02d}"))
                except:
                    pass
            
            if remaining <= 0:
                if hasattr(self, 'window') and self.window:
                    self.window.after(0, self.auto_submit_all)
                break
                
            time.sleep(1)
            
    def auto_submit_all(self):
        """Auto-submit for all students when time's up"""
        if self.active_quiz:
            self.active_quiz = False
            self.quiz_status_var.set("⏹️ Quiz Ended - Time's Up")
            
            for student_ip in self.student_responses:
                state.send_command_to_student(student_ip, "QUIZ_TIME_UP")
                
            self.grade_quiz()
            
    def end_quiz(self):
        """End the quiz manually"""
        if messagebox.askyesno("Confirm", "Are you sure you want to end the quiz?"):
            self.active_quiz = False
            self.quiz_status_var.set("⏹️ Quiz Ended")
            
            for student_ip in state.students:
                state.send_command_to_student(student_ip, "QUIZ_ENDED")
                
            self.grade_quiz()
            
    def receive_submission(self, student_ip, student_num, answers):
        """Receive final submission from student"""
        if student_ip in self.student_responses:
            self.student_responses[student_ip]['answers'] = answers
            self.student_responses[student_ip]['status'] = 'submitted'
            self.student_responses[student_ip]['student_num'] = student_num
            self.refresh_progress()
            state.add_log(f"Student {student_num} ({student_ip}) submitted quiz")
            
            # Check if all students have submitted
            self.check_all_submitted()
            
    def check_all_submitted(self):
        """Check if all students have submitted"""
        if not self.active_quiz:
            return
            
        total_students = len(self.student_responses)
        submitted = sum(1 for data in self.student_responses.values() if data['status'] == 'submitted')
        
        if submitted == total_students and total_students > 0:
            self.active_quiz = False
            self.quiz_status_var.set("⏹️ Quiz Complete - All Submitted")
            messagebox.showinfo("Quiz Complete", "All students have submitted. Auto-grading now...")
            self.grade_quiz()
            
    def refresh_progress(self):
        """Refresh student progress display"""
        if not hasattr(self, 'progress_tree'):
            return
            
        # Clear tree
        for item in self.progress_tree.get_children():
            self.progress_tree.delete(item)
            
        # Add students
        for student_ip, data in self.student_responses.items():
            answered = len(data['answers'])
            total = len(data['questions'])
            
            status = data.get('status', 'in_progress')
            if status == 'submitted':
                status_display = "✅ Submitted"
            else:
                status_display = f"▶️ {answered}/{total}"
                
            student_num = data.get('student_num', 'Unknown')
            
            self.progress_tree.insert('', 'end', values=(
                student_num,
                student_ip,
                status_display,
                f"{answered}/{total}",
                data.get('score', 0)
            ))
            
    def grade_quiz(self):
        """Grade all submissions and show final results"""
        marks_correct = self.marks_correct_var.get()
        marks_wrong = self.marks_wrong_var.get()
        
        results = []
        
        for student_ip, data in self.student_responses.items():
            correct = 0
            wrong = 0
            unanswered = 0
            
            for q in data['questions']:
                q_num = str(q['number'])
                student_answer = data['answers'].get(q_num, '')
                
                if not student_answer:
                    unanswered += 1
                elif student_answer == q['correct']:
                    correct += 1
                else:
                    wrong += 1
                    
            score = (correct * marks_correct) - (wrong * marks_wrong)
            data['score'] = max(0, score)  # Don't go below 0
            
            total_possible = len(data['questions']) * marks_correct
            percentage = (score / total_possible) * 100 if total_possible > 0 else 0
            
            # Determine status
            if data.get('status') == 'submitted':
                status = '✅ Completed'
            else:
                status = '⚠️ Incomplete'
            
            results.append({
                'student_num': data.get('student_num', 'Unknown'),
                'ip': student_ip,
                'score': score,
                'correct': correct,
                'wrong': wrong,
                'unanswered': unanswered,
                'percentage': percentage,
                'status': status
            })
            
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Update results display
        self.update_results_display(results)
        
        # Show summary
        self.show_quiz_summary(results)
        
        # Switch to results tab
        if self.notebook:
            self.notebook.select(2)  # Select results tab
            
        # Save results
        self.save_results(results)
        
        state.add_log(f"Quiz graded: {len(results)} students")
        messagebox.showinfo("Grading Complete", f"Quiz has been graded!\nCheck Results tab for details.")
        
    def update_results_display(self, results):
        """Update results tree"""
        if not hasattr(self, 'results_tree'):
            return
            
        # Clear tree
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
            
        # Add results
        for i, result in enumerate(results, 1):
            self.results_tree.insert('', 'end', values=(
                i,
                result['student_num'],
                result['score'],
                result['correct'],
                result['wrong'],
                f"{result['percentage']:.1f}%",
                result['status']
            ))
            
    def show_quiz_summary(self, results):
        """Show quiz summary"""
        if not results:
            return
            
        total_students = len(results)
        completed = sum(1 for r in results if r['status'] == '✅ Completed')
        avg_score = sum(r['score'] for r in results) / total_students
        max_score = max(r['score'] for r in results)
        min_score = min(r['score'] for r in results)
        
        summary = f"📊 Quiz Results Summary\n\n"
        summary += f"Total Students: {total_students}\n"
        summary += f"Completed: {completed}\n"
        summary += f"Incomplete: {total_students - completed}\n"
        summary += f"Average Score: {avg_score:.1f}\n"
        summary += f"Highest Score: {max_score}\n"
        summary += f"Lowest Score: {min_score}\n"
        summary += f"Total Questions: {len(self.questions)}\n"
        
        if hasattr(self, 'summary_var'):
            self.summary_var.set(summary)
            
    def save_results(self, results):
        """Save results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quiz_results_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump({
                    'quiz_id': self.quiz_id,
                    'timestamp': timestamp,
                    'settings': {
                        'marks_correct': self.marks_correct_var.get(),
                        'marks_wrong': self.marks_wrong_var.get(),
                        'duration': self.duration_var.get()
                    },
                    'results': results
                }, f, indent=2)
            state.add_log(f"Results saved to {filename}")
        except Exception as e:
            state.add_log(f"Error saving results: {e}")
            
    def export_csv(self):
        """Export results to CSV"""
        from datetime import datetime
        
        filename = f"quiz_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("Rank,Student Number,Score,Correct,Wrong,Unanswered,Percentage,Status\n")
                
                for item in self.results_tree.get_children():
                    values = self.results_tree.item(item)['values']
                    # Add unanswered count (not in display)
                    f.write(f"{values[0]},{values[1]},{values[2]},{values[3]},{values[4]},0,{values[5]},{values[6]}\n")
                    
            messagebox.showinfo("Success", f"Results exported to {filename}")
            state.add_log(f"Results exported to {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")
            
    def show_statistics(self):
        """Show detailed statistics"""
        if not hasattr(self, 'results_tree') or not self.results_tree.get_children():
            messagebox.showwarning("Warning", "No results to show statistics for!")
            return
            
        # Calculate statistics
        scores = []
        for item in self.results_tree.get_children():
            values = self.results_tree.item(item)['values']
            scores.append(float(values[2]))  # Score
            
        if scores:
            try:
                import statistics
                stats = f"📈 Statistics\n\n"
                stats += f"Number of Students: {len(scores)}\n"
                stats += f"Mean: {statistics.mean(scores):.2f}\n"
                stats += f"Median: {statistics.median(scores):.2f}\n"
                if len(scores) > 1:
                    stats += f"Std Dev: {statistics.stdev(scores):.2f}\n"
                    stats += f"Variance: {statistics.variance(scores):.2f}\n"
                
                messagebox.showinfo("Statistics", stats)
            except:
                messagebox.showinfo("Statistics", f"Number of students: {len(scores)}")
                
    def new_quiz(self):
        """Start a new quiz (clear results but keep questions)"""
        if messagebox.askyesno("Confirm", "Start new quiz? Current results will be cleared."):
            self.student_responses = {}
            self.active_quiz = False
            self.quiz_id = None
            self.quiz_status_var.set("No active quiz")
            self.timer_var.set("Time remaining: --:--")
            
            # Clear trees
            if hasattr(self, 'progress_tree'):
                for item in self.progress_tree.get_children():
                    self.progress_tree.delete(item)
                    
            if hasattr(self, 'results_tree'):
                for item in self.results_tree.get_children():
                    self.results_tree.delete(item)
                    
            self.summary_var.set("No results available")
            
            # Switch to setup tab
            if self.notebook:
                self.notebook.select(0)
                
            state.add_log("Ready for new quiz")