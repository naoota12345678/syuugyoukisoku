"""
「23」問題のデバッグスクリプト
実際のPDFで「23」がどこに出現するか詳細に調査
"""

from coordinate_ocr import CoordinateOCR
from google.cloud import vision
from pdf2image import convert_from_path
import tempfile
import os
import re

def debug_23_in_pdf(pdf_path: str):
    """PDFから「23」を含むブロックを詳細に調査"""

    print("=" * 80)
    print("「23」問題デバッグ")
    print("=" * 80)
    print(f"PDFファイル: {pdf_path}")
    print()

    # Vision APIクライアント
    client = vision.ImageAnnotatorClient()

    # 座標ベースOCR（デバッグモード）
    ocr = CoordinateOCR(debug=True)

    # PDFを画像に変換
    print("PDFを画像に変換中...")
    images = convert_from_path(pdf_path, dpi=300)
    print(f"  {len(images)}ページを検出")
    print()

    # 対象ページのみ処理（第22条、第23条がありそうなページ）
    # 通常は10-15ページあたり
    target_pages = range(min(5, len(images)), min(15, len(images)))

    for page_num in target_pages:
        image = images[page_num]
        print(f"\n{'='*80}")
        print(f"ページ {page_num + 1} を処理中")
        print(f"{'='*80}")

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            temp_path = temp_file.name

        try:
            # 画像を保存
            image.save(temp_path, 'PNG', quality=95)

            # Vision APIでOCR
            with open(temp_path, 'rb') as image_file:
                content = image_file.read()

            vision_image = vision.Image(content=content)
            response = client.document_text_detection(
                image=vision_image,
                image_context={
                    "language_hints": ["ja"],
                    "text_detection_params": {
                        "enable_text_detection_confidence_score": True
                    }
                }
            )

            if response.error.message:
                print(f"Error: {response.error.message}")
                continue

            # 全ブロックを抽出
            all_blocks = ocr.extract_all_blocks(response)
            print(f"\n抽出されたブロック数: {len(all_blocks)}")

            # 「23」を含むブロックを探す
            blocks_with_23 = []
            for i, block in enumerate(all_blocks):
                text = block['text'].strip()
                if '23' in text or text == '23':
                    blocks_with_23.append((i, block))

            if blocks_with_23:
                print(f"\n「23」を含むブロック: {len(blocks_with_23)}個")
                print(f"\n{'順序':<6} {'座標(x,y)':<20} {'サイズ(w×h)':<15} {'テキスト':<50}")
                print("-" * 100)

                for i, block in blocks_with_23:
                    x = block['x_center']
                    y = block['y_center']
                    w = block['width']
                    h = block['height']
                    text_preview = block['text'].strip()[:50]
                    print(f"{i:<6} ({x:.0f}, {y:.0f}){'':<8} {w:.0f}×{h:.0f}{'':<8} '{text_preview}'")

                    # 前後のブロックも表示
                    if i > 0:
                        prev = all_blocks[i-1]
                        print(f"  前: '{prev['text'].strip()[:40]}'")
                    if i < len(all_blocks) - 1:
                        next_block = all_blocks[i+1]
                        print(f"  後: '{next_block['text'].strip()[:40]}'")
                    print()

            # 第22条、第23条を含むブロックも探す
            article_blocks = []
            for i, block in enumerate(all_blocks):
                text = block['text'].strip()
                if re.match(r'第(22|23)条', text):
                    article_blocks.append((i, block))

            if article_blocks:
                print(f"\n第22条/第23条を含むブロック: {len(article_blocks)}個")
                for i, block in article_blocks:
                    print(f"  {block['text'].strip()[:100]}")

        finally:
            # 一時ファイル削除
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass


if __name__ == "__main__":
    # テスト対象のPDFファイル（ユーザーが指定）
    import sys

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # デフォルトパス（適宜変更）
        pdf_path = input("PDFファイルのパスを入力してください: ").strip('"')

    if not os.path.exists(pdf_path):
        print(f"エラー: PDFファイルが見つかりません: {pdf_path}")
        sys.exit(1)

    debug_23_in_pdf(pdf_path)
