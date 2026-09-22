"""Long-running scheduler: runs the agent every N minutes."""
from apscheduler.schedulers.blocking import BlockingScheduler
from config.settings import settings
from core.agent import run_once
from core.utils import logger, ensure_dirs


def job():
    logger.info("Scheduled run starting")
    try:
        r = run_once(notify=True)
        logger.info(f"Scheduled run done: {r['new']} new, {r['changed']} changed")
    except Exception as e:
        logger.exception(f"Scheduled run failed: {e}")


def main():
    ensure_dirs()
    interval = settings.poll_interval_minutes
    logger.info(f"Scheduler starting, interval={interval} minutes")
    job()
    sched = BlockingScheduler()
    sched.add_job(job, "interval", minutes=interval)
    sched.start()


if __name__ == "__main__":
    main()
