"""
アプリケーションのバージョン表示問題を診断するスクリプト
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

def analyze_app_version_issue():
    """アプリでのバージョン表示問題を分析"""
    
    db = FirestoreDatabase(project_id='syuugyoukisoku')
    
    # 1. get_regulation_by_id をテスト
    regulation_id = "KrarWpZYZ4i8mpJKg25m"
    print("=== get_regulation_by_id のテスト ===")
    regulation = db.get_regulation_by_id(regulation_id)
    
    if regulation:
        print(f"✅ 規程が見つかりました")
        print(f"  - 規程名: {regulation.get('name')}")
        print(f"  - 会社ID: {regulation.get('company_id')}")
        print(f"  - current_version: {regulation.get('current_version')}")
        
        company_id = regulation.get('company_id')
        
        # 2. バージョン履歴を確認
        print(f"\n=== バージョン履歴 ===")
        versions = db.get_all_versions(company_id, regulation_id)
        print(f"バージョン数: {len(versions)}")
        
        for v in versions:
            print(f"\n  Version {v.get('version_number')}:")
            print(f"    - Document ID: {v.get('id')}")
            print(f"    - created_at: {v.get('created_at')}")
            
        # 3. 各バージョンの内容を比較
        print(f"\n=== 各バージョンの内容比較 ===")
        for version_num in [3, 4, 5]:
            print(f"\nVersion {version_num}:")
            content = db.get_regulation_content(company_id, regulation_id, version=version_num)
            if content:
                raw_text = content.get('raw_text', '')
                # 最初と最後の100文字を表示
                print(f"  最初の100文字: {raw_text[:100]}")
                print(f"  最後の100文字: {raw_text[-100:]}")
                print(f"  全体の長さ: {len(raw_text)}文字")
            else:
                print(f"  ❌ 取得失敗")
                
    else:
        print("❌ 規程が見つかりません（IDの問題？）")

if __name__ == "__main__":
    analyze_app_version_issue()
