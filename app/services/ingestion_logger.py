import json
import time
from pathlib import Path

LOG_DIR = Path("outputs")
LOG_FILE = LOG_DIR / "ingestion_log.json"


def write_ingestion_log(entry: dict):
    """
    Persist ingestion event for reproducibility & thesis experiments
    """

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    entry["timestamp"] = time.time()

    if LOG_FILE.exists():
        try:
            data = json.loads(LOG_FILE.read_text())
        except Exception:
            data = []
    else:
        data = []

    data.append(entry)

    LOG_FILE.write_text(json.dumps(data, indent=2))