import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from loguru import logger
from config.settings import settings

logger.remove()
logger.add(sys.stderr, level=settings.log_level)
logger.add("logs/agent.log", rotation="10 MB", retention="14 days", level=settings.log_level)

def stable_hash(obj: dict, keys: list[str]) -> str:
    subset = {k: obj.get(k) for k in keys}
    blob = json.dumps(subset, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()

def now_local() -> datetime:
    return datetime.now()

def ensure_dirs():
    for d in ["data", "data/snapshots", "logs"]:
        Path(d).mkdir(parents=True, exist_ok=True)
