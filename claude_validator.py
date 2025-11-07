# claude_validator.py - Fixed for newer Anthropic library versions
import os
import json

class ClaudeValidator:
    """Claude APIを使用して就業規則を検証・生成するクラス"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        
        # Try to initialize with newer library version
        try:
            from anthropic import Anthropic
            # Don't pass any proxy parameters - let library handle defaults
            self.client = Anthropic(
                api_key=self.api_key,
                # Removed all proxy-related parameters
            )
        except Exception as e:
            # If still fails, try alternative initialization
            try:
                import anthropic
                self.client = anthropic.Client(api_key=self.api_key)
            except:
                raise Exception(f"Failed to initialize Anthropic client: {e}")
        
        self.models_path = "models/"
    
    def _load_model(self, filename: str) -> str:
        """モデル規程を読み込み"""
        model_path = os.path.join(self.models_path, filename)
        try:
            with open(model_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"モデルファイル {filename} が見つかりません"
    
    def _call_claude(self, prompt: str, max_tokens: int = 4096, model: str = "claude-sonnet-4-20250514") -> str:
        """Claude APIを呼び出し

        Args:
            prompt: プロンプト
            max_tokens: 最大トークン数
            model: 使用するモデル
                - "claude-sonnet-4-20250514" (デフォルト): 高性能、検証・修正・チャット向け
                - "claude-3-5-haiku-20241022": 高速・低コスト、構造化向け
        """
        try:
            message = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            return f"API Error: {str(e)}"
    
    def validate_main_rules(self, extracted_rules) -> dict:
        """本則就業規則をモデルと突合して検証"""
        
        model = self._load_model("main_rules_model.txt")
        rules_text = self._structure_to_text(extracted_rules)
        
        prompt = f"""あなたは経験豊富な社会保険労務士です。

【モデル就業規則（適切な規程の基準）】
{model}

【実際の就業規則】
{rules_text}

上記2つを比較し、実際の就業規則の問題点を抽出してください。

以下の観点で分析：
1. 法令違反または抵触の可能性がある箇所
2. 記載が不明確または曖昧な箇所
3. 必須事項の記載漏れ
4. 表現が不適切な箇所

各問題点について以下のJSON形式で出力してください：
```json
{{
  "modifications": [
    {{
      "article_number": "第○条",
      "modification_type": "法令抵触" or "表現の明確化" or "必須事項漏れ" or "表現不適切",
      "before_text": "現在の記載内容",
      "after_text": "推奨する修正内容",
      "reason": "修正が必要な理由の詳細説明"
    }}
  ]
}}
```

必ずJSON形式のみで回答してください。"""

        response = self._call_claude(prompt, max_tokens=8000)
        
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response
            
            result = json.loads(json_str)
            return {
                "success": True,
                "modifications": result.get("modifications", [])
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析エラー: {str(e)}",
                "raw_response": response
            }

    def validate_main_rules_from_text(self, raw_text: str) -> dict:
        """raw_textから直接検証（構造化不要）"""

        model = self._load_model("main_rules_model.txt")

        prompt = f"""あなたは経験豊富な社会保険労務士です。

【モデル就業規則（適切な規程の基準）】
{model}

【実際の就業規則（PDFから抽出したテキスト）】
{raw_text}

上記2つを比較し、実際の就業規則の問題点を抽出してください。

以下の観点で分析：
1. 法令違反または抵触の可能性がある箇所
2. 記載が不明確または曖昧な箇所
3. 必須事項の記載漏れ
4. 表現が不適切な箇所

各問題点について以下のJSON形式で出力してください：
```json
{{
  "modifications": [
    {{
      "article_number": "第○条",
      "modification_type": "法令抵触" or "表現の明確化" or "必須事項漏れ" or "表現不適切",
      "before_text": "現在の記載内容",
      "after_text": "推奨する修正内容",
      "reason": "修正が必要な理由の詳細説明"
    }}
  ]
}}
```

重要：
- 元のテキストから章・条を正確に理解して分析してください
- すべての章・条を確認し、漏れなく検証してください

必ずJSON形式のみで回答してください。"""

        response = self._call_claude(prompt, max_tokens=16000, model="claude-sonnet-4-20250514")

        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response

            result = json.loads(json_str)
            return {
                "success": True,
                "modifications": result.get("modifications", [])
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析エラー: {str(e)}",
                "raw_response": response
            }

    def generate_part_time_rules(self, main_rules_data: dict) -> dict:
        """本則を元にパート就業規則を生成"""
        
        model = self._load_model("part_time_rules_model.txt")
        company_name = main_rules_data.get("company_name", "○○株式会社")
        
        prompt = f"""あなたは経験豊富な社会保険労務士です。

