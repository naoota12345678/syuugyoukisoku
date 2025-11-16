#!/usr/bin/env python3
"""
バージョン1を表示できない問題の応急処置スクリプト
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['USE_FIRESTORE'] = 'true'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'syuugyoukisoku'

from firestore_database import FirestoreDatabase
from firebase_admin import firestore

def show_version_1(regulation_id):
    """バージョン1（または最も古いバージョン）を強制的に取得して表示"""
    
    db = FirestoreDatabase()
    
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        print(f"規程ID {regulation_id} が見つかりません")
        return
    
    company_id = regulation['company_id']
    
    # 全バージョンを取得して作成日時でソート（古い順）
    versions = db.get_all_versions(company_id, regulation_id)
    if not versions:
        print("バージョンが見つかりません")
        return
    
    # 作成日時でソート（最も古いものを取得）
    versions_sorted = sorted(versions, key=lambda v: v.get('created_at', ''))
    oldest_version = versions_sorted[0]
    
    print(f"\n=== 最も古いバージョンの情報 ===")
    print(f"バージョン番号: {oldest_version.get('version_number')}")
    print(f"作成日時: {oldest_version.get('created_at')}")
    
    # raw_textを表示
    raw_text = oldest_version.get('raw_text', '')
    if raw_text:
        print(f"\n=== テキスト内容（最初の500文字）===")
        print(raw_text[:500])
        print(f"\n... (全{len(raw_text)}文字)")
    else:
        print("\nraw_textが見つかりません")
    
    return oldest_version


def create_version_1_from_oldest(regulation_id):
    """最も古いバージョンをバージョン1として複製"""
    
    db = FirestoreDatabase()
    
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return
    
    company_id = regulation['company_id']
    
    # 既存のバージョン1があるかチェック
    existing_v1 = db.get_regulation_content(company_id, regulation_id, version=1)
    if existing_v1:
        print("バージョン1は既に存在します")
        return
    
    # 最も古いバージョンを取得
    oldest = show_version_1(regulation_id)
    if not oldest:
        return
    
    print("\n最も古いバージョンをバージョン1として保存しますか？ (yes/no): ", end='')
    answer = input().strip().lower()
    
    if answer == 'yes':
        # バージョン1として保存
        db.save_regulation_content(
            company_id=company_id,
            regulation_id=regulation_id,
            content_dict=oldest.get('content_json'),
            version=1,
            raw_text=oldest.get('raw_text'),
            tables=oldest.get('tables'),
            description="最も古いバージョンから復元"
        )
        print("✅ バージョン1を作成しました")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python fix_version_1.py <regulation_id> [--create]")
        sys.exit(1)
    
    regulation_id = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2] == '--create':
        create_version_1_from_oldest(regulation_id)
    else:
        show_version_1(regulation_id)
