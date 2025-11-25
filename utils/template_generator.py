# utils/template_generator.py

import json
from typing import Dict, Any
from utils.llm import run_gpt_json


# -------------------------------------------------
# 1. System Prompt: キャプション → テンプレ抽出
# -------------------------------------------------

TEMPLATE_EXTRACTION_PROMPT = """
あなたは Instagram 自動投稿システムの「テンプレート抽出AI」です。

目的：
ユーザーが入力したキャプションを分析し、
投稿内容に依存しすぎない “汎用テンプレート” を生成してください。

## 重要な制約
1. caption_structure は投稿内容ではなく **一般的・普遍的な構造** にしてください。
   - 例：イントロ / 説明 / 特徴 / メリット / 体験内容 / おすすめ / 締め / ハッシュタグ
   - 投稿キャプションの本文をそのまま構造名にしない。

2. writing_style は投稿に依存しすぎないよう、  
   以下の **分類カテゴリ** のいずれかを選んでください：
   - calm & sacred（落ち着いた・神聖）
   - friendly & supportive（やさしく支援的）
   - casual（カジュアル）
   - informative（情報提供型）
   - energetic（元気・ポジティブ）
   - elegant（上品・スタイリッシュ）

   この分類の範囲内で、emoji_usage / formatting / punctuation も一般化してください。

3. hashtag_pattern は投稿固有タグを使わず、  
   **一般化されたタグカテゴリ** のみを使用してください。
   - #地域名
   - #業種名
   - #サービス名
   - #ブランド名
   - #関連テーマ

4. example_structure は「入力キャプションの内容に沿って良い」。  
   しかし、**例文としての簡潔な説明にすること**。

5. example_caption は **入力キャプションをそのまま返す**。  
   ※絶対に編集しない、加筆しない、翻訳もしない。

6. 出力は **1つの JSON のみ**。説明文を混ぜない。

## Few-shot：既存テンプレ例
以下は既存のテンプレ例です。この形式を必ず参考にしてください。

{TEMPLATE_EXAMPLES}

## 出力形式（絶対に正確に守ること）

{{
  "name": "<テンプレート名（短く）>",
  "caption_structure": ["...", "..."],
  "writing_style": {{
      "tone": "",
      "emoji_usage": "",
      "sentence_length": "",
      "formatting": "",
      "punctuation": ""
  }},
  "hashtag_pattern": ["...", "..."],
  "example_structure": ["...", "..."],
  "example_caption": "<入力キャプションをそのまま返す>"
}}

"""


# -------------------------------------------------
# 2. Validation helper
# -------------------------------------------------

REQUIRED_TEMPLATE_KEYS = [
    "name",
    "caption_structure",
    "writing_style",
    "hashtag_pattern",
    "example_structure",
    "example_caption",
]


def _validate_template_dict(data: Dict[str, Any]):
    """
    Validate that the template JSON has all required keys and structure.
    Raise ValueError if invalid.
    """
    for key in REQUIRED_TEMPLATE_KEYS:
        if key not in data:
            raise ValueError(f"Missing required template field: {key}")

    if not isinstance(data["caption_structure"], list):
        raise ValueError("caption_structure must be a list")

    if not isinstance(data["example_structure"], list):
        raise ValueError("example_structure must be a list")

    if not isinstance(data["hashtag_pattern"], list):
        raise ValueError("hashtag_pattern must be a list")

    if not isinstance(data["writing_style"], dict):
        raise ValueError("writing_style must be a dict")

    return True


# -------------------------------------------------
# 3. Public API: caption → template
# -------------------------------------------------

def generate_template_from_post(caption_text: str) -> Dict[str, Any]:
    """
    キャプションを入力するとテンプレートJSONを生成する関数。
    GPTはSTRICT JSONで返すように制御している。
    """

    result = run_gpt_json(
        prompt=caption_text,
        history=[{"role": "system", "content": TEMPLATE_EXTRACTION_PROMPT}],
        max_completion_tokens=2048,
    )

    # Validate structure
    _validate_template_dict(result)

    return result