【パート就業規則モデル】
{model}

【会社情報】
会社名: {company_name}

上記モデルを基に、この会社のパートタイム・有期雇用労働者就業規則を作成してください。

要件：
1. パートタイム・有期雇用労働法に完全準拠
2. 会社名を適切に反映
3. 必須の章構成を含める
4. 有給休暇の比例付与表を含める

以下のJSON形式で出力してください：
```json
{{
  "regulation_name": "パートタイム・有期雇用労働者就業規則",
  "chapters": [
    {{
      "number": "第1章",
      "title": "総則",
      "articles": [
        {{
          "number": "第1条",
          "title": "目的",
          "content": "条文の内容",
          "items": ["1. 項目1", "2. 項目2"]
        }}
      ]
    }}
  ]
}}
```

必ずJSON形式のみで回答してください。"""

        response = self._call_claude(prompt, max_tokens=16000)
        
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response
            
            result = json.loads(json_str)
            return {
                "success": True,
                "regulation": result
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析エラー: {str(e)}",
                "raw_response": response
            }
    
    def rebuild_regulation_with_modifications(self, original_structure, modifications, company_name) -> dict:
        """修正を適用して就業規則を再構築"""

        original_text = self._structure_to_text(original_structure)

        # 修正内容をまとめる
        modifications_text = []
        for mod in modifications:
            modifications_text.append(f"""
条番号: {mod['article_number']}
修正タイプ: {mod['modification_type']}
修正前: {mod['before_text']}
修正後: {mod['after_text']}
理由: {mod['reason']}
""")

        modifications_summary = "\n---\n".join(modifications_text)

        prompt = f"""あなたは経験豊富な社会保険労務士です。

【会社名】
{company_name}

【元の就業規則】
{original_text}

【適用する修正】
{modifications_summary}

上記の修正を適用して、完全な就業規則を再構築してください。

重要な指示：
1. 指示された修正のみを正確に適用すること
2. 条番号を自動で振り直すこと（追加・削除があった場合）
3. 会社名を「{company_name}」に統一すること
4. それ以外の内容は一切変更しないこと
5. 章・条の構造を維持すること

以下のJSON形式で出力してください：
```json
{{
  "regulation_name": "就業規則",
  "company_name": "{company_name}",
  "chapters": [
    {{
      "number": "第1章",
      "title": "総則",
      "articles": [
        {{
          "number": "第1条",
          "title": "目的",
          "content": ["条文の内容"],
          "items": ["1. 項目1", "2. 項目2"]
        }}
      ]
    }}
  ],
  "changes_summary": [
    "第10条の内容を修正しました",
    "条番号を振り直しました"
  ]
}}
```

必ずJSON形式のみで回答してください。"""

        response = self._call_claude(prompt, max_tokens=16000)

        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response

            result = json.loads(json_str)
            return {
                "success": True,
                "regulation": result,
                "changes_summary": result.get("changes_summary", [])
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析エラー: {str(e)}",
                "raw_response": response
            }

    def chat_about_regulation(self, regulation_structure, company_name, user_message, chat_history=None, raw_text=None) -> dict:
        """就業規則について対話的に相談"""

        # raw_textがあればそれを使用、なければ構造化データから変換
        if raw_text:
            regulation_text = raw_text
        else:
            regulation_text = self._structure_to_text(regulation_structure)

        # チャット履歴を整形
        history_text = ""
        if chat_history:
            for msg in chat_history[-5:]:  # 直近5件のみ
                role = "ユーザー" if msg['role'] == 'user' else "AI"
                history_text += f"{role}: {msg['content']}\n\n"

        prompt = f"""あなたは経験豊富な社会保険労務士です。

【会社情報】
会社名: {company_name}

【現在の就業規則】
{regulation_text}

【会話履歴】
{history_text}

【ユーザーの質問/相談】
{user_message}

上記の質問/相談に対して、以下の方針で回答してください：

1. 質問の場合：就業規則の内容を参照して正確に回答
2. 修正/追加の相談の場合：
   - 具体的な修正案を提示
   - 法的根拠を説明
   - 修正が必要であれば、has_modification=trueとして提案内容を返す

