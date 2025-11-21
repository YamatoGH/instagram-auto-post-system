from utils.caption_agent import generate_instagram_caption
from utils.post_instagram import post_to_instagram



# ========================================
# 事業内容、写真リスト、タイトル、内容方針、(テンプレートリスト)→インスタに自動投稿
# ========================================
def auto_post_instagram(user_input, image_paths, templates_json):
    """事業内容、写真リスト、タイトル、内容方針→インスタに自動投稿"""
    # キャプション生成
    result = generate_instagram_caption(
            user_input,
            templates_json,
            model="gpt-4.1-mini",
        ) 

    final_caption = result["final_caption"]

    # インスタ投稿
    post_to_instagram(image_paths, final_caption)

    print(f"投稿完了:{final_caption}")