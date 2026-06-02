"""
商品認識サービスモジュール

Gemini Vision APIを使用した商品認識と商品データベース照合
"""
import base64
import os
from typing import Optional, Dict, Any, Tuple
from PIL import Image
import io
import google.generativeai as genai
from dotenv import load_dotenv

from database import db

# 環境変数読み込み
load_dotenv()


class ProductRecognitionService:
    """商品認識サービスクラス"""
    
    def __init__(self):
        """初期化"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY が設定されていません")
        
        # Gemini API設定
        genai.configure(api_key=self.api_key)
        
        # Vision用モデル - 制限回避のため優先順位を調整
        model_candidates = [
            'gemini-flash-latest',    # 最優先（別の無料枠）
            'gemini-2.0-flash',       # 2番目の候補
            'gemini-pro-latest',      # 3番目の候補
            'gemini-2.5-flash',       # gemini-2.5-flashの制限に達した場合の予備
            'gemini-2.5-pro',         # 最終候補
        ]
        
        self.vision_model = None
        last_error = None
        
        for model_name in model_candidates:
            try:
                test_model = genai.GenerativeModel(model_name)
                # 実際にテスト生成を試みる
                test_response = test_model.generate_content("test")
                self.vision_model = test_model
                print(f"[OK] Successfully using vision model: {model_name}")
                break
            except Exception as e:
                last_error = str(e)
                print(f"[NG] Model {model_name} not available: {str(e)[:100]}")
                continue
        
        if not self.vision_model:
            # すべて失敗した場合、利用可能なモデルをリスト
            try:
                print("\n利用可能なモデル一覧:")
                available_models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
                        print(f"  - {m.name} ({m.display_name})")
                
                error_msg = f"利用可能なGemini Visionモデルが見つかりませんでした。\n"
                error_msg += f"利用可能なモデル: {available_models}\n"
                error_msg += f"最後のエラー: {last_error}"
                raise ValueError(error_msg)
            except Exception as e:
                raise ValueError(f"Gemini APIに接続できません: {str(e)}")
    
    def recognize_product(
        self,
        image_data: str,
        session_id: str
    ) -> Tuple[Optional[Dict], float, Optional[str]]:
        """
        画像から商品を認識
        
        Args:
            image_data: Base64エンコードされた画像データ
            session_id: セッションID
            
        Returns:
            (商品情報, 信頼度, エラーメッセージ)
        """
        try:
            # Base64デコード
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Gemini Vision APIで画像分析
            prompt = """
この画像に写っている商品を認識してください。

以下の情報を日本語で返してください：
1. 商品名（できるだけ具体的に）
2. カテゴリ（例: パソコン、スマートフォン、家電、衣類など）
3. ブランド名（分かれば）
4. 主な特徴（3つ程度）

以下のJSON形式で回答してください：
```json
{
  "product_name": "商品名",
  "category": "カテゴリ",
  "brand": "ブランド名",
  "features": ["特徴1", "特徴2", "特徴3"]
}
```

商品が認識できない場合は、以下を返してください：
```json
{
  "product_name": "不明",
  "category": "不明",
  "brand": "不明",
  "features": []
}
```
"""
            
            response = self.vision_model.generate_content([prompt, image])
            raw_result = response.text.strip()
            
            # JSONブロックを抽出
            import json
            import re
            
            json_match = re.search(r'```json\s*(.*?)\s*```', raw_result, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                # JSONブロックがない場合は全体をパース試行
                result = json.loads(raw_result)
            
            # 商品が認識できたか確認
            if result.get('product_name') == '不明':
                return None, 0.0, "商品を認識できませんでした。別の角度から撮影してください。"
            
            # データベースから類似商品を検索
            product_name = result.get('product_name', '')
            category = result.get('category', '')
            brand = result.get('brand', '')
            
            # 検索戦略を改善
            matched_products = []
            
            # 1. ブランド名で絞り込み（ブランドが分かる場合）
            if brand and brand != "不明":
                matched_products = db.search_products(brand)
                
                # 2. さらに商品名の主要キーワードで絞り込み
                if matched_products:
                    # 商品名から主要なキーワードを抽出（数字やモデル名）
                    keywords = re.findall(r'\w+', product_name)
                    
                    # キーワードでフィルタリング
                    filtered = []
                    for product in matched_products:
                        product_text = f"{product['name']} {product.get('keywords', [])}".lower()
                        # いずれかのキーワードがマッチすればOK
                        for keyword in keywords:
                            if len(keyword) >= 2 and keyword.lower() in product_text:
                                filtered.append(product)
                                break
                    
                    if filtered:
                        matched_products = filtered
            
            # 3. ブランド検索で見つからない場合、カテゴリで検索
            if not matched_products and category and category != "不明":
                matched_products = db.search_products(category)
            
            # 4. 商品名の一部で検索
            if not matched_products:
                # 商品名から主要キーワードを抽出
                keywords = re.findall(r'\w+', product_name)
                for keyword in keywords:
                    if len(keyword) >= 3:  # 3文字以上のキーワード
                        matched_products = db.search_products(keyword)
                        if matched_products:
                            break
            
            if matched_products:
                # 複数マッチした場合、スコアリングして最適な商品を選択
                if len(matched_products) > 1:
                    best_product = None
                    best_score = 0
                    
                    for product in matched_products:
                        score = 0
                        product_text = f"{product['name']} {' '.join(product.get('keywords', []))}".lower()
                        
                        # ブランド名が一致
                        if brand and brand != "不明" and brand.lower() in product_text:
                            score += 10
                        
                        # 商品名のキーワードが含まれている
                        keywords = re.findall(r'\w+', product_name.lower())
                        for keyword in keywords:
                            if len(keyword) >= 2 and keyword in product_text:
                                score += 5
                        
                        # カテゴリが一致
                        if category and category != "不明" and category in product['category']:
                            score += 3
                        
                        if score > best_score:
                            best_score = score
                            best_product = product
                    
                    if best_product:
                        product = best_product
                    else:
                        product = matched_products[0]
                else:
                    product = matched_products[0]
                
                confidence = 0.8  # 仮の信頼度
                
                # 検出ログを保存
                db.save_detection_log(
                    session_id=session_id,
                    product_id=product['id'],
                    confidence=confidence,
                    raw_result=raw_result
                )
                
                return product, confidence, None
            else:
                # データベースに該当商品なし
                message = f"認識結果: {product_name}（{category}）\nデータベースに該当商品が見つかりませんでした。"
                
                # 検出ログを保存（product_id=None）
                db.save_detection_log(
                    session_id=session_id,
                    product_id=None,
                    confidence=0.5,
                    raw_result=raw_result
                )
                
                return None, 0.5, message
        
        except Exception as e:
            print(f"商品認識エラー: {e}")
            import traceback
            traceback.print_exc()
            return None, 0.0, f"商品認識中にエラーが発生しました: {str(e)}"
    
    def get_product_info(self, product_id: int) -> Optional[Dict]:
        """
        商品情報を取得
        
        Args:
            product_id: 商品ID
            
        Returns:
            商品情報
        """
        return db.get_product(product_id)


# グローバルインスタンス
product_recognition_service = ProductRecognitionService()
