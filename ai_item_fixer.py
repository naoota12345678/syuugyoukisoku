"""
AI項番号修正モジュール

OCRで抽出したテキストの項番号のみをAIで修正する
- テキストは一切削除しない
- 項番号の位置のみを修正
"""

import os
from anthropic import Anthropic
from typing import Optional


class AIItemNumberFixer:
    """AIを使って項番号のみを修正"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Claude API Key（省略時は環境変数から取得）
        """
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")

        # Claude APIクライアントを初期化（バージョン互換性対応）
        try:
            # 新しいバージョンのAnthropicライブラリ
            self.client = Anthropic(api_key=api_key)
        except TypeError:
            # 古いバージョンの場合
            import anthropic
            self.client = anthropic.Client(api_key=api_key)

    def fix_item_numbers(self, text: str) -> str:
        """
        項番号のみを修正（テキストは削除しない）

        Args:
            text: OCRで抽出したテキスト

        Returns:
            項番号を修正したテキスト
        """
        prompt = f"""あなたは就業規則のOCRテキストを修正する専門家です。

以下のテキストは就業規則からOCR抽出したものです。
項番号（1. 2. 3. や ①②③ など）の位置に問題がある場合のみ修正してください。

【重要なルール】
1. **テキストは一切削除しない**（ページ番号も含めて全て残す）
2. 項番号が本文から離れている場合は、正しい位置に移動する
3. 項番号以外のテキストは一切変更しない
4. 改行位置も極力そのまま維持する
5. 条文（第○条）、章番号（第○章）は絶対に変更しない

【修正例】
修正前:
```
第22条(代休)
1. ...
2. ...
3.
前項の代休は...
```

修正後:
```
第22条(代休)
1. ...
2. ...
3. 前項の代休は...
```

【対象テキスト】
```
{text}
```

修正後のテキストのみを出力してください（説明は不要）。"""

        try:
            # Claude Haiku 3.5を使用（高速・低コスト）
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=8192,
                temperature=0.1,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            return response.content[0].text.strip()

        except Exception as e:
            print(f"AI修正エラー: {e}")
            # エラー時は元のテキストをそのまま返す
            return text


if __name__ == "__main__":
    # テスト用
    fixer = AIItemNumberFixer()

    test_text = """第22条(代休)
1. 会社は、休日に勤務させた場合、代休を与えることがある。
2. 前項の代休は、所属長が指定する。
3.
前項の代休は、休日勤務した日から1ヶ月以内の取得を原則とする。

第23条(変形労働時間制)
1. 会社は、1ヶ月単位の変形労働時間制を採用する。
2. 各変形期間の労働日数及び労働時間は、就業カレンダーで定める。
3.
各変形期間の出勤日及び休日については、変形期間開始前に通知する。
"""

    print("=== 修正前 ===")
    print(test_text)

    fixed = fixer.fix_item_numbers(test_text)

    print("\n=== 修正後 ===")
    print(fixed)
