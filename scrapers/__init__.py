from .attendance import scrape_attendance
from .courses import scrape_courses
from .exams import scrape_exam_results
from .fees import scrape_fee_challans
from .exam_seats import scrape_exam_seats
from .community_services import scrape_community_services

__all__ = [
    "scrape_attendance",
    "scrape_courses",
    "scrape_exam_results",
    "scrape_fee_challans",
    "scrape_exam_seats",
    "scrape_community_services",
]
