# firestore_database.py
"""FirestoreをバックエンドとしたDatabase クラス（SQLiteと同じインターフェース）"""

from google.cloud import firestore
from datetime import datetime
import json
from typing import Dict, List, Optional

class FirestoreDatabase:
    """Firestoreを使ったデータベースクラス（database.pyと互換性あり）"""

    def __init__(self, project_id=None):
        """Firestoreクライアントを初期化"""
        self.db = firestore.Client(project=project_id)
        print(f"Firestore initialized (project: {project_id or 'default'})")

    # ===== 会社関連 =====
    def create_company(self, name, address=None):
        """会社を登録"""
        doc_ref = self.db.collection('companies').document()
        data = {
            'name': name,
            'address': address,
            'created_at': datetime.utcnow()
        }
        doc_ref.set(data)
        return doc_ref.id

    def get_company(self, company_id):
        """会社情報を取得"""
        doc = self.db.collection('companies').document(str(company_id)).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def get_all_companies(self):
        """全ての会社を取得"""
        companies = []
        docs = self.db.collection('companies').order_by('name').stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            companies.append(data)
        return companies

    # ===== 規程関連 =====
    def create_regulation(self, company_id, reg_type, name, source_type, original_filename=None):
        """規程を登録"""
        doc_ref = self.db.collection('regulations').document()
        data = {
            'company_id': str(company_id),
            'type': reg_type,
            'name': name,
            'status': 'draft',
            'source_type': source_type,
            'original_filename': original_filename,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        doc_ref.set(data)
        return doc_ref.id

    def get_regulation(self, regulation_id):
        """規程情報を取得"""
        doc = self.db.collection('regulations').document(str(regulation_id)).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            # datetimeをstrに変換
            if 'created_at' in data and isinstance(data['created_at'], datetime):
                data['created_at'] = data['created_at'].isoformat()
            if 'updated_at' in data and isinstance(data['updated_at'], datetime):
                data['updated_at'] = data['updated_at'].isoformat()
            return data
        return None

    def get_company_regulations(self, company_id):
        """会社の全規程を取得"""
        regulations = []
        docs = self.db.collection('regulations')\
            .where('company_id', '==', str(company_id))\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            # datetimeをstrに変換
            if 'created_at' in data and isinstance(data['created_at'], datetime):
                data['created_at'] = data['created_at'].isoformat()
            if 'updated_at' in data and isinstance(data['updated_at'], datetime):
                data['updated_at'] = data['updated_at'].isoformat()
            regulations.append(data)
        return regulations

    def update_regulation_status(self, regulation_id, status):
        """規程のステータスを更新"""
        doc_ref = self.db.collection('regulations').document(str(regulation_id))
        doc_ref.update({
            'status': status,
            'updated_at': datetime.utcnow()
        })

    # ===== 規程内容関連 =====
    def save_regulation_content(self, regulation_id, content_dict, version=1, raw_text=None, tables=None):
        """規程内容を保存（JSON形式 + 生テキスト + 表データ）"""
        doc_ref = self.db.collection('regulation_content').document()
        data = {
            'regulation_id': str(regulation_id),
            'content_json': content_dict,  # Firestoreは直接dictを保存可能
            'raw_text': raw_text,
            'tables': tables,  # Firestoreは直接listを保存可能
            'version': version,
            'created_at': datetime.utcnow()
        }
        doc_ref.set(data)

    def get_regulation_content(self, regulation_id, version=None):
        """規程内容を取得（表データを含む）"""
        query = self.db.collection('regulation_content')\
            .where('regulation_id', '==', str(regulation_id))

        if version:
            query = query.where('version', '==', version)

        query = query.order_by('version', direction=firestore.Query.DESCENDING).limit(1)

        docs = list(query.stream())
        if docs:
            data = docs[0].to_dict()
            data['id'] = docs[0].id
            # content_jsonはFirestoreから直接dictとして取得
            # tablesもFirestoreから直接listとして取得（存在しない場合は空リスト）
            if 'tables' not in data or data['tables'] is None:
                data['tables'] = []
            return data
        return None

    # ===== 修正提案関連 =====
    def create_modification(self, regulation_id, article_number, mod_type,
                          before_text, after_text, reason):
        """修正提案を作成"""
        doc_ref = self.db.collection('modifications').document()
        data = {
            'regulation_id': str(regulation_id),
            'article_number': article_number,
            'modification_type': mod_type,
            'before_text': before_text,
            'after_text': after_text,
            'reason': reason,
            'status': 'pending',
            'applied_at': None,
            'created_at': datetime.utcnow()
        }
        doc_ref.set(data)
        return doc_ref.id

    def get_pending_modifications(self, regulation_id):
        """未適用の修正提案を取得"""
        modifications = []
        docs = self.db.collection('modifications')\
            .where('regulation_id', '==', str(regulation_id))\
            .where('status', '==', 'pending')\
            .order_by('created_at')\
            .stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            modifications.append(data)
        return modifications

    def apply_modification(self, modification_id):
        """修正を適用"""
        doc_ref = self.db.collection('modifications').document(str(modification_id))
        doc_ref.update({
            'status': 'applied',
            'applied_at': datetime.utcnow()
        })

    def reject_modification(self, modification_id):
        """修正を却下"""
        doc_ref = self.db.collection('modifications').document(str(modification_id))
        doc_ref.update({
            'status': 'rejected',
            'applied_at': datetime.utcnow()
        })

    def get_modification(self, modification_id):
        """特定の修正を取得"""
        doc = self.db.collection('modifications').document(str(modification_id)).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def get_modification_history(self, regulation_id):
        """修正履歴を取得"""
        modifications = []
        docs = self.db.collection('modifications')\
            .where('regulation_id', '==', str(regulation_id))\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            modifications.append(data)
        return modifications

    def get_latest_version(self, regulation_id):
        """最新のバージョン番号を取得"""
        docs = list(self.db.collection('regulation_content')\
            .where('regulation_id', '==', str(regulation_id))\
            .order_by('version', direction=firestore.Query.DESCENDING)\
            .limit(1)\
            .stream())

        if docs:
            return docs[0].to_dict().get('version', 0)
        return 0

    # ===== 検証結果関連 =====
    def save_validation_result(self, regulation_id, model_used, issues_count):
        """検証結果を保存"""
        doc_ref = self.db.collection('validation_results').document()
        data = {
            'regulation_id': str(regulation_id),
            'model_used': model_used,
            'issues_count': issues_count,
            'validation_date': datetime.utcnow()
        }
        doc_ref.set(data)

    def get_validation_history(self, regulation_id):
        """検証履歴を取得"""
        results = []
        docs = self.db.collection('validation_results')\
            .where('regulation_id', '==', str(regulation_id))\
            .order_by('validation_date', direction=firestore.Query.DESCENDING)\
            .stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            results.append(data)
        return results

    # ===== 追加メソッド（app.pyで使用） =====
    def get_all_versions(self, regulation_id):
        """特定の規程の全バージョンを取得"""
        versions = []
        docs = self.db.collection('regulation_content')\
            .where('regulation_id', '==', str(regulation_id))\
            .order_by('version', direction=firestore.Query.DESCENDING)\
            .stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            # datetimeをstrに変換
            if 'created_at' in data and isinstance(data['created_at'], datetime):
                data['created_at'] = data['created_at'].isoformat()
            versions.append(data)
        return versions

    def update_regulation(self, regulation_id, updates):
        """規程情報を更新"""
        doc_ref = self.db.collection('regulations').document(str(regulation_id))
        updates['updated_at'] = datetime.utcnow()
        doc_ref.update(updates)

    def get_companies_with_regulation_count(self):
        """会社一覧を規程数と共に取得"""
        companies = []
        company_docs = self.db.collection('companies').stream()

        for company_doc in company_docs:
            company_data = company_doc.to_dict()
            company_data['id'] = company_doc.id

            # 各会社の規程数を取得
            regulation_count = len(list(
                self.db.collection('regulations')
                .where('company_id', '==', company_doc.id)
                .stream()
            ))
            company_data['regulation_count'] = regulation_count
            companies.append(company_data)

        return sorted(companies, key=lambda x: x['id'], reverse=True)

    def delete_company(self, company_id):
        """会社を削除"""
        self.db.collection('companies').document(str(company_id)).delete()
