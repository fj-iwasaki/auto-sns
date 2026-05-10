from typing import List, Iterable
from src.models import Item


def _hay(item: Item) -> str:
    return f"{item.title}\n{item.summary}".lower()


def keep(item: Item, include_any: Iterable[str], exclude_any: Iterable[str]) -> bool:
    hay = _hay(item)
    if any(bad.lower() in hay for bad in exclude_any):
        return False
    inc = list(include_any)
    if not inc:
        return True
    return any(needle.lower() in hay for needle in inc)


def dedupe(items: List[Item]) -> List[Item]:
    seen = set()
    out: List[Item] = []
    for it in items:
        k = it.key()
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def rank(items: List[Item]) -> List[Item]:
    """スコアと公開日時の降順。スコア無しは0扱い。"""
    def score(it: Item):
        s = it.score if isinstance(it.score, (int, float)) else 0
        return (s, it.published or "")
    return sorted(items, key=score, reverse=True)
