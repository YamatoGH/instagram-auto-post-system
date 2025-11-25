import json
from typing import Dict, Any, List
from utils.llm import run_gpt_json, run_gpt 
import os
import requests
from dotenv import load_dotenv

load_dotenv()

template_selector_prompt = """
You are an Instagram auto-post system's Caption Planner.

### Task
Based on:
- business_type
- title
- direction
and the template list below (TEMPLATES),

Return:
`selected_template` : best matching template name  


### Template rules
Choose the best category using:
1. title (keywords strongly determine category)
2. direction (intent: product / location / tips / story / announcement / case)
3. caption_structure match
4. business_type only filters out unnatural choices

### Output JSON ONLY:
{{
  "selected_template": "<template_name>"
}}

### TEMPLATES
{TEMPLATES}
"""





def filter_templates(templates_json: Dict[str, Any], required_keys: List[str]) -> Dict[str, Any]:
    """
    テンプレートJSONから必要なキーのみ抽出した軽量テンプレJSONを返す。

    Args:
        templates_json: テンプレート JSON
        required_keys: 抜き取りたい項目（例: ["name", "caption_structure"]）

    Returns:
        抽出されたテンプレ JSON
    """

    filtered = {"categories": []}

    for category in templates_json.get("categories", []):
        new_category = {}
        for key in required_keys:
            if key in category:
                new_category[key] = category[key]

        # name がないと破綻するため強制チェック
        if "name" not in new_category:
            raise ValueError(f"テンプレカテゴリに 'name' がありません: {category}")

        filtered["categories"].append(new_category)

    return filtered





# -------------------------------------------------
# Template Selector 実行関数（run_gpt_json を利用）
# -------------------------------------------------
def run_template_selector(
    user_input: Dict[str, Any],
    templates_json: Dict[str, Any],
):
    """
    module to get caption plan from template and user input.
    Caption Planner モジュールのメイン関数
    - System Prompt を生成
    - user_input をプロンプトに渡す
    - run_gpt_json() を利用して JSON を受け取る
    """
    
    extracted_templates = filter_templates(
        templates_json,
        required_keys=["name", "caption_structure"]
    )

    system_prompt = template_selector_prompt.format(
        TEMPLATES=json.dumps(extracted_templates, ensure_ascii=False, indent=2)
    )

    # history= に system prompt を最初のメッセージとして渡す
    return run_gpt_json(
        prompt=json.dumps(user_input, ensure_ascii=False),
        history=[{"role": "system", "content": system_prompt}],
        max_completion_tokens=1024,
    )






caption_planner_prompt = """
You are the Caption Planner AI.

### Purpose
Using:
- selected_template
- full template data (caption_structure, writing_style, etc.)
- business_type
- title
- direction

Generate:
1) "caption_plan": a structural plan customized to the user's title, business_type, and direction
2) "query": only the necessary info requests for later RAG retrieval

### Behavior

- caption_plan:
  - Follow the selected template's caption_structure
  - BUT adapt the plan to the user's:
      - title (specific topic)
      - direction (intent)
      - business_type (context)

- query:
  - Only include info that cannot be created automatically
  - Must be factual, specific, and RAG-friendly
  - Do NOT create queries for sections like:
      - generic introduction
      - closing sentences
      - generic hashtag parts

### Output Format (STRICT)

Return ONLY one JSON object:

{{
  "caption_plan": "<plan customized for the user>",
  "query": ["<query1>", "<query2>", "..."]
}}

### Template Provided
{TEMPLATE}
"""





def run_caption_planner(
    user_input: Dict[str, Any],
    selected_template: str,
    templates_json: Dict[str, Any],
):
    """
    Caption Planner:
    user_input = {
        "business_type": ...,
        "title": ...,
        "direction": ...
    }

    selected_template = template_selector の出力
    """

    # --- 1. テンプレ取得（全情報） ---
    target = None
    for c in templates_json["categories"]:
        if c["name"] == selected_template:
            target = c
            break

    if target is None:
        raise ValueError(f"Template not found: {selected_template}")

    # --- 2. Caption Planner 用プロンプト作成 ---
    system_prompt = caption_planner_prompt.format(
        TEMPLATE=json.dumps(target, ensure_ascii=False, indent=2)
    )

    # --- 3. GPT に渡す最終 user payload ---
    payload = {
        "selected_template": selected_template,
        **user_input   # ← business_type, title, direction をそのまま展開
    }

    # --- 4. GPT 実行 ---
    return run_gpt_json(
        prompt=json.dumps(payload, ensure_ascii=False),
        history=[{"role": "system", "content": system_prompt}],
        max_completion_tokens=1024,
    )





# -----------------------------
# APIキーを1回だけロード
# -----------------------------
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
if not SERPER_API_KEY:
    raise ValueError("SERPER_API_KEY is missing from environment variables")

SERPER_URL = "https://google.serper.dev/search"
SERPER_HEADERS = {
    "X-API-KEY": SERPER_API_KEY,
    "Content-Type": "application/json"
}


