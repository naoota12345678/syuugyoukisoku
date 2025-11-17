"""
Cloud Run環境でのFirebase接続確認スクリプト
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 環境変数の状態を表示
print("=== 環境変数の確認 ===")
print(f"USE_FIRESTORE: {os.environ.get('USE_FIRESTORE', 'Not set')}")
print(f"GOOGLE_CLOUD_PROJECT: {os.environ.get('GOOGLE_CLOUD_PROJECT', 'Not set')}")
print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'Not set')}")

# Firebaseの認証情報を確認
import json
import glob

print("\n=== Firebase認証ファイルの確認 ===")
firebase_files = glob.glob("*firebase*.json")
print(f"Firebaseファイル: {firebase_files}")

if firebase_files:
    with open(firebase_files[0], 'r') as f:
        creds = json.load(f)
        print(f"Project ID in file: {creds.get('project_id')}")

# 環境変数を明示的に設定
os.environ['USE_FIRESTORE'] = 'true'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'syuugyoukisoku'

# Google Cloud認証の設定
if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
    if firebase_files:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = firebase_files[0]
        print(f"\nGOOGLE_APPLICATION_CREDENTIALS set to: {firebase_files[0]}")

# Firestore接続テスト
try:
    from firestore_database import FirestoreDatabase
    
    print("\n=== Firestore接続テスト ===")
    db = FirestoreDatabase()
    
    # 会社一覧を取得
    companies = db.get_all_companies()
    print(f"✅ 接続成功！会社数: {len(companies)}")
    
    if companies:
        print("\n登録されている会社:")
        for company in companies[:5]:  # 最初の5件を表示
            print(f"  - {company.get('name')} (ID: {company.get('id')})")
    
except Exception as e:
    print(f"\n❌ エラー: {e}")
    import traceback
    traceback.print_exc()
