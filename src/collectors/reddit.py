"""Reddit収集。

旧来は /r/{sub}/new.json を使っていたが、2024年以降の制限強化で
無認証アクセスが 403 になりやすい。本実装は public RSS (/new.rss)
にフォールバックする。両方失敗したら静かにスキップ。
"""
from typing import List
import feedparser
from src.http import get
from src.models import Item


def _parse_rss(sub: str, body: bytes) -> List[Item]:
    parsed = feedparser.parse(body)
    items: List[Item] = []
    for e in parsed.entries:
        title = (e.get("title") or "").strip()
        link = e.get("link") or ""
        if not title or not link:
            continue
        items.append(Item(
            source=f"reddit:r/{sub}",
            title=title,
            url=link,
            summary=(e.get("summary") or "")[:1000],
            author=e.get("author", ""),
            published=e.get("published", e.get("updated", "")),
        ))
    return items


def fetch(subreddits: List[str], limit_per_sub: int = 25) -> List[Item]:
    items: List[Item] = []
    for sub in subreddits:
        rss_url = f"https://www.reddit.com/r/{sub}/new.rss?limit={limit_per_sub}"
        r = get(rss_url, headers={"Accept": "application/rss+xml,*/*"})
        if r and r.status_code == 200 and (b"<rss" in r.content[:200].lower()
                                            or b"<feed" in r.content[:200].lower()):
            sub_items = _parse_rss(sub, r.content)
            if sub_items:
                items += sub_items
                continue

        json_url = f"https://www.reddit.com/r/{sub}/new.json?limit={limit_per_sub}"
        r = get(json_url, headers={"Accept": "application/json"})
        if not r or r.status_code != 200:
            print(f"[reddit] skip r/{sub}: rss/json both failed (last status={getattr(r, 'status_code', None)})")
            continue
        try:
            data = r.json()
        except Exception as e:
            print(f"[reddit] json parse failed for r/{sub}: {e}")
            continue
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            title = d.get("title", "").strip()
            permalink = d.get("permalink", "")
            external = d.get("url_overridden_by_dest") or ""
            url_final = external or f"https://www.reddit.com{permalink}"
            if not title or not url_final:
                continue
            items.append(Item(
                source=f"reddit:r/{sub}",
                title=title,
                url=url_final,
                summary=(d.get("selftext") or "")[:1000],
                author=d.get("author", ""),
                score=d.get("score"),
                published=str(d.get("created_utc", "")),
            ))
    return items