def web_rag_search(queries: List[str], *, num_results: int = 3) -> List[Dict[str, Any]]:
    """
    RAG用のWeb検索。
    - queries: Caption Planner が生成した query のリスト
    - Serper API による Google検索
    """

    rag_results = []

    for q in queries:
        payload = {"q": q, "num": num_results}

        response = requests.post(SERPER_URL, headers=SERPER_HEADERS, json=payload)
        data = response.json()

        extracted = []
        for item in data.get("organic", []):
            extracted.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", "")
            })

        rag_results.append({
            "query": q,
            "results": extracted
        })

    return rag_results



caption_writer_prompt = """
You are the Caption Writer AI for an Instagram auto-post system.

### Your goal
Generate a final Instagram caption based on:
- business_type
- title
- direction
- selected_template
- template data (caption_structure, writing_style, hashtag_pattern, etc.)
- caption_plan (outline generated by the Caption Planner)
- rag_results (factual/context information retrieved via RAG)

### Inputs (from the user message as JSON)
- business_type: what kind of business this is
- title: post title or main topic
- direction: intent of the post (what to emphasize)
- caption_plan: structural plan you MUST roughly follow
- rag_results: list of objects { "query": "...", "context": "..." }

### How to write

1. Follow the template's caption_structure and the given caption_plan
   - Use caption_plan as the outline (sections and flow)
   - You don't have to label sections; just write a natural caption

2. Use rag_results as factual/context information
   - Read each { query, context }
   - Use context to enrich the caption with concrete details
   - Do NOT copy context verbatim; rewrite naturally in English
   - If some queries have no useful context, just ignore them

3. Respect template writing_style when possible:
   - tone (casual / friendly / etc.)
   - emoji_usage
   - sentence_length
   - formatting (line breaks, emphasis)
   - punctuation

4. Hashtags:
   - At the end of the caption, generate hashtags based on:
     - hashtag_pattern in the template (if available)
     - business_type
     - title / content
   - Use English 
   - Put all hashtags in the last 1〜2 lines

5. Very important:
   - Do NOT output the plan or queries
   - Do NOT explain what you are doing
   - Output ONLY the final caption text, no JSON, no extra wrapping
"""






def run_caption_writer(
    user_input: Dict[str, Any],
    selected_template: str,
    templates_json: Dict[str, Any],
    caption_plan_result: Dict[str, Any],
    rag_results: List[Dict[str, str]],
) -> str:
    """
    Caption Writer:
    - caption_plan + RAG + writing_style を基に最終キャプションを生成
    """

    # 1. テンプレの writing_style のみ取得
    writing_style = None
    for c in templates_json.get("categories", []):
        if c.get("name") == selected_template:
            writing_style = c.get("writing_style", {})
            break

    if writing_style is None:
        raise ValueError(f"writing_style not found for template: {selected_template}")

    # 2. system prompt 構築
    system_prompt = (
        caption_writer_prompt
        + "\n\n### Writing Style\n"
        + json.dumps(writing_style, ensure_ascii=False, indent=2)
    )

    # 3. モデルへ渡す payload
    payload = {
        "business_type": user_input.get("business_type"),
        "title": user_input.get("title"),
        "direction": user_input.get("direction"),
        "caption_plan": caption_plan_result.get("caption_plan"),
        "rag_results": rag_results,
    }

    # 4. GPT 呼び出し
    caption = run_gpt(
        prompt=json.dumps(payload, ensure_ascii=False),
        history=[{"role": "system", "content": system_prompt}],
        max_completion_tokens=2048,
    )

    return caption









def generate_instagram_caption(
    user_input: Dict[str, Any],
    templates_json: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Instagram 自動投稿生成のフルパイプライン。
    - Template Selector
    - Caption Planner
    - Web RAG
    - Caption Writer
    
    最終キャプションと中間結果すべて返す。
    """

    # ----------------------------------------
    # 1. Template Selector（テンプレ選択）
    # ----------------------------------------
    selector_output = run_template_selector(
        user_input=user_input,
        templates_json=templates_json,
    )
    selected_template = selector_output["selected_template"]

    # ----------------------------------------
    # 2. Caption Planner（構造作成 & RAGクエリ生成）
    # ----------------------------------------
    planner_output = run_caption_planner(
        user_input=user_input,
        selected_template=selected_template,
        templates_json=templates_json,
    )

    # 生成されたクエリ
    rag_queries = planner_output.get("query", [])

    # ----------------------------------------
    # 3. Web RAG（Serper検索）
    # ----------------------------------------
    rag_results = []
    if rag_queries:
        rag_results = web_rag_search(rag_queries)

    # ----------------------------------------
    # 4. Caption Writer（最終キャプション生成）
    # ----------------------------------------
    final_caption = run_caption_writer(
        user_input=user_input,
        selected_template=selected_template,
        templates_json=templates_json,
        caption_plan_result=planner_output,
        rag_results=rag_results,
    )

    # ----------------------------------------
    # 戻り値（最終キャプション＋ログ）
    # ----------------------------------------
    return {
        "template_selector": selector_output,
        "caption_planner": planner_output,
        "rag_results": rag_results,
        "final_caption": final_caption,
    }
