"""
Firestoreの全データを確認するスクリプト
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

def check_all_data():
    db = FirestoreDatabase()
    
    print("=== Firestore データ確認 ===\n")
    
    # 1. 会社一覧
    companies = db.get_all_companies()
    print(f"会社数: {len(companies)}")
    
    if not companies:
        print("❌ 会社が1件も登録されていません")
        return
    
    for company in companies:
        print(f"\n会社: {company.get('name')} (ID: {company.get('id')})")
        
        # 2. 各会社の規程を確認
        regulations = db.get_company_regulations(company['id'])
        print(f"  規程数: {len(regulations)}")
        
        for reg in regulations:
            print(f"\n  規程ID: {reg.get('id')}")
            print(f"    - 名前: {reg.get('name')}")
            print(f"    - current_version: {reg.get('current_version', 1)}")
            print(f"    - ステータス: {reg.get('status')}")
            
            # 3. バージョン数を確認
            versions_ref = db.db.collection('companies').document(company['id'])\
                .collection('regulations').document(reg['id'])\
                .collection('versions')
            
            versions = list(versions_ref.stream())
            print(f"    - バージョン数: {len(versions)}")
            
            if versions:
                # 最新バージョンの詳細
                for v in versions[:3]:  # 最初の3つ
                    data = v.to_dict()
                    print(f"      * version {data.get('version_number')}: {data.get('description', 'No description')}")

if __name__ == "__main__":
    check_all_data()
