"""
Gemini会話サービスモジュール

Gemini Text APIを使用したAI接客応答生成
"""
import os
from typing import List, Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv

from database import db

# 環境変数読み込み
load_dotenv()


class GeminiChatService:
    """Gemini会話サービスクラス"""
    
    def __init__(self):
        """初期化"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY が設定されていません")
        
        # Gemini API設定
        genai.configure(api_key=self.api_key)
        
        # Chat用モデル - 制限回避のため優先順位を調整
        model_candidates = [
            'gemini-flash-latest',    # 最優先（別の無料枠）
            'gemini-2.0-flash',       # 2番目の候補
            'gemini-pro-latest',      # 3番目の候補
            'gemini-2.5-flash',       # gemini-2.5-flashの制限に達した場合の予備
            'gemini-2.5-pro',         # 最終候補
        ]
        
        self.chat_model = None
        last_error = None
        
        for model_name in model_candidates:
            try:
                test_model = genai.GenerativeModel(model_name)
                # 実際にテスト生成を試みる
                test_response = test_model.generate_content("test")
                self.chat_model = test_model
                print(f"[OK] Successfully using chat model: {model_name}")
                break
            except Exception as e:
                last_error = str(e)
                print(f"[NG] Chat model {model_name} not available: {str(e)[:100]}")
                continue
        
        if not self.chat_model:
            # すべて失敗した場合、利用可能なモデルをリスト
            try:
                print("\n利用可能なモデル一覧:")
                available_models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
                        print(f"  - {m.name} ({m.display_name})")
                
                error_msg = f"利用可能なGeminiチャットモデルが見つかりませんでした。\n"
                error_msg += f"利用可能なモデル: {available_models}\n"
                error_msg += f"最後のエラー: {last_error}"
                raise ValueError(error_msg)
            except Exception as e:
                raise ValueError(f"Gemini APIに接続できません: {str(e)}")
    
    def generate_response(
        self,
        user_message: str,
        session_id: str,
        product_id: Optional[int] = None
    ) -> str:
        """
        ユーザーメッセージに対する応答を生成
        
        Args:
            user_message: ユーザーからのメッセージ
            session_id: セッションID
            product_id: 現在表示中の商品ID
            
        Returns:
            生成された応答テキスト
        """
        try:
            # システムプロンプトの構築
            system_prompt = self._build_system_prompt(product_id)
            
            # 会話履歴の取得
            conversation_history = db.get_conversation_history(session_id, limit=5)
            
            # 完全なプロンプトを構築
            full_prompt = f"{system_prompt}\n\n"
            
            # 会話履歴を追加
            if conversation_history:
                full_prompt += "【これまでの会話】\n"
                for history in conversation_history[-3:]:
                    full_prompt += f"お客様: {history['user_message']}\n"
                    full_prompt += f"スタッフ: {history['ai_response']}\n\n"
            
            # 現在の質問を追加
            full_prompt += f"【お客様からの質問】\n{user_message}\n\n"
            full_prompt += "【スタッフの回答】\n"
            
            # Gemini APIコール
            response = self.chat_model.generate_content(full_prompt)
            
            if response and hasattr(response, 'text') and response.text:
                ai_response = response.text.strip()
            else:
                ai_response = "申し訳ございません。ただいま回答を生成できませんでした。もう一度お試しください。"
            
            # 会話履歴を保存
            db.save_conversation(
                session_id=session_id,
                user_message=user_message,
                ai_response=ai_response,
                product_id=product_id
            )
            
            return ai_response
        
        except Exception as e:
            print(f"Gemini Chat Error: {e}")
            import traceback
            traceback.print_exc()
            return f"申し訳ございません。現在システムに問題が発生しております。（エラー: {str(e)}）"
    
    def _build_system_prompt(self, product_id: Optional[int] = None) -> str:
        """
        システムプロンプトを構築
        
        Args:
            product_id: 商品ID
            
        Returns:
            システムプロンプト文字列
        """
        base_prompt = """あなたは日本の小売店舗のベテラン販売スタッフです。
以下のルールに従って、お客様に丁寧かつ的確に商品説明や質問対応を行ってください。

【対応ルール】
1. 常に丁寧な言葉遣いで、お客様目線で対応すること
2. 商品情報が提供されている場合は、その情報を最優先で参照すること
3. お客様のニーズを理解し、最適な商品を提案すること
4. 専門用語は分かりやすく説明すること
5. 不明な点は正直に伝え、調べて後ほど回答する旨を伝えること
6. 簡潔で分かりやすい説明を心がけること
7. 必要に応じて、商品の比較や関連商品の提案も行うこと
"""
        
        if product_id:
            # 商品情報を取得
            product = db.get_product(product_id)
            
            if product:
                product_context = f"\n【現在ご案内中の商品情報】\n"
                product_context += f"商品名: {product['name']}\n"
                product_context += f"ブランド: {product['brand']}\n"
                product_context += f"カテゴリ: {product['category']}\n"
                product_context += f"価格: {product['price']:,}円\n"
                product_context += f"説明: {product['description']}\n"
                
                if product.get('specifications'):
                    product_context += f"仕様:\n"
                    for key, value in product['specifications'].items():
                        product_context += f"  - {key}: {value}\n"
                
                product_context += f"在庫: {product['stock']}個\n"
                
                return base_prompt + product_context
        
        return base_prompt + "\n【商品情報】\n現在、特定の商品は選択されていません。お客様のご要望をお聞きして、最適な商品をご案内します。"
    
    def generate_product_introduction(self, product_id: int) -> str:
        """
        商品の自動紹介文を生成
        
        Args:
            product_id: 商品ID
            
        Returns:
            紹介文
        """
        product = db.get_product(product_id)
        
        if not product:
            return "商品情報が見つかりませんでした。"
        
        try:
            prompt = f"""
以下の商品について、お客様に分かりやすく魅力的な紹介文を生成してください。
3〜4文程度で、商品の特徴やメリットを簡潔に説明してください。

商品名: {product['name']}
ブランド: {product['brand']}
カテゴリ: {product['category']}
価格: {product['price']:,}円
説明: {product['description']}
"""
            
            if product.get('specifications'):
                prompt += "\n仕様:\n"
                for key, value in product['specifications'].items():
                    prompt += f"  - {key}: {value}\n"
            
            response = self.chat_model.generate_content(prompt)
            
            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()
            else:
                return f"{product['name']}のご紹介です。{product['description']}"
        
        except Exception as e:
            print(f"Product introduction generation error: {e}")
            return f"{product['name']}のご紹介です。{product['description']}"


# グローバルインスタンス
gemini_chat_service = GeminiChatService()
