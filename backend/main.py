"""
FastAPI メインアプリケーション

商品認識AI接客システムのバックエンドAPI
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uuid
import logging

from models import (
    ProductRecognitionRequest, ProductRecognitionResponse, ProductInfo,
    ChatRequest, ChatResponse,
    ConversationHistory, DetectionLog, SessionInfo,
    StatsResponse, HealthResponse
)
from database import db
from product_service import product_recognition_service
from gemini_service import gemini_chat_service

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション初期化
app = FastAPI(
    title="商品認識AI接客システム API",
    description="Gemini APIを活用した商品認識と自動接客システム",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンに限定すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
    """ルートエンドポイント - ヘルスチェック"""
    return HealthResponse(
        status="ok",
        database_status="connected",
        gemini_api_status="configured"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    ヘルスチェックエンドポイント
    
    システムの稼働状態を確認
    """
    try:
        # データベース接続チェック
        db_stats = db.get_stats()
        db_status = "ok" if db_stats else "error"
        
        return HealthResponse(
            status="healthy",
            database_status=db_status,
            gemini_api_status="ok"
        )
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="サービスが利用できません"
        )


@app.post("/api/recognize", response_model=ProductRecognitionResponse)
async def recognize_product(request: ProductRecognitionRequest):
    """
    商品認識エンドポイント
    
    画像から商品を認識し、データベースと照合
    """
    try:
        # セッションID生成（未指定の場合）
        session_id = request.session_id or str(uuid.uuid4())
        
        logger.info(f"商品認識リクエスト受信 - Session: {session_id}")
        
        # 商品認識
        product, confidence, error_message = product_recognition_service.recognize_product(
            image_data=request.image_data,
            session_id=session_id
        )
        
        if product:
            # 成功
            logger.info(f"商品認識成功 - Product ID: {product['id']}, Confidence: {confidence}")
            
            # 検出ログIDを取得（最新のログ）
            logs = db.get_detection_logs(session_id, limit=1)
            detection_id = logs[0]['id'] if logs else None
            
            return ProductRecognitionResponse(
                success=True,
                product=ProductInfo(**product),
                confidence=confidence,
                message="商品を認識しました",
                session_id=session_id,
                detection_id=detection_id
            )
        else:
            # 失敗
            logger.warning(f"商品認識失敗 - Session: {session_id}, Message: {error_message}")
            
            return ProductRecognitionResponse(
                success=False,
                product=None,
                confidence=confidence,
                message=error_message or "商品を認識できませんでした",
                session_id=session_id
            )
    
    except Exception as e:
        logger.error(f"商品認識エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"商品認識中にエラーが発生しました: {str(e)}"
        )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    チャットエンドポイント
    
    ユーザーからのメッセージに対してAIが応答
    """
    try:
        logger.info(f"チャットリクエスト受信 - Session: {request.session_id}, Message: {request.message[:50]}...")
        
        # Gemini APIで応答生成
        ai_response = gemini_chat_service.generate_response(
            user_message=request.message,
            session_id=request.session_id,
            product_id=request.product_id
        )
        
        logger.info(f"応答生成完了 - Response: {ai_response[:50]}...")
        
        return ChatResponse(
            message=ai_response,
            session_id=request.session_id
        )
    
    except Exception as e:
        logger.error(f"チャット処理エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"チャット処理中にエラーが発生しました: {str(e)}"
        )


@app.get("/api/product/{product_id}", response_model=ProductInfo)
async def get_product(product_id: int):
    """
    商品情報取得エンドポイント
    
    指定されたIDの商品情報を取得
    """
    try:
        product = db.get_product(product_id)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品が見つかりません"
            )
        
        return ProductInfo(**product)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"商品情報取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"商品情報取得中にエラーが発生しました: {str(e)}"
        )


@app.post("/api/product/introduction/{product_id}")
async def get_product_introduction(product_id: int):
    """
    商品紹介文生成エンドポイント
    
    AIが商品の魅力的な紹介文を生成
    """
    try:
        introduction = gemini_chat_service.generate_product_introduction(product_id)
        
        return {
            "product_id": product_id,
            "introduction": introduction
        }
    
    except Exception as e:
        logger.error(f"商品紹介文生成エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"商品紹介文生成中にエラーが発生しました: {str(e)}"
        )


@app.get("/api/history/{session_id}")
async def get_history(session_id: str, limit: int = 50):
    """
    会話履歴取得エンドポイント
    
    指定されたセッションの会話履歴を取得
    """
    try:
        history = db.get_conversation_history(session_id, limit=limit)
        return history
    
    except Exception as e:
        logger.error(f"会話履歴取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"会話履歴取得中にエラーが発生しました: {str(e)}"
        )


@app.get("/api/detections/{session_id}")
async def get_detections(session_id: str, limit: int = 10):
    """
    検出ログ取得エンドポイント
    
    指定されたセッションの検出ログを取得
    """
    try:
        logs = db.get_detection_logs(session_id, limit=limit)
        return logs
    
    except Exception as e:
        logger.error(f"検出ログ取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"検出ログ取得中にエラーが発生しました: {str(e)}"
        )


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """
    統計情報取得エンドポイント
    
    システム全体の統計情報を取得
    """
    try:
        stats = db.get_stats()
        
        # SessionInfoモデルに変換
        recent_sessions = []
        for session in stats.get('recent_sessions', []):
            recent_sessions.append(SessionInfo(
                session_id=session['session_id'],
                created_at=session['created_at'],
                last_active=session['last_active'],
                status=session['status'],
                total_messages=session.get('message_count', 0),
                total_detections=session.get('detection_count', 0)
            ))
        
        return StatsResponse(
            total_sessions=stats['total_sessions'],
            total_conversations=stats['total_conversations'],
            total_detections=stats['total_detections'],
            top_products=stats['top_products'],
            recent_sessions=recent_sessions
        )
    
    except Exception as e:
        logger.error(f"統計情報取得エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"統計情報取得中にエラーが発生しました: {str(e)}"
        )


@app.post("/api/session/{session_id}/close")
async def close_session(session_id: str):
    """
    セッション終了エンドポイント
    
    指定されたセッションを終了状態にする
    """
    try:
        success = db.close_session(session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="セッションが見つかりません"
            )
        
        return {"message": "セッションを終了しました", "session_id": session_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"セッション終了エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"セッション終了中にエラーが発生しました: {str(e)}"
        )


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
