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

    def analyze_structure(self, text: str) -> dict:
        """
        構造（章・条・項番号）の問題を分析して修正提案を返す

        Args:
            text: OCRで抽出したテキスト

        Returns:
            dict: {"success": bool, "fixes": list, "fixed_text": str}
        """
        prompt = f"""あなたはOCRで抽出されたテキストの問題を分析する専門家です。

【あなたの役割】
PDFからOCR抽出した直後のテキストを分析し、構造的な問題を検出して修正案を提示してください。

【検出すべき問題】
1. **項番号の後に改行がない**
   - 例: `2.個人情報とは...` → `2.\n個人情報とは...`

2. **項番号の欠落**
   - 例: 1,2,4,5 → 3が抜けている可能性

3. **項番号が文章の途中に入り込んでいる**
   - 文章が途中で切れ、項番号が挟まり、その後続く

4. **不自然な半角スペースの混入**
   - 文章の途中に意味のない空白

5. **単語の途中で改行されている**
   - 単語が分断されている

【対象テキスト】
```
{text}
```

【出力形式】
以下のJSON形式で出力してください：

```json
{{
  "fixes": [
    {{
      "location": "第XX条 項Y",
      "fix_type": "項番号後の改行欠落" or "項番号の欠落" or "項番号の誤配置" or "不自然な空白" or "単語の分断",
      "before_text": "修正前のテキスト（該当箇所を50文字程度抜粋）",
      "after_text": "修正後のテキスト（該当箇所を50文字程度）",
      "reason": "修正が必要な理由"
    }}
  ],
  "fixed_text": "修正後の全文"
}}
```

【重要な原則】
- テキストの内容は一切変更しない
- 項番号の数を増やさない、減らさない（欠落は警告のみ）
- ただ「正しい位置に移動する」だけ
- 必ずJSON形式のみで回答してください（説明は不要）"""

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

            result_text = response.content[0].text.strip()

            # JSONを抽出（```json ... ``` の中身を取得）
            import json
            import re

            json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # ```なしの場合
                json_str = result_text

            result = json.loads(json_str)

            return {
                "success": True,
                "fixes": result.get("fixes", []),
                "fixed_text": result.get("fixed_text", text)
            }

        except Exception as e:
            print(f"AI構造修正エラー: {e}")
            import traceback
            traceback.print_exc()
            # エラー時は問題なしとして返す
            return {
                "success": False,
                "error": str(e),
                "fixes": [],
                "fixed_text": text
            }


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
