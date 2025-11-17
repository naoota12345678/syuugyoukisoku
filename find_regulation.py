"""
規程IDから会社IDを探すスクリプト
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

def find_regulation():
    db = FirestoreDatabase()
    
    regulation_id = "KrarWpZYZ4i8mpJKg25m"
    print(f"規程ID {regulation_id} を検索中...")
    
    # get_regulation_by_idを使って検索
    regulation = db.get_regulation_by_id(regulation_id)
    
    if regulation:
        print(f"\n✅ 規程が見つかりました！")
        print(f"  - 規程名: {regulation.get('name')}")
        print(f"  - 会社ID: {regulation.get('company_id')}")
        print(f"  - current_version: {regulation.get('current_version')}")
        
        # 会社情報も取得
        company = db.get_company(regulation.get('company_id'))
        if company:
            print(f"  - 会社名: {company.get('name')}")
        
        return regulation.get('company_id'), regulation_id
    else:
        print("❌ 規程が見つかりません")
        
        # 全会社から検索
        print("\n全ての会社から規程を検索中...")
        companies = db.get_all_companies()
        
        for company in companies:
            print(f"\n会社: {company.get('name')} (ID: {company.get('id')})")
            regulations = db.get_company_regulations(company['id'])
            
            for reg in regulations:
                if reg['id'] == regulation_id:
                    print(f"  ✅ 見つかりました！")
                    print(f"    - 規程名: {reg.get('name')}")
                    return company['id'], regulation_id
        
        return None, None

if __name__ == "__main__":
    company_id, regulation_id = find_regulation()
    
    if company_id:
        print(f"\n\n診断スクリプトで使用する値:")
        print(f"会社ID: {company_id}")
        print(f"規程ID: {regulation_id}")
