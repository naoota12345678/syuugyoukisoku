"""
座標ベースの完全OCRシステム
1. すべてのテキストを座標付きで取得
2. 座標順に並べ替え
3. ノイズ除去（慎重に）
4. 完全テキストとして結合
"""

from typing import List, Dict, Tuple, Optional
import re


class CoordinateOCR:
    """座標情報を使った正確なテキスト抽出"""

    def __init__(self, debug=False):
        # デバッグモードフラグ
        self.debug = debug
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

        判定基準（修正版）:
        1. 1-3桁の数字のみ
        2. 周囲のコンテキストで判定
           - 「第」「条」などがある → 条番号として残す
           - 丸数字（①②③）の間にある → ページ番号として除去
           - 孤立している → ページ番号として除去
        3. ページの上端・下端は優先的にページ番号として扱う

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

        num = int(text)
        y_center = block['y_center']
        same_page_blocks = [b for b in all_blocks if b['page'] == block['page'] and b != block]

        # 周囲50px以内のブロックを取得
        nearby_blocks = [
            b for b in same_page_blocks
            if abs(b['x_center'] - block['x_center']) < 100 and
               abs(b['y_center'] - block['y_center']) < 50
        ]

        # 周囲のテキストを確認
        nearby_texts = [b['text'].strip() for b in nearby_blocks]

        # 条番号の一部かどうかをチェック
        # 前後に「第」「条」「(」などがある場合は条番号として残す
        for nearby_text in nearby_texts:
            if re.search(r'第|条|（|章', nearby_text):
                return False  # 条番号・章番号の一部なので残す

        # ページの上端または下端で、孤立している場合はページ番号
        is_at_edge = (y_center < 150) or (y_center > page_height - 150)
        if is_at_edge and not nearby_blocks:
            return True

        # 周囲に項番号パターンがある場合
        # → その間に挟まった数字はページ番号の可能性が高い

        # 丸数字パターン（①②③）
        has_circle_numbers_nearby = any(
            re.search(r'[①-⑳]', nearby_text) for nearby_text in nearby_texts
        )

        # 括弧なし数字パターン（1. 2. 3.）
        has_plain_item_numbers_nearby = any(
            re.match(r'^[0-9]{1,2}[.．、]', nearby_text) for nearby_text in nearby_texts
        )

        # 括弧付き数字パターン（(1) (2) (3)）
        has_paren_item_numbers_nearby = any(
            re.match(r'^\([0-9]{1,2}\)', nearby_text) for nearby_text in nearby_texts
        )

        # いずれかの項番号パターンがあれば、間の孤立数字はページ番号
        if has_circle_numbers_nearby or has_plain_item_numbers_nearby or has_paren_item_numbers_nearby:
            # 項番号のシーケンス中にある数字はページ番号の可能性が高い
            if self.debug:
                print(f"[DEBUG] ページ番号判定: '{text}' は項番号の間にある孤立数字（周囲: {nearby_texts[:3]}）")
            return True

        # 周囲に長文（50文字以上）がない場合はページ番号
        has_long_text_nearby = any(len(t) > 50 for t in nearby_texts)
        if not has_long_text_nearby and not nearby_blocks:
            return True

        # その他の場合は項番号の可能性が高い
        return False

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

    def remove_out_of_sequence_numbers(self, blocks: List[Dict]) -> List[Dict]:
        """
        項番号のシーケンスをチェックして、順序が飛んでいる数字を削除

        例: 1, 2, 3, 23, 4 → 23を削除（3→23→4は不自然）
        例: ①, ②, ③, 23, ④ → 23を削除（丸数字のシーケンス中の数字）

        Args:
            blocks: ブロックのリスト

        Returns:
            シーケンス外の数字を削除したブロックリスト
        """
        if not blocks:
            return blocks

        filtered_blocks = []

        # ページごとに処理
        pages = {}
        for block in blocks:
            page = block['page']
            if page not in pages:
                pages[page] = []
            pages[page].append(block)

        for page, page_blocks in pages.items():
            # すべてのブロックをスキャンして、項番号らしきものを収集
            item_candidates = []

            for i, block in enumerate(page_blocks):
                text = block['text'].strip()
                item_type = None
                item_value = None

                # 丸数字パターン
                if re.match(r'^[①-⑳]+$', text):
                    circle_map = {'①':1,'②':2,'③':3,'④':4,'⑤':5,'⑥':6,'⑦':7,'⑧':8,'⑨':9,'⑩':10,
                                  '⑪':11,'⑫':12,'⑬':13,'⑭':14,'⑮':15,'⑯':16,'⑰':17,'⑱':18,'⑲':19,'⑳':20}
                    if text in circle_map:
                        item_type = 'circle'
                        item_value = circle_map[text]

                # 括弧付き数字パターン (1), (2), (3)
                elif re.match(r'^\([0-9]+\)$', text):
                    match = re.match(r'^\(([0-9]+)\)$', text)
                    if match:
                        item_type = 'paren'
                        item_value = int(match.group(1))

                # 孤立した1-2桁の数字
                elif re.match(r'^[0-9]{1,2}$', text):
                    item_type = 'plain'
                    item_value = int(text)

                if item_type and item_value:
                    item_candidates.append({
                        'index': i,
                        'block': block,
                        'type': item_type,
                        'value': item_value
                    })

            # 項番号が3個以上ある場合のみシーケンスチェック
            if len(item_candidates) >= 3:
                suspicious_blocks = set()

                # 連続する3つの項番号をチェック
                for i in range(1, len(item_candidates) - 1):
                    prev = item_candidates[i - 1]
                    curr = item_candidates[i]
                    next_item = item_candidates[i + 1]

                    # 項番号のタイプをチェック
                    # 前後が丸数字で、真ん中だけ普通の数字の場合は異常
                    if prev['type'] == 'circle' and curr['type'] == 'plain' and next_item['type'] == 'circle':
                        # 丸数字のシーケンス中に数字が挟まっている = 異常
                        suspicious_blocks.add(id(curr['block']))
                        if self.debug:
                            print(f"[DEBUG] 異常な項番号（タイプ不一致）: {prev['type']}:{prev['value']} → {curr['type']}:{curr['value']} → {next_item['type']}:{next_item['value']} (ページ{page})")
                        continue

                    # 数値のシーケンスチェック
                    # 前後の数字から大きく離れている場合は異常
                    # 例: 3 → 23 → 4 の場合、23は異常
                    if curr['value'] > prev['value'] + 10 and curr['value'] > next_item['value'] + 10:
                        suspicious_blocks.add(id(curr['block']))
                        if self.debug:
                            print(f"[DEBUG] 異常な項番号（値が飛躍）: {prev['value']} → {curr['value']} → {next_item['value']} (ページ{page})")
                        continue

                    # より賢い判定: 前後の値が連続していて、真ん中が大きく異なる場合
                    # 例: 3 → 23 → 4 (3と4は連続、23は異常)
                    if abs(next_item['value'] - prev['value']) <= 2:  # 前後が連続または近接
                        if curr['value'] > prev['value'] + 5 or curr['value'] < prev['value'] - 5:
                            suspicious_blocks.add(id(curr['block']))
                            if self.debug:
                                print(f"[DEBUG] 異常な項番号（前後が連続だが中央が異常）: {prev['value']} → {curr['value']} → {next_item['value']} (ページ{page})")

                # ページのブロックをフィルタリング
                for block in page_blocks:
                    if id(block) not in suspicious_blocks:
                        filtered_blocks.append(block)
            else:
                # 項番号が少ない場合はそのまま
                filtered_blocks.extend(page_blocks)

        return filtered_blocks

    def merge_blocks_to_text(self, blocks: List[Dict]) -> str:
        """
        ブロックを結合して完全なテキストにする

        ルール:
        - ページごとに空行を挿入
        - 項番号パターン（1. 2. 3.など）の直後にテキストがある場合は同じ行に結合
        - 項番号のシーケンスを検出して、欠けている番号を補完
        - その他のブロックは改行で区切る
        """
        if not blocks:
            return ""

        # 項番号を事前に検出してシーケンスを把握
        item_numbers = self._detect_item_number_sequence(blocks)

        lines = []
        current_page = None
        i = 0
        current_item_number = None

        while i < len(blocks):
            block = blocks[i]

            # ページが変わったら空行を挿入
            if block['page'] != current_page:
                if current_page is not None:
                    lines.append("")  # ページ間の空行
                current_page = block['page']
                current_item_number = None  # ページが変わったら項番号をリセット

            text = block['text'].strip()

            # 項番号パターンかどうかをチェック
            item_match = re.match(r'^([0-9]{1,2})[.．、]$', text)

            if item_match:
                # 項番号を記録
                current_item_number = int(item_match.group(1))

                # 次のブロックと結合
                if i + 1 < len(blocks):
                    next_block = blocks[i + 1]

                    # 次のブロックが同じページで、Y座標が近い（50px以内）場合は結合
                    if (next_block['page'] == block['page'] and
                        abs(next_block['y_center'] - block['y_center']) < 50):

                        # 項番号とテキストを結合
                        combined_text = text + " " + next_block['text'].strip()
                        lines.append(combined_text)

                        # 次のブロックはスキップ
                        i += 2
                        continue

                # 次のブロックが遠い場合は項番号だけ出力
                lines.append(text)
                i += 1
                continue

            # 丸数字や括弧付き数字の項番号
            is_circle_item = re.match(r'^[①-⑳]$', text)
            is_paren_item = re.match(r'^\([0-9]{1,2}\)$', text)

            if is_circle_item or is_paren_item:
                # 次のブロックと結合
                if i + 1 < len(blocks):
                    next_block = blocks[i + 1]

                    if (next_block['page'] == block['page'] and
                        abs(next_block['y_center'] - block['y_center']) < 50):

                        combined_text = text + " " + next_block['text'].strip()
                        lines.append(combined_text)
                        i += 2
                        continue

                lines.append(text)
                i += 1
                continue

            # 項番号が欠けている可能性をチェック
            # 前の項番号が3で、次に「4.」がない場合、このテキストが4項の可能性
            if current_item_number and not item_match and not is_circle_item and not is_paren_item:
                # 次の項番号を探す
                next_item = self._find_next_item_number(blocks, i + 1, block['page'])

                # 現在の項番号+1が次に来るべき番号で、でもそれがない場合
                expected_next = current_item_number + 1
                if next_item and next_item > expected_next:
                    # このテキストは欠けている項番号の内容の可能性
                    # 項番号を補完して出力
                    lines.append(f"{expected_next}. {text}")
                    current_item_number = expected_next
                    i += 1
                    continue

            # 通常のブロック
            lines.append(text)
            i += 1

        return '\n'.join(lines)

    def _detect_item_number_sequence(self, blocks: List[Dict]) -> List[int]:
        """ブロックから項番号のシーケンスを検出"""
        item_numbers = []
        for block in blocks:
            text = block['text'].strip()
            match = re.match(r'^([0-9]{1,2})[.．、]$', text)
            if match:
                item_numbers.append(int(match.group(1)))
        return sorted(set(item_numbers))

    def _find_next_item_number(self, blocks: List[Dict], start_idx: int, current_page: int) -> Optional[int]:
        """次の項番号を探す"""
        for i in range(start_idx, min(start_idx + 10, len(blocks))):
            if blocks[i]['page'] != current_page:
                break
            text = blocks[i]['text'].strip()
            match = re.match(r'^([0-9]{1,2})[.．、]$', text)
            if match:
                return int(match.group(1))
        return None

    def process_response(self, response, debug=False) -> Dict:
        """
        Vision APIレスポンスを処理して完全テキストを抽出

        Args:
            response: Vision APIのレスポンス
            debug: Trueの場合、詳細なデバッグ情報を出力

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
            print(f"\n{'='*80}")
            print(f"[ステップ1] 抽出されたブロック数: {len(all_blocks)}")
            self._debug_print_item_numbers(all_blocks, "抽出直後")

        # ステップ2: 座標順に並べ替え
        sorted_blocks = self.sort_blocks_by_coordinates(all_blocks)
        if debug:
            print(f"\n{'='*80}")
            print(f"[ステップ2] 並べ替え完了")
            self._debug_print_item_numbers(sorted_blocks, "並べ替え後")

        # ステップ3: ノイズ除去（保守的）
        cleaned_blocks = self.remove_noise_blocks(sorted_blocks, aggressive=False)
        removed_count = len(sorted_blocks) - len(cleaned_blocks)
        if debug:
            print(f"\n{'='*80}")
            print(f"[ステップ3] ノイズ除去: {removed_count}個のブロックを除去")
            if removed_count > 0:
                removed_blocks = [b for b in sorted_blocks if b not in cleaned_blocks]
                print(f"  除去されたブロック:")
                for b in removed_blocks[:10]:  # 最初の10個を表示
                    print(f"    - '{b['text'][:30]}' (page={b['page']}, y={b['y_center']:.0f})")

        # ステップ3.5: 項番号シーケンスチェック（異常な数字を除去）
        sequence_checked_blocks = self.remove_out_of_sequence_numbers(cleaned_blocks)
        seq_removed_count = len(cleaned_blocks) - len(sequence_checked_blocks)
        if debug and seq_removed_count > 0:
            print(f"\n{'='*80}")
            print(f"[ステップ3.5] 項番号シーケンスチェック: {seq_removed_count}個の異常な数字を除去")
            removed_blocks = [b for b in cleaned_blocks if b not in sequence_checked_blocks]
            for b in removed_blocks:
                print(f"    - '{b['text']}' (page={b['page']}, y={b['y_center']:.0f})")

        # ステップ4: テキストに結合
        full_text = self.merge_blocks_to_text(sequence_checked_blocks)
        if debug:
            print(f"\n{'='*80}")
            print(f"[ステップ4] 完全テキスト生成: {len(full_text)}文字")

        return {
            'raw_text': full_text,
            'blocks': sequence_checked_blocks,
            'stats': {
                'total_blocks': len(all_blocks),
                'after_sorting': len(sorted_blocks),
                'after_cleaning': len(cleaned_blocks),
                'after_sequence_check': len(sequence_checked_blocks),
                'removed_noise': removed_count,
                'removed_out_of_sequence': seq_removed_count,
                'total_chars': len(full_text)
            }
        }

    def _debug_print_item_numbers(self, blocks: List[Dict], stage: str):
        """
        デバッグ用: 項番号を含むブロックの情報を出力

        Args:
            blocks: ブロックのリスト
            stage: 処理段階の名前
        """
        # 項番号パターン
        item_patterns = [
            re.compile(r'^[①-⑳]+'),  # 丸数字
            re.compile(r'^\([0-9]+\)'),  # (1)(2)(3)
            re.compile(r'^[0-9]+[.．、]'),  # 1. 2. 3.
            re.compile(r'^\d{1,2}$'),  # 孤立した数字
        ]

        print(f"\n【{stage}の項番号パターン】")
        item_blocks = []

        for i, block in enumerate(blocks):
            text = block['text'].strip()
            for pattern in item_patterns:
                if pattern.match(text):
                    item_blocks.append((i, block))
                    break

        if not item_blocks:
            print("  項番号パターンのブロックなし")
            return

        print(f"  検出された項番号: {len(item_blocks)}個")
        print(f"\n  {'順序':<6} {'ページ':<6} {'X座標':<8} {'Y座標':<8} {'テキスト':<30}")
        print(f"  {'-'*70}")

        for i, block in item_blocks[:20]:  # 最初の20個を表示
            text_preview = block['text'].strip()[:30]
            print(f"  {i:<6} {block['page']:<6} {block['x_center']:<8.0f} {block['y_center']:<8.0f} '{text_preview}'")


def test_coordinate_ocr():
    """テスト用（実際のVision APIレスポンスが必要）"""
    print("CoordinateOCR モジュールが正常にロードされました")
    print("使用方法:")
    print("  ocr = CoordinateOCR()")
    print("  result = ocr.process_response(vision_api_response, debug=True)")
    print("  full_text = result['raw_text']")


if __name__ == "__main__":
    test_coordinate_ocr()
