"""Nitter経由のX収集（ベストエフォート）。

Nitter公開インスタンスは不安定で、しばしば502/Cloudflareブロックを返す。
全インスタンスがダメな時は静かにスキップする。X公式APIに切り替える場合は
別途 collectors/x_official.py を実装することを推奨。
"""
from typing import List
import feedparser
from src.http import get
from src.models import Item


def fetch(usernames: List[str], instances: List[str], per_user: int = 10) -> List[Item]:
    items: List[Item] = []
    if not instances:
        return items
    for user in usernames:
        body = None
        used_instance = None
        for inst in instances:
            inst = inst.rstrip("/")
            url = f"{inst}/{user}/rss"
            r = get(url, headers={"Accept": "application/rss+xml,*/*"}, retries=1)
            if r and r.status_code == 200 and b"<rss" in r.content[:200].lower():
                body = r.content
                used_instance = inst
                break
        if not body:
            print(f"[nitter] no working instance for @{user}")
            continue
        parsed = feedparser.parse(body)
        for e in parsed.entries[:per_user]:
            title = (e.get("title") or "").strip()
            link = e.get("link") or ""
            if not title or not link:
                continue
            items.append(Item(
                source=f"x:@{user}",
                title=title,
                url=link.replace(used_instance, "https://x.com") if used_instance else link,
                summary=(e.get("summary") or "")[:1000],
                author=user,
                published=e.get("published", ""),
            ))
    return items
