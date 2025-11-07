#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""既存のraw_textを構造化して更新するスクリプト"""

import sys
import os
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# パスを設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from claude_validator import ClaudeValidator
from database import Database
import json

def fix_existing_data():
    print("=" * 60)
    print("既存データの構造化処理")
    print("=" * 60)

    # 初期化
    print("\n1. 初期化...")
    try:
        validator = ClaudeValidator()
        db = Database()
        print("   [OK] 初期化成功")
    except Exception as e:
        print(f"   [NG] 初期化失敗: {e}")
        return

    # 構造化が必要なデータを取得
    print("\n2. 構造化が必要なデータを検索...")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, regulation_id, content_json, raw_text, version
        FROM regulation_content
        WHERE length(content_json) <= 2 AND raw_text IS NOT NULL
        ORDER BY id DESC
    """)
    records = cursor.fetchall()
    conn.close()

    if not records:
        print("   構造化が必要なデータが見つかりませんでした")
        return

    print(f"   {len(records)}件のデータが見つかりました")

    # 各レコードを処理
    for i, record in enumerate(records, 1):
        record_dict = dict(record)
        record_id = record_dict['id']
        regulation_id = record_dict['regulation_id']
        raw_text = record_dict['raw_text']
        version = record_dict['version']

        print(f"\n3-{i}. レコードID={record_id}, 規程ID={regulation_id} を処理中...")
        print(f"      raw_text: {len(raw_text)}文字")

        # 構造化を実行
        try:
            result = validator.structure_regulation_text(raw_text)

            if result['success']:
                structure = result.get('structure', [])
                print(f"      [OK] 構造化成功: {len(structure)}章")

                # データベースを更新
                conn = db.get_connection()
                cursor = conn.cursor()

                # 構造化データを保存
                content_dict = {"structure": structure}
                content_json = json.dumps(content_dict, ensure_ascii=False)

                cursor.execute("""
                    UPDATE regulation_content
                    SET content_json = ?
                    WHERE id = ?
                """, (content_json, record_id))

                conn.commit()
                conn.close()
                print(f"      [OK] データベース更新完了")

            else:
                print(f"      [NG] 構造化失敗")
                print(f"      エラー: {result.get('error', 'N/A')}")

        except Exception as e:
            import traceback
            print(f"      [NG] 例外発生: {e}")
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("処理完了")
    print("=" * 60)

if __name__ == "__main__":
    fix_existing_data()
