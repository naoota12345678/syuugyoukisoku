#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""構造化処理のテスト"""

import sys
import os
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# パスを設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from claude_validator import ClaudeValidator

def test_structure():
    print("=" * 60)
    print("構造化処理テスト")
    print("=" * 60)

    # Validatorの初期化
    print("\n1. ClaudeValidatorを初期化...")
    try:
        validator = ClaudeValidator()
        print("   [OK] 初期化成功")
    except Exception as e:
        print(f"   [NG] 初期化失敗: {e}")
        return

    # temp_raw_text.txtから読み込み
    print("\n2. raw_textを読み込み...")
    raw_text_path = os.path.join(BASE_DIR, "temp_raw_text.txt")
    try:
        with open(raw_text_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        print(f"   [OK] {len(raw_text)}文字読み込み成功")
    except Exception as e:
        print(f"   [NG] 読み込み失敗: {e}")
        return

    # テスト用に最初の5000文字のみ使用
    test_text = raw_text[:5000]
    print(f"\n3. テスト用に{len(test_text)}文字を使用")

    # 構造化を実行
    print("\n4. 構造化処理を実行...")
    try:
        result = validator.structure_regulation_text(test_text)

        if result['success']:
            print(f"   [OK] 構造化成功")
            structure = result.get('structure', [])
            print(f"   章の数: {len(structure)}")

            if structure:
                print(f"\n   最初の章:")
                first_chapter = structure[0]
                print(f"   - 番号: {first_chapter.get('number', 'N/A')}")
                print(f"   - タイトル: {first_chapter.get('title', 'N/A')}")
                print(f"   - 条の数: {len(first_chapter.get('articles', []))}")
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

if __name__ == "__main__":
    test_structure()
