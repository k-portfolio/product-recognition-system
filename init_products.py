"""
商品データ初期化スクリプト

products.jsonから商品データをデータベースに登録
"""
import sys
import os
import json

# パスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import db


def load_products():
    """商品データをJSONから読み込み"""
    # スクリプトのディレクトリを基準にする
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'data', 'products.json')
    
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"商品データファイルが見つかりません: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get('products', [])


def initialize_products():
    """商品データをデータベースに登録"""
    products = load_products()
    
    print(f"商品データを読み込みました: {len(products)}件")
    print()
    
    registered_count = 0
    
    for product in products:
        try:
            product_id = db.add_product(
                name=product['name'],
                category=product['category'],
                brand=product['brand'],
                price=product['price'],
                description=product['description'],
                specifications=product.get('specifications', {}),
                stock=product.get('stock', 0),
                keywords=product.get('keywords', [])
            )
            
            print(f"✓ 登録完了: {product['name']} (ID: {product_id})")
            registered_count += 1
        
        except Exception as e:
            print(f"✗ 登録失敗: {product['name']} - {e}")
    
    print()
    print(f"========================================")
    print(f"登録完了: {registered_count}/{len(products)}件")
    print(f"========================================")


if __name__ == "__main__":
    print("========================================")
    print("商品データ初期化")
    print("========================================")
    print()
    
    # global宣言を最初に
    global db
    
    # 既存データの確認
    existing_products = db.get_all_products()
    
    if existing_products:
        print(f"データベースに既に{len(existing_products)}件の商品が登録されています。")
        print()
        response = input("既存データを削除して再登録しますか？ (y/N): ")
        
        if response.lower() != 'y':
            print("処理を中止しました。")
            sys.exit(0)
        
        # 既存データの削除（簡易実装：データベースファイル削除）
        print("既存データを削除しています...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, "data", "store.db")
        if os.path.exists(db_path):
            os.remove(db_path)
            print("削除完了")
        
        # データベース再初期化
        from database import Database
        db = Database()
        print()
    
    # 商品データ登録
    initialize_products()
