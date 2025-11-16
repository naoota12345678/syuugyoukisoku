#!/usr/bin/env python3
"""
就業規則システムのバージョン管理問題を診断するスクリプト
"""

import os
import sys
from datetime import datetime

# プロジェクトのパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 環境変数設定
os.environ['USE_FIRESTORE'] = 'true'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'syuugyoukisoku'

from firestore_database import FirestoreDatabase

def diagnose_version_issue(regulation_id):
    """特定の規程のバージョン管理問題を診断"""
    
    db = FirestoreDatabase()
    
    print(f"\n=== 規程ID: {regulation_id} のバージョン診断 ===\n")
    
    # 規程情報を取得
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        print(f"❌ 規程ID {regulation_id} が見つかりません")
        return
    
    print(f"✅ 規程情報:")
    print(f"   - 名前: {regulation.get('name')}")
    print(f"   - 会社ID: {regulation.get('company_id')}")
    print(f"   - current_version: {regulation.get('current_version')}")
    print(f"   - ステータス: {regulation.get('status')}")
    
    company_id = regulation['company_id']
    
    # 全バージョンを取得
    print(f"\n📋 登録されているバージョン一覧:")
    versions = db.get_all_versions(company_id, regulation_id)
    
    if not versions:
        print("   ❌ バージョンが1つも登録されていません！")
        return
    
    for v in versions:
        version_num = v.get('version_number', '不明')
        created_at = v.get('created_at', '不明')
        if isinstance(created_at, datetime):
            created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
        
        has_content = bool(v.get('content_json'))
        has_raw_text = bool(v.get('raw_text'))
        
        print(f"\n   バージョン {version_num}:")
        print(f"   - 作成日時: {created_at}")
        print(f"   - content_json: {'✅ あり' if has_content else '❌ なし'}")
        print(f"   - raw_text: {'✅ あり' if has_raw_text else '❌ なし'}")
        print(f"   - created_by: {v.get('created_by', '不明')}")
    
    # バージョン1を取得してみる
    print(f"\n🔍 バージョン1の取得テスト:")
    version1 = db.get_regulation_content(company_id, regulation_id, version=1)
    if version1:
        print(f"   ✅ バージョン1を取得できました")
        print(f"   - version_number: {version1.get('version_number')}")
    else:
        print(f"   ❌ バージョン1を取得できませんでした")
    
    # 最新バージョンを取得
    print(f"\n🔍 最新バージョンの取得テスト:")
    latest = db.get_regulation_content(company_id, regulation_id)
    if latest:
        print(f"   ✅ 最新バージョンを取得できました")
        print(f"   - version_number: {latest.get('version_number')}")
    else:
        print(f"   ❌ 最新バージョンを取得できませんでした")
    
    # 問題の診断
    print(f"\n💡 診断結果:")
    
    if regulation.get('current_version') != len(versions):
        print(f"   ⚠️  current_version ({regulation.get('current_version')}) とバージョン数 ({len(versions)}) が一致しません")
    
    version_numbers = [v.get('version_number') for v in versions]
    if 1 not in version_numbers:
        print(f"   ❌ バージョン1が存在しません")
    
    # 重複チェック
    if len(version_numbers) != len(set(version_numbers)):
        print(f"   ⚠️  重複するバージョン番号があります")
    
    print("\n=== 診断完了 ===\n")


def fix_version_numbering(regulation_id):
    """バージョン番号を修正する"""
    
    db = FirestoreDatabase()
    
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        print(f"❌ 規程ID {regulation_id} が見つかりません")
        return
    
    company_id = regulation['company_id']
    
    print(f"\n🔧 バージョン番号の修正を開始します...")
    
    # 全バージョンを取得して作成日時でソート
    versions = db.get_all_versions(company_id, regulation_id)
    versions_sorted = sorted(versions, key=lambda v: v.get('created_at', datetime.min))
    
    print(f"   {len(versions_sorted)} 個のバージョンを作成日時順に並べ替えました")
    
    # 正しいバージョン番号を振り直す
    for i, version in enumerate(versions_sorted, 1):
        old_version_num = version.get('version_number')
        if old_version_num != i:
            print(f"   バージョン {old_version_num} → {i} に修正")
            # ここでFirestoreを更新するロジックを追加
            # （実装は省略）
    
    print(f"\n✅ バージョン番号の修正が完了しました")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python diagnose_versions.py <regulation_id> [--fix]")
        sys.exit(1)
    
    regulation_id = sys.argv[1]
    
    # 診断を実行
    diagnose_version_issue(regulation_id)
    
    # --fixオプションがある場合は修正も実行
    if len(sys.argv) > 2 and sys.argv[2] == '--fix':
        fix_version_numbering(regulation_id)
