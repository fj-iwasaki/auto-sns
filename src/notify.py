"""Power Automate (Teams Workflows) → Teams投稿フローへ送信。

Teams Workflows アプリの "Post to a chat when a webhook request is received"
テンプレートはリクエストボディ全体を Adaptive Card JSON として解釈する。
よって本モジュールは Adaptive Card をルート階層で送る。
"""
import json
import os
from typing import Optional
import requests


def _build_card(digest: dict, title_prefix: str) -> dict:
    body = [
        {
            "type": "TextBlock",
            "size": "Large",
            "weight": "Bolder",
            "text": f"{title_prefix} | Claude Code / Codex 副業ダイジェスト",
            "wrap": True,
        }
    ]
    overall = digest.get("overall", "")
    if overall:
        body.append({"type": "TextBlock", "text": overall, "wrap": True, "isSubtle": True})

    for h in digest.get("highlights", [])[:8]:
        title = h.get("title", "(no title)")
        url = h.get("url", "")
        summary = h.get("summary", "")
        idea = h.get("income_idea", "")
        steps = h.get("how_to_start") or []
        tags = h.get("tags") or []

        body.append({"type": "TextBlock", "text": f"**[{title}]({url})**", "wrap": True, "spacing": "Medium"})
        if summary:
            body.append({"type": "TextBlock", "text": summary, "wrap": True})
        if idea:
            body.append({"type": "TextBlock", "text": f"💡 {idea}", "wrap": True, "color": "Accent"})
        if steps:
            body.append({
                "type": "TextBlock",
                "text": "\n".join(f"- {s}" for s in steps[:5]),
                "wrap": True,
            })
        if tags:
            body.append({"type": "TextBlock", "text": " ".join(f"`{t}`" for t in tags), "wrap": True, "isSubtle": True})

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": body,
    }


def _build_markdown(digest: dict, title_prefix: str) -> str:
    lines = [f"## {title_prefix} | Claude Code / Codex 副業ダイジェスト", ""]
    overall = digest.get("overall", "")
    if overall:
        lines += [overall, ""]
    for h in digest.get("highlights", [])[:8]:
        title = h.get("title", "(no title)")
        url = h.get("url", "")
        lines.append(f"### [{title}]({url})")
        if h.get("summary"):
            lines.append(h["summary"])
        if h.get("income_idea"):
            lines.append(f"💡 **収益化:** {h['income_idea']}")
        steps = h.get("how_to_start") or []
        if steps:
            lines.append("**着手ステップ:**")
            lines += [f"1. {s}" for s in steps[:5]]
        tags = h.get("tags") or []
        if tags:
            lines.append(" ".join(f"`{t}`" for t in tags))
        lines.append("")
    return "\n".join(lines)


CARD_SIZE_LIMIT_BYTES = 24_000  # Teams Adaptive Card は ~25KB が上限


def _trim_to_fit(digest: dict, title_prefix: str) -> dict:
    """サイズ超過時は highlights を削って収める。"""
    digest = dict(digest)
    highlights = list(digest.get("highlights", []))
    while True:
        card = _build_card({**digest, "highlights": highlights}, title_prefix)
        size = len(json.dumps(card, ensure_ascii=False).encode("utf-8"))
        if size <= CARD_SIZE_LIMIT_BYTES or len(highlights) <= 1:
            return card
        highlights.pop()


def send(digest: dict, title_prefix: str, webhook_url: Optional[str] = None) -> bool:
    webhook_url = webhook_url or os.environ.get("TEAMS_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print("[notify] TEAMS_WEBHOOK_URL not set; printing payload only")
        print(json.dumps(digest, ensure_ascii=False, indent=2))
        return False

    payload = _trim_to_fit(digest, title_prefix)
    try:
        r = requests.post(webhook_url, json=payload, timeout=20)
        if r.status_code >= 300:
            print(f"[notify] webhook returned {r.status_code}: {r.text[:300]}")
            return False
        return True
    except requests.RequestException as e:
        print(f"[notify] webhook failed: {e}")
        return False
