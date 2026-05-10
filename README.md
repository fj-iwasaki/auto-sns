# auto-sns: Claude Code / Codex 副業ダイジェスト → Teams 自動配信

X / Reddit / Hacker News / dev.to / Zenn / Qiita / Anthropic・OpenAI公式ブログ などから
**Claude Code・Codex を使った副業・収入化**に関する情報を1日3回（JST 07:00 / 12:00 / 17:00）
収集し、Geminiで日本語要約 + 実装ステップ化したうえで Teams チャットへ自動投稿します。

追加費用ゼロを目標とした構成:

| 機能 | 使うもの | 課金 |
|---|---|---|
| 収集 | 公開JSON / RSS（X は Nitter 経由ベストエフォート） | 無料 |
| 要約 | Google Gemini API（gemini-2.5-flash, 無料枠） | 無料枠で運用 |
| 配信 | Teams Workflows アプリの "Post to a chat when a webhook request is received" テンプレート | 無料 |
| 実行 | GitHub Actions cron | 無料枠 |

---

## 0. 既知の制約・注意

- **X / Instagram の公式 API は有料化されており、本ツールでは使っていません**。
  X は Nitter の公開インスタンスから RSS で取得しますが、停止・ブロックが頻発します。
  確実な X 取得が必要なら別途 X API Basic ($200/月〜) や RSSHub 自前ホストを検討してください。
- スクレイピングは各サービスの利用規約に従ってください。本リポジトリは公式 API・公開フィードのみを利用します。
- Gemini 無料枠の RPM / 1日あたりトークン上限を超える場合は `MAX_ITEMS` を下げるか、Anthropic/OpenAI 有料 API へ切り替えてください。

---

## 1. セットアップ

### 1-1. Teams Workflows アプリでフローを作る

本ツールは **リクエストボディ全体を Adaptive Card JSON として投稿** する方式に揃っています。
make.powerautomate.com で直接作成するルートは、近年のテナントで匿名 SAS URL（`sig=` 付き）が
発行されない設定が多く詰まりやすいので、**Teams 内蔵の Workflows アプリ経由**を推奨します。

1. **Microsoft Teams** を開く → 左サイドバーの「**アプリ**」（または「…その他のアプリ」）
2. 検索窓に `Workflows` → **Workflows** アプリを開く（必要なら「追加」）
3. 上部タブ **「Create」** → 検索窓に `webhook`
4. **`Post to a chat when a webhook request is received`** テンプレートを選択（chat 版。channel 版でも可）
5. コネクタのサインイン状態を **`Continue`** で承認
6. パラメータ:
   - **Microsoft Teams Chat**: 投稿先のチャットを選ぶ。
     **重要**: Teams の「Notes（自分用メモ）」スレッドは Graph API 上の正式な ChatThread ではないため
     `Call made for a thread which is not a ChatThread` エラーになります。
     事前に Teams で **自分自身宛のチャットを1件作成**（左メニュー「チャット」→ 新規チャットアイコン →
     宛先に自分のメールアドレスを入れて何か送信）してから、それを選択してください。
     `Chat with Flow bot` を選ぶ運用でも可。
7. **`Create flow`** を押す → 「Workflow created!」画面に表示される **HTTP URL**（末尾に `&sig=...` が付くもの）をコピー。
   これが `TEAMS_WEBHOOK_URL` の値です。

> 参考: 旧来の Teams 「Incoming Webhook」コネクタおよび「Post to a channel when a webhook is received」の旧版は
> Microsoft により段階的廃止されており、現状は **Workflows アプリのテンプレート経由**が公式の代替手段です。

#### このフローが期待するペイロード形式

このテンプレートは「**HTTP リクエストボディ全体を Adaptive Card JSON として解釈**」します。
本ツールの `src/notify.py` は次のような形でPOSTします（手動でカード形式を変えたい場合の参考）:

```json
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.4",
  "body": [
    { "type": "TextBlock", "size": "Large", "weight": "Bolder", "text": "ヘッダー", "wrap": true },
    { "type": "TextBlock", "text": "...", "wrap": true }
  ]
}
```

`title` / `text` / `attachments` などのラッパーは**含めません**。Workflows テンプレートの内部変数 `Body` がリクエストボディそのものを Adaptive Card として読みます。サイズ上限は約 25KB なので、`src/notify.py` の `_trim_to_fit` がはみ出した場合は highlights を末尾から削って収める仕組みです。

### 1-2. Gemini API キーを取得

1. https://aistudio.google.com/app/apikey でキー発行（Google アカウントで無料）。
2. これが `GEMINI_API_KEY`。

### 1-3. リポジトリを GitHub に push

