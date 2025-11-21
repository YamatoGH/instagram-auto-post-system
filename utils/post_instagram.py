import os
import time
import dotenv
import requests
from google.cloud import storage

# ----------------------------------------
# .env 読み込み
# ----------------------------------------
dotenv.load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
IG_USER_ID = os.getenv("IG_USER_ID")
ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")


# ========================================
#  GCS アップロード（署名付きURL）
# ========================================
def upload_to_gcs(local_path, dest_path):
    """ローカル画像を GCS にアップロードし、署名付きURL を生成して返す"""
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(dest_path)

    # アップロード
    blob.upload_from_filename(local_path)

    # 署名付きURL（有効期限：1時間）
    url = blob.generate_signed_url(
        version="v4",
        expiration=3600,
        method="GET"
    )

    return url


# ========================================
#  Instagram 子メディア
# ========================================
def create_child_media(image_url):
    url = f"https://graph.facebook.com/v24.0/{IG_USER_ID}/media"
    
    params = {
        "image_url": image_url,
        "is_carousel_item": True,
        "access_token": ACCESS_TOKEN
    }

    res = requests.post(url, params=params).json()
    return res.get("id")


# ========================================
#  親カルーセル → publish
# ========================================
def publish_carousel(child_ids, caption):
    """子メディアをまとめてカルーセル投稿"""
    url = f"https://graph.facebook.com/v24.0/{IG_USER_ID}/media"

    params = {
        "caption": caption,
        "children": ",".join(child_ids),
        "media_type": "CAROUSEL",
        "access_token": ACCESS_TOKEN
    }

    res = requests.post(url, params=params).json()
    parent_id = res.get("id")

    if not parent_id:
        raise RuntimeError(f"親メディア作成に失敗: {res}")

    # Instagram API の仕様で少し待つ
    time.sleep(2)

    publish_url = f"https://graph.facebook.com/v24.0/{IG_USER_ID}/media_publish"
    publish_res = requests.post(
        publish_url,
        params={"creation_id": parent_id, "access_token": ACCESS_TOKEN}
    ).json()

    if "id" not in publish_res:
        raise RuntimeError(f"公開に失敗: {publish_res}")

    return publish_res


# ========================================
#  外部呼び出し用：まとめて投稿
# ========================================
def post_to_instagram(image_paths, caption):
    """
    画像リストとキャプションを渡すと、Instagram にカルーセル投稿する関数
    image_paths = ["img/a.png", "img/b.jpg", ...]
    """

    # ---------- GCS にアップロード ----------
    signed_urls = []
    for p in image_paths:
        dest = f"instagram/{os.path.basename(p)}"
        url = upload_to_gcs(p, dest)
        signed_urls.append(url)

    # ---------- 子メディア作成 ----------
    child_ids = []
    for url in signed_urls:
        cid = create_child_media(url)
        if cid:
            child_ids.append(cid)

    if not child_ids:
        raise RuntimeError("子メディアが1件も作成できませんでした。")

    # ---------- カルーセル公開 ----------
    result = publish_carousel(child_ids, caption)
    return result



