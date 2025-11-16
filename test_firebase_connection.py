"""
Firebaseの接続を修正するスクリプト
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 環境変数を設定
os.environ['USE_FIRESTORE'] = 'true'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'syuugyoukisoku'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'syuugyoukisoku-firebase-adminsdk-fbsvc-c755ae852f.json'

# ローカルでテスト
from firestore_database import FirestoreDatabase

try:
    db = FirestoreDatabase()
    print("✅ Firebaseに接続できました！")
    
    # 会社一覧を取得してテスト
    companies = db.get_all_companies()
    print(f"会社数: {len(companies)}")
    
except Exception as e:
    print(f"❌ エラー: {e}")
    print("\n解決方法:")
    print("1. gcloud auth application-default login を実行")
    print("2. または、サービスアカウントキーのパスを確認")
