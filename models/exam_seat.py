from pydantic import BaseModel


class ExamSeat(BaseModel):
    title: str
    class_name: str
    date: str
    session: str
    start_time: str
    room: str
    row: str
    column: str
    status: str = ""
    fee_defaulter: str = ""
