"""
iPhone 14 撮影前提テストスクリプト

商品認識AI接客システムに対して、
iPhone 14が撮影された前提で各エンドポイントをテストする
"""
import sys
import os
import json
import base64
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

BASE_URL = "http://localhost:8000"
SESSION_ID = "test-iphone14-session-001"


def print_section(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(label, value, success=True):
    status = "[PASS]" if success else "[FAIL]"
    print(f"  {status} {label}: {value}")


def create_iphone14_image():
    """iPhone 14 を模したテスト用画像を生成（PIL使用）"""
    # 黒背景のスマートフォン型画像
    img = Image.new("RGB", (300, 600), color=(10, 10, 10))
    draw = ImageDraw.Draw(img)

    # ボディ（角丸風の矩形）
    draw.rectangle([20, 20, 280, 580], outline=(80, 80, 80), width=3)

    # 画面部分
    draw.rectangle([30, 50, 270, 530], fill=(30, 30, 30))

    # ノッチ（Dynamic Island 風）
    draw.ellipse([120, 55, 180, 75], fill=(0, 0, 0))

    # Apple ロゴ風（円）
    draw.ellipse([130, 240, 170, 280], outline=(200, 200, 200), width=2)

    # テキスト
    draw.text((90, 300), "iPhone 14", fill=(255, 255, 255))
    draw.text((100, 330), "Apple Inc.", fill=(150, 150, 150))
    draw.text((85, 360), "A15 Bionic", fill=(100, 100, 255))

    # カメラモジュール（背面風）
    draw.ellipse([80, 420, 120, 460], fill=(20, 20, 20), outline=(60, 60, 60), width=2)
    draw.ellipse([160, 420, 200, 460], fill=(20, 20, 20), outline=(60, 60, 60), width=2)

    return img


def image_to_base64(img):
    """PIL Imageをbase64文字列に変換"""
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


# ==============================================================
# テスト 1: ヘルスチェック
# ==============================================================
def test_health():
    print_section("テスト 1: ヘルスチェック")
    resp = requests.get(f"{BASE_URL}/health")
    data = resp.json()
    ok = resp.status_code == 200 and data.get("status") == "healthy"
    print_result("ステータスコード", resp.status_code, resp.status_code == 200)
    print_result("DB状態", data.get("database_status"), data.get("database_status") == "ok")
    print_result("Gemini API状態", data.get("gemini_api_status"), data.get("gemini_api_status") == "ok")
    return ok


# ==============================================================
# テスト 2: 商品認識（iPhone 14 画像を送信）
# ==============================================================
def test_recognize_iphone14():
    print_section("テスト 2: 商品認識 - iPhone 14 画像を送信")

    img = create_iphone14_image()
    image_b64 = image_to_base64(img)
    print(f"  画像サイズ: 300x600px, base64サイズ: {len(image_b64)} chars")

    payload = {
        "image_data": image_b64,
        "session_id": SESSION_ID
    }

    resp = requests.post(f"{BASE_URL}/api/recognize", json=payload)
    data = resp.json()

    print_result("ステータスコード", resp.status_code, resp.status_code == 200)
    print(f"  認識結果:")
    print(f"    success     : {data.get('success')}")
    print(f"    message     : {data.get('message')}")
    print(f"    confidence  : {data.get('confidence')}")
    print(f"    session_id  : {data.get('session_id')}")

    if data.get("product"):
        p = data["product"]
        print(f"  認識した商品:")
        print(f"    id          : {p.get('id')}")
        print(f"    name        : {p.get('name')}")
        print(f"    brand       : {p.get('brand')}")
        print(f"    category    : {p.get('category')}")
        print(f"    price       : {p.get('price'):,}円")
        print(f"    stock       : {p.get('stock')}")
        iphone14_detected = "iPhone 14" in p.get("name", "")
        print_result("iPhone 14 認識", p.get("name"), iphone14_detected)
        return data.get("product", {}).get("id")
    else:
        print(f"  [INFO] 商品未認識 (Gemini判定): {data.get('message')}")
        return None


# ==============================================================
# テスト 3: 商品情報直接取得（iPhone 14 のDB IDで）
# ==============================================================
def test_get_iphone14_product():
    print_section("テスト 3: 商品情報取得 - iPhone 14 (DBから直接)")

    # 全商品から iPhone 14 を検索
    all_products_resp = requests.get(f"{BASE_URL}/api/stats")
    stats = all_products_resp.json()

    iphone14_id = None
    for p in stats.get("top_products", []):
        if "iPhone 14" in p.get("name", "") and "Pro" not in p.get("name", ""):
            iphone14_id = p["id"]
            break

    if iphone14_id is None:
        # IDを直接試行 (products.jsonの順序から推定)
        for pid in range(1, 20):
            r = requests.get(f"{BASE_URL}/api/product/{pid}")
            if r.status_code == 200:
                p = r.json()
                if "iPhone 14" in p.get("name", "") and "Pro" not in p.get("name", ""):
                    iphone14_id = pid
                    break

    if iphone14_id:
        resp = requests.get(f"{BASE_URL}/api/product/{iphone14_id}")
        p = resp.json()
        print_result("ステータスコード", resp.status_code, resp.status_code == 200)
        print(f"  iPhone 14 商品情報:")
        print(f"    id          : {p.get('id')}")
        print(f"    name        : {p.get('name')}")
        print(f"    brand       : {p.get('brand')}")
        print(f"    category    : {p.get('category')}")
        print(f"    price       : {p.get('price'):,}円")
        print(f"    stock       : {p.get('stock')}個")
        specs = p.get("specifications", {})
        print(f"  仕様:")
        for k, v in specs.items():
            print(f"    {k}: {v}")
        return iphone14_id
    else:
        print("  [FAIL] iPhone 14 がDBに見つかりません")
        return None


# ==============================================================
# テスト 4: AI接客チャット（iPhone 14 を前提とした会話）
# ==============================================================
def test_chat_iphone14(product_id):
    print_section("テスト 4: AI接客チャット - iPhone 14 について質問")

    questions = [
        "iPhone 14の特徴を教えてください",
        "バッテリーの持ちはどうですか？",
        "Galaxy S24 Ultraと比べてどちらがおすすめですか？",
    ]

    all_ok = True
    for i, question in enumerate(questions, 1):
        print(f"\n  質問 {i}: {question}")
        payload = {
            "message": question,
            "session_id": SESSION_ID,
            "product_id": product_id
        }
        resp = requests.post(f"{BASE_URL}/api/chat", json=payload)
        data = resp.json()
        ok = resp.status_code == 200 and bool(data.get("message"))
        answer = data.get("message", "")
        # 最初の100文字だけ表示
        preview = answer[:120].replace("\n", " ") + ("..." if len(answer) > 120 else "")
        print_result(f"応答取得", f"OK ({len(answer)}文字)", ok)
        print(f"  応答プレビュー: {preview}")
        if not ok:
            all_ok = False

    return all_ok


# ==============================================================
# テスト 5: 商品紹介文生成
# ==============================================================
def test_product_introduction(product_id):
    print_section("テスト 5: iPhone 14 紹介文自動生成")

    resp = requests.post(f"{BASE_URL}/api/product/introduction/{product_id}")
    data = resp.json()
    ok = resp.status_code == 200 and bool(data.get("introduction"))
    print_result("ステータスコード", resp.status_code, resp.status_code == 200)
    intro = data.get("introduction", "")
    print(f"  生成された紹介文 ({len(intro)}文字):")
    print(f"  {intro}")
    return ok


# ==============================================================
# テスト 6: 会話履歴確認
# ==============================================================
def test_history():
    print_section("テスト 6: 会話履歴確認")

    resp = requests.get(f"{BASE_URL}/api/history/{SESSION_ID}")
    history = resp.json()
    ok = resp.status_code == 200 and isinstance(history, list)
    print_result("ステータスコード", resp.status_code, resp.status_code == 200)
    print_result("履歴件数", f"{len(history)}件", len(history) > 0)
    for h in history:
        print(f"  [{h.get('timestamp', '')[:19]}] Q: {h.get('user_message', '')[:50]}")
    return ok


# ==============================================================
# テスト 7: 検出ログ確認
# ==============================================================
def test_detection_logs():
    print_section("テスト 7: 検出ログ確認")

    resp = requests.get(f"{BASE_URL}/api/detections/{SESSION_ID}")
    logs = resp.json()
    ok = resp.status_code == 200 and isinstance(logs, list)
    print_result("ステータスコード", resp.status_code, resp.status_code == 200)
    print_result("検出ログ件数", f"{len(logs)}件")
    for log in logs:
        print(f"  [{log.get('timestamp', '')[:19]}] product_id={log.get('product_id')}, confidence={log.get('confidence')}")
    return ok


# ==============================================================
# テスト 8: 統計情報
# ==============================================================
def test_stats():
    print_section("テスト 8: システム統計情報")

    resp = requests.get(f"{BASE_URL}/api/stats")
    data = resp.json()
    ok = resp.status_code == 200
    print_result("ステータスコード", resp.status_code, resp.status_code == 200)
    print(f"  総セッション数    : {data.get('total_sessions')}")
    print(f"  総会話数          : {data.get('total_conversations')}")
    print(f"  総検出数          : {data.get('total_detections')}")
    print(f"  人気商品 TOP3:")
    for p in data.get("top_products", [])[:3]:
        print(f"    - {p.get('name')} (検出: {p.get('detection_count')}回)")
    return ok


# ==============================================================
# テスト 9: セッション終了
# ==============================================================
def test_close_session():
    print_section("テスト 9: セッション終了")

    resp = requests.post(f"{BASE_URL}/api/session/{SESSION_ID}/close")
    data = resp.json()
    ok = resp.status_code == 200
    print_result("ステータスコード", resp.status_code, resp.status_code == 200)
    print_result("メッセージ", data.get("message", ""), ok)
    return ok


# ==============================================================
# メイン
# ==============================================================
if __name__ == "__main__":
    print()
    print("*" * 60)
    print("  product-recognition-system テスト")
    print("  前提: iPhone 14 が撮影された")
    print("*" * 60)

    results = {}

    results["health"] = test_health()
    iphone14_product_id = test_recognize_iphone14()
    iphone14_product_id_direct = test_get_iphone14_product()

    # 商品IDを確定（認識テストで取れなければ直接取得IDを使う）
    final_product_id = iphone14_product_id or iphone14_product_id_direct

    if final_product_id:
        results["chat"] = test_chat_iphone14(final_product_id)
        results["introduction"] = test_product_introduction(final_product_id)
    else:
        print("\n[SKIP] iPhone 14 の product_id が取得できなかったためチャット/紹介文テストをスキップ")

    results["history"] = test_history()
    results["detections"] = test_detection_logs()
    results["stats"] = test_stats()
    results["close_session"] = test_close_session()

    # 結果サマリー
    print()
    print("=" * 60)
    print("  テスト結果サマリー")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, ok in results.items():
        status = "[PASS]" if ok else "[FAIL]"
        print(f"  {status} {name}")
    print()
    print(f"  結果: {passed}/{total} PASSED")
    print("=" * 60)
