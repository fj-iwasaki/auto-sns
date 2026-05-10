from typing import List
import feedparser
from src.http import get
from src.models import Item


def fetch(feeds: List[str], per_feed: int = 20) -> List[Item]:
    items: List[Item] = []
    for url in feeds:
        r = get(url, headers={"Accept": "application/rss+xml,application/atom+xml,*/*"})
        if not r or r.status_code != 200:
            print(f"[rss] skip {url}: status={getattr(r, 'status_code', None)}")
            continue
        parsed = feedparser.parse(r.content)
        if parsed.bozo and not parsed.entries:
            print(f"[rss] parse failed {url}: {parsed.bozo_exception}")
            continue
        feed_title = (parsed.feed.get("title") or url) if hasattr(parsed.feed, "get") else url
        for e in parsed.entries[:per_feed]:
            title = (e.get("title") or "").strip()
            link = e.get("link") or ""
            if not title or not link:
                continue
            summary = e.get("summary") or e.get("description") or ""
            items.append(Item(
                source=f"rss:{feed_title}",
                title=title,
                url=link,
                summary=summary[:1000],
                author=e.get("author", ""),
                published=e.get("published", e.get("updated", "")),
            ))
    return items
