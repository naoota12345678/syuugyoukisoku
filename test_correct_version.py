"""
正しいIDでバージョン取得をテストするスクリプト
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

def test_version_retrieval():
    # 正しいプロジェクトIDで初期化
    db = FirestoreDatabase(project_id='syuugyoukisoku')
    
    # 正しいID
    company_id = "Hh9epYKQAa80qf4jgYES"  # 0が先！
    regulation_id = "KrarWpZYZ4i8mpJKg25m"
    
    print(f"=== バージョン取得テスト ===")
    print(f"会社ID: {company_id}")
    print(f"規程ID: {regulation_id}\n")
    
    # 各バージョンを個別に取得
    for version_num in [0, 1, 2, 3, 4, 5]:
        print(f"\nバージョン {version_num} を取得中...")
        content = db.get_regulation_content(company_id, regulation_id, version=version_num)
        
        if content:
            print(f"  ✅ 成功!")
            print(f"  - Document ID: {content.get('id')}")
            print(f"  - version_number: {content.get('version_number')}")
            print(f"  - description: {content.get('description')}")
            print(f"  - based_on_version: {content.get('based_on_version')}")
            print(f"  - raw_text の最初の50文字: {content.get('raw_text', '')[:50]}...")
        else:
            print(f"  ❌ 失敗")
    
    # 最新バージョン（指定なし）も取得
    print(f"\n\n最新バージョン（version指定なし）を取得中...")
    latest_content = db.get_regulation_content(company_id, regulation_id)
    
    if latest_content:
        print(f"  ✅ 成功!")
        print(f"  - version_number: {latest_content.get('version_number')}")
    else:
        print(f"  ❌ 失敗")

if __name__ == "__main__":
    test_version_retrieval()
