#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""表検出のテストスクリプト"""

import sys
import os
import glob
from pdf_parser import PDFParser

def test_table_detection(pdf_path, debug=True):
    """PDFから表を検出してテスト"""
    print("=" * 80)
    print("表検出テスト")
    print("=" * 80)
    print(f"PDFファイル: {pdf_path}")
    print(f"デバッグモード: {debug}")
    print("=" * 80)

    # PDFParserを作成（デバッグモード有効）
    parser = PDFParser(use_ocr=True, debug=debug)

    # PDFを解析
    result = parser.extract_from_pdf(pdf_path)

    if not result['success']:
        print(f"\nエラー: {result.get('error', 'Unknown error')}")
        return

    # 結果を表示
    print("\n" + "=" * 80)
    print("検出結果")
    print("=" * 80)

    # 会社情報
    company_info = result.get('company_info', {})
    if company_info.get('company_name'):
        print(f"会社名: {company_info['company_name']}")
    if company_info.get('effective_date'):
        print(f"施行日: {company_info['effective_date']}")

    # 表の検出結果
    tables = result.get('tables', [])
    print(f"\n検出された表の数: {len(tables)}個")

    if tables:
        for i, table in enumerate(tables, 1):
            print(f"\n--- 表 {i} (ページ {table['page']}) ---")
            data = table['data']
            print(f"行数: {len(data)}行")
            if data:
                col_counts = [len(row) for row in data]
                print(f"列数: {min(col_counts)}〜{max(col_counts)}列")

                # 最初の数行を表示
                print("\n[プレビュー]")
                for j, row in enumerate(data[:5], 1):
                    print(f"  行{j}: {' | '.join(row[:6])}")  # 最初の6列まで
                if len(data) > 5:
                    print(f"  ... (他 {len(data) - 5}行)")
    else:
        print("\n⚠ 表が検出されませんでした")
        print("   デバッグモードのログを確認してください")

    # テキスト長
    raw_text = result.get('raw_text', '')
    print(f"\n抽出テキスト: {len(raw_text)}文字")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    # アップロードされたPDFを探す
    upload_dir = "uploads"

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # 最新のPDFを探す
        pdfs = glob.glob(f"{upload_dir}/**/*.pdf", recursive=True)
        if pdfs:
            pdf_path = sorted(pdfs, key=os.path.getmtime)[-1]
            print(f"最新のPDFを使用: {pdf_path}\n")
        else:
            print("PDFが見つかりません")
            print("使用方法: python test_table_detection.py <PDFファイルパス>")
            sys.exit(1)

    # テスト実行
    test_table_detection(pdf_path, debug=True)
