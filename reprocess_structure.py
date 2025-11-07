#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""既存の規程データを再構造化"""

import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import Database
from claude_validator import ClaudeValidator
import json

def reprocess_regulation():
    print("=" * 80)
    print("既存規程データの再構造化")
    print("=" * 80)

    db = Database()
    validator = ClaudeValidator()

    conn = db.get_connection()
    cursor = conn.cursor()

    # 最新の規程を取得
    cursor.execute('''
        SELECT rc.id, rc.regulation_id, rc.version, rc.raw_text, r.name
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

    content_id, regulation_id, version, raw_text, reg_name = result

    print(f"\n規程名: {reg_name}")
    print(f"規程ID: {regulation_id}")
    print(f"バージョン: {version}")
    print(f"raw_text長: {len(raw_text)}文字")

    if not raw_text:
        print("\nエラー: raw_textが空です")
        conn.close()
        return

    print(f"\n改善されたプロンプトで構造化を開始します...")
    print("※この処理には2-3分かかる場合があります")

    structure_result = validator.structure_regulation_text(raw_text)

    if not structure_result['success']:
        print(f"\n❌ 構造化失敗: {structure_result.get('error')}")
        conn.close()
        return

    structure = structure_result['structure']
    print(f"\n✅ 構造化完了: {len(structure)}章")

    # 各章の情報を表示
    total_articles = 0
    for chapter in structure:
        chapter_num = chapter.get('number', '不明')
        chapter_title = chapter.get('title', '不明')
        articles = chapter.get('articles', [])
        total_articles += len(articles)
        print(f"  {chapter_num} {chapter_title} ({len(articles)}条)")

    print(f"\n合計: {len(structure)}章、{total_articles}条")

    # 時間外労働に関する条を確認
    has_overtime = False
    for chapter in structure:
        for article in chapter.get('articles', []):
            article_title = article.get('title', '')
            if '時間外' in article_title or '休日労働' in article_title:
                print(f"  ✅ 時間外労働の条を発見: {article.get('number')} ({article_title})")
                has_overtime = True

    if not has_overtime:
        print(f"  ⚠️ 警告: 時間外労働に関する条が見つかりません")

    # データベースを更新
    print(f"\nデータベースを更新します...")

    content_json = json.dumps(structure, ensure_ascii=False, indent=2)

    cursor.execute('''
        UPDATE regulation_content
        SET content_json = ?
        WHERE id = ?
    ''', (content_json, content_id))

    conn.commit()
    conn.close()

    print(f"\n✅ 更新完了！")
    print(f"\n再度確認スクリプトを実行して結果を確認してください：")
    print(f"  python check_json_structure.py")

if __name__ == "__main__":
    reprocess_regulation()
