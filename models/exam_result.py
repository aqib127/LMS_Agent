from pydantic import BaseModel


class ExamResult(BaseModel):
    code: str
    title: str
    credit_hours: int
    grade: str           # "C+", "A", "N/A"
    grade_points: float  # 2.33, 4.0, 0 for N/A
    product: float       # credit_hours * grade_points
    semester: str = ""   # filled from page context
