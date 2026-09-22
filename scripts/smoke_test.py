from config.settings import settings
from core.utils import logger, ensure_dirs

ensure_dirs()
logger.info("Settings loaded successfully")
logger.info(f"LMS base URL: {settings.lms_base_url}")
logger.info(f"Login URL: {settings.lms_login_url}")
logger.info(f"Headless: {settings.headless}")
logger.info("Scaffold OK")
