"""
Firestoreのcurrent_versionを手動で更新するスクリプト
"""
import os
from firebase_admin import credentials, firestore, initialize_app

# Firebase初期化
try:
    initialize_app()
except:
    pass

db = firestore.client()

# regulation IDを指定
regulation_id = "KrarWpZYZ4i8mpJKg25m"

# regulationドキュメントを検索
companies = db.collection('companies').stream()

for company in companies:
    company_id = company.id
    regulation_ref = db.collection('companies').document(company_id).collection('regulations').document(regulation_id)
    regulation = regulation_ref.get()

    if regulation.exists:
        print(f"Found regulation in company: {company_id}")
        current_data = regulation.to_dict()
        print(f"Current version: {current_data.get('current_version')}")

        # current_versionを3に更新
        regulation_ref.update({
            'current_version': 3
        })

        print(f"Updated current_version to 3")

        # 確認
        updated = regulation_ref.get().to_dict()
        print(f"New current_version: {updated.get('current_version')}")
        break
