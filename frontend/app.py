"""
Streamlit フロントエンドアプリケーション

商品認識AI接客システムのUI
"""
import streamlit as st
import requests
import uuid
import base64
from datetime import datetime
from PIL import Image
import io
import cv2
import numpy as np

# ページ設定
st.set_page_config(
    page_title="商品認識AI接客システム",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API設定
API_BASE_URL = "http://localhost:8000"

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .product-card {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: #f9f9f9;
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
    }
    .ai-message {
        background-color: #f1f8e9;
        margin-right: 20%;
    }
    .timestamp {
        font-size: 0.8rem;
        color: #666;
        margin-top: 0.5rem;
    }
    .confidence-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.9rem;
        font-weight: bold;
    }
    .confidence-high {
        background-color: #4caf50;
        color: white;
    }
    .confidence-medium {
        background-color: #ff9800;
        color: white;
    }
    .confidence-low {
        background-color: #f44336;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """セッション状態の初期化"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'current_product' not in st.session_state:
        st.session_state.current_product = None
    
    if 'camera_active' not in st.session_state:
        st.session_state.camera_active = False


def capture_image_from_camera():
    """カメラから画像をキャプチャ"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        st.error("カメラを開けませんでした。カメラが接続されているか確認してください。")
        return None
    
    # カメラのウォームアップ
    for _ in range(5):
        cap.read()
    
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        # BGRからRGBに変換
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)
    else:
        st.error("画像のキャプチャに失敗しました。")
        return None


def recognize_product(image):
    """商品認識APIを呼び出し"""
    try:
        # 画像をBase64にエンコード
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # API呼び出し
        with st.spinner("商品を認識中..."):
            response = requests.post(
                f"{API_BASE_URL}/api/recognize",
                json={
                    "image_data": img_str,
                    "session_id": st.session_state.session_id
                },
                timeout=30
            )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"エラー: {response.status_code}")
            return None
    
    except Exception as e:
        st.error(f"商品認識エラー: {e}")
        return None


def send_message(message, product_id=None):
    """チャットメッセージを送信"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={
                "message": message,
                "session_id": st.session_state.session_id,
                "product_id": product_id
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"エラー: {response.status_code}")
            return None
    
    except Exception as e:
        st.error(f"メッセージ送信エラー: {e}")
        return None


