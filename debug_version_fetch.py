"""
バージョン取得の問題をデバッグするスクリプト
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

def debug_version_fetch():
    db = FirestoreDatabase()
    
    company_id = "Hh9epYKQAa8Dqf4jgYES"
    regulation_id = "KrarWpZYZ4i8mpJKg25m"
    
    print("=== バージョン取得のデバッグ ===\n")
    
    # 1. 全バージョンの詳細を表示
    versions_ref = db.db.collection('companies').document(company_id)\
        .collection('regulations').document(regulation_id)\
        .collection('versions')
    
    all_versions = list(versions_ref.stream())
    print(f"総バージョン数: {len(all_versions)}")
    
    print("\n各バージョンの詳細:")
    for doc in all_versions:
        data = doc.to_dict()
        print(f"\nDocument ID: {doc.id}")
        print(f"  version_number: {data.get('version_number')} (型: {type(data.get('version_number'))})")
        print(f"  description: {data.get('description')}")
        print(f"  based_on_version: {data.get('based_on_version')}")
        print(f"  raw_text長さ: {len(data.get('raw_text', ''))}")
    
    # 2. get_regulation_content関数のテスト
    print("\n\n=== get_regulation_content テスト ===")
    
    for version in [4, 5]:
        print(f"\nバージョン{version}を取得...")
        content = db.get_regulation_content(company_id, regulation_id, version=version)
        
        if content:
            print(f"  ✅ 取得成功")
            print(f"  - Document ID: {content.get('id')}")
            print(f"  - version_number: {content.get('version_number')}")
            print(f"  - raw_text最初の50文字: {content.get('raw_text', '')[:50]}...")
        else:
            print(f"  ❌ 取得失敗")
            
            # 手動で検索
            print(f"  手動検索を試行...")
            for doc in all_versions:
                data = doc.to_dict()
                if data.get('version_number') == version:
                    print(f"  ✓ 手動で見つかりました: {doc.id}")
                    break
            else:
                print(f"  ✗ 手動でも見つかりません")

if __name__ == "__main__":
    debug_version_fetch()