以下のJSON形式で回答してください：
```json
{{
  "response": "ユーザーへの回答メッセージ",
  "has_modification": true/false,
  "modification": {{
    "article_number": "第XX条",
    "modification_type": "AI相談",
    "before_text": "現在の記載（新規追加の場合は空欄）",
    "after_text": "推奨する内容",
    "reason": "修正/追加が必要な理由"
  }}
}}
```

必ずJSON形式のみで回答してください。"""

        response = self._call_claude(prompt, max_tokens=4096)

        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response

            result = json.loads(json_str)
            return {
                "success": True,
                "response": result.get("response", ""),
                "has_modification": result.get("has_modification", False),
                "modification": result.get("modification")
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析エラー: {str(e)}",
                "raw_response": response
            }

    def structure_regulation_text(self, raw_text: str) -> dict:
        """OCRで抽出したテキストを構造化されたJSONに変換"""

        # テキストサイズに応じて処理方法を選択
        text_length = len(raw_text)

        # 50,000文字以下の場合は一括処理（Sonnet 4で処理可能）
        if text_length <= 50000:
            print(f"Claude API（Sonnet 4）でテキストを構造化しています（{text_length}文字）...")
            return self._structure_regulation_text_single(raw_text)
        else:
            # 50,000文字を超える場合のみ分割処理
            print(f"大規模テキスト（{text_length}文字）を分割処理します...")
            return self._structure_regulation_text_chunked(raw_text)

    def _structure_regulation_text_single(self, raw_text: str) -> dict:
        """単一のテキストを構造化"""

        prompt = f"""あなたは経験豊富な社会保険労務士です。

以下はPDFから抽出された就業規則のテキストです。このテキストを構造化されたJSON形式に変換してください。

【抽出されたテキスト】
{raw_text}

以下のJSON形式で出力してください：
```json
{{
  "regulation_name": "就業規則",
  "chapters": [
    {{
      "number": "第1章",
      "title": "総則",
      "articles": [
        {{
          "number": "第1条",
          "title": "目的",
          "content": ["この規則は、〜"],
          "items": [
            {{"number": "1", "text": "項目1の内容"}},
            {{"number": "2", "text": "項目2の内容"}}
          ]
        }}
      ]
    }}
  ]
}}
```

【絶対に守るべき重要な指示】
1. ★★★ すべての章、条、項を一つも省略せず、必ず全て抽出すること ★★★
2. ★★★ 第1章から最終章まで、第1条から最終条まで、すべて漏れなく含めること ★★★
3. 元のテキストの内容を正確に保持すること（要約や省略は絶対に禁止）
4. 章番号、条番号、項番号を正確に記録すること
5. 節（第1節、第2節など）がある場合も、その中のすべての条を含めること
6. 必ずJSON形式のみで回答してください（説明文は不要）

★重要★：情報の省略や削除は一切行わないでください。元のテキストにあるすべての章・条を含めてください。

必ずJSON形式のみで回答してください。"""

        # Sonnet 4で処理（高速・高精度）
        # 大規模文書対応のため、max_tokensを大きく設定
        response = self._call_claude(prompt, max_tokens=32000, model="claude-sonnet-4-20250514")

        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response

            result = json.loads(json_str)
            return {
                "success": True,
                "structure": result.get("chapters", [])
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析エラー: {str(e)}",
                "raw_response": response
            }

    def _structure_regulation_text_chunked(self, raw_text: str) -> dict:
        """大規模なテキストを分割して構造化（3分割処理）"""

        import re

        print(f"大規模文書（{len(raw_text)}文字）を分割処理します...")

        # ページマーカーで分割
        pages = re.split(r'### ページ \d+ ###', raw_text)
        pages = [p.strip() for p in pages if p.strip()]

        if not pages:
            return {"success": False, "error": "ページ分割に失敗しました"}

        # 3分割するための境界を計算
        total_pages = len(pages)
        chunk_size = max(1, total_pages // 3)

        chunks = [
            "\n\n".join(pages[0:chunk_size]),
            "\n\n".join(pages[chunk_size:chunk_size*2]),
            "\n\n".join(pages[chunk_size*2:])
        ]

        print(f"  - 全{total_pages}ページを3分割: {len(chunks[0])}, {len(chunks[1])}, {len(chunks[2])}文字")

        # 各チャンクを構造化
        all_chapters = []
        for i, chunk in enumerate(chunks, 1):
            if not chunk.strip():
                continue

            print(f"  - チャンク {i}/3 を構造化中...")

            prompt = f"""あなたは経験豊富な社会保険労務士です。

