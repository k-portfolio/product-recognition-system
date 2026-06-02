"""
データベース管理モジュール

SQLiteを使用した商品データ、セッション、会話履歴の管理
"""
import sqlite3
import json
import os
from contextlib import contextmanager
from typing import List, Dict, Optional, Any
from datetime import datetime


class Database:
    """データベース管理クラス"""
    
    def __init__(self, db_path: str = "data/store.db"):
        """
        初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._initialize_db()
    
    def _ensure_db_directory(self):
        """データベースディレクトリの作成"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """
        データベース接続のコンテキストマネージャー
        
        Yields:
            sqlite3.Connection: データベース接続
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _initialize_db(self):
        """データベーステーブルの初期化"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 商品マスタテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    specifications TEXT,
                    stock INTEGER DEFAULT 0,
                    keywords TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # セッションテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # 会話履歴テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    product_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)
            
            # 検出ログテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    product_id INTEGER,
                    confidence REAL NOT NULL,
                    raw_result TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)
    
    # ============ 商品関連操作 ============
    
    def add_product(
        self,
        name: str,
        category: str,
        brand: str,
        price: int,
        description: str,
        specifications: Dict[str, Any] = None,
        stock: int = 0,
        keywords: List[str] = None
    ) -> int:
        """
        商品を追加
        
        Returns:
            int: 追加された商品ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            specs_json = json.dumps(specifications, ensure_ascii=False) if specifications else None
            keywords_json = json.dumps(keywords, ensure_ascii=False) if keywords else None
            
            cursor.execute("""
                INSERT INTO products (name, category, brand, price, description, specifications, stock, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, category, brand, price, description, specs_json, stock, keywords_json))
            
            return cursor.lastrowid
    
    def get_product(self, product_id: int) -> Optional[Dict]:
        """
        商品情報を取得
        
        Args:
            product_id: 商品ID
            
        Returns:
            商品情報の辞書、存在しない場合はNone
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            row = cursor.fetchone()
            
            if row:
                product = dict(row)
                # JSON文字列をPythonオブジェクトに変換
                if product.get('specifications'):
                    product['specifications'] = json.loads(product['specifications'])
                if product.get('keywords'):
                    product['keywords'] = json.loads(product['keywords'])
                return product
            return None
    
    def get_all_products(self) -> List[Dict]:
        """
        全商品を取得
        
        Returns:
            商品リスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products")
            rows = cursor.fetchall()
            
            products = []
            for row in rows:
                product = dict(row)
                if product.get('specifications'):
                    product['specifications'] = json.loads(product['specifications'])
                if product.get('keywords'):
                    product['keywords'] = json.loads(product['keywords'])
                products.append(product)
            
            return products
    
    def search_products(self, keyword: str) -> List[Dict]:
        """
        商品を検索
        
        Args:
            keyword: 検索キーワード
            
        Returns:
            マッチした商品のリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM products
                WHERE name LIKE ? OR description LIKE ? OR keywords LIKE ?
            """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
            
            rows = cursor.fetchall()
            products = []
            for row in rows:
                product = dict(row)
                if product.get('specifications'):
                    product['specifications'] = json.loads(product['specifications'])
                if product.get('keywords'):
                    product['keywords'] = json.loads(product['keywords'])
                products.append(product)
            
            return products
    
    def update_product_stock(self, product_id: int, stock: int) -> bool:
        """
        在庫数を更新
        
        Returns:
            更新成功したか
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE products
                SET stock = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (stock, product_id))
            
            return cursor.rowcount > 0
    
    # ============ セッション関連操作 ============
    
    def create_or_update_session(self, session_id: str) -> None:
        """セッションを作成または更新"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (session_id, last_active)
                VALUES (?, CURRENT_TIMESTAMP)
            """, (session_id,))
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """セッション情報を取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def close_session(self, session_id: str) -> bool:
        """セッションを終了"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions
                SET status = 'closed', last_active = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))
            return cursor.rowcount > 0
    
    # ============ 会話履歴関連操作 ============
    
    def save_conversation(
        self,
        session_id: str,
        user_message: str,
        ai_response: str,
        product_id: Optional[int] = None
    ) -> int:
        """
        会話を保存
        
        Returns:
            挿入されたレコードのID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # セッション更新
            self.create_or_update_session(session_id)
            
            # 会話履歴に挿入
            cursor.execute("""
                INSERT INTO conversations (session_id, user_message, ai_response, product_id)
                VALUES (?, ?, ?, ?)
            """, (session_id, user_message, ai_response, product_id))
            
            return cursor.lastrowid
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """
        会話履歴を取得
        
        Args:
            session_id: セッションID
            limit: 取得件数
            
        Returns:
            会話履歴のリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (session_id, limit))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ============ 検出ログ関連操作 ============
    
    def save_detection_log(
        self,
        session_id: str,
        product_id: Optional[int],
        confidence: float,
        raw_result: Optional[str] = None
    ) -> int:
        """
        検出ログを保存
        
        Returns:
            挿入されたレコードのID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # セッション更新
            self.create_or_update_session(session_id)
            
            cursor.execute("""
                INSERT INTO detection_logs (session_id, product_id, confidence, raw_result)
                VALUES (?, ?, ?, ?)
            """, (session_id, product_id, confidence, raw_result))
            
            return cursor.lastrowid
    
    def get_detection_logs(self, session_id: str, limit: int = 10) -> List[Dict]:
        """検出ログを取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM detection_logs
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ============ 統計情報 ============
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 総セッション数
            cursor.execute("SELECT COUNT(*) as count FROM sessions")
            total_sessions = cursor.fetchone()['count']
            
            # 総会話数
            cursor.execute("SELECT COUNT(*) as count FROM conversations")
            total_conversations = cursor.fetchone()['count']
            
            # 総検出数
            cursor.execute("SELECT COUNT(*) as count FROM detection_logs")
            total_detections = cursor.fetchone()['count']
            
            # 人気商品（検出回数順）
            cursor.execute("""
                SELECT p.id, p.name, p.category, COUNT(d.id) as detection_count
                FROM products p
                LEFT JOIN detection_logs d ON p.id = d.product_id
                GROUP BY p.id
                ORDER BY detection_count DESC
                LIMIT 10
            """)
            top_products = [dict(row) for row in cursor.fetchall()]
            
            # 最近のセッション
            cursor.execute("""
                SELECT s.*, 
                       (SELECT COUNT(*) FROM conversations c WHERE c.session_id = s.session_id) as message_count,
                       (SELECT COUNT(*) FROM detection_logs d WHERE d.session_id = s.session_id) as detection_count
                FROM sessions s
                ORDER BY s.last_active DESC
                LIMIT 5
            """)
            recent_sessions = [dict(row) for row in cursor.fetchall()]
            
            return {
                'total_sessions': total_sessions,
                'total_conversations': total_conversations,
                'total_detections': total_detections,
                'top_products': top_products,
                'recent_sessions': recent_sessions
            }


# グローバルインスタンス
db = Database()
