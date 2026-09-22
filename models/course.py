from pydantic import BaseModel


class Course(BaseModel):
    code: str
    title: str
    credit_hours: int
    class_name: str = ""
    teacher: str = ""
    teacher_email: str = ""
    fee_status: str = ""
    offered_title: str = ""
