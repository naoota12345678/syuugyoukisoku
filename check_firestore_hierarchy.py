"""
Firestoreの階層を順番に確認するスクリプト
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

def check_firestore_hierarchy():
    # 直接Firestoreクライアントを作成
    db = firestore.Client(project='syuugyoukisoku')
    print(f"Firestore Client Project: {db.project}")
    
    print("\n=== 1. Companies コレクション ===")
    companies = list(db.collection('companies').stream())
    print(f"会社数: {len(companies)}")
    
    if companies:
        for company in companies[:2]:  # 最初の2社のみ
            print(f"\n会社ID: {company.id}")
            company_data = company.to_dict()
            print(f"  会社名: {company_data.get('name')}")
            
            # regulations サブコレクション
            regulations = list(db.collection('companies').document(company.id).collection('regulations').stream())
            print(f"  規程数: {len(regulations)}")
            
            if regulations:
                for reg in regulations[:2]:  # 最初の2つのみ
                    print(f"\n    規程ID: {reg.id}")
                    reg_data = reg.to_dict()
                    print(f"      規程名: {reg_data.get('name')}")
                    
                    # versions サブコレクション
                    versions = list(db.collection('companies').document(company.id).collection('regulations').document(reg.id).collection('versions').stream())
                    print(f"      バージョン数: {len(versions)}")
                    
                    if versions:
                        for ver in versions[:3]:  # 最初の3つのみ
                            ver_data = ver.to_dict()
                            print(f"        - Doc ID: {ver.id}")
                            print(f"          version_number: {ver_data.get('version_number')}")
    
    # 特定の規程を直接確認
    print("\n\n=== 2. 特定の規程を直接確認 ===")
    company_id = "Hh9epYKQAa8Dqf4jgYES"
    regulation_id = "KrarWpZYZ4i8mpJKg25m"
    
    # 会社ドキュメントの存在確認
    company_doc = db.collection('companies').document(company_id).get()
    print(f"会社ドキュメント存在: {company_doc.exists}")
    
    if company_doc.exists:
        # 規程ドキュメントの存在確認
        reg_doc = db.collection('companies').document(company_id).collection('regulations').document(regulation_id).get()
        print(f"規程ドキュメント存在: {reg_doc.exists}")
        
        if reg_doc.exists:
            # バージョンコレクションの確認
            versions_path = f"companies/{company_id}/regulations/{regulation_id}/versions"
            print(f"\nパス: {versions_path}")
            
            versions = list(db.collection('companies').document(company_id)
                          .collection('regulations').document(regulation_id)
                          .collection('versions').stream())
            
            print(f"バージョン数: {len(versions)}")
            
            for ver in versions:
                data = ver.to_dict()
                print(f"\n  Document ID: {ver.id}")
                print(f"  version_number: {data.get('version_number')} (型: {type(data.get('version_number'))})")

if __name__ == "__main__":
    check_firestore_hierarchy()
