"""
Firestoreデータベースのバージョン情報を確認するスクリプト
バージョン番号の表示問題を調査
"""
import os
import json
from google.cloud import firestore

# Firestore直接アクセス
print("Connecting to Firestore...")
db_client = firestore.Client()

# 会社IDと規程IDを指定
company_id = "1"
regulation_id = "8ca6e5ad-ccaf-429b-9a00-ffbe1c6094cf"  # デプロイされているアプリから取得

print(f"\n=== 規程 {regulation_id} のバージョンデータ ===")

# Firestoreからバージョンデータを直接取得
versions_ref = db_client.collection('companies').document(company_id)\
    .collection('regulations').document(regulation_id)\
    .collection('versions')

# 全てのバージョンドキュメントを取得
docs = list(versions_ref.stream())

print(f"取得されたドキュメント数: {len(docs)}")
print("\nバージョン詳細:")

# バージョンデータを解析
version_data = []
for doc in docs:
    data = doc.to_dict()
    data['doc_id'] = doc.id
    version_data.append(data)

# version_numberでソート
version_data_sorted = sorted(version_data, key=lambda x: x.get('version_number', 0), reverse=True)

for i, ver in enumerate(version_data_sorted):
    version_num = ver.get('version_number', ver.get('version', 'N/A'))
    created_at = ver.get('created_at', 'N/A')
    doc_id = ver.get('doc_id', 'N/A')

    print(f"\n[{i}] version_number = {version_num}")
    print(f"    created_at = {created_at}")
    print(f"    doc_id = {doc_id}")
    print(f"    全キー: {list(ver.keys())}")

print(f"\n=== まとめ ===")
print(f"データベース内のバージョン番号: {[v.get('version_number', 'N/A') for v in version_data_sorted]}")
print(f"配列インデックス: {list(range(len(version_data_sorted)))}")
print(f"\n問題: UIは配列インデックス(0-based)を表示しているが、データベースは1-basedのバージョン番号を使用")
