# app/questions.py

# BAARS-IV: Sample questions
QUESTIONS = [
    "Do you often have trouble wrapping up the final details of a project?",
    "Do you often fidget or squirm with your hands or feet when you have to sit down for a long time?",
    "How often do you have difficulty sustaining attention in tasks?",
    "Do you often forget appointments or obligations?",
]

RESPONSE_OPTIONS = ["Never or Rarely", "Sometimes", "Often", "Very Often"]

def get_question(index):
    """Retrieve a question by index."""
    if 0 <= index < len(QUESTIONS):
        return QUESTIONS[index]
    return None

def get_total_questions():
    return len(QUESTIONS)
