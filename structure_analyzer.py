"""
就業規則の構造解析システム
絶対ルール：元のテキストは削除・要約しない。構造情報のみを追加する。
"""

import re
from typing import Dict, List, Optional

class StructureAnalyzer:
    """
    就業規則のテキストから構造情報を抽出
    元のテキストは一切変更せず、メタデータのみを生成
    """

    def __init__(self):
        # 章のパターン
        self.chapter_pattern = re.compile(r'^第[〇一二三四五六七八九十百0-9]+章')

        # 条のパターン（見出し付き）
        self.article_pattern = re.compile(r'^第([〇一二三四五六七八九十百0-9]+)条\s*[（(](.+?)[）)]')

        # 項のパターン（様々な形式に対応）
        self.item_patterns = [
            re.compile(r'^([①-⑳]+)'),  # 丸数字
            re.compile(r'^\(([0-9]+)\)'),  # (1)(2)(3)
            re.compile(r'^([0-9]+)[.．、]'),  # 1. 2. 3.
        ]

    def _is_noise_line(self, line: str) -> bool:
        """
        ノイズ行かどうかを判定（構造解析時に無視する）

        ノイズの例:
        - 孤立した1-2桁の数字（ページ番号など）
        - 極端に短い行（1-2文字）
        """
        line = line.strip()

        # 空行
        if not line:
            return True

        # 孤立した1-2桁の数字のみ（ページ番号の可能性）
        if re.match(r'^\d{1,2}$', line):
            return True

        # 極端に短い行（1-2文字）で、意味のある文字でない場合
        if len(line) <= 2 and not re.match(r'^[第①-⑳()\d]+', line):
            return True

        return False

    def analyze(self, raw_text: str) -> Dict:
        """
        完全テキストから構造情報を抽出

        Args:
            raw_text: OCRで抽出した完全なテキスト（変更しない）

        Returns:
            {
                "raw_text": "元のテキスト（絶対に変更しない）",
                "structure": {
                    "chapters": [...],
                    "articles": [...],
                    "items": [...]
                }
            }
        """
        lines = raw_text.split('\n')

        structure = {
            "chapters": [],
            "articles": [],
            "items": []
        }

        current_position = 0
        current_chapter = None
        current_article = None

        for line_num, line in enumerate(lines):
            line = line.strip()

            # ノイズ行をスキップ（でもテキストは削除しない）
            if self._is_noise_line(line):
                current_position += len(line) + 1
                continue

            line_start = current_position
            line_end = current_position + len(line)

            # 章の検出
            chapter_match = self.chapter_pattern.match(line)
            if chapter_match:
                chapter_text = chapter_match.group(0)
                # 章のタイトル（章番号の後のテキスト）
                title = line[len(chapter_text):].strip()

                current_chapter = {
                    "type": "chapter",
                    "number": chapter_text,
                    "title": title,
                    "line_number": line_num + 1,
                    "start_pos": line_start,
                    "end_pos": line_end,
                    "full_text": line  # 元のテキストを保存
                }
                structure["chapters"].append(current_chapter)
                current_article = None

            # 条の検出
            article_match = self.article_pattern.match(line)
            if article_match:
                article_num = article_match.group(1)
                article_title = article_match.group(2)

                current_article = {
                    "type": "article",
                    "number": f"第{article_num}条",
                    "title": article_title,
                    "chapter": current_chapter["number"] if current_chapter else None,
                    "line_number": line_num + 1,
                    "start_pos": line_start,
                    "end_pos": line_end,
                    "full_text": line  # 元のテキストを保存
                }
                structure["articles"].append(current_article)

            # 項の検出（複数パターン対応）
            item_number = None
            for pattern in self.item_patterns:
                match = pattern.match(line)
                if match:
                    item_number = self._normalize_item_number(match.group(1))
                    break

            if item_number and current_article:
                item = {
                    "type": "item",
                    "number": item_number,
                    "article": current_article["number"],
                    "chapter": current_chapter["number"] if current_chapter else None,
                    "line_number": line_num + 1,
                    "start_pos": line_start,
                    "end_pos": line_end,
                    "full_text": line  # 元のテキストを保存
                }
                structure["items"].append(item)

            current_position = line_end + 1  # +1 for newline

        return {
            "raw_text": raw_text,  # 元のテキストは絶対に変更しない
            "structure": structure,
            "metadata": {
                "total_chapters": len(structure["chapters"]),
                "total_articles": len(structure["articles"]),
                "total_items": len(structure["items"])
            }
        }

    def _normalize_item_number(self, item_str: str) -> int:
        """
        項番号を正規化（丸数字、(1)、1. などを数字に統一）
        """
        # 丸数字の変換
        circle_numbers = {
            '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5,
            '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
            '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15,
            '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20
        }

        if item_str in circle_numbers:
            return circle_numbers[item_str]

        # 数字文字列をintに変換
        try:
            return int(item_str)
        except ValueError:
            return 0

    def get_text_by_article(self, result: Dict, article_number: str) -> Optional[str]:
        """
        特定の条のテキストを元のraw_textから抽出

        Args:
            result: analyze()の戻り値
            article_number: 例: "第70条"

        Returns:
            その条の完全なテキスト
        """
        # 該当する条を検索
        article = None
        for art in result["structure"]["articles"]:
            if art["number"] == article_number:
                article = art
                break

        if not article:
            return None

        # 次の条の開始位置を取得
        article_index = result["structure"]["articles"].index(article)
        if article_index + 1 < len(result["structure"]["articles"]):
            next_article = result["structure"]["articles"][article_index + 1]
            end_pos = next_article["start_pos"]
        else:
            # 最後の条の場合
            end_pos = len(result["raw_text"])

        # raw_textから該当部分を抽出
        return result["raw_text"][article["start_pos"]:end_pos].strip()


