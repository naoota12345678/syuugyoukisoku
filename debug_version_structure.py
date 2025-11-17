"""
バージョンデータの詳細構造を確認するスクリプト
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
import json

def debug_version_structure():
    db = FirestoreDatabase()
    
    company_id = "Hh9epYKQAa8Dqf4jgYES"
    regulation_id = "KrarWpZYZ4i8mpJKg25m"
    
    print("=== バージョンデータの構造を確認 ===\n")
    
    # 全バージョンのドキュメントを取得
    versions_ref = db.db.collection('companies').document(company_id)\
        .collection('regulations').document(regulation_id)\
        .collection('versions')
    
    all_versions = list(versions_ref.stream())
    print(f"総ドキュメント数: {len(all_versions)}")
    
    # 各ドキュメントの全フィールドを表示
    for i, doc in enumerate(all_versions):
        print(f"\n\n=== ドキュメント {i+1} ===")
        print(f"Document ID: {doc.id}")
        
        data = doc.to_dict()
        print(f"フィールド数: {len(data)}")
        
        # 全フィールドを表示（raw_textとtables以外）
        for key, value in data.items():
            if key in ['raw_text', 'tables', 'content_json']:
                if isinstance(value, str):
                    print(f"  {key}: (文字列, 長さ: {len(value)})")
                else:
                    print(f"  {key}: (型: {type(value)})")
            else:
                print(f"  {key}: {value} (型: {type(value)})")
        
        # version関連のフィールドを特別に確認
        print("\n  バージョン関連フィールド:")
        for key in ['version', 'version_number', 'version_num', 'ver']:
            if key in data:
                print(f"    ✓ {key} = {data[key]}")
            else:
                print(f"    ✗ {key} = 存在しない")

if __name__ == "__main__":
    debug_version_structure()