def get_product_introduction(product_id):
    """商品紹介文を取得"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/product/introduction/{product_id}",
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get('introduction', '')
        else:
            return None
    
    except Exception as e:
        st.error(f"紹介文取得エラー: {e}")
        return None


def display_product_card(product, confidence=None):
    """商品カードを表示"""
    st.markdown('<div class="product-card">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # 商品画像プレースホルダー
        st.image("https://via.placeholder.com/300x300?text=Product+Image", use_container_width=True)
        
        if confidence is not None:
            # 信頼度バッジ
            if confidence >= 0.7:
                badge_class = "confidence-high"
                badge_text = f"認識信頼度: {confidence:.0%}"
            elif confidence >= 0.4:
                badge_class = "confidence-medium"
                badge_text = f"認識信頼度: {confidence:.0%}"
            else:
                badge_class = "confidence-low"
                badge_text = f"認識信頼度: {confidence:.0%}"
            
            st.markdown(f'<span class="confidence-badge {badge_class}">{badge_text}</span>', unsafe_allow_html=True)
    
    with col2:
        st.subheader(f"{product['name']}")
        st.write(f"**ブランド:** {product['brand']}")
        st.write(f"**カテゴリ:** {product['category']}")
        st.write(f"**価格:** ¥{product['price']:,}")
        
        st.write("**商品説明:**")
        st.write(product['description'])
        
        if product.get('specifications'):
            st.write("**仕様:**")
            for key, value in product['specifications'].items():
                st.write(f"- {key}: {value}")
        
        st.write(f"**在庫:** {product['stock']}個")
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_chat_interface():
    """チャットインターフェースを表示"""
    st.subheader("💬 商品について質問する")
    
    # チャット履歴表示
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            role = message.get('role')
            content = message.get('content')
            timestamp = message.get('timestamp', '')
            
            if role == 'user':
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>あなた</strong><br>
                    {content}
                    <div class="timestamp">{timestamp}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message ai-message">
                    <strong>🤖 スタッフ</strong><br>
                    {content}
                    <div class="timestamp">{timestamp}</div>
                </div>
                """, unsafe_allow_html=True)
    
    # 入力フォーム
    st.markdown("---")
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "メッセージを入力してください",
            height=100,
            placeholder="例: この商品の特徴を教えてください"
        )
        col1, col2 = st.columns([1, 4])
        
        with col1:
            submit_button = st.form_submit_button("送信", use_container_width=True)
    
    # 送信ボタン処理
    if submit_button and user_input.strip():
        # ユーザーメッセージを追加
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.messages.append({
            'role': 'user',
            'content': user_input,
            'timestamp': current_time
        })
        
        # APIコール
        product_id = st.session_state.current_product['id'] if st.session_state.current_product else None
        response = send_message(user_input, product_id)
        
        if response:
            # ボット応答を追加
            st.session_state.messages.append({
                'role': 'assistant',
                'content': response.get('message', ''),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            st.rerun()


def main():
    """メインアプリケーション"""
    initialize_session_state()
    
    # ヘッダー
    st.markdown('<div class="main-header">🛍️ 商品認識AI接客システム</div>', unsafe_allow_html=True)
    
    # サイドバー
    with st.sidebar:
        st.title("📱 操作パネル")
        
        st.markdown("---")
        st.subheader("📊 セッション情報")
        st.text(f"Session ID: {st.session_state.session_id[:8]}...")
        st.text(f"メッセージ数: {len(st.session_state.messages)}")
        
        st.markdown("---")
        st.subheader("💡 使い方")
        st.markdown("""
        1. 「商品を認識」ボタンをクリック
        2. カメラに商品を映す
        3. 商品情報が表示されます
        4. チャットで質問できます
        """)
        
        st.markdown("---")
        if st.button("🔄 セッションリセット", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.current_product = None
            st.rerun()
    
    # メインコンテンツ
    tab1, tab2 = st.tabs(["🎥 商品認識", "📊 統計情報"])
    
    with tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📷 カメラ")
            
            if st.button("商品を認識", type="primary", use_container_width=True):
                # カメラから画像をキャプチャ
                image = capture_image_from_camera()
                
                if image:
                    st.image(image, caption="キャプチャした画像", use_container_width=True)
                    
                    # 商品認識
                    result = recognize_product(image)
                    
                    if result and result.get('success'):
                        product = result.get('product')
                        confidence = result.get('confidence', 0)
                        
                        st.session_state.current_product = product
                        
                        st.success(f"商品を認識しました: {product['name']}")
                        
                        # 商品紹介文を取得
                        introduction = get_product_introduction(product['id'])
                        if introduction:
                            # 自動メッセージとして追加
                            st.session_state.messages.append({
                                'role': 'assistant',
                                'content': introduction,
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                    else:
                        message = result.get('message', '商品を認識できませんでした')
                        st.warning(message)
        
        with col2:
            st.subheader("🏷️ 商品情報")
            
            if st.session_state.current_product:
                display_product_card(
                    st.session_state.current_product,
                    confidence=None
                )
            else:
                st.info("商品を認識すると、ここに商品情報が表示されます。")
        
        st.markdown("---")
        
        # チャットインターフェース
        display_chat_interface()
    
    with tab2:
        st.subheader("📊 システム統計")
        
        try:
            response = requests.get(f"{API_BASE_URL}/api/stats", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                
                # メトリクス表示
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("総セッション数", stats['total_sessions'])
                
                with col2:
                    st.metric("総会話数", stats['total_conversations'])
                
                with col3:
                    st.metric("総検出数", stats['total_detections'])
                
                st.markdown("---")
                
                # 人気商品
                st.subheader("🏆 人気商品")
                
                if stats.get('top_products'):
                    for product in stats['top_products'][:5]:
                        st.write(f"**{product['name']}** ({product['category']}) - 検出回数: {product['detection_count']}")
                else:
                    st.info("まだデータがありません")
            else:
                st.error("統計情報の取得に失敗しました")
        
        except Exception as e:
            st.error(f"統計情報取得エラー: {e}")


if __name__ == "__main__":
    main()
