#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""データベースを完全にリセット（自動実行版）"""

import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import Database

def reset_database_auto():
    print("=" * 60)
    print("データベースの自動リセット")
    print("=" * 60)

    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    # 各テーブルのレコード数を表示
    print("\n【削除前の状態】")
    tables = ['companies', 'regulations', 'regulation_content', 'modifications', 'validation_results']
    for table in tables:
        cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
        count = cursor.fetchone()['count']
        print(f"  {table}: {count}件")

    print("\nすべてのデータを削除します...")

    # 外部キー制約を一時的に無効化
    cursor.execute('PRAGMA foreign_keys = OFF')

    # すべてのテーブルをクリア
    cursor.execute('DELETE FROM validation_results')
    cursor.execute('DELETE FROM modifications')
    cursor.execute('DELETE FROM regulation_content')
    cursor.execute('DELETE FROM regulations')
    cursor.execute('DELETE FROM companies')

    # 外部キー制約を再度有効化
    cursor.execute('PRAGMA foreign_keys = ON')

    # オートインクリメントをリセット
    cursor.execute('DELETE FROM sqlite_sequence')

    conn.commit()

    # 削除後の状態を表示
    print("\n【削除後の状態】")
    for table in tables:
        cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
        count = cursor.fetchone()['count']
        print(f"  {table}: {count}件")

    conn.close()

    print("\n" + "=" * 60)
    print("✓ リセット完了！まっさらな状態になりました。")
    print("=" * 60)

if __name__ == "__main__":
    reset_database_auto()
