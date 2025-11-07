#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""施行日カラムを追加"""

import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import Database

def add_effective_date_column():
    print("=" * 60)
    print("データベースに施行日カラムを追加")
    print("=" * 60)

    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    # regulationsテーブルにeffective_dateカラムを追加
    try:
        cursor.execute('''
            ALTER TABLE regulations
            ADD COLUMN effective_date DATE
        ''')
        print("\n✓ effective_date カラムを追加しました")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("\n✓ effective_date カラムは既に存在します")
        else:
            print(f"\n✗ エラー: {e}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("完了")
    print("=" * 60)

if __name__ == "__main__":
    add_effective_date_column()
