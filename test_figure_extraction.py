#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Vision APIで図・表の検出テスト"""

import sys
import os
import io
from google.cloud import vision
from pdf2image import convert_from_path
import tempfile
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# .envファイルから環境変数を読み込み
load_dotenv()

def test_figure_detection(pdf_path):
    """PDFから図・表を検出"""

    print("=" * 80)
    print("図・表の検出テスト")
    print("=" * 80)

    # Google Cloud認証設定
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and not os.path.isabs(cred_path):
        # 相対パスの場合、絶対パスに変換
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.join(base_dir, cred_path)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_path
        print(f"Vision API credentials: {abs_path}\n")

    client = vision.ImageAnnotatorClient()

    # PDFを画像に変換
    print(f"\nPDFを画像に変換中: {pdf_path}")
    images = convert_from_path(pdf_path, dpi=200)
    print(f"総ページ数: {len(images)}")

    for page_num, image in enumerate(images, 1):
        print(f"\n{'='*80}")
        print(f"ページ {page_num} を分析中...")
        print(f"{'='*80}")

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            temp_path = temp_file.name
            image.save(temp_path, 'PNG')

        try:
            # Vision APIで分析
            with open(temp_path, 'rb') as image_file:
                content = image_file.read()

            vision_image = vision.Image(content=content)

            # ロゴ検出（図や表も検出される）
            response = client.logo_detection(image=vision_image)
            logos = response.logo_annotations

            if logos:
                print(f"  ロゴ/図形検出: {len(logos)}個")
                for i, logo in enumerate(logos, 1):
                    print(f"    図{i}: 信頼度 {logo.score:.2%}")

            # オブジェクトローカライゼーション（物体検出）
            response = client.object_localization(image=vision_image)
            objects = response.localized_object_annotations

            if objects:
                print(f"  オブジェクト検出: {len(objects)}個")
                for obj in objects:
                    print(f"    {obj.name}: 信頼度 {obj.score:.2%}")
                    vertices = obj.bounding_poly.normalized_vertices
                    print(f"      位置: ({vertices[0].x:.2f}, {vertices[0].y:.2f}) - ({vertices[2].x:.2f}, {vertices[2].y:.2f})")

            # テキスト検出で表を推測
            response = client.document_text_detection(image=vision_image)

            if response.full_text_annotation:
                text = response.full_text_annotation.text
                lines = text.split('\n')

                # 表らしき行を検出（数字や記号が多い行）
                table_lines = []
                for line in lines:
                    if line.strip():
                        # 数字、記号、スペースの割合
                        non_kanji = sum(1 for c in line if not '\u4e00' <= c <= '\u9fff')
                        if len(line) > 5 and non_kanji / len(line) > 0.5:
                            table_lines.append(line)

                if table_lines:
                    print(f"  表形式らしき行: {len(table_lines)}行")
                    for i, line in enumerate(table_lines[:3], 1):
                        print(f"    {i}: {line[:60]}...")

        finally:
            # 一時ファイル削除
            if os.path.exists(temp_path):
                os.remove(temp_path)

    print(f"\n{'='*80}")
    print("分析完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    # アップロードされたPDFを探す
    upload_dir = "uploads"

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # 最新のPDFを探す
        import glob
        pdfs = glob.glob(f"{upload_dir}/**/*.pdf", recursive=True)
        if pdfs:
            pdf_path = sorted(pdfs, key=os.path.getmtime)[-1]
            print(f"最新のPDFを使用: {pdf_path}")
        else:
            print("PDFが見つかりません")
            print("使用方法: python test_figure_extraction.py <PDFファイルパス>")
            sys.exit(1)

    test_figure_detection(pdf_path)
