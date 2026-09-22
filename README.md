# LMS AI Agent — Bahria University

Personal AI agent that scrapes your Bahria CMS + LMS, stores everything
locally, detects changes, emails digests, and answers questions via chat.

## Features

- **Auto-login** to CMS using enrollment number
- **Scrapes** CMS (attendance, courses, results, fees, exam seats, community services)
- **Scrapes** LMS (assignments, quizzes, lecture notes, announcements, past papers)
- **SQLite storage** with change detection
- **Email notifications** when anything changes
- **Local LLM** (Ollama + Qwen) for free-form questions
- **Interactive chat** CLI
- **Scheduled** to run automatically (cron)

## Quick start

    source .venv/bin/activate
    python -m scripts.chat              # Interactive chat
    python -m scripts.run_once          # One CMS refresh
    python -m scripts.refresh_lms       # One LMS deep refresh

## Chat commands

    /attendance      attendance per course
    /lowest          courses with lowest attendance
    /fees            all fee challans
    /unpaid          unpaid fees
    /results         recent exam results
    /exams           scheduled exams
    /courses         registered courses
    /assignments     all assignments
    /deadlines       pending assignments
    /quizzes         quizzes per course
    /announcements   latest announcements
    /notes <course>  lecture notes for a course
    /papers          past papers
    /refresh         refresh CMS
    /refresh-lms     deep refresh LMS
    /stats           database totals
    /help            this list

Or just type a question:
    "What's due this week?"
    "Show me CSL 320 lecture notes"
    "Any new announcements?"

## Automatic runs

- **Every 30 minutes** (7 AM – 10 PM): CMS refresh + email if changed
- **Daily at 6 AM**: Deep LMS refresh + email if changed

Check logs:
    tail -f logs/agent.log
    tail -f logs/cron.log
    tail -f logs/lms.log

## Configuration

Edit `.env` to change:
- `LMS_ENROLLMENT_NO` / `LMS_PASSWORD` — CMS credentials
- `SMTP_USER` / `SMTP_PASS` / `EMAIL_TO` — Gmail notifications
- `LLM_PROVIDER` / `LLM_MODEL` — Ollama/OpenAI/Anthropic/none
- `POLL_INTERVAL_MINUTES` — how often CMS is refreshed

## Structure

    config/settings.py       Settings loader
    core/auth.py             CMS auto-login
    core/browser.py          Playwright wrapper
    core/storage.py          SQLite + diff
    core/scraper_runner.py   CMS pipeline
    core/lms_runner.py       LMS deep pipeline
    core/agent.py            Orchestrator
    core/ai_engine.py        LLM brain
    core/llm.py              Provider wrapper
    core/notifier.py         Email sender
    scrapers/*.py            Page parsers
    models/*.py              Pydantic models
    bot/commands.py          Chat command router
    scripts/*.py             Entry points
# LMS_Agent
