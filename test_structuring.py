# test_structuring.py - Claude API構造化テスト
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import Database
from claude_validator import ClaudeValidator

def test_structuring():
    """保存済みのraw_textを使ってClaude API構造化をテスト"""

    print("=" * 60)
    print("Claude API 構造化診断テスト")
    print("=" * 60)

    # 1. データベースから最新のregulationを取得
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT regulation_id, raw_text, content_json
        FROM regulation_content
        ORDER BY regulation_id DESC
        LIMIT 1
    ''')

    row = cursor.fetchone()
    conn.close()

    if not row:
        print("[X] データベースにデータが見つかりません")
        return

    regulation_id, raw_text, content_json = row

    print(f"\n[1] データベース確認")
    print(f"   regulation_id: {regulation_id}")
    print(f"   raw_text長さ: {len(raw_text) if raw_text else 0}文字")
    print(f"   content_json: {content_json[:100] if content_json else 'None'}...")

    # 2. Validatorの初期化テスト
    print(f"\n[2] Validator初期化テスト")
    try:
        validator = ClaudeValidator()
        print("   [OK] Validator初期化成功")
    except Exception as e:
        print(f"   [X] Validator初期化失敗: {e}")
        return

    # 3. raw_textの検証
    print(f"\n[3] raw_text検証")
    if not raw_text:
        print("   [X] raw_textが空です")
        return

    print(f"   [OK] raw_text存在: {len(raw_text)}文字")
    print(f"   最初の500文字:")
    print("   " + "-" * 50)
    print("   " + raw_text[:500].replace("\n", "\n   "))
    print("   " + "-" * 50)

    # 4. Claude API構造化テスト
    print(f"\n[4] Claude API構造化実行")
    print("   Claude APIを呼び出しています...")

    try:
        result = validator.structure_regulation_text(raw_text)

        if result['success']:
            structure = result['structure']
            print(f"   [OK] 構造化成功: {len(structure)}章")

            # 最初の章を表示
            if structure:
                first_chapter = structure[0]
                print(f"\n   最初の章:")
                print(f"   - number: {first_chapter.get('number')}")
                print(f"   - title: {first_chapter.get('title')}")
                print(f"   - 条数: {len(first_chapter.get('articles', []))}")

                if first_chapter.get('articles'):
                    first_article = first_chapter['articles'][0]
                    print(f"\n   最初の条:")
                    print(f"   - number: {first_article.get('number')}")
                    print(f"   - title: {first_article.get('title')}")
        else:
            print(f"   [X] 構造化失敗: {result.get('error')}")
            if 'raw_response' in result:
                print(f"\n   Claude APIの生レスポンス（最初の1000文字）:")
                print("   " + "-" * 50)
                print("   " + result['raw_response'][:1000].replace("\n", "\n   "))
                print("   " + "-" * 50)

    except Exception as e:
        print(f"   [X] 例外発生: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)

if __name__ == "__main__":
    test_structuring()
