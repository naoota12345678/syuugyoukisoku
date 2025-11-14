"""
第72条のOCR生データを確認するスクリプト
"""
import os
import sys
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Firebase Admin SDK初期化
os.environ['USE_FIREBASE'] = '1'

from firebase_database import FirebaseDatabase

db = FirebaseDatabase()

# 規程IDを指定（ブラウザのURLから取得）
regulation_id = input("規程ID (fL48oIEAISFyF2mo8i3o など): ")
company_id = "Hh9epYKQAa80qf4jgYES"  # ダイトクの会社ID

# 規程情報を取得
regulation = db.get_regulation_by_id(regulation_id)
if not regulation:
    print("規程が見つかりません")
    sys.exit(1)

print(f"規程名: {regulation['name']}")
print(f"現在のバージョン: {regulation.get('current_version', 1)}")

# 全バージョンを取得
versions = db.get_all_versions(company_id, regulation_id)
print(f"\n全バージョン数: {len(versions)}")

# 最初のバージョン（OCR直後）を取得
if versions:
    first_version = min(versions, key=lambda v: v['version_number'])
    print(f"\n=== バージョン {first_version['version_number']} (OCR直後) ===")
    print(f"作成日時: {first_version.get('created_at', 'N/A')}")

    raw_text = first_version.get('raw_text', '')

    # 第72条周辺を抽出
    if '第72条' in raw_text:
        lines = raw_text.split('\n')
        for i, line in enumerate(lines):
            if '第72条' in line:
                print(f"\n第72条の位置: {i}行目")
                print("\n----- 第72条周辺のテキスト (前後30行) -----")
                start = max(0, i - 5)
                end = min(len(lines), i + 30)
                for j in range(start, end):
                    print(f"{j:3d}: {lines[j]}")
                break
    else:
        print("第72条が見つかりません")
        print(f"\nraw_textの最初の500文字:\n{raw_text[:500]}")
