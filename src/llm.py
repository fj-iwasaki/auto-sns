"""Gemini無料枠で日本語要約と実装ステップ生成。

API key無し、もしくはAPI失敗時はテンプレベースのフォールバックで動作継続。
"""
import json
import os
from typing import List
from src.models import Item


SYSTEM = """あなたはAIエンジニア向けの編集者です。Claude Code / Codex を使った副業・収入化のヒントを抽出します。
出力は厳密にJSONのみ。前後に説明文やコードフェンスを付けない。
JSONスキーマ:
{
  "highlights": [
    {
      "title": "短い日本語タイトル",
      "url": "元URL",
      "summary": "150文字以内の日本語要約",
      "income_idea": "副業/収益化として何ができるか（80文字以内、日本語）",
      "how_to_start": ["具体的な実装ステップ", "..."],
      "tags": ["claude-code" など最大4個]
    }
  ],
  "overall": "今日のダイジェスト総評（200文字以内、日本語）"
}
ルール:
- 必ず元URLをそのまま保持。
- 副業に直結しない投稿（単なるリリースノート等）は省く。最大8件。
- how_to_startは具体的・実行可能なステップを3〜5個。Claude Code / Codex のコマンドや手順を含める。
"""


def _items_to_prompt(items: List[Item]) -> str:
    rows = []
    for i, it in enumerate(items, 1):
        rows.append(
            f"[{i}] source={it.source} | score={it.score}\n"
            f"title: {it.title}\nurl: {it.url}\n"
            f"summary: {it.summary[:500]}\n"
        )
    return "\n".join(rows)


def _fallback(items: List[Item]) -> dict:
    highlights = []
    for it in items[:8]:
        highlights.append({
            "title": it.title[:60],
            "url": it.url,
            "summary": (it.summary or it.title)[:150],
            "income_idea": "(LLM未使用) 元記事を確認し副業導線を検討",
            "how_to_start": ["元記事を読む", "Claude CodeまたはCodexで再現を試す"],
            "tags": [it.source.split(":")[0]],
        })
    return {
        "highlights": highlights,
        "overall": "Gemini未設定のため簡易リスト表示中。GEMINI_API_KEYを設定すると要約が有効化されます。",
    }


def summarize(items: List[Item]) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or not items:
        return _fallback(items)

    try:
        import warnings
        warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
        import google.generativeai as genai
    except ImportError:
        print("[llm] google-generativeai not installed, fallback")
        return _fallback(items)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM,
        )
        prompt = "次の記事リストから副業・収入化に関係するハイライトを抽出してください。\n\n" + _items_to_prompt(items)
        resp = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,
                "response_mime_type": "application/json",
                "max_output_tokens": 16384,
            },
        )
        text = resp.text or ""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as je:
            finish = getattr(resp.candidates[0], "finish_reason", None) if resp.candidates else None
            print(f"[llm] gemini JSON decode failed (finish={finish}): {je}")
            print(f"[llm] last 200 chars: {text[-200:]!r}")
            return _fallback(items)
        if "highlights" not in data:
            raise ValueError("missing highlights field")
        return data
    except Exception as e:
        print(f"[llm] gemini failed: {e}; using fallback")
        return _fallback(items)
