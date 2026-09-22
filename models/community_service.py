from pydantic import BaseModel


class CommunityService(BaseModel):
    semester: str
    organization: str
    job_title: str
    completed_date: str
    hours: str
