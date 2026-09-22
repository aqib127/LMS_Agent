from pydantic import BaseModel


class AttendanceRecord(BaseModel):
    code: str
    title: str
    credit_hours: int
    class_name: str = ""
    teacher: str = ""
    present_hours: float = 0.0
    absent_hours: float = 0.0
    total_hours: float = 0.0
    percentage: float = 0.0
