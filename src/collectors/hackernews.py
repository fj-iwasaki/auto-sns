from typing import List
from urllib.parse import quote
from src.http import get
from src.models import Item


def fetch(queries: List[str], hours: int = 24, hits: int = 30) -> List[Item]:
    items: List[Item] = []
    import time
    since = int(time.time()) - hours * 3600
    for q in queries:
        url = (
            "https://hn.algolia.com/api/v1/search_by_date"
            f"?query={quote(q)}&tags=(story,comment)&hitsPerPage={hits}"
            f"&numericFilters=created_at_i>{since}"
        )
        r = get(url)
        if not r or r.status_code != 200:
            print(f"[hn] skip query '{q}': status={getattr(r, 'status_code', None)}")
            continue
        try:
            data = r.json()
        except Exception as e:
            print(f"[hn] json parse failed: {e}")
            continue
        for h in data.get("hits", []):
            title = (h.get("title") or h.get("story_title") or "").strip()
            url_final = h.get("url") or h.get("story_url")
            if not url_final:
                obj_id = h.get("objectID")
                if obj_id:
                    url_final = f"https://news.ycombinator.com/item?id={obj_id}"
            if not title or not url_final:
                continue
            items.append(Item(
                source=f"hackernews:{q}",
                title=title,
                url=url_final,
                summary=(h.get("comment_text") or h.get("story_text") or "")[:1000],
                author=h.get("author", ""),
                score=h.get("points"),
                published=h.get("created_at", ""),
            ))
    return items
