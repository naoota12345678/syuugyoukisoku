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
        prompt = f"""あなたはOCRで抽出されたテキストの整理を行う専門家です。

【あなたの役割】
PDFからOCR抽出した直後のテキストを整理する作業です。
OCRエラーにより誤配置された項番号を、本来あるべき位置に移動させてください。

【絶対にやらないこと】
- 新しい条文や項を追加する
- 条番号を振り直す
- 内容を法令に合わせて修正する
- テキストの内容を変更・削除する

【やること】
- OCRで誤配置された項番号を、本来の位置に戻す
- 改行で分断された単語を連結する
- ページ番号が項番号の間に入っていれば除去する

【OCRの典型的なエラーパターンと対処方法】

パターン1: **項番号が文章の途中に入り込んでいる**
- 現象: 文章が途中で切れ、項番号が挟まり、その後文章が続く
- 対処: 途中の項番号を取り出し、次の自然な段落の先頭に配置
- 判断基準: 文章として意味が通るかどうか

パターン2: **項番号と本文が分離している**
- 現象: 項番号だけの行があり、その前後に本文がある
- 対処: 項番号がどの文章に属するか文脈から判断し、正しい位置に配置
- 判断基準: 前の文章が完結しているか、項番号の連続性（1,2,3...）

パターン3: **単語の途中で改行されている**
- 現象: 単語が途中で切れて次の行に続いている
- 対処: 改行を削除して単語を連結

パターン4: **ページ番号が項番号の間に混入**
- 現象: 項番号の連続の中に数字だけの行がある
- 対処: ページ番号と判断できる数字を除去

【重要な原則】
- テキストの内容は一切変更しない
- 項番号の数を増やさない、減らさない
- ただ「正しい位置に移動する」だけ
- 文脈を読んで、どの文章にどの項番号が属するか判断する
- 不自然な場所にある項番号を見つけ、それがどこに属するかを推理する

【対象テキスト】
```
{text}
```

修正後のテキストのみを出力してください（説明は不要）。"""

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
