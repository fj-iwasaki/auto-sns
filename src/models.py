from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Item:
    source: str
    title: str
    url: str
    summary: str = ""
    author: str = ""
    published: Optional[str] = None
    score: Optional[int] = None
    lang: str = ""
    raw: dict = field(default_factory=dict)

    def key(self) -> str:
        return self.url.split("?")[0].rstrip("/")

    def to_dict(self) -> dict:
        return asdict(self)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
