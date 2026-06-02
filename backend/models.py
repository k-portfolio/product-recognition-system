"""
データモデル定義モジュール

Pydanticを使用してAPIリクエスト/レスポンスのスキーマを定義
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProductRecognitionRequest(BaseModel):
    """商品認識リクエストモデル"""
    image_data: str = Field(..., description="Base64エンコードされた画像データ")
    session_id: Optional[str] = Field(None, description="セッションID")


class ProductInfo(BaseModel):
    """商品情報モデル"""
    id: int = Field(..., description="商品ID")
    name: str = Field(..., description="商品名")
    category: str = Field(..., description="カテゴリ")
    brand: str = Field(..., description="ブランド")
    price: int = Field(..., description="価格（円）")
    description: str = Field(..., description="商品説明")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="仕様")
    stock: int = Field(..., description="在庫数")
    keywords: List[str] = Field(default_factory=list, description="検索キーワード")


class ProductRecognitionResponse(BaseModel):
    """商品認識レスポンスモデル"""
    success: bool = Field(..., description="認識成功フラグ")
    product: Optional[ProductInfo] = Field(None, description="商品情報")
    confidence: float = Field(default=0.0, description="認識信頼度（0.0-1.0）")
    message: str = Field(default="", description="メッセージ")
    session_id: str = Field(..., description="セッションID")
    detection_id: Optional[int] = Field(None, description="検出ログID")


class ChatRequest(BaseModel):
    """チャットリクエストモデル"""
    message: str = Field(..., min_length=1, max_length=1000, description="ユーザーからのメッセージ")
    session_id: str = Field(..., description="セッションID")
    product_id: Optional[int] = Field(None, description="現在表示中の商品ID")


class ChatResponse(BaseModel):
    """チャットレスポンスモデル"""
    message: str = Field(..., description="AIからの応答メッセージ")
    session_id: str = Field(..., description="セッションID")
    timestamp: datetime = Field(default_factory=datetime.now, description="応答時刻")


class ConversationHistory(BaseModel):
    """会話履歴モデル"""
    id: int = Field(..., description="履歴ID")
    session_id: str = Field(..., description="セッションID")
    user_message: str = Field(..., description="ユーザーメッセージ")
    ai_response: str = Field(..., description="AI応答")
    timestamp: datetime = Field(..., description="タイムスタンプ")
    product_id: Optional[int] = Field(None, description="関連商品ID")


class DetectionLog(BaseModel):
    """検出ログモデル"""
    id: int = Field(..., description="検出ID")
    session_id: str = Field(..., description="セッションID")
    product_id: Optional[int] = Field(None, description="商品ID")
    confidence: float = Field(..., description="信頼度")
    timestamp: datetime = Field(..., description="検出時刻")
    raw_result: Optional[str] = Field(None, description="Gemini APIの生レスポンス")


class SessionInfo(BaseModel):
    """セッション情報モデル"""
    session_id: str = Field(..., description="セッションID")
    created_at: datetime = Field(..., description="作成日時")
    last_active: datetime = Field(..., description="最終アクティブ日時")
    status: str = Field(default="active", description="ステータス")
    total_messages: int = Field(default=0, description="総メッセージ数")
    total_detections: int = Field(default=0, description="総検出数")


class StatsResponse(BaseModel):
    """統計情報レスポンスモデル"""
    total_sessions: int = Field(..., description="総セッション数")
    total_conversations: int = Field(..., description="総会話数")
    total_detections: int = Field(..., description="総検出数")
    top_products: List[Dict[str, Any]] = Field(default_factory=list, description="人気商品")
    recent_sessions: List[SessionInfo] = Field(default_factory=list, description="最近のセッション")


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str = Field(..., description="ステータス")
    timestamp: datetime = Field(default_factory=datetime.now, description="チェック時刻")
    database_status: str = Field(default="unknown", description="データベース状態")
    gemini_api_status: str = Field(default="unknown", description="Gemini API状態")
