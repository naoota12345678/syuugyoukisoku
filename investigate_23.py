"""
Firestoreから規程データを取得して「23」がどこに出現しているか調査
"""

from firestore_database import FirestoreDatabase
import json

def investigate_23():
    """「23」という数字がどこに出現しているか調査"""
    db = FirestoreDatabase()

    # すべての会社を取得
    companies = db.get_all_companies()
    print(f"会社数: {len(companies)}")

    for company in companies:
        print(f"\n=== 会社: {company['name']} (ID: {company['id']}) ===")

        # この会社の規程を取得
        regulations = db.get_all_regulations(company['id'])
        print(f"規程数: {len(regulations)}")

        for regulation in regulations:
            print(f"\n--- 規程: {regulation.get('name', 'N/A')} (ID: {regulation['id']}) ---")

            # 最新バージョンのコンテンツを取得
            content = db.get_regulation_content(company['id'], regulation['id'])

            if not content:
                print("  コンテンツなし")
                continue

            # raw_textに「23」が含まれているか確認
            raw_text = content.get('raw_text', '')
            if '23' in raw_text:
                print(f"  ✓ raw_textに「23」が含まれています")

                # 「23」の周辺テキストを表示
                lines = raw_text.split('\n')
                for i, line in enumerate(lines):
                    if '23' in line:
                        print(f"    行{i+1}: {line}")
                        # 前後の行も表示
                        if i > 0:
                            print(f"    行{i}  (前): {lines[i-1]}")
                        if i < len(lines) - 1:
                            print(f"    行{i+2}(後): {lines[i+1]}")
                        print()

            # blocksに「23」が含まれているか確認
            blocks_str = content.get('blocks', '[]')
            if isinstance(blocks_str, str):
                try:
                    blocks = json.loads(blocks_str)
                except:
                    blocks = []
            else:
                blocks = blocks_str

            # 「23」を含むブロックを探す
            blocks_with_23 = [b for b in blocks if '23' in b.get('text', '')]

            if blocks_with_23:
                print(f"  ✓ blocksに「23」を含むブロックが{len(blocks_with_23)}個あります")

                for block in blocks_with_23:
                    print(f"\n  【ブロック情報】")
                    print(f"    テキスト: '{block['text']}'")
                    print(f"    ページ: {block.get('page', 'N/A')}")
                    print(f"    座標: x={block.get('x_min', 0)}-{block.get('x_max', 0)}, y={block.get('y_min', 0)}-{block.get('y_max', 0)}")
                    print(f"    中心座標: (x={block.get('x_center', 0)}, y={block.get('y_center', 0)})")
                    print(f"    サイズ: width={block.get('width', 0)}, height={block.get('height', 0)}")

                    # このブロックの前後のブロックも確認
                    block_index = blocks.index(block)
                    print(f"    ブロック番号: {block_index + 1} / {len(blocks)}")

                    if block_index > 0:
                        prev_block = blocks[block_index - 1]
                        print(f"    前のブロック: '{prev_block.get('text', '')}' (page={prev_block.get('page', 'N/A')})")

                    if block_index < len(blocks) - 1:
                        next_block = blocks[block_index + 1]
                        print(f"    次のブロック: '{next_block.get('text', '')}' (page={next_block.get('page', 'N/A')})")

if __name__ == "__main__":
    investigate_23()
