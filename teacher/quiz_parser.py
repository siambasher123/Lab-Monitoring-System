# quiz_parser.py - Parse MCQs from PDF
import PyPDF2
import re
import os
import json
from tkinter import messagebox

class QuizParser:
    @staticmethod
    def parse_pdf(file_path):
        """Extract MCQs from PDF file"""
        questions = []
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                # Extract text from all pages
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                # Parse questions (format: Q1. Question? A. Option1 B. Option2 C. Option3 D. Option4 Answer: A)
                # This pattern can be adjusted based on your PDF format
                question_pattern = r'Q(\d+)\.\s*(.*?)\s*A\.\s*(.*?)\s*B\.\s*(.*?)\s*C\.\s*(.*?)\s*D\.\s*(.*?)\s*Answer:\s*([A-D])'
                
                matches = re.finditer(question_pattern, text, re.DOTALL | re.IGNORECASE)
                
                for match in matches:
                    q_num = match.group(1)
                    question_text = match.group(2).strip()
                    option_a = match.group(3).strip()
                    option_b = match.group(4).strip()
                    option_c = match.group(5).strip()
                    option_d = match.group(6).strip()
                    correct_answer = match.group(7).upper()
                    
                    # Map correct answer to option text
                    answer_map = {
                        'A': option_a,
                        'B': option_b,
                        'C': option_c,
                        'D': option_d
                    }
                    
                    question = {
                        'number': int(q_num),
                        'text': question_text,
                        'options': {
                            'A': option_a,
                            'B': option_b,
                            'C': option_c,
                            'D': option_d
                        },
                        'correct': correct_answer,
                        'correct_text': answer_map[correct_answer]
                    }
                    
                    questions.append(question)
                
                return questions
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse PDF: {str(e)}")
            return []

    @staticmethod
    def save_questions(questions, filename="quiz_questions.json"):
        """Save parsed questions to JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        return filename

    @staticmethod
    def load_questions(filename="quiz_questions.json"):
        """Load questions from JSON"""
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

# For testing
if __name__ == "__main__":
    # Test the parser
    print("Quiz Parser Module Loaded Successfully")