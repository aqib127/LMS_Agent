"""
Interactive CLI chatbot.

Run:
    python -m scripts.chat
Type questions or /commands. Type 'quit' or Ctrl+D to exit.
"""
from bot.commands import handle
from core.storage import init_db
from core.utils import ensure_dirs, logger


BANNER = """\
════════════════════════════════════════════════════════════
  LMS Agent — interactive chat
  Type /help for commands, or ask a question in plain English.
  Type 'quit' to exit.
════════════════════════════════════════════════════════════
"""


def main():
    ensure_dirs()
    init_db()
    print(BANNER)

    while True:
        try:
            line = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not line:
            continue
        if line.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break

        try:
            reply = handle(line)
        except Exception as e:
            logger.exception("handle failed")
            reply = f"❌ Error: {e}"

        print(f"\nBot: {reply}\n")


if __name__ == "__main__":
    main()
