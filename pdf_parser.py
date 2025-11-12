# pdf_parser.py
import pdfplumber
import re
import os
import tempfile
import csv
import json
from typing import Dict, List, Optional
from pdf2image import convert_from_path
from structure_analyzer import StructureAnalyzer
from coordinate_ocr import CoordinateOCR

# Google Cloud Vision APIのインポート（オプション）
try:
    from google.cloud import vision
    VISION_API_AVAILABLE = True
except ImportError:
    VISION_API_AVAILABLE = False
    print("Warning: Google Cloud Vision API not available. OCR will be limited.")

class PDFParser:
    """PDFから就業規則を抽出するクラス（高精度OCR対応）"""

    def __init__(self, use_ocr=True, debug=False, use_ai_fix=True):
        # 章のパターン（タイトルが同じ行または次の行にある場合に対応）
        self.chapter_pattern = re.compile(r'^第[〇一二三四五六七八九十百0-9]+章')
        self.chapter_with_title_pattern = re.compile(r'^第[〇一二三四五六七八九十百0-9]+章\s+(.+)')
        # 条のパターン
        self.article_pattern = re.compile(r'^第([〇一二三四五六七八九十百0-9]+)条\s*[（(](.+?)[）)]')
        # 項のパターン
        self.item_pattern = re.compile(r'^([0-9①-⑳]+)[.．、\s]')
        self.sub_item_pattern = re.compile(r'^[（(]([0-9]+)[）)]')
        # ページマーカーのパターン
        self.page_marker_pattern = re.compile(r'^###\s*ページ\s+\d+\s*###')
        self.use_ocr = use_ocr and VISION_API_AVAILABLE
        self.debug = debug  # デバッグモードフラグ
        self.use_ai_fix = use_ai_fix  # AI項番号修正を使用するか

        # 構造解析器を初期化
        self.structure_analyzer = StructureAnalyzer()

        # 座標ベースOCRを初期化（デバッグフラグを渡す）
        self.coordinate_ocr = CoordinateOCR(debug=self.debug)

        # AI項番号修正器を初期化（use_ai_fix=Trueの場合のみ）
        self.ai_fixer = None
        if self.use_ai_fix:
            try:
                from ai_item_fixer import AIItemNumberFixer
                self.ai_fixer = AIItemNumberFixer()
                if self.debug:
                    print("AI項番号修正を有効化しました")
            except Exception as e:
                print(f"AI項番号修正の初期化に失敗: {e}")
                self.use_ai_fix = False

        # Google Cloud Vision API認証設定
        # GOOGLE_APPLICATION_CREDENTIALSがJSON文字列の場合、
        # Vision APIはデフォルト認証を使用するため、特別な処理は不要
        if self.use_ocr:
            cred_data = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if cred_data:
                # JSON文字列かファイルパスかを判定
                if cred_data.strip().startswith('{'):
                    # JSON文字列の場合: 一時ファイルとして保存
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        f.write(cred_data)
                        temp_cred_path = f.name
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_cred_path
                    print(f"Vision API credentials set from JSON string (temp file: {temp_cred_path})")
                elif not os.path.isabs(cred_data):
                    # 相対パスの場合、絶対パスに変換
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    abs_path = os.path.join(base_dir, cred_data)
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_path
                    print(f"Vision API credentials set: {abs_path}")
    
    def _detect_table_structure(self, blocks: List[Dict], debug=False) -> Optional[List[List[str]]]:
        """
        ブロックの配置から表構造を検出する（改善版）
        """
        if not blocks:
            return None

        # Y座標でグループ化（行を検出）
        rows = {}
        row_threshold = 20  # 同じ行とみなすY座標の差の閾値

        for block in blocks:
            y = block['y']
            found_row = False

            for row_y in list(rows.keys()):
                if abs(y - row_y) < row_threshold:
                    rows[row_y].append(block)
                    found_row = True
                    break

            if not found_row:
                rows[y] = [block]

        # 行をソート
        sorted_rows = sorted(rows.items(), key=lambda x: x[0])

        # 各行でX座標でソート（列の順序を保持）
        table_data = []
        for row_y, row_blocks in sorted_rows:
            row_blocks.sort(key=lambda b: b['x'])
            table_data.append([block['text'].strip() for block in row_blocks])

        # 表らしいかチェック（改善版：より柔軟な基準）
        if len(table_data) >= 2:  # 最低2行以上（ヘッダー+データ）
            col_counts = [len(row) for row in table_data]

            if debug:
                print(f"    表候補を検出: {len(table_data)}行, 列数分布: {col_counts}")

            # 条件1: 少なくとも2列以上
            avg_cols = sum(col_counts) / len(col_counts)
            if avg_cols < 2:
                if debug:
                    print(f"    → 除外: 平均列数が2未満 ({avg_cols:.1f})")
                return None

            # 条件2: 最頻値の列数を求める
            from collections import Counter
            col_count_freq = Counter(col_counts)
            most_common_cols = col_count_freq.most_common(1)[0][0]

            if debug:
                print(f"    最頻列数: {most_common_cols}列 (出現: {col_count_freq[most_common_cols]}行)")

            # 条件3: 最頻値±2以内の列数の行が全体の50%以上あれば表とみなす
            # （ヘッダー行や小計行で列数が異なることを許容）
            similar_col_rows = sum(1 for count in col_counts if abs(count - most_common_cols) <= 2)
            ratio = similar_col_rows / len(col_counts)

            if debug:
                print(f"    類似列数の行: {similar_col_rows}/{len(col_counts)} ({ratio:.1%})")

            if ratio >= 0.5:  # 50%以上の行が類似した列数
                if debug:
                    print(f"    → 表として認識!")
                return table_data
            else:
                if debug:
                    print(f"    → 除外: 列数の一貫性が低い ({ratio:.1%})")

        return None

    def _extract_text_with_tables(self, response):
        """
        Vision APIのレスポンスから、表構造を考慮してテキストを抽出する
        """
        if not response.full_text_annotation:
            return "", []

        all_text = []
        detected_tables = []

        for page_num, page in enumerate(response.full_text_annotation.pages):
            blocks = []

            for block in page.blocks:
                vertices = block.bounding_box.vertices
                if vertices:
                    top_left_y = vertices[0].y if vertices[0].y else 0
                    top_left_x = vertices[0].x if vertices[0].x else 0

                    # ブロック内のテキストを結合
                    block_text = ""
                    for paragraph in block.paragraphs:
                        para_text = ""
                        for word in paragraph.words:
                            word_text = ""
                            for symbol in word.symbols:
                                word_text += symbol.text
                                if hasattr(symbol.property, 'detected_break'):
                                    break_type = symbol.property.detected_break.type_
                                    if break_type in [1, 3]:  # SPACE or LINE_BREAK
                                        word_text += " "
                                    elif break_type == 5:  # EOL_SURE_SPACE
                                        word_text += "\n"
                            para_text += word_text
                        block_text += para_text

                    blocks.append({
                        'text': block_text,
                        'y': top_left_y,
                        'x': top_left_x,
                        'width': vertices[2].x - vertices[0].x if vertices[2].x and vertices[0].x else 0,
                        'height': vertices[2].y - vertices[0].y if vertices[2].y and vertices[0].y else 0
                    })

            # 表構造を検出
            if self.debug and blocks:
                print(f"  ページ {page_num + 1}: {len(blocks)}個のブロックを分析中...")
            table_data = self._detect_table_structure(blocks, debug=self.debug)

            if table_data:
                # 表として記録
                detected_tables.append({
                    'page': page_num + 1,
                    'data': table_data
                })

                # 表をテキストに含める
                table_text = "\n[表データ検出]\n"
                table_text += "-" * 50 + "\n"
                for row in table_data:
                    table_text += " | ".join(row) + "\n"
                table_text += "-" * 50 + "\n"
                all_text.append(table_text)
            else:
                # 通常のテキストとして処理
                blocks.sort(key=lambda b: (b['y'], b['x']))

                # 行ごとにグループ化
                lines = []
                if blocks:
                    current_line = [blocks[0]]
                    current_y = blocks[0]['y']

                    for block in blocks[1:]:
                        if abs(block['y'] - current_y) < 30:
                            current_line.append(block)
                        else:
                            current_line.sort(key=lambda b: b['x'])
                            lines.append(' '.join([b['text'] for b in current_line]))
                            current_line = [block]
                            current_y = block['y']

                    current_line.sort(key=lambda b: b['x'])
                    lines.append(' '.join([b['text'] for b in current_line]))

                if lines:
                    all_text.append('\n'.join(lines))

        return '\n'.join(all_text), detected_tables

    def extract_from_pdf(self, pdf_path: str) -> Dict:
        """PDFファイルから就業規則を抽出（高精度OCR対応・表検出対応）"""
        try:
            # 常にVision APIを使用（最高精度）
            if self.use_ocr:
                print("Google Cloud Vision APIで高精度OCR処理を開始します...")
                full_text, detected_tables = self._extract_with_vision_api(pdf_path)
                print(f"Vision APIで{len(full_text)}文字抽出しました")
                if detected_tables:
                    print(f"  {len(detected_tables)}個の表を検出しました")
            else:
                # Vision API利用不可の場合のみpdfplumberを使用
                print("pdfplumberでテキスト抽出します...")
                full_text = self._extract_with_pdfplumber(pdf_path)
                detected_tables = []
                print(f"pdfplumberで{len(full_text)}文字抽出しました")

            # メタ情報抽出
            company_info = self._extract_company_info(full_text)

            # 構造解析を実行（元のテキストは変更しない）
            print("構造解析を実行中...")
            structure_result = self.structure_analyzer.analyze(full_text)
            print(f"  章: {structure_result['metadata']['total_chapters']}個")
            print(f"  条: {structure_result['metadata']['total_articles']}個")
            print(f"  項: {structure_result['metadata']['total_items']}個")

            # テキスト、表、構造情報を返す
            return {
                "success": True,
                "company_info": company_info,
                "raw_text": full_text,  # 完全テキスト（変更なし）
                "structure": structure_result["structure"],  # 構造情報（追加のみ）
                "tables": detected_tables
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """pdfplumberでテキストを抽出"""
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            return full_text

    def _extract_with_vision_api(self, pdf_path: str):
        """Google Cloud Vision APIでOCR処理（完全テキスト抽出・表検出対応）"""
        if not VISION_API_AVAILABLE:
            return "Vision API is not available", []

        client = vision.ImageAnnotatorClient()
        all_text = []
        all_tables = []

        try:
            # PDFを画像に変換（高解像度で完全抽出）
            images = convert_from_path(pdf_path, dpi=300)
            print(f"{len(images)}ページをOCR処理中...")

            for i, image in enumerate(images, 1):
                print(f"  ページ {i}/{len(images)} 処理中...", end=" ")

                # 一時ファイルに保存
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    temp_path = temp_file.name

                try:
                    image.save(temp_path, 'PNG', quality=95)  # 高品質で保存

                    # Vision APIでOCR（最高精度設定）
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

                    # 座標ベースの完全テキスト抽出（正確な読み取り順序）
                    ocr_result = self.coordinate_ocr.process_response(response, debug=self.debug)
                    page_text = ocr_result['raw_text']

                    if self.debug:
                        print(f"    OCR統計: {ocr_result['stats']}")

                    # 表構造を検出（別途）
                    page_tables = []
                    if response.full_text_annotation:
                        blocks = []
                        for page in response.full_text_annotation.pages:
                            for block in page.blocks:
                                vertices = block.bounding_box.vertices
                                if vertices:
                                    top_left_y = vertices[0].y if vertices[0].y else 0
                                    top_left_x = vertices[0].x if vertices[0].x else 0

                                    # ブロック内のテキストを結合
                                    block_text = ""
                                    for paragraph in block.paragraphs:
                                        para_text = ""
                                        for word in paragraph.words:
                                            word_text = ''.join([symbol.text for symbol in word.symbols])
                                            para_text += word_text + " "
                                        block_text += para_text.strip() + "\n"

                                    blocks.append({
                                        'text': block_text,
                                        'y': top_left_y,
                                        'x': top_left_x,
                                        'width': vertices[2].x - vertices[0].x if vertices[2].x and vertices[0].x else 0,
                                        'height': vertices[2].y - vertices[0].y if vertices[2].y and vertices[0].y else 0
                                    })

                        # 表構造を検出
                        table_data = self._detect_table_structure(blocks, debug=self.debug)
                        if table_data:
                            page_tables.append({
                                'page': i,
                                'data': table_data
                            })

                    if page_text:
                        all_text.append(f"### ページ {i} ###\n{page_text}\n")
                        print(f"OK ({len(page_text)}文字", end="")

                        # 表情報を保存
                        all_tables.extend(page_tables)

                        if page_tables:
                            print(f", 表{len(page_tables)}個", end="")
                        print(")")
                    else:
                        print("テキストなし")

                finally:
                    # 一時ファイル削除
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass

            # 全ページのテキストを結合
            full_text = "\n".join(all_text)

            # AI項番号修正を適用（有効な場合のみ）
            if self.use_ai_fix and self.ai_fixer:
                try:
                    print("\nAIで項番号を修正中...")
                    full_text = self.ai_fixer.fix_item_numbers(full_text)
                    print("AI修正完了")
                except Exception as e:
                    print(f"AI修正エラー（元のテキストを使用）: {e}")

            return full_text, all_tables

        except Exception as e:
            print(f"Vision API error: {str(e)}")
            import traceback
            traceback.print_exc()
            return "", []
    
    def _extract_company_info(self, text: str) -> Dict:
        """会社情報を抽出"""
        info = {
            "company_name": None,
            "address": None,
            "effective_date": None
        }
        
        # 会社名抽出（よくあるパターン）
        company_patterns = [
            r'([^\s]+(?:株式会社|有限会社|合同会社|一般社団法人|NPO法人))',
            r'(株式会社[^\s]+|有限会社[^\s]+|合同会社[^\s]+)',
        ]
        for pattern in company_patterns:
            match = re.search(pattern, text[:500])  # 最初の部分から
            if match:
                info["company_name"] = match.group(1)
                break
        
        # 施行日抽出
        date_pattern = r'(令和|平成)(\d+)年(\d+)月(\d+)日'
        match = re.search(date_pattern, text[:500])
        if match:
            info["effective_date"] = match.group(0)
        
        return info
    
    def _parse_structure(self, text: str) -> List[Dict]:
        """テキストを構造化"""
        lines = text.split('\n')
        chapters = []
        current_chapter = None
        current_article = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 章の検出
            chapter_match = self.chapter_pattern.match(line)
            if chapter_match:
                if current_chapter:
                    chapters.append(current_chapter)
                current_chapter = {
                    "type": "chapter",
                    "number": line.split()[0],
                    "title": chapter_match.group(1),
                    "articles": []
                }
                current_article = None
                continue
            
            # 条の検出
            article_match = self.article_pattern.match(line)
            if article_match:
                if current_article and current_chapter:
                    current_chapter["articles"].append(current_article)
                
                current_article = {
                    "type": "article",
                    "number": f"第{article_match.group(1)}条",
                    "title": article_match.group(2),
                    "content": [],
                    "items": []
                }
                continue
            
            # 項の検出
            item_match = self.item_pattern.match(line)
            if item_match and current_article:
                current_article["items"].append({
                    "number": item_match.group(1),
                    "text": line
                })
                continue
            
            # その他の本文
            if current_article:
                current_article["content"].append(line)
        
        # 最後の章と条を追加
        if current_article and current_chapter:
            current_chapter["articles"].append(current_article)
        if current_chapter:
            chapters.append(current_chapter)
        
        return chapters
    
    def extract_text_only(self, pdf_path: str) -> str:
        """PDFからテキストのみを抽出"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                return full_text
        except Exception as e:
            return f"Error: {str(e)}"
