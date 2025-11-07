#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""最新の1件のraw_textを構造化して更新するスクリプト"""

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

def fix_one_record():
    print("=" * 60)
    print("最新データの構造化処理")
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

    # 最新の1件を取得
    print("\n2. 最新のデータを検索...")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, regulation_id, content_json, raw_text, version
        FROM regulation_content
        WHERE length(content_json) <= 2 AND raw_text IS NOT NULL
        ORDER BY id DESC
        LIMIT 1
    """)
    record = cursor.fetchone()
    conn.close()

    if not record:
        print("   構造化が必要なデータが見つかりませんでした")
        return

    record_dict = dict(record)
    record_id = record_dict['id']
    regulation_id = record_dict['regulation_id']
    raw_text = record_dict['raw_text']
    version = record_dict['version']

    print(f"   レコードID={record_id}, 規程ID={regulation_id}")
    print(f"   raw_text: {len(raw_text)}文字")

    # 構造化を実行
    print(f"\n3. 構造化処理を実行中...")
    try:
        result = validator.structure_regulation_text(raw_text)

        if result['success']:
            structure = result.get('structure', [])
            print(f"   [OK] 構造化成功: {len(structure)}章")

            # 章の詳細を表示
            for i, chapter in enumerate(structure[:3], 1):  # 最初の3章のみ
                chapter_num = chapter.get('number', 'N/A')
                chapter_title = chapter.get('title', 'N/A')
                articles_count = len(chapter.get('articles', []))
                print(f"      {chapter_num} {chapter_title}: {articles_count}条")

            # データベースを更新
            print(f"\n4. データベースを更新中...")
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
            print(f"   [OK] データベース更新完了")

        else:
            print(f"   [NG] 構造化失敗")
            print(f"   エラー: {result.get('error', 'N/A')}")
            if 'raw_response' in result:
                print(f"\n   レスポンス（最初の500文字）:")
                print(f"   {result['raw_response'][:500]}")

    except Exception as e:
        import traceback
        print(f"   [NG] 例外発生: {e}")
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("処理完了")
    print("=" * 60)

if __name__ == "__main__":
    fix_one_record()
