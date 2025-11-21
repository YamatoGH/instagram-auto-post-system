# instagram-auto-post-system

Instagram へ「キャプション生成 → 画像アップロード → カルーセル投稿」までを自動化するツールです。Notebook やスクリプトから関数を呼び出す形で動作します。

## 仕組みの流れ
- `main.auto_post_instagram()` が司令塔。`user_input`（事業種別・タイトル・方向性）、ローカル画像パス、テンプレート JSON を受け取り、キャプション生成と投稿をまとめて実行。
- キャプション生成は `utils/caption_agent.py` で実行  
  1) Template Selector (`run_template_selector`): タイトル/方向性から最適テンプレートを LLM で選択  
  2) Caption Planner (`run_caption_planner`): 選択テンプレートを元に構成案と RAG 用クエリを生成  
  3) Web RAG (`web_rag_search`): Serper API で必要情報を検索し要約  
  4) Caption Writer (`run_caption_writer`): RAG 結果とテンプレの文体規則を使い最終キャプション生成  
  5) `generate_instagram_caption()` は中間結果と最終キャプションを返す
- 投稿は `utils/post_instagram.py` が担当  
  - 画像を GCS へアップロードし署名付き URL を作成 (`upload_to_gcs`)  
  - Instagram Graph API で子メディアを作成→親カルーセルを publish (`create_child_media`, `publish_carousel`)  
  - `post_to_instagram()` は画像リストとキャプションを受け取り投稿まで完結
- LLM 呼び出しは `utils/llm.py` でラップし、OpenAI Chat Completions を利用

## モジュールと役割
- `main.py` : `auto_post_instagram()` を提供するエントリーポイント
- `utils/caption_agent.py` : テンプレ選択／構成案生成／RAG／キャプション生成の一連処理
- `utils/llm.py` : OpenAI API 呼び出しラッパー (`run_gpt`, `run_gpt_json`)
- `utils/post_instagram.py` : GCS へのアップロードと Instagram Graph API でのカルーセル投稿
- `utils/template_example.json` : テンプレート例（カテゴリ名・構成・文体・ハッシュタグ方針など）

## 必要な環境変数（.env で読み込み）
- `OPENAI_API_KEY` : LLM 呼び出し用
- `SERPER_API_KEY` : Web 検索（Serper）
- `GOOGLE_APPLICATION_CREDENTIALS` : GCS 用サービスアカウント JSON のパス
- `GCS_BUCKET_NAME` : 画像を置く GCS バケット名
- `IG_USER_ID` : Instagram Graph API のユーザー ID
- `IG_ACCESS_TOKEN` : Instagram Graph API トークン

## セットアップと実行例
依存ライブラリ（例）: `openai`, `python-dotenv`, `google-cloud-storage`, `requests`

```bash
pip install openai python-dotenv google-cloud-storage requests
```

```python
import json
from main import auto_post_instagram

user_input = {
    "business_type": "travel_agency",
    "title": "Kyoto private tour",
    "direction": "story"
}

with open("utils/template_example.json", "r", encoding="utf-8") as f:
    templates = json.load(f)

image_paths = ["images/sample1.png", "images/sample2.png"]
auto_post_instagram(user_input, image_paths, templates)
```

## 依存関係ダイアグラム
```mermaid
flowchart TD
  IN[Input (business_type/title/direction, image paths, templates)] --> TS[run_template_selector]
  TS --> CP[run_caption_planner]
  CP --> RAG[RAG: web_rag_search -> Serper API]
  CP --> CW[run_caption_writer]
  RAG --> CW
  CW --> OUT[投稿]
```
