import json
from typing import Dict, Any, List
from utils.llm import run_gpt_json 



caption_planner_prompt = """
You are an Instagram auto-post system's Caption Planner.

### Task
Based on:
- business_type
- title
- direction
and the template list below (TEMPLATES),

Return:
1. `selected_template` : best matching template name  
2. `required_info` : list of questions needed to write the caption

### Template rules
Choose the best category using:
1. title (keywords strongly determine category)
2. direction (intent: product / location / tips / story / announcement / case)
3. caption_structure match
4. business_type only filters out unnatural choices

### Question rules
Use the selected template's caption_structure.
Make simple, concise questions.
Ask only what is necessary to write the caption.

### Output JSON ONLY:
{{
  "selected_template": "<template_name>",
  "required_info": ["<q1>", "<q2>",...]
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
# 2. Caption Planner 実行関数（run_gpt_json を利用）
# -------------------------------------------------
def run_caption_planner(
    user_input: Dict[str, Any],
    templates_json: Dict[str, Any],
    *,
    model: str = "gpt-5-nano",
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

    system_prompt = caption_planner_prompt.format(
        TEMPLATES=json.dumps(extracted_templates, ensure_ascii=False, indent=2)
    )

    # history= に system prompt を最初のメッセージとして渡す
    return run_gpt_json(
        prompt=json.dumps(user_input, ensure_ascii=False),
        history=[{"role": "system", "content": system_prompt}],
        model=model,
        parse_json=True,
        max_completion_tokens=1024,
    )


