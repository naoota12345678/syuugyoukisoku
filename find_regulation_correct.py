"""
正しい会社IDで規程を検索するスクリプト
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

from google.cloud import firestore

def find_regulation_with_versions():
    db = firestore.Client(project='syuugyoukisoku')
    
    # 正しい会社ID
    company_id = "Hh9epYKQAa80qf4jgYES"  # 0が先
    target_regulation_id = "KrarWpZYZ4i8mpJKg25m"
    
    print(f"会社ID: {company_id}")
    print(f"探している規程ID: {target_regulation_id}\n")
    
    # 会社の全規程を確認
    regulations = list(db.collection('companies').document(company_id).collection('regulations').stream())
    print(f"規程総数: {len(regulations)}")
    
    found = False
    for reg in regulations:
        reg_data = reg.to_dict()
        print(f"\n規程ID: {reg.id}")
        print(f"  名前: {reg_data.get('name')}")
        print(f"  current_version: {reg_data.get('current_version')}")
        
        if reg.id == target_regulation_id:
            found = True
            print("  ✅ 目的の規程が見つかりました！")
            
            # バージョンを確認
            versions = list(db.collection('companies').document(company_id)
                          .collection('regulations').document(reg.id)
                          .collection('versions').stream())
            
            print(f"  バージョン数: {len(versions)}")
            
            for ver in versions:
                ver_data = ver.to_dict()
                print(f"\n    Document ID: {ver.id}")
                print(f"    version_number: {ver_data.get('version_number')}")
                print(f"    description: {ver_data.get('description')}")
                print(f"    based_on_version: {ver_data.get('based_on_version')}")
    
    if not found:
        print(f"\n❌ 規程ID {target_regulation_id} は見つかりませんでした")

if __name__ == "__main__":
    find_regulation_with_versions()
