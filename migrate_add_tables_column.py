#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""既存のデータベースにtables_jsonカラムを追加するマイグレーション"""

import sqlite3
import os
import sys
import io

# Windows環境でのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def migrate_database():
    """regulation_contentテーブルにtables_jsonカラムを追加"""
    db_path = "database/regulations.db"

    if not os.path.exists(db_path):
        print("データベースが見つかりません。新規作成時は自動的にカラムが追加されます。")
        return

    print(f"データベース: {db_path}")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # カラムが既に存在するか確認
        cursor.execute("PRAGMA table_info(regulation_content)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'tables_json' in columns:
            print("[OK] tables_jsonカラムは既に存在します")
        else:
            print("tables_jsonカラムを追加中...")
            cursor.execute('''
                ALTER TABLE regulation_content
                ADD COLUMN tables_json TEXT
            ''')
            conn.commit()
            print("[OK] tables_jsonカラムを追加しました")

        # 確認
        cursor.execute("PRAGMA table_info(regulation_content)")
        print("\n現在のカラム:")
        for col in cursor.fetchall():
            col_id, name, col_type, not_null, default, pk = col
            print(f"  - {name} ({col_type})")

        print("\n" + "=" * 60)
        print("マイグレーション完了！")

    except Exception as e:
        print(f"エラー: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
