"""
AI構造修正モジュール

OCRで抽出したテキストの構造（章・条・項番号）のみを修正
- 文章は絶対に触らない
- 章番号・条番号・項番号の順序を整理
- ページ番号の混入を除去
"""

import os
from typing import Optional
import httpx


class AIStructureFixer:
    """AIを使って就業規則の構造（章・条・項番号）のみを修正"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Claude API Key（省略時は環境変数から取得）
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")

        # カスタムHTTPクライアントを作成（proxiesなし）
        try:
            from anthropic import Anthropic

            # proxiesを明示的にNoneにしたカスタムクライアント
            http_client = httpx.Client(timeout=60.0)

            self.client = Anthropic(
                api_key=self.api_key,
                http_client=http_client
            )
        except Exception as e:
            raise Exception(f"Failed to initialize Anthropic client: {e}")

    def fix_structure(self, text: str) -> str:
        """
        構造（章・条・項番号）のみを修正（文章は絶対に触らない）

        Args:
            text: OCRで抽出したテキスト

        Returns:
            構造を修正したテキスト
        """
        prompt = f"""あなたは就業規則のOCRテキストの構造を修正する専門家です。

以下のテキストは就業規則からOCR抽出したものです。
章・条・項番号の構造に問題がある場合のみ修正してください。

【絶対に守るルール】
1. **文章は一切変更しない・削除しない**（1文字たりとも触らない）
2. **章番号（第○章）・条番号（第○条）・項番号（1. 2. ①②③）の位置・順序のみ修正**
3. ページ番号が項番号の間に入っている場合は除去
4. 項番号が本文から離れている場合は正しい位置に移動
5. 章・条の番号順序が乱れている場合は整理
6. 改行位置は極力そのまま維持

【修正例1: 項番号と本文の分離】
修正前:
```
第22条(代休)
1. 会社は、休日に勤務させた場合、代休を与えることがある。
2. 前項の代休は、所属長が指定する。
3.
前項の代休は、休日勤務した日から1ヶ月以内の取得を原則とする。
```

修正後:
```
第22条(代休)
1. 会社は、休日に勤務させた場合、代休を与えることがある。
2. 前項の代休は、所属長が指定する。
3. 前項の代休は、休日勤務した日から1ヶ月以内の取得を原則とする。
```

【修正例2: ページ番号の除去】
修正前:
```
第22条(代休)
1. ...
2. ...
23
3. 前項の代休は...
```

修正後:
```
第22条(代休)
1. ...
2. ...
3. 前項の代休は...
```

【修正例3: 章番号の順序整理】
修正前:
```
第3章 給与
第1条 ...
第5章 休暇
第2条 ...
第4章 労働時間
第3条 ...
```

修正後:
```
第3章 給与
第1条 ...
第4章 労働時間
第3条 ...
第5章 休暇
第2条 ...
```

【対象テキスト】
```
{text}
```

修正後のテキストのみを出力してください（説明は不要）。
文章内容は絶対に変更しないでください。"""

        try:
            # Claude Sonnet 4を使用（高精度な構造理解が必要）
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
                temperature=0.0,  # 決定的な出力
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            return response.content[0].text.strip()

        except Exception as e:
            print(f"AI構造修正エラー: {e}")
            # エラー時は元のテキストをそのまま返す
            return text


if __name__ == "__main__":
    # テスト用
    fixer = AIStructureFixer()

    test_text = """第2章 採用及び異動

第3条(採用手続)
1. 会社は、入社を希望する者の中から選考試験を行い、これに合格した者を採用する。
2. 前項により採用することが決定した者は、会社が指定した期日までに次の書類を提出しなければならない。
3.
第2項の定めにより会社に提出した書類の記載事項に変更が生じたときは、速やかに書面で会社に変更事項を届け出なければならない。

第4条(試用期間)
1. 新たに採用した者については、採用した日から3ヶ月間を試用期間とする。
2.
23
試用期間中または試用期間満了時に従業員として不適格と認めた場合は、本採用を行わないことがある。
3. 前項の場合、会社は14日前に予告するか、または平均賃金の14日分以上の手当を支給して解雇することができる。"""

    print("=== 修正前 ===")
    print(test_text)

    fixed = fixer.fix_structure(test_text)

    print("\n=== 修正後 ===")
    print(fixed)
