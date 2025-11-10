"""
座標ベースの完全OCRシステム
1. すべてのテキストを座標付きで取得
2. 座標順に並べ替え
3. ノイズ除去（慎重に）
4. 完全テキストとして結合
"""

from typing import List, Dict, Tuple
import re


class CoordinateOCR:
    """座標情報を使った正確なテキスト抽出"""

    def __init__(self):
        # ノイズパターン（孤立した数字など）
        self.noise_patterns = [
            re.compile(r'^\d{1,2}$'),  # 1桁または2桁の数字のみ（ページ番号など）
            re.compile(r'^[ⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ]+$'),  # ローマ数字のみ
        ]

    def extract_all_blocks(self, response) -> List[Dict]:
        """
        Vision APIレスポンスからすべてのブロックを座標付きで抽出

        Args:
            response: Vision APIのレスポンス

        Returns:
            ブロックのリスト（テキスト、座標、サイズ付き）
        """
        blocks = []

        if not response.full_text_annotation:
            return blocks

        for page_num, page in enumerate(response.full_text_annotation.pages):
            for block_idx, block in enumerate(page.blocks):
                # ブロックの境界ボックス
                vertices = block.bounding_box.vertices
                if not vertices or len(vertices) < 4:
                    continue

                # 座標を取得
                x_min = min(v.x for v in vertices if v.x)
                y_min = min(v.y for v in vertices if v.y)
                x_max = max(v.x for v in vertices if v.x)
                y_max = max(v.y for v in vertices if v.y)

                # ブロック内のテキストを結合
                block_text = ""
                for paragraph in block.paragraphs:
                    para_text = ""
                    for word in paragraph.words:
                        word_text = ''.join([symbol.text for symbol in word.symbols])

                        # 単語の後の区切り（スペースや改行）を判定
                        if word.symbols:
                            last_symbol = word.symbols[-1]
                            if hasattr(last_symbol, 'property') and hasattr(last_symbol.property, 'detected_break'):
                                break_type = last_symbol.property.detected_break.type_
                                if break_type == 1 or break_type == 3:  # SPACE or LINE_BREAK
                                    word_text += " "
                                elif break_type == 5:  # EOL_SURE_SPACE
                                    word_text += "\n"

                        para_text += word_text

                    if para_text.strip():
                        block_text += para_text

                if block_text.strip():
                    blocks.append({
                        'text': block_text.strip(),
                        'page': page_num + 1,
                        'block_index': block_idx,
                        'x_min': x_min,
                        'y_min': y_min,
                        'x_max': x_max,
                        'y_max': y_max,
                        'width': x_max - x_min,
                        'height': y_max - y_min,
                        'x_center': (x_min + x_max) / 2,
                        'y_center': (y_min + y_max) / 2,
                    })

        return blocks

    def sort_blocks_by_coordinates(self, blocks: List[Dict]) -> List[Dict]:
        """
        ブロックを座標順に並べ替え（読み取り順序を修正）

        並べ替えルール:
        1. ページ番号順
        2. Y座標順（上から下）
        3. 同じY座標ならX座標順（左から右）
        """
        # Y座標の近さの閾値（同じ行とみなす範囲）
        y_threshold = 20

        sorted_blocks = []

        # ページごとに処理
        pages = {}
        for block in blocks:
            page = block['page']
            if page not in pages:
                pages[page] = []
            pages[page].append(block)

        # 各ページを処理
        for page_num in sorted(pages.keys()):
            page_blocks = pages[page_num]

            # Y座標でグループ化（同じ行）
            rows = []
            for block in page_blocks:
                # 既存の行に追加できるか確認
                added = False
                for row in rows:
                    # 行の平均Y座標を計算
                    avg_y = sum(b['y_center'] for b in row) / len(row)
                    if abs(block['y_center'] - avg_y) < y_threshold:
                        row.append(block)
                        added = True
                        break

                if not added:
                    # 新しい行を作成
                    rows.append([block])

            # 各行をY座標でソート
            rows.sort(key=lambda row: sum(b['y_center'] for b in row) / len(row))

            # 各行内でX座標でソート
            for row in rows:
                row.sort(key=lambda b: b['x_center'])
                sorted_blocks.extend(row)

        return sorted_blocks

    def is_noise(self, block: Dict) -> bool:
        """
        ノイズかどうかを判定（使用していない - 参考用）

        ノイズの条件:
        1. 孤立した1-2桁の数字（ページ番号など）
        2. 極端に小さいテキスト
        3. ページの隅にあるテキスト
        """
        text = block['text'].strip()

        # 空文字列
        if not text:
            return True

        # 孤立した数字パターン
        for pattern in self.noise_patterns:
            if pattern.match(text):
                # ただし、項番号の可能性がある場合は残す
                # （前後のブロックとの距離で判定）
                if len(text) <= 2 and text.isdigit():
                    # 後で項番号として使えるかもしれないので、慎重に
                    return False
                return True

        # 極端に小さいテキスト（フォントサイズの推定）
        # ブロックの高さが極端に小さい場合
        if block['height'] < 10:
            return True

        return False

    def is_likely_page_number(self, block: Dict, all_blocks: List[Dict], page_height: int = 3000) -> bool:
        """
        ページ番号の可能性が高いかを判定

        判定基準:
        1. 1-3桁の数字のみ
        2. ページの上端(y < 150)または下端(y > page_height - 150)
        3. 周囲50px以内に他のテキストがない（孤立している）

        Args:
            block: 判定対象のブロック
            all_blocks: 同じページの全ブロック
            page_height: ページの高さ（デフォルト3000はA4サイズ想定）

        Returns:
            True: ページ番号の可能性が高い
            False: ページ番号ではない可能性が高い（項番号など）
        """
        text = block['text'].strip()

        # 1-3桁の数字のみ
        if not re.match(r'^\d{1,3}$', text):
            return False

        # ページの上端または下端にあるか
        y_center = block['y_center']
        is_at_edge = (y_center < 150) or (y_center > page_height - 150)

        if not is_at_edge:
            # ページ中央にある数字は項番号の可能性が高い
            return False

        # 同じページの他のブロックを取得
        same_page_blocks = [b for b in all_blocks if b['page'] == block['page'] and b != block]

        # 周囲50px以内に他のテキストがあるか確認
        nearby_blocks = [
            b for b in same_page_blocks
            if abs(b['x_center'] - block['x_center']) < 100 and
               abs(b['y_center'] - block['y_center']) < 50
        ]

        # 周囲にテキストがある = 項番号の可能性が高い
        if nearby_blocks:
            return False

        # すべての条件を満たす = ページ番号の可能性が高い
        return True

    def remove_noise_blocks(self, blocks: List[Dict], aggressive=False) -> List[Dict]:
        """
        ノイズブロックを除去（ページ番号を賢く除去）

        戦略:
        - ページの端にある孤立した数字のみを「ページ番号」として除去
        - ページ中央にある数字は項番号の可能性があるため残す
        - 周囲にテキストがある数字も残す

        Args:
            blocks: ブロックのリスト
            aggressive: Trueの場合、より積極的にノイズを除去（現在未使用）

        Returns:
            ノイズ除去後のブロックリスト
        """
        if not blocks:
            return blocks

        # ページ番号を除去
        filtered_blocks = []
        for block in blocks:
            # ページ番号かどうかを判定
            if self.is_likely_page_number(block, blocks):
                # ページ番号と判定された場合はスキップ
                continue

            # 空のブロックも除去
            if not block['text'].strip():
                continue

            filtered_blocks.append(block)

        return filtered_blocks

    def merge_blocks_to_text(self, blocks: List[Dict]) -> str:
        """
        ブロックを結合して完全なテキストにする

        ルール:
        - ページごとに「### ページ X ###」を挿入
        - ブロック間は改行で区切る
        """
        if not blocks:
            return ""

        lines = []
        current_page = None

        for block in blocks:
            # ページが変わったらページマーカーを挿入
            if block['page'] != current_page:
                if current_page is not None:
                    lines.append("")  # ページ間の空行
                lines.append(f"### ページ {block['page']} ###")
                lines.append("")
                current_page = block['page']

            # ブロックのテキストを追加
            lines.append(block['text'])

        return '\n'.join(lines)

    def process_response(self, response, debug=False) -> Dict:
        """
        Vision APIレスポンスを処理して完全テキストを抽出

        Returns:
            {
                'raw_text': '完全なテキスト',
                'blocks': ブロック情報のリスト,
                'stats': 統計情報
            }
        """
        # ステップ1: すべてのブロックを抽出
        all_blocks = self.extract_all_blocks(response)
        if debug:
            print(f"[ステップ1] 抽出されたブロック数: {len(all_blocks)}")

        # ステップ2: 座標順に並べ替え
        sorted_blocks = self.sort_blocks_by_coordinates(all_blocks)
        if debug:
            print(f"[ステップ2] 並べ替え完了")

        # ステップ3: ノイズ除去（保守的）
        cleaned_blocks = self.remove_noise_blocks(sorted_blocks, aggressive=False)
        removed_count = len(sorted_blocks) - len(cleaned_blocks)
        if debug:
            print(f"[ステップ3] ノイズ除去: {removed_count}個のブロックを除去")
            if removed_count > 0:
                removed_texts = [b['text'] for b in sorted_blocks if b not in cleaned_blocks]
                print(f"  除去されたテキスト: {removed_texts[:5]}")  # 最初の5個を表示

        # ステップ4: テキストに結合
        full_text = self.merge_blocks_to_text(cleaned_blocks)
        if debug:
            print(f"[ステップ4] 完全テキスト生成: {len(full_text)}文字")

        return {
            'raw_text': full_text,
            'blocks': cleaned_blocks,
            'stats': {
                'total_blocks': len(all_blocks),
                'after_sorting': len(sorted_blocks),
                'after_cleaning': len(cleaned_blocks),
                'removed_noise': removed_count,
                'total_chars': len(full_text)
            }
        }


def test_coordinate_ocr():
    """テスト用（実際のVision APIレスポンスが必要）"""
    print("CoordinateOCR モジュールが正常にロードされました")
    print("使用方法:")
    print("  ocr = CoordinateOCR()")
    print("  result = ocr.process_response(vision_api_response, debug=True)")
    print("  full_text = result['raw_text']")


if __name__ == "__main__":
    test_coordinate_ocr()