def test_analyzer():
    """テスト用サンプル"""
    sample_text = """第7章 表彰、制裁

第70条(制裁の種類と程度)

この就業規則および関連する諸規定の禁止・制限事項に抵触する社員には以下のいずれかの制裁を行う。

① 訓戒… 始末書を取り、 将来を戒める。

② 減給･･･ 1回の額が平均賃金の1日分の半額、 総額が一賃金支払期における賃金総額の10分の1以内で賃金を減ずる
(3) 出勤停止…7日を限度として出勤の停止を命じ、 その期間の賃金は支払わない

④ 職務内容の変更・制限・・・ 始末書を提出させ、その職務内容を変更、または制限し、その職務内容、または制限された職務の範囲に応じて給与支給額を引き下げる
⑤ 降級降格・・・ 始末書を提出させ、 役職を免じ、 または引き下げ、変更後の役職 職位に応じ給与支給額を引き下げる
⑥ 懲戒解雇‥‥･予告期間を設けることなく即時解雇をする。この場合、所轄労働基準監督署長の認定を受けた場合は、 解雇予告手当は支給しない"""

    analyzer = StructureAnalyzer()
    result = analyzer.analyze(sample_text)

    print("=" * 80)
    print("元のテキスト（変更なし）:")
    print(result["raw_text"])
    print("\n" + "=" * 80)
    print("構造情報（追加のみ）:")
    print(f"\n章: {len(result['structure']['chapters'])}個")
    for chapter in result['structure']['chapters']:
        print(f"  {chapter['number']} {chapter['title']}")

    print(f"\n条: {len(result['structure']['articles'])}個")
    for article in result['structure']['articles']:
        print(f"  {article['number']} {article['title']} (行{article['line_number']})")

    print(f"\n項: {len(result['structure']['items'])}個")
    for item in result['structure']['items']:
        print(f"  項{item['number']} {item['article']} (行{item['line_number']})")

    print("\n" + "=" * 80)
    print("第70条のテキストを抽出:")
    article_text = analyzer.get_text_by_article(result, "第70条")
    print(article_text)


if __name__ == "__main__":
    test_analyzer()
