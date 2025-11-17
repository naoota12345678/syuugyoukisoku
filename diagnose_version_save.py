"""
バージョン履歴保存の問題を診断するスクリプト
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

def diagnose_version_save():
    db = FirestoreDatabase()
    
    # テスト用の会社IDと規程ID
    company_id = input("会社ID（例：Hh9epYKQAa8Dqf4jgYES）: ")
    regulation_id = input("規程ID: ")
    
    if not company_id or not regulation_id:
        print("会社IDと規程IDは必須です")
        return
    
    print(f"\n=== 診断開始: company_id={company_id}, regulation_id={regulation_id} ===")
    
    # 1. 規程情報を取得
    regulation = db.get_regulation(company_id, regulation_id)
    if not regulation:
        print("❌ 規程が見つかりません")
        return
    
    print(f"\n✅ 規程情報:")
    print(f"  - 名前: {regulation.get('name')}")
    print(f"  - current_version: {regulation.get('current_version', 'なし')}")
    
    # 2. 全バージョンを取得
    print(f"\n=== バージョン一覧 ===")
    versions_ref = db.db.collection('companies').document(company_id)\
        .collection('regulations').document(regulation_id)\
        .collection('versions')
    
    versions = list(versions_ref.stream())
    print(f"バージョン数: {len(versions)}")
    
    for doc in versions:
        data = doc.to_dict()
        print(f"\n  バージョンID: {doc.id}")
        print(f"  - version_number: {data.get('version_number')}")
        print(f"  - based_on_version: {data.get('based_on_version')}")
        print(f"  - description: {data.get('description')}")
        print(f"  - created_at: {data.get('created_at')}")
        print(f"  - raw_text長さ: {len(data.get('raw_text', ''))}")
    
    # 3. 新バージョン保存のテスト
    print(f"\n=== 新バージョン保存テスト ===")
    test_save = input("テスト保存を実行しますか？ (y/n): ")
    
    if test_save.lower() == 'y':
        # 現在のバージョンを取得
        current_version = regulation.get('current_version', 1)
        new_version = current_version + 1
        
        print(f"\nバージョン{new_version}として保存を試みます...")
        
        # 最新のコンテンツを取得
        content_data = db.get_regulation_content(company_id, regulation_id)
        if content_data:
            raw_text = content_data.get('raw_text', '')
            tables = content_data.get('tables', [])
            
            # 新バージョンとして保存
            version_id = db.save_regulation_content(
                company_id=company_id,
                regulation_id=regulation_id,
                content_dict=None,
                version=new_version,
                raw_text=raw_text + "\n\n【テスト追記】このバージョンはテストで作成されました。",
                tables=tables,
                based_on_version=current_version,
                description="診断テスト"
            )
            
            print(f"✅ バージョン{new_version}を保存しました (ID: {version_id})")
            
            # 再度バージョン一覧を確認
            print(f"\n=== 保存後のバージョン一覧 ===")
            versions = list(versions_ref.stream())
            print(f"バージョン数: {len(versions)}")
            
            for doc in versions:
                data = doc.to_dict()
                print(f"  - version_number: {data.get('version_number')}")

if __name__ == "__main__":
    diagnose_version_save()
