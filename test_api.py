#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API動作テスト"""

import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import Database

def test_api_data():
    print("=" * 60)
    print("API動作テスト")
    print("=" * 60)

    db = Database()

    # 最新の規程IDを取得
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, company_id, name, status
        FROM regulations
        ORDER BY id DESC
        LIMIT 1
    """)
    regulation = cursor.fetchone()

    if regulation:
        reg_dict = dict(regulation)
        print(f"\n最新の規程:")
        print(f"  ID: {reg_dict['id']}")
        print(f"  名前: {reg_dict['name']}")
        print(f"  ステータス: {reg_dict['status']}")

        # この規程の修正提案を取得
        regulation_id = reg_dict['id']
        cursor.execute("""
            SELECT id, article_number, modification_type, status
            FROM modifications
            WHERE regulation_id = ?
            ORDER BY id
        """, (regulation_id,))

        mods = cursor.fetchall()
        print(f"\n  修正提案: {len(mods)}件")
        for mod in mods:
            mod_dict = dict(mod)
            print(f"    - ID={mod_dict['id']}: {mod_dict['article_number']} ({mod_dict['status']})")

    conn.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_api_data()
