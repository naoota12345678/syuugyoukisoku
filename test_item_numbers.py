"""
項番号の抽出・並べ替えをデバッグするテストスクリプト

実際のPDFファイルを使って、項番号がどの処理段階でどこに移動しているか確認します。
"""

import os
import sys
from coordinate_ocr import CoordinateOCR
from google.cloud import vision
from pdf2image import convert_from_path
import tempfile

def test_pdf_item_numbers(pdf_path: str):
    """PDFファイルの項番号抽出をデバッグ"""

    print("=" * 80)
    print("項番号抽出デバッグテスト")
    print("=" * 80)
    print(f"PDFファイル: {pdf_path}")
    print()

    # Vision APIクライアント
    client = vision.ImageAnnotatorClient()

    # 座標ベースOCR
    ocr = CoordinateOCR()

    # PDFを画像に変換
    print("PDFを画像に変換中...")
    images = convert_from_path(pdf_path, dpi=300)
    print(f"  {len(images)}ページを検出")
    print()

    # 各ページを処理
    for page_num, image in enumerate(images, 1):
        print(f"\n{'='*80}")
        print(f"ページ {page_num}/{len(images)} を処理中")
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

            # デバッグモードで処理
            print(f"\nOCR処理を開始（デバッグモード）")
            ocr_result = ocr.process_response(response, debug=True)

            print(f"\n{'='*80}")
            print("処理結果サマリー")
            print(f"{'='*80}")
            print(f"統計情報:")
            for key, value in ocr_result['stats'].items():
                print(f"  {key}: {value}")

            # 抽出されたテキストの先頭を表示
            raw_text = ocr_result['raw_text']
            print(f"\n抽出されたテキスト（先頭500文字）:")
            print("-" * 80)
            print(raw_text[:500])
            print("-" * 80)

            # 最初の3ページのみテスト（全ページは長すぎる）
            if page_num >= 3:
                print("\n最初の3ページのみテスト完了")
                break

        finally:
            # 一時ファイル削除
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == "__main__":
    # テスト対象のPDFファイル
    pdf_path = r"\\192.168.3.63\Qnap\★顧客\た\1068_ダイトク\①会社資料\②就業規則\2_本則\20240921_本則.pdf"

    if not os.path.exists(pdf_path):
        print(f"エラー: PDFファイルが見つかりません: {pdf_path}")
        sys.exit(1)

    test_pdf_item_numbers(pdf_path)
