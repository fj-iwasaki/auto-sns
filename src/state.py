"""過去送信URLの簡易キャッシュ。state/seen.json に追記。"""
import json
import os
from pathlib import Path
from typing import Iterable, Set

STATE_DIR = Path(os.environ.get("STATE_DIR", "state"))
SEEN_PATH = STATE_DIR / "seen.json"
MAX_KEEP = 5000


def load_seen() -> Set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        return set(json.loads(SEEN_PATH.read_text("utf-8")))
    except Exception:
        return set()


def save_seen(keys: Iterable[str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    arr = list(keys)[-MAX_KEEP:]
    SEEN_PATH.write_text(json.dumps(arr, ensure_ascii=False), "utf-8")
