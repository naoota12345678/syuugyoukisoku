"""
完全テキスト抽出OCRシステム
- すべてのテキストを余すところなく抽出
- 絶対に漏れや抜けや要約があってはならない
- 生データとしてそのまま出力
"""

from google.cloud import vision
import io
import os
from pdf2image import convert_from_path
import tempfile
from datetime import datetime
import shutil
import time

# 設定
INPUT_DIR = r"C:\Users\naoot\Desktop\syuugyoukisoku\input"
OUTPUT_DIR = r"C:\Users\naoot\Desktop\syuugyoukisoku\output"
CREDENTIALS_PATH = r"C:\Users\naoot\Desktop\syuugyoukisoku\syuugyoukisoku-e41737e9bf51.json"

def setup_credentials():
    """認証ファイルのセットアップを行う"""
    try:
        if os.path.exists(CREDENTIALS_PATH):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
            print(f"認証ファイルを設定しました: {CREDENTIALS_PATH}")
            return True
        else:
            print(f"Error: Credentials file not found: {CREDENTIALS_PATH}")
            return False
    except Exception as e:
        print(f"Error setting up credentials: {str(e)}")
        return False

def extract_all_text_comprehensive(response):
    """Vision APIレスポンスからすべてのテキストを包括的に抽出"""
    all_texts = []

    # メイン全体テキスト
    if response.text_annotations:
        main_text = response.text_annotations[0].description
        if main_text and main_text.strip():
            all_texts.append(("MAIN_TEXT", main_text))

    # 詳細ブロック単位のテキスト
    if response.full_text_annotation:
        for page in response.full_text_annotation.pages:
            for block_idx, block in enumerate(page.blocks):
                block_text = ""
                for paragraph in block.paragraphs:
                    para_text = ""
                    for word in paragraph.words:
                        word_text = ''.join([symbol.text for symbol in word.symbols])
                        para_text += word_text + " "
                    block_text += para_text.strip() + "\n"

                if block_text.strip():
                    all_texts.append((f"BLOCK_{block_idx}", block_text.strip()))

    # 重複を除去して結合
    unique_texts = []
    seen_texts = set()

    for text_type, text_content in all_texts:
        if text_content not in seen_texts:
            unique_texts.append((text_type, text_content))
            seen_texts.add(text_content)

    return unique_texts

def process_pdf_complete(pdf_path):
    """PDFを処理して完全なテキストファイルに出力"""

    base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 出力ファイルパス
    output_path = os.path.join(OUTPUT_DIR, f"{base_filename}_{timestamp}_完全テキスト.txt")

    # Vision APIクライアントを初期化
    client = vision.ImageAnnotatorClient()

    try:
        print(f"\n処理中: {os.path.basename(pdf_path)}")
        print(f"出力ファイル: {os.path.basename(output_path)}")

        # PDFを画像に変換
        print("PDFを画像に変換中...")
        images = convert_from_path(
            pdf_path,
            dpi=300,  # 高解像度で処理
            thread_count=1,
        )

        print(f"{len(images)} ページを変換しました")

        # 結果を保存するための変数
        all_content = []

        # メタデータ
        doc_title = os.path.splitext(os.path.basename(pdf_path))[0]
        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        all_content.extend([
            f"# {doc_title} - 完全テキスト抽出版",
            f"",
            f"処理日時: {timestamp_str}",
            f"総ページ数: {len(images)}",
            f"抽出方式: すべてのテキストを余すところなく抽出（絶対に漏れや抜けや要約なし）",
            f"",
            f"{'=' * 80}",
            f"",
        ])

        # 各ページを処理
        total_chars = 0
        for i, image in enumerate(images, 1):
            print(f"ページ {i}/{len(images)} を処理中...", end=" ")

            temp_file_path = None
            try:
                # 一時ファイルに保存
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    temp_file_path = temp_file.name

                image.save(temp_file_path, 'PNG', quality=95)  # 高品質で保存

                # Vision APIでOCR（最高精度設定）
                with open(temp_file_path, 'rb') as image_file:
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
                    print(f"エラー: {response.error.message}")
                    continue

                # すべてのテキストを包括的に抽出
                all_extracted_texts = extract_all_text_comprehensive(response)

                if all_extracted_texts:
                    # ページヘッダーを追加
                    all_content.extend([
                        f"### ページ {i} ###",
                        f"",
                    ])

                    # メインテキストのみを出力（重複を避けるため）
                    # MAIN_TEXTが最も完全なテキストを含んでいる
                    for text_type, text_content in all_extracted_texts:
                        if text_type == "MAIN_TEXT":
                            all_content.append(text_content)
                            total_chars += len(text_content)
                            break

                    # 区切り線を追加
                    all_content.extend([
                        f"",
                        f"",
                    ])

                    print(f"完了 ({len(text_content)} 文字)")
                else:
                    print("テキストが抽出されませんでした")

            finally:
                # 一時ファイルを削除
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except:
                        pass

        # ファイルを保存
        print(f"\nファイルを保存中...")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_content))

        print(f"\n処理完了: {os.path.basename(pdf_path)}")
        print(f"  出力ファイル: {os.path.basename(output_path)}")
        print(f"  総文字数: {total_chars:,} 文字")

        return True

    except Exception as e:
        print(f"\nエラーが発生しました: {os.path.basename(pdf_path)}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def process_all_pdfs():
    """inputフォルダ内の全PDFファイルを処理する"""

    if not setup_credentials():
        return

    if not os.path.exists(INPUT_DIR):
        print(f"Inputフォルダを作成します: {INPUT_DIR}")
        os.makedirs(INPUT_DIR)
        print(f"\nPDFファイルを {INPUT_DIR} に配置してから再度実行してください。")
        return

    if not os.path.exists(OUTPUT_DIR):
        print(f"Outputフォルダを作成します: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR)

    # PDFファイルを検索
    import glob
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))

    if not pdf_files:
        print(f"\nPDFファイルが見つかりません: {INPUT_DIR}")
        print(f"PDFファイルをこのフォルダに配置してから再度実行してください。")
        return

    print(f"\n{len(pdf_files)} 個のPDFファイルが見つかりました")
    print("=" * 80)

    successful = 0
    failed = 0

    for pdf_file in pdf_files:
        if process_pdf_complete(pdf_file):
            successful += 1
        else:
            failed += 1

    print("\n" + "=" * 80)
    print("処理結果:")
    print(f"処理ファイル数: {len(pdf_files)}")
    print(f"成功: {successful}")
    print(f"失敗: {failed}")
    print(f"\n出力ファイルの場所: {OUTPUT_DIR}")

if __name__ == "__main__":
    print("=" * 80)
    print("完全テキスト抽出OCRシステム")
    print("絶対に漏れや抜けや要約があってはならない完全抽出")
    print("=" * 80)
    print(f"Inputフォルダ: {INPUT_DIR}")
    print(f"Outputフォルダ: {OUTPUT_DIR}")
    print()

    start_time = time.time()
    process_all_pdfs()
    total_time = time.time() - start_time

    print(f"\n総処理時間: {total_time:.1f} 秒")
