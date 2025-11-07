#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""JSONの詳細構造を確認"""

import sys
import os
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import Database

def check_json_structure():
    print("=" * 80)
    print("JSON構造の詳細確認")
    print("=" * 80)

    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    # 最新の規程を取得
    cursor.execute('''
        SELECT rc.content_json, rc.raw_text, r.name
        FROM regulation_content rc
        JOIN regulations r ON rc.regulation_id = r.id
        ORDER BY r.id DESC
        LIMIT 1
    ''')

    result = cursor.fetchone()

    if not result:
        print("規程が見つかりません")
        conn.close()
        return

    content_json, raw_text, reg_name = result

    print(f"\n規程名: {reg_name}\n")

    # JSON構造を表示
    print("【構造化されたJSON】")
    print("=" * 80)

    data = json.loads(content_json)

    for chapter in data:
        chapter_num = chapter.get('number', '不明')
        chapter_title = chapter.get('title', '不明')
        articles = chapter.get('articles', [])

        print(f"\n{chapter_num} {chapter_title} ({len(articles)}条)")

        for article in articles:
            article_num = article.get('number', '不明')
            article_title = article.get('title', '不明')
            print(f"  {article_num} ({article_title})")

    # raw_textから実際の章・条の構造を抽出
    print("\n\n【raw_textから抽出した章・条の構造】")
    print("=" * 80)

    import re

    lines = raw_text.split('\n')

    # 章のパターン
    chapter_pattern = re.compile(r'^第([0-9０-９〇一二三四五六七八九十百]+)章')
    # 条のパターン
    article_pattern = re.compile(r'^第([0-9０-９〇一二三四五六七八九十百]+)条[\s　]*[（(](.+?)[）)]')

    current_chapter = None

    for line in lines:
        line = line.strip()

        # 章
        chapter_match = chapter_pattern.match(line)
        if chapter_match:
            current_chapter = line
            print(f"\n{line}")
            continue

        # 条
        article_match = article_pattern.match(line)
        if article_match:
            print(f"  {line[:80]}")

    # 時間外労働に関する条を探す
    print("\n\n【「時間外」「休日労働」を含む行】")
    print("=" * 80)

    for i, line in enumerate(lines):
        if '時間外' in line or '休日労働' in line:
            print(f"行{i+1}: {line.strip()[:100]}")

    conn.close()

if __name__ == "__main__":
    check_json_structure()
