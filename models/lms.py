from pydantic import BaseModel


class LmsAssignment(BaseModel):
    course: str
    number: str
    title: str
    added: str = ""
    marks_obtained: str = ""
    status: str = ""           # "Deadline Exceeded", "Pending", "Submitted"...
    deadline: str = ""


class LmsQuiz(BaseModel):
    course: str
    number: str
    title: str
    marks: str = ""
    solution: str = ""
    deadline: str = ""


class LmsLectureNote(BaseModel):
    course: str
    week: str
    title: str
    files: str = ""              # human-readable: "1. Download Lecture"
    files_url: str = ""          # relative URL: "Download.php?k=..."
    videos: str = ""
    remarks: str = ""


class LmsPaperDownload(BaseModel):
    course: str
    number: str
    term: str
    paper: str = ""
    paper_url: str = ""          # relative URL
    remarks: str = ""
    marks: str = ""
    deadline: str = ""


class LmsAnnouncement(BaseModel):
    course: str
    number: str
    title: str
    body: str
    posted_date: str = ""


class LmsPaper(BaseModel):
    course: str
    number: str
    term: str
    paper: str = ""
    remarks: str = ""
    marks: str = ""
    returned: str = ""
    deadline: str = ""


class LmsCoursePlan(BaseModel):
    course: str
    week: str
    content: str
    outcome: str


class LmsCourseOutline(BaseModel):
    course: str
    outline_url: str