以下は就業規則の一部です。このテキストを構造化されたJSON形式に変換してください。

【抽出されたテキスト（第{i}部分）】
{chunk}

以下のJSON形式で出力してください：
```json
{{
  "chapters": [
    {{
      "number": "第X章",
      "title": "章タイトル",
      "articles": [
        {{
          "number": "第X条",
          "title": "条タイトル",
          "content": ["条文の内容"],
          "items": [
            {{"number": "1", "text": "項目1の内容"}},
            {{"number": "2", "text": "項目2の内容"}}
          ]
        }}
      ]
    }}
  ]
}}
```

重要な指示：
1. この部分に含まれるすべての章、条、項を漏れなく抽出すること
2. 元のテキストの内容を正確に保持すること
3. 章番号、条番号、項番号を正確に記録すること
4. 章が途中から始まっている場合でも、その章の内容を記録すること
5. 必ずJSON形式のみで回答してください（説明文は不要）

必ずJSON形式のみで回答してください。"""

            # Haiku 3.5で処理（高速・低コスト）
            response = self._call_claude(prompt, max_tokens=8192, model="claude-3-5-haiku-20241022")

            try:
                if "```json" in response:
                    json_start = response.find("```json") + 7
                    json_end = response.find("```", json_start)
                    json_str = response[json_start:json_end].strip()
                else:
                    json_str = response

                result = json.loads(json_str)
                chunk_chapters = result.get("chapters", [])

                print(f"    → {len(chunk_chapters)}章を抽出")
                all_chapters.extend(chunk_chapters)

            except json.JSONDecodeError as e:
                print(f"    → JSON解析エラー: {e}")
                continue

        # 章の重複を排除（同じ章番号が複数ある場合は結合）
        merged_chapters = self._merge_duplicate_chapters(all_chapters)

        print(f"  - 結合完了: 合計{len(merged_chapters)}章")

        return {
            "success": True,
            "structure": merged_chapters
        }

    def _merge_duplicate_chapters(self, chapters):
        """重複する章番号を結合"""
        chapter_dict = {}

        for chapter in chapters:
            chapter_num = chapter.get('number', '')

            if chapter_num in chapter_dict:
                # 既存の章に条を追加
                existing_articles = chapter_dict[chapter_num].get('articles', [])
                new_articles = chapter.get('articles', [])
                chapter_dict[chapter_num]['articles'] = existing_articles + new_articles
            else:
                chapter_dict[chapter_num] = chapter

        # リストに戻す（章番号順にソート）
        import re
        def extract_chapter_number(chapter):
            num_str = chapter.get('number', '第0章')
            # 漢数字を数値に変換
            match = re.search(r'第(.+?)章', num_str)
            if match:
                kanji_num = match.group(1)
                # 簡易的な漢数字→数値変換
                kanji_to_num = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                               '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
                return kanji_to_num.get(kanji_num, 0)
            return 0

        sorted_chapters = sorted(chapter_dict.values(), key=extract_chapter_number)
        return sorted_chapters

    def _structure_to_text(self, structure) -> str:
        """構造化データをテキストに変換"""
        text_parts = []
        
        # structureの型を判定
        if isinstance(structure, list):
            # 既にリストの場合
            chapters = structure
        elif isinstance(structure, dict):
            # 辞書の場合
            if "structure" in structure:
                chapters = structure["structure"]
            elif "chapters" in structure:
                chapters = structure["chapters"]
            else:
                chapters = []
        else:
            chapters = []
        
        for chapter in chapters:
            if not isinstance(chapter, dict):
                continue
                
            text_parts.append(f"\n{chapter.get('number', '')} {chapter.get('title', '')}\n")
            
            articles = chapter.get("articles", [])
            for article in articles:
                if not isinstance(article, dict):
                    continue
                    
                text_parts.append(f"\n{article.get('number', '')}（{article.get('title', '')}）")
                
                content = article.get("content", [])
                if isinstance(content, list):
                    for c in content:
                        text_parts.append(str(c))
                elif isinstance(content, str):
                    text_parts.append(content)
                
                items = article.get("items", [])
                for item in items:
                    if isinstance(item, dict):
                        text_parts.append(f"  {item.get('number', '')} {item.get('text', '')}")
                    else:
                        text_parts.append(f"  {item}")
        
        return "\n".join(text_parts)
