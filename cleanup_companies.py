#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重複した会社を整理するスクリプト"""

import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import Database

def cleanup_duplicate_companies():
    print("=" * 60)
    print("重複会社の整理")
    print("=" * 60)

    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    # 会社ごとにグループ化
    cursor.execute('''
        SELECT name, GROUP_CONCAT(id) as ids, COUNT(*) as count
        FROM companies
        GROUP BY name
        HAVING count > 1
        ORDER BY count DESC
    ''')

    duplicates = cursor.fetchall()

    if not duplicates:
        print("\n重複している会社はありません。")
        conn.close()
        return

    print(f"\n重複している会社: {len(duplicates)}件")
    print()

    for dup in duplicates:
        dup_dict = dict(dup)
        company_name = dup_dict['name']
        ids = dup_dict['ids'].split(',')
        count = dup_dict['count']

        print(f"会社名: {company_name}")
        print(f"  重複数: {count}件")
        print(f"  ID: {', '.join(ids)}")

        # 各IDの規程数を確認
        for company_id in ids:
            cursor.execute('''
                SELECT COUNT(*) as reg_count
                FROM regulations
                WHERE company_id = ?
            ''', (int(company_id),))

            reg_count = cursor.fetchone()['reg_count']
            print(f"    ID={company_id}: {reg_count}件の規程")

        # 規程がある最初のIDを残して、他を削除
        keep_id = None
        delete_ids = []

        for company_id in ids:
            cursor.execute('''
                SELECT COUNT(*) as reg_count
                FROM regulations
                WHERE company_id = ?
            ''', (int(company_id),))

            reg_count = cursor.fetchone()['reg_count']

            if reg_count > 0 and keep_id is None:
                keep_id = int(company_id)
            elif reg_count == 0:
                delete_ids.append(int(company_id))

        # 規程がない会社を削除
        if delete_ids:
            print(f"  → 削除するID: {', '.join(map(str, delete_ids))}")
            for del_id in delete_ids:
                cursor.execute('DELETE FROM companies WHERE id = ?', (del_id,))

        # 規程がある会社が複数ある場合は統合
        if keep_id:
            remaining_ids = [int(id) for id in ids if int(id) != keep_id and int(id) not in delete_ids]
            if remaining_ids:
                print(f"  → ID={keep_id}に統合、他のIDの規程を移動")
                for move_id in remaining_ids:
                    cursor.execute('''
                        UPDATE regulations
                        SET company_id = ?
                        WHERE company_id = ?
                    ''', (keep_id, move_id))

                    cursor.execute('DELETE FROM companies WHERE id = ?', (move_id,))

        print()

    conn.commit()
    conn.close()

    print("=" * 60)
    print("整理完了")
    print("=" * 60)

if __name__ == "__main__":
    cleanup_duplicate_companies()
