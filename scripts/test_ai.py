"""
Quick test of the AI engine.
"""
from core.ai_engine import lowest_attendance, unpaid_fees, upcoming_exams, recent_results, answer


def main():
    print("\n=== lowest_attendance ===")
    print(lowest_attendance())

    print("\n=== unpaid_fees ===")
    print(unpaid_fees())

    print("\n=== upcoming_exams ===")
    print(upcoming_exams())

    print("\n=== recent_results ===")
    print(recent_results())

    print("\n=== free-form question ===")
    print(answer("What is my attendance looking like this semester?"))


if __name__ == "__main__":
    main()
