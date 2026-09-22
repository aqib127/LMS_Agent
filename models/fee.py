from pydantic import BaseModel


class FeeChallan(BaseModel):
    semester: str
    type: str
    challan_no: str
    amount: str
    due_date: str
    status: str
    deposit_date: str = ""
    remarks: str = ""
