"""
Gemini API 接続テストスクリプト
"""
import os
import sys

# パス追加
sys.path.insert(0, 'backend')

print("=" * 60)
print("Gemini API 接続テスト")
print("=" * 60)
print()

# 1. APIキー確認
print("[1/4] APIキーの確認...")
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY が設定されていません")
    print("   .envファイルを確認してください")
    sys.exit(1)
print(f"✓ APIキーが設定されています: {api_key[:10]}...")
print()

# 2. Gemini APIライブラリ確認
print("[2/4] Gemini APIライブラリの確認...")
try:
    import google.generativeai as genai
    print("✓ google-generativeai がインストールされています")
except ImportError:
    print("❌ google-generativeai がインストールされていません")
    print("   pip install google-generativeai を実行してください")
    sys.exit(1)
print()

# 3. 利用可能なモデルの確認
print("[3/4] 利用可能なモデルの確認...")
genai.configure(api_key=api_key)

try:
    models = []
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            models.append(model.name)
            print(f"  ✓ {model.name}")
    
    if not models:
        print("❌ 利用可能なモデルが見つかりませんでした")
        sys.exit(1)
    
    print(f"\n利用可能なモデル数: {len(models)}")
except Exception as e:
    print(f"❌ モデルリストの取得に失敗: {e}")
    sys.exit(1)
print()

# 4. 実際にテスト生成
print("[4/4] テスト生成...")
test_models = [
    'gemini-2.5-flash',
    'gemini-flash-latest',
    'gemini-2.0-flash',
    'gemini-2.5-pro',
    'gemini-pro-latest',
]

success = False
for model_name in test_models:
    try:
        print(f"  試行: {model_name}...", end=" ")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("こんにちは")
        if response and response.text:
            print(f"✓ 成功")
            print(f"    レスポンス: {response.text[:50]}...")
            success = True
            break
    except Exception as e:
        print(f"✗ 失敗: {str(e)[:80]}")

print()

if success:
    print("=" * 60)
    print("✅ すべてのテストに成功しました！")
    print("=" * 60)
else:
    print("=" * 60)
    print("❌ テスト生成に失敗しました")
    print("   利用可能なモデルを確認してください")
    print("=" * 60)
    sys.exit(1)
