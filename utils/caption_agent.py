import json
from typing import Dict, Any, List
from utils.llm import run_gpt_json 


caption_planner_prompt = """
あなたは Instagram 自動投稿システムの「投稿プラン生成AI（Caption Planner）」です。

あなたの役割は、ユーザーの入力
- business_type（事業内容）
- title（タイトル）
- direction（投稿の内容方針）
と、システム側が渡すテンプレート情報（TEMPLATES）を基に、

1. 投稿内容に最も適したテンプレートカテゴリ（selected_template）を1つ選ぶ  
2. キャプション生成に必要な追加情報（required_info）を質問形式で生成する  

この2つだけを行います。

----------------------------------------
【テンプレート】
{templates}
----------------------------------------

【テンプレ選択ルール（最適化）】

テンプレートの選択は以下の優先順位に従って行う：

1. title
   タイトルに含まれるキーワードからカテゴリを推定する
   例)
   - 商品・メニュー名 → product
   - 地名・景色 → location
   - ノウハウ・歴史・解説 → tips
   - 出来事・人物・感情 → story
   - 告知・変更 → announcement
   - 実績・事例 → case

2. direction
   例)
   - 「魅力を伝えたい」→ product / location  
   - 「雰囲気を伝えたい」→ location  
   - 「知識を伝えたい」→ tips  
   - 「体験を語りたい」→ story  
   - 「告知をしたい」→ announcement  
   - 「成果・ビフォーアフター」→ case  

3. caption_structure（カテゴリ固有の構造）との一致度
   - direction が重視する情報と構造が最も一致するカテゴリを優先する

4. business_type は “不自然なカテゴリを排除するための補助” としてのみ使用
   - 主要判断には使わない
   - 不自然な場合のみ再評価する

最も整合性の高いカテゴリを必ず1つだけ選ぶこと。

----------------------------------------
【質問生成ルール（最適化）】

カテゴリの caption_structure を参考に、
各セクションを具体的に書くために必要な情報を質問形式で生成する。

作成手順：
1. caption_structure の各項目を確認し、  
   その内容を書くために必要な情報をシンプルな質問にする。

2. direction を優先し、  
   ユーザーが重視したい内容を深掘りする質問を増やす。

3. キャプション生成に直接不要な質問は作らない。

4. 質問の数は必要十分な数でよい（多すぎず少なすぎず）。

質問は簡潔で、ユーザーが答えやすい形にすること。

----------------------------------------
【出力形式（厳守）】

必ず以下の JSON 形式のみで返す：

{{
  "selected_template": "<カテゴリ名>",
  "required_info": [
    "<質問1>",
    "<質問2>",
    ...
  ]
}}

----------------------------------------
【禁止事項】
- caption_structure やテンプレ内容をそのまま出力しない
- example_structure / example_caption を出力しない
- キャプション本文を生成しない
- JSON 以外の文章を出力しない

以上を守り、ユーザー入力に対して最適なテンプレート選択と必要質問を出力してください。
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
    model: str = "gpt-5.1-mini",
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
        templates=json.dumps(extracted_templates, ensure_ascii=False, indent=2)
    )

    # history= に system prompt を最初のメッセージとして渡す
    return run_gpt_json(
        prompt=json.dumps(user_input, ensure_ascii=False),
        history=[{"role": "system", "content": system_prompt}],
        model=model,
        temperature=0.2,
        parse_json=True,
    )