```pwsh
cd C:\work\auto-sns
git init
git add .
git commit -m "init: auto-sns digest pipeline"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

### 1-4. GitHub Secrets / Variables を設定

リポジトリの Settings → Secrets and variables → Actions:

**Secrets**
- `GEMINI_API_KEY`
- `TEAMS_WEBHOOK_URL`

**Variables**（任意）
- `NITTER_INSTANCES`: 例 `https://nitter.net,https://nitter.privacydev.net`
   空 or 未設定なら X 収集をスキップ（推奨：まずは未設定で動かして、Reddit/HN/RSS だけで動作確認）
- `MAX_ITEMS`: 例 `15`

### 1-5. 動作確認

GitHub の Actions タブから `SNS digest to Teams` を開き **Run workflow** で手動実行。
- `dry_run=true` にすると Teams へ送らずログだけ確認できる。
- 成功すれば `state/seen.json` がコミットされ、次回以降は重複URLを除外する。

---

## 2. ローカル動作確認（Windows / PowerShell）

```pwsh
cd C:\work\auto-sns
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
# .env を編集して GEMINI_API_KEY と TEAMS_WEBHOOK_URL を設定

# まずは送信せず確認
python -m src.main --dry-run --slot morning

# 実送信
python -m src.main --slot morning
```

---

## 3. ファイル構成

```
auto-sns/
├─ .github/workflows/digest.yml   # cron (JST 07/12/17)
├─ config/
│  ├─ feeds.yaml                  # 収集ソース定義
│  └─ keywords.yaml               # フィルタキーワード
├─ src/
│  ├─ collectors/                 # Reddit / HN / dev.to / RSS / Nitter
│  ├─ filter.py                   # キーワード絞り込み・dedupe・rank
│  ├─ llm.py                      # Gemini要約（無料枠）
│  ├─ notify.py                   # Power Automate webhook → Teams
│  ├─ state.py                    # 既送URLキャッシュ
│  └─ main.py                     # オーケストレーション
├─ requirements.txt
├─ .env.example
└─ README.md
```

---

## 4. 出力イメージ（Teams で受け取るもの）

> ☀️ 朝 05/11 07:00 | Claude Code / Codex 副業ダイジェスト
>
> 今日のハイライト: Claude Code のサブエージェント機能を使った受託開発効率化が複数...
>
> ### [Claude CodeのSubagentで実装委譲を自動化した話](https://...)
> Claude Code のサブエージェント機能で要件定義→実装を分業し...
> 💡 **収益化:** 受託案件のテンプレ化で工数を半分にし時間単価を上げる
> **着手ステップ:**
> 1. `claude /agents create implementer` でサブエージェント定義
> 2. ...
> `claude-code` `受託`

---

## 5. カスタマイズ

- **キーワードを変える** → `config/keywords.yaml` の `include_any` / `exclude_any`
- **収集元を増やす** → `config/feeds.yaml` に RSS URL や subreddit を追加
- **時刻を変える** → `.github/workflows/digest.yml` の cron（UTCで指定）
- **Gemini 以外で要約したい** → `src/llm.py` の `summarize` を Anthropic / OpenAI SDK に差し替え

---

## 6. トラブルシュート

| 症状 | 原因 / 対処 |
|---|---|
| Webhook 呼び出しが `401 DirectApiAuthorizationRequired` | URL に `&sig=...` が付いていない＝OAuth 必須の Direct API URL になっている。Teams Workflows アプリ経由（§1-1）でフローを作り直す。`make.powerautomate.com` 直接作成は近年のテナントで匿名URLが発行されない場合が多い |
| `Call made for a thread which is not a ChatThread` で投稿失敗 | 投稿先が「Notes（自分用メモ）」スレッドになっている。Teams で **自分宛のチャットを別途1件作成**してフローの "Microsoft Teams Chat" 設定で選び直す。`Chat with Flow bot` でも可 |
| `Property 'type' must be 'AdaptiveCard'` | リクエストボディ全体が Adaptive Card である必要がある。`{type:"AdaptiveCard", version:"1.4", body:[...]}` の形で送る（`src/notify.py` は既にこの形） |
| Teams に届かないがフローは「成功」 | フローの実行履歴で投稿アクションの「入力」を確認。`Body` 変数が空評価されている場合は §1-1 のテンプレ通りに作り直すのが早い |
| Gemini が `RESOURCE_EXHAUSTED` | 無料枠超過。`MAX_ITEMS` を下げる、もしくは1日2回に減らす |
| Gemini が JSON decode 失敗 | `max_output_tokens` 不足の可能性。`src/llm.py` の値を上げる（現在 16384）。それでも失敗する場合 `[llm] last 200 chars` のログから原因特定 |
| Reddit が 403 | User-Agent ブロックが厳しい。`src/http.py` の UA を変更するか、Reddit を諦めて他ソースで運用（HN・dev.to・Zenn・Qiitaだけでも十分量取れる） |
| Nitter が全滅 | 公開インスタンスは寿命短い。`NITTER_INSTANCES` を空にして X はスキップ運用が現実的 |
| GitHub Actions の時刻ズレ | cron は UTC。サマータイム影響なし、JST 固定で動く |
