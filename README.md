# 商品認識AI接客システム

カメラに映した商品を Gemini Vision API で認識し、社内の商品データベースと照合したうえで、
「ベテラン販売スタッフ」として価格・仕様・在庫を踏まえた質問対応や関連商品提案を、
自然な日本語チャットで行う Web アプリケーションです。

## システム構成

```
Streamlit（カメラ撮影 + チャットUI）
    ↕  REST (JSON)
FastAPI（商品認識 / 接客応答 / 履歴・統計API）
    ↕
SQLite（商品マスタ / セッション / 会話履歴 / 検出ログ）
    ↕
Google Gemini（Vision: 画像認識 / Text: 応答生成）
```

バックエンド・フロントエンド・データ層を分離した3層構成です。

## 実装上の工夫

「外部AIを呼ぶだけ」では実用にならないため、出力の揺らぎを吸収して既存データへ確実に橋渡しする部分を作り込んでいます。

### 1. 認識結果 → 商品DBの多段マッチング
Gemini Vision には JSON 形式での回答を指示し、応答から ```` ```json ```` ブロックを正規表現で抽出してパースします。
得られたブランド／商品名／カテゴリをそのまま使うのではなく、商品マスタに対して次の多段検索で最適な1件を決定します。

1. ブランド名で絞り込み
2. 商品名の主要キーワードでさらに絞り込み
3. 見つからなければカテゴリで再検索
4. それでも無ければ商品名キーワードで部分一致検索
5. 複数候補はスコアリング（ブランド一致 +10 / キーワード一致 +5 / カテゴリ一致 +3）で最良を選択

### 2. Gemini モデルのフォールバック
無料枠のレート制限（15リクエスト/分）で特定モデルが使えなくなっても止まらないよう、
優先順位付きのモデル候補を順にテスト生成し、実際に応答が得られたモデルを採用します（Vision・Text 双方に適用）。
全候補が失敗した場合は、利用可能なモデル一覧を出力して原因を切り分けられるようにしています。

### 3. 文脈を保持した接客応答
販売員ペルソナのシステムプロンプトに、直近3件の会話履歴と現在案内中の商品情報を差し込んで応答を生成。
会話は SQLite にセッション単位で保存し、文脈を維持します。

### 4. 運用を意識したAPI
ヘルスチェック、統計（セッション/会話/検出数・人気商品）、検出ログ（信頼度付き）などのエンドポイントを用意し、
Pydantic でリクエスト/レスポンスを型検証しています。

## 技術スタック

| 層 | 使用技術 |
|----|----------|
| バックエンド | FastAPI / Pydantic / SQLite / google-generativeai / Pillow |
| フロントエンド | Streamlit / OpenCV / Requests |
| AI | Google Gemini（Vision・Text） |

## 主要APIエンドポイント

| メソッド | パス | 概要 |
|----------|------|------|
| POST | `/api/recognize` | 画像から商品を認識しDB照合 |
| POST | `/api/chat` | 接客応答を生成 |
| GET | `/api/product/{id}` | 商品情報を取得 |
| POST | `/api/product/introduction/{id}` | 商品紹介文を生成 |
| GET | `/api/stats` | システム統計を取得 |
| GET | `/health` | ヘルスチェック |

## セットアップ

```bash
# 1. APIキーを設定（.env.example をコピーして編集）
copy .env.example .env        # GEMINI_API_KEY を記入

# 2. 仮想環境と依存関係（バックエンド / フロントエンドそれぞれ）
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt

# 3. 起動
python backend/main.py        # http://localhost:8000/docs
streamlit run frontend/app.py # http://localhost:8501
```

Google AI Studio（<https://aistudio.google.com/app/apikey>）で Gemini API キーを取得してください。

## 現状の制約と今後の改善

プロトタイプとして、以下は意図的に簡略化しています。

- 認識の `confidence` は暫定の固定値で、Vision の出力からのスコア化は未実装
- CORS は全許可・認証なし（本番では特定オリジン限定＋認証が必要）
- SQLite 単一プロセス構成（スケール時は PostgreSQL への移行を想定）

## ライセンス

MIT License
