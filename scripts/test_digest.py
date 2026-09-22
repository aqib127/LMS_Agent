from core.ai_engine import digest
from core.notifier import send_email

FAKE = {
    "fees": [{"semester": "Fall-2026", "amount": "Rs. 104,340",
              "status": "Not Paid", "due_date": "12/10/2026"}],
    "attendance": [{"code": "CSL 320", "title": "Operating System Lab",
                    "percentage": 66.67}],
    "exam_results": [{"code": "SEN 220", "title": "Software Engineering",
                      "grade": "C+", "grade_points": 2.33}],
    "exam_seats": [{"title": "Discrete Mathematics", "date": "19/08/2026",
                    "start_time": "12:15 PM", "room": "F2", "row": "2", "column": "4"}],
    "lms_assignments": [
        {"course": "Operating Systems Lab", "title": "Linux Commands",
         "deadline": "14 September 2026", "status": "Deadline Exceeded"},
        {"course": "AI Lab", "title": "Python Tutorial",
         "deadline": "22 September 2026", "status": "Submit"},
    ],
    "lms_announcements": [
        {"course": "Theory of Automata", "title": "General",
         "posted_date": "11-09-2026", "body": "Today is a work-from-home day..."}],
    "lms_lecture_notes": [
        {"course": "Operating Systems Lab", "week": "5", "title": "Memory Management",
         "files": "Download Lecture", "videos": ""}],
    "lms_quizzes": [
        {"course": "AI Lab", "title": "Quiz 1", "marks": "10"}],
}

body = digest(FAKE)
subject = "LMS: 🧪 test digest (all categories)"
send_email(subject=subject, body=body)
print(f"Sent test digest — subject: {subject}")
