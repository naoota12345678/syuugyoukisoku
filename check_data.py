#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""データベース内の規程データを確認"""

import sys
import os
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import Database

def check_regulation_data():
    print("=" * 80)
    print("規程データの確認")
    print("=" * 80)

    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    # すべての規程を取得
    cursor.execute('''
        SELECT id, name, company_id, created_at
        FROM regulations
        ORDER BY id DESC
    ''')

    regulations = cursor.fetchall()

    if not regulations:
        print("\n規程が登録されていません。")
        conn.close()
        return

    print(f"\n登録されている規程: {len(regulations)}件\n")

    for reg in regulations:
        reg_id, name, company_id, created_at = reg
        print(f"\n{'='*80}")
        print(f"規程ID: {reg_id}")
        print(f"規程名: {name}")
        print(f"作成日: {created_at}")
        print(f"{'='*80}")

        # この規程の最新バージョンを取得
        cursor.execute('''
            SELECT version, content_json, raw_text
            FROM regulation_content
            WHERE regulation_id = ?
            ORDER BY version DESC
            LIMIT 1
        ''', (reg_id,))

        content = cursor.fetchone()

        if not content:
            print("❌ コンテンツが見つかりません")
            continue

        version, content_json, raw_text = content

        print(f"\n最新バージョン: {version}")
        print(f"\n【raw_text】")
        print(f"文字数: {len(raw_text) if raw_text else 0}文字")

        if raw_text:
            # 最初の1000文字を表示
            print(f"\n--- 最初の1000文字 ---")
            print(raw_text[:1000])

            # 「時間外労働」という文字列が含まれているか確認
            if "時間外労働" in raw_text:
                print(f"\n✅ 「時間外労働」という文字列が見つかりました")
                # その周辺のテキストを表示
                idx = raw_text.find("時間外労働")
                start = max(0, idx - 100)
                end = min(len(raw_text), idx + 200)
                print(f"\n--- 「時間外労働」周辺のテキスト ---")
                print(raw_text[start:end])
            else:
                print(f"\n❌ 「時間外労働」という文字列が見つかりません")

            # 表形式のデータがあるか確認（連続した数字や記号のパターン）
            print(f"\n【表・図形式データの確認】")
            lines = raw_text.split('\n')
            table_like_lines = []
            for i, line in enumerate(lines[:200]):  # 最初の200行を確認
                # 数字や記号が多い行（表の可能性）
                if line.strip() and len(line.strip()) > 5:
                    # 数字、記号、スペースの割合を計算
                    non_kanji = sum(1 for c in line if not '\u4e00' <= c <= '\u9fff')
                    if non_kanji / len(line) > 0.5:  # 半分以上が数字・記号
                        table_like_lines.append((i+1, line.strip()[:80]))

            if table_like_lines:
                print(f"表形式らしき行が {len(table_like_lines)} 行見つかりました:")
                for line_num, line_text in table_like_lines[:10]:  # 最初の10行だけ表示
                    print(f"  行{line_num}: {line_text}")
            else:
                print("表形式らしき行は見つかりませんでした")

        print(f"\n\n【content_json】")
        print(f"サイズ: {len(content_json) if content_json else 0}バイト")

        if content_json:
            try:
                data = json.loads(content_json)
                if isinstance(data, list) and len(data) > 0:
                    print(f"章の数: {len(data)}章")

                    # 各章の情報を表示
                    for i, chapter in enumerate(data, 1):
                        chapter_title = chapter.get('title', '不明')
                        articles = chapter.get('articles', [])
                        print(f"  第{i}章: {chapter_title} ({len(articles)}条)")

                        # 時間外労働に関する条を探す
                        for article in articles:
                            article_title = article.get('title', '')
                            if '時間外' in article_title or '休日労働' in article_title:
                                print(f"    ✅ 見つかりました: {article.get('number')} ({article_title})")

                    # 時間外労働に関する条が見つからない場合
                    has_overtime = any(
                        '時間外' in article.get('title', '') or '休日労働' in article.get('title', '')
                        for chapter in data
                        for article in chapter.get('articles', [])
                    )

                    if not has_overtime:
                        print(f"\n  ❌ 構造化データに「時間外労働」に関する条が見つかりません")
                        print(f"     raw_textには存在する可能性があります")
                else:
                    print("⚠️ 空のデータまたは章が0件")
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析エラー: {e}")
        else:
            print("❌ content_jsonが空です")

        print(f"\n")

    conn.close()

if __name__ == "__main__":
    check_regulation_data()
