"""
Send a test email.
"""
from core.notifier import send_email

def main():
    ok = send_email(
        subject="LMS Agent — test email",
        body="If you can read this, your Gmail SMTP setup works.\n\n"
             "You'll receive notifications here when new data appears on your LMS.",
    )
    print("OK" if ok else "FAILED — check credentials and app password")

if __name__ == "__main__":
    main()
