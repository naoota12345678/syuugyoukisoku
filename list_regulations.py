"""
会社の規程一覧を表示するスクリプト
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 環境変数を設定
os.environ['USE_FIRESTORE'] = 'true'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'syuugyoukisoku'

# Firebase認証の設定
firebase_files = [f for f in os.listdir('.') if 'firebase' in f and f.endswith('.json')]
if firebase_files:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = firebase_files[0]

from firestore_database import FirestoreDatabase

def list_regulations():
    db = FirestoreDatabase()
    
    # 会社一覧を取得
    companies = db.get_all_companies()
    
    print("=== 会社一覧 ===")
    for i, company in enumerate(companies):
        print(f"{i+1}. {company.get('name')} (ID: {company.get('id')})")
    
    # 会社を選択
    choice = input("\n会社番号を選択してください: ")
    try:
        company = companies[int(choice) - 1]
        company_id = company['id']
    except:
        print("無効な選択です")
        return
    
    # 規程一覧を取得
    regulations = db.get_company_regulations(company_id)
    
    print(f"\n=== {company['name']}の規程一覧 ===")
    for reg in regulations:
        print(f"\n規程ID: {reg.get('id')}")
        print(f"  - 名前: {reg.get('name')}")
        print(f"  - current_version: {reg.get('current_version', 1)}")
        print(f"  - 作成日: {reg.get('created_at')}")

if __name__ == "__main__":
    list_regulations()
