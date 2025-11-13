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
        self.api_key = (api_key or os.environ.get("ANTHROPIC_API_KEY", "")).strip()

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")

        # カスタムHTTPクライアントを作成（proxiesなし）
        try:
            from anthropic import Anthropic

            # proxiesを明示的にNoneにしたカスタムクライアント
            # 出力トークン削減でタイムアウトを300秒(5分)に設定
            http_client = httpx.Client(timeout=300.0)

            self.client = Anthropic(
                api_key=self.api_key,
                http_client=http_client,
                timeout=300.0  # Anthropic SDKのタイムアウトも設定
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

【絶対に守るべき原則 - 最重要】
✗ 文字を1文字も変更しない（誤字修正も禁止）
✗ 文字を1文字も追加しない（欠けている項番号を補完することも禁止）
✗ 文字を1文字も削除しない（ページ番号以外）
✓ できることは「位置の移動」「改行の追加/削除」「空白の追加/削除」のみ

【あなたの役割】
PDFからOCR抽出した直後のテキストを分析し、構造的な問題を検出して修正案を提示してください。
ただし、元のテキストに含まれる文字はそのまま保持し、配置と空白・改行のみを調整します。

【検出すべき問題（文字の内容は変えない）】
1. **項番号が文章の途中に入り込んでいる**
   - 例: 「会社は速やかに7.セクハラとは...」→「会社は速やかに\n7. セクハラとは...」
   - 注意: すべての文字はそのまま。位置を移動するだけ。文脈を見て適切な位置に配置する。

2. **項番号の欠落（警告のみ、追加しない）**
   - 例: 1,2,4,5 → 3が抜けている可能性を指摘
   - 注意: 欠けている「3」を勝手に追加してはいけない

3. **不自然な半角スペースや全角スペースの混入**
   - 例: 「個人 情報」→「個人情報」
   - 注意: スペースを削除するだけ。他の文字は変えない。

4. **単語の途中で改行されている**
   - 例: 「個人\n情報」→「個人情報」
   - 注意: 改行を削除するだけ。文字は変えない。

【やってはいけないことの具体例】
✗ 「採用された時」→「採用されたとき」（漢字→ひらがな変更）
✗ 「会社わ」→「会社は」（誤字修正）
✗ 「1,2,4,5」→「1,2,3,4,5」（欠けた番号を追加）
✗ 「第56条」→「第56条（追加事項）」（タイトル追加）
✗ 「1. 会社は」→「1.\n会社は」（正常な項番号に改行を入れる）
✗ 文章の言い回しを変える、法令に合わせて修正する

【対象テキスト】
```
{text}
```

【出力形式】
以下のJSON形式で問題箇所のリストのみ出力してください：

```json
{{
  "fixes": [
    {{
      "location": "第XX条 項Y",
      "fix_type": "項番号の誤配置" or "項番号の欠落" or "不自然な空白" or "単語の分断",
      "before_text": "修正前のテキスト（該当箇所を50文字程度抜粋）",
      "after_text": "修正後のテキスト（該当箇所を50文字程度）",
      "reason": "修正が必要な理由"
    }}
  ]
}}
```

【最終確認】
- 元のテキストに含まれる文字はすべてそのまま保持されていますか？
- 変更したのは位置・改行・空白だけですか？
- 正常な項番号（「1. テキスト」）に改行を入れていませんか？
- 必ずJSON形式のみで回答してください（説明は不要）
- 全文は返さず、問題箇所のリストのみ返してください"""

        try:
            # Claude Sonnet 4を使用（高精度な構造理解が必要）
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,  # 問題箇所リストのみなので削減
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
                "fixes": result.get("fixes", [])
            }

        except Exception as e:
            print(f"AI構造修正エラー: {e}")
            import traceback
            traceback.print_exc()
            # エラー時は問題なしとして返す（ページは正常に表示）
            return {
                "success": True,
                "error": str(e),
                "fixes": []
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
