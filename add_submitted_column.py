#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""提出日カラムを追加"""

import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import Database

def add_submitted_column():
    print("=" * 60)
    print("データベースに提出日カラムを追加")
    print("=" * 60)

    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    # regulationsテーブルにsubmitted_atカラムを追加
    try:
        cursor.execute('''
            ALTER TABLE regulations
            ADD COLUMN submitted_at DATETIME
        ''')
        print("\n✓ submitted_at カラムを追加しました")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("\n✓ submitted_at カラムは既に存在します")
        else:
            print(f"\n✗ エラー: {e}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("完了")
    print("=" * 60)

if __name__ == "__main__":
    add_submitted_column()
