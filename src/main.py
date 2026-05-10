"""エントリーポイント: 収集 → フィルタ → 要約 → Teams送信。

実行例:
  python -m src.main                # 通常実行（送信あり）
  python -m src.main --dry-run      # 送信せず標準出力
  python -m src.main --slot morning # スロット名のラベル指定
"""
import argparse
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Windows コンソール (cp932) で絵文字を print してもクラッシュしないように
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

import yaml
from dotenv import load_dotenv

from src import filter as flt
from src import llm, notify, state
from src.collectors import devto, hackernews, nitter, reddit, rss
from src.models import Item


JST = timezone(timedelta(hours=9))


def _slot_label(slot: str | None) -> str:
    now = datetime.now(JST)
    if slot == "morning":
        return f"☀️ 朝 {now:%m/%d 07:00}"
    if slot == "noon":
        return f"🍱 昼 {now:%m/%d 12:00}"
    if slot == "evening":
        return f"🌆 夕 {now:%m/%d 17:00}"
    return f"{now:%m/%d %H:%M JST}"


def load_config() -> tuple[dict, dict]:
    root = Path(__file__).resolve().parents[1]
    feeds = yaml.safe_load((root / "config" / "feeds.yaml").read_text("utf-8")) or {}
    keywords = yaml.safe_load((root / "config" / "keywords.yaml").read_text("utf-8")) or {}
    return feeds, keywords


def collect_all(feeds: dict) -> list[Item]:
    items: list[Item] = []
    items += reddit.fetch(feeds.get("reddit_subs", []))
    items += hackernews.fetch(feeds.get("hn_queries", []))
    items += devto.fetch(feeds.get("devto_tags", []))
    items += rss.fetch(feeds.get("rss_feeds", []))

    nitter_instances = [
        s.strip() for s in os.environ.get("NITTER_INSTANCES", "").split(",") if s.strip()
    ]
    if nitter_instances:
        items += nitter.fetch(feeds.get("nitter_users", []), nitter_instances)
    else:
        print("[main] NITTER_INSTANCES empty -> skip X collection")

    print(f"[main] collected total={len(items)}")
    return items


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--slot", choices=["morning", "noon", "evening"])
    parser.add_argument("--max-items", type=int,
                        default=int(os.environ.get("MAX_ITEMS") or "15"))
    args = parser.parse_args()

    feeds, keywords = load_config()
    items = collect_all(feeds)

    inc = keywords.get("include_any", [])
    exc = keywords.get("exclude_any", [])
    items = [it for it in items if flt.keep(it, inc, exc)]
    print(f"[main] after keyword filter={len(items)}")

    items = flt.dedupe(items)
    print(f"[main] after dedupe={len(items)}")

    seen = state.load_seen()
    fresh = [it for it in items if it.key() not in seen]
    print(f"[main] fresh (not seen before)={len(fresh)}")

    if not fresh:
        print("[main] nothing new, skip notification")
        return 0

    fresh = flt.rank(fresh)[: args.max_items]

    digest = llm.summarize(fresh)
    label = _slot_label(args.slot)

    if args.dry_run:
        print("=== DRY RUN OUTPUT ===")
        print(notify._build_markdown(digest, label))
        return 0

    ok = notify.send(digest, label)
    if ok:
        new_seen = list(seen) + [it.key() for it in fresh]
        state.save_seen(new_seen)
        print(f"[main] notified, seen cache size={len(new_seen)}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
