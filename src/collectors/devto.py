from typing import List
from src.http import get
from src.models import Item


def fetch(tags: List[str], per_tag: int = 20) -> List[Item]:
    items: List[Item] = []
    for tag in tags:
        url = f"https://dev.to/api/articles?tag={tag}&per_page={per_tag}&top=1"
        r = get(url)
        if not r or r.status_code != 200:
            print(f"[devto] skip tag {tag}: status={getattr(r, 'status_code', None)}")
            continue
        try:
            arr = r.json()
        except Exception as e:
            print(f"[devto] json parse failed: {e}")
            continue
        for a in arr:
            title = (a.get("title") or "").strip()
            url_final = a.get("url")
            if not title or not url_final:
                continue
            items.append(Item(
                source=f"devto:{tag}",
                title=title,
                url=url_final,
                summary=(a.get("description") or "")[:1000],
                author=(a.get("user") or {}).get("username", ""),
                score=a.get("public_reactions_count"),
                published=a.get("published_at", ""),
            ))
    return items
