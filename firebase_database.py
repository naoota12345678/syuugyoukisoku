# firebase_database.py
"""Firebase Admin SDKを使った透明性の高いDatabaseクラス"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json
import os
from typing import Dict, List, Optional

class FirebaseDatabase:
    """
    Firebase Admin SDKを使ったデータベースクラス

    構造:
    companies/{companyId}
      └─ regulations/{regulationId} (サブコレクション)
           └─ versions/{versionId} (サブコレクション)
           │    └─ applied_changes/{changeId} (サブコレクション)
           └─ modifications/{modificationId} (サブコレクション)
           └─ validation_results/{validationId} (サブコレクション)
    """

    _initialized = False

    def __init__(self, project_id=None):
        """Firebase Admin SDKを初期化"""
        if not FirebaseDatabase._initialized:
            try:
                # 環境変数からサービスアカウントキーを取得
                cred_data = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

                if cred_data:
                    # JSONファイルパスかJSON文字列かを判定
                    if cred_data.strip().startswith('{'):
                        # JSON文字列の場合（Secret Managerから直接読み込まれた場合）
                        import json
                        cred_dict = json.loads(cred_data)
                        cred = credentials.Certificate(cred_dict)
                        firebase_admin.initialize_app(cred, {
                            'projectId': project_id or 'syuugyoukisoku'
                        })
                        print(f"✅ Firebase Admin SDK initialized with service account JSON (project: {cred_dict.get('project_id')})")
                    elif os.path.exists(cred_data):
                        # ファイルパスの場合
                        cred = credentials.Certificate(cred_data)
                        firebase_admin.initialize_app(cred, {
                            'projectId': project_id or 'syuugyoukisoku'
                        })
                        print(f"✅ Firebase Admin SDK initialized with service account file: {cred_data}")
                    else:
                        # デフォルト認証にフォールバック
                        firebase_admin.initialize_app(options={
                            'projectId': project_id or 'syuugyoukisoku'
                        })
                        print(f"✅ Firebase Admin SDK initialized with default credentials (project: {project_id or 'syuugyoukisoku'})")
                else:
                    # デフォルト認証（Cloud Run環境など）
                    firebase_admin.initialize_app(options={
                        'projectId': project_id or 'syuugyoukisoku'
                    })
                    print(f"✅ Firebase Admin SDK initialized with default credentials (project: {project_id or 'syuugyoukisoku'})")

                FirebaseDatabase._initialized = True
            except ValueError as e:
                # すでに初期化済みの場合
                if "The default Firebase app already exists" in str(e):
                    print("⚠️ Firebase Admin SDK already initialized")
                else:
                    raise

        self.db = firestore.client()
        print(f"📊 Firestore client ready (project: {project_id or 'default'})")

    # ===== 会社関連 =====
    def create_company(self, name, address=None):
        """会社を登録"""
        doc_ref = self.db.collection('companies').document()
        data = {
            'name': name,
            'address': address,
            'regulation_count': 0,
            'created_at': datetime.utcnow()
        }
        doc_ref.set(data)
        print(f"✅ 会社を作成: {name} (ID: {doc_ref.id})")
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
        docs = self.db.collection('companies').stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            companies.append(data)
        print(f"📋 取得した会社数: {len(companies)}")
        return sorted(companies, key=lambda x: x.get('name', ''))

    def get_companies_with_regulation_count(self):
        """会社一覧を規程数と共に取得（regulation_countフィールドを使用）"""
        companies = []
        docs = self.db.collection('companies').stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            # regulation_count フィールドを使用（非正規化）
            if 'regulation_count' not in data:
                data['regulation_count'] = 0
            companies.append(data)
        print(f"📋 取得した会社数: {len(companies)}")
        return sorted(companies, key=lambda x: x.get('name', ''))

    def delete_company(self, company_id):
        """会社を削除"""
        self.db.collection('companies').document(str(company_id)).delete()
        print(f"🗑️ 会社を削除: {company_id}")

    # ===== 規程関連 =====
    def create_regulation(self, company_id, reg_type, name, source_type, original_filename=None):
        """規程を登録（サブコレクションとして）"""
        # 会社情報を取得（company_name を非正規化して保存）
        company = self.get_company(company_id)
        company_name = company['name'] if company else ''

        # regulations サブコレクションに追加
        doc_ref = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document()

        data = {
            'name': name,
            'type': reg_type,
            'status': 'draft',
            'source_type': source_type,
            'original_filename': original_filename,
            'company_id': str(company_id),  # 逆参照用
            'company_name': company_name,  # 非正規化
            'current_version': 0,  # 最新バージョン番号
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        doc_ref.set(data)

        # 会社の regulation_count を増やす
        self.db.collection('companies').document(str(company_id)).update({
            'regulation_count': firestore.Increment(1)
        })

        print(f"✅ 規程を作成: {name} (ID: {doc_ref.id}, Company: {company_name})")
        return doc_ref.id

    def get_regulation(self, company_id, regulation_id):
        """規程情報を取得"""
        doc = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id)).get()
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

    def get_regulation_by_id(self, regulation_id):
        """規程IDのみで規程を検索（Collection Groupクエリ使用）"""
        # regulations コレクショングループから全てのregulationsを検索
        docs = self.db.collection_group('regulations').stream()

        for doc in docs:
            if doc.id == str(regulation_id):
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
        docs = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').stream()

        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            # datetimeをstrに変換
            if 'created_at' in data and isinstance(data['created_at'], datetime):
                data['created_at'] = data['created_at'].isoformat()
            if 'updated_at' in data and isinstance(data['updated_at'], datetime):
                data['updated_at'] = data['updated_at'].isoformat()
            regulations.append(data)

        # created_atでソート（アプリ側でソート、インデックス不要）
        return sorted(regulations, key=lambda x: x.get('created_at', ''), reverse=True)

    def update_regulation_status(self, company_id, regulation_id, status):
        """規程のステータスを更新"""
        doc_ref = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))
        doc_ref.update({
            'status': status,
            'updated_at': datetime.utcnow()
        })
        print(f"📝 規程ステータス更新: {regulation_id} → {status}")

    def update_regulation(self, company_id, regulation_id, updates):
        """規程情報を更新"""
        doc_ref = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))
        updates['updated_at'] = datetime.utcnow()
        doc_ref.update(updates)
        print(f"📝 規程情報更新: {regulation_id}")

    # ===== 規程内容（バージョン）関連 =====
    def save_regulation_content(self, company_id, regulation_id, content_dict, version=1, raw_text=None, tables=None, based_on_version=None, description=None):
        """規程内容を保存（バージョンとして）"""
        # versions サブコレクションに追加
        doc_ref = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('versions').document()

        data = {
            'version_number': version,
            'content_json': json.dumps(content_dict, ensure_ascii=False) if content_dict else None,
            'raw_text': raw_text,
            'tables': json.dumps(tables, ensure_ascii=False) if tables else None,
            'created_by': 'upload',  # 'upload' or 'modifications'
            'source_modification_ids': [],  # このバージョンを作成した修正IDリスト
            'based_on_version': based_on_version,  # どのバージョンから作成されたか
            'description': description,  # バージョンの説明文
            'created_at': datetime.utcnow()
        }
        doc_ref.set(data)

        # 規程の current_version を更新
        self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .update({'current_version': version})

        print(f"✅ 規程内容を保存: Version {version} (ID: {doc_ref.id})")
        return doc_ref.id

    def get_regulation_content(self, company_id, regulation_id, version=None):
        """規程内容を取得"""
        versions_ref = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('versions')

        if version:
            # 特定バージョンを取得
            docs = list(versions_ref.where('version_number', '==', version).limit(1).stream())
        else:
            # 最新バージョンを取得（アプリ側でソート）
            all_docs = list(versions_ref.stream())
            docs = sorted(all_docs, key=lambda d: d.to_dict().get('version_number', 0), reverse=True)[:1]

        if docs:
            data = docs[0].to_dict()
            data['id'] = docs[0].id
            # JSON文字列をパース
            if 'content_json' in data and data['content_json']:
                data['content_json'] = json.loads(data['content_json'])
            if 'tables' in data and data['tables']:
                data['tables'] = json.loads(data['tables'])
            else:
                data['tables'] = []
            return data
        return None

    def get_latest_version(self, company_id, regulation_id):
        """最新のバージョン番号を取得"""
        docs = list(self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('versions').stream())

        if docs:
            versions = [d.to_dict().get('version_number', 0) for d in docs]
            return max(versions) if versions else 0
        return 0

    def get_all_versions(self, company_id, regulation_id):
        """特定の規程の全バージョンを取得"""
        versions = []
        docs = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('versions').stream()

        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            # datetimeをstrに変換
            if 'created_at' in data and isinstance(data['created_at'], datetime):
                data['created_at'] = data['created_at'].isoformat()
            versions.append(data)

        # version_number でソート（アプリ側でソート）
        return sorted(versions, key=lambda x: x.get('version_number', 0), reverse=True)

    # ===== 修正提案関連 =====
    def create_modification(self, company_id, regulation_id, article_number, mod_type,
                          before_text, after_text, reason, target_version=None):
        """修正提案を作成"""
        doc_ref = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('modifications').document()

        data = {
            'target_version': target_version or 1,  # どのバージョンへの修正か
            'article_number': article_number,
            'modification_type': mod_type,
            'before_text': before_text,
            'after_text': after_text,
            'reason': reason,
            'status': 'pending',  # 'pending', 'applied', 'rejected'
            'applied_in_version': None,  # 適用されたバージョン番号
            'applied_at': None,
            'rejected_at': None,
            'rejection_reason': None,
            'created_at': datetime.utcnow()
        }
        doc_ref.set(data)
        print(f"✅ 修正提案を作成: {article_number} - {mod_type}")
        return doc_ref.id

    def get_pending_modifications(self, company_id, regulation_id):
        """未適用の修正提案を取得"""
        modifications = []
        docs = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('modifications').where('status', '==', 'pending').stream()

        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            modifications.append(data)

        # created_at でソート（アプリ側）
        return sorted(modifications, key=lambda x: x.get('created_at', datetime.min))

    def apply_modification(self, company_id, regulation_id, modification_id, applied_in_version):
        """修正を適用"""
        doc_ref = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('modifications').document(str(modification_id))

        doc_ref.update({
            'status': 'applied',
            'applied_in_version': applied_in_version,
            'applied_at': datetime.utcnow()
        })
        print(f"✅ 修正を適用: {modification_id}")

    def reject_modification(self, company_id, regulation_id, modification_id, rejection_reason=''):
        """修正を却下"""
        doc_ref = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('modifications').document(str(modification_id))

        doc_ref.update({
            'status': 'rejected',
            'rejected_at': datetime.utcnow(),
            'rejection_reason': rejection_reason
        })
        print(f"⛔ 修正を却下: {modification_id}")

    def get_modification(self, company_id, regulation_id, modification_id):
        """特定の修正を取得"""
        doc = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('modifications').document(str(modification_id)).get()

        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def get_modification_history(self, company_id, regulation_id):
        """修正履歴を取得（全て：適用済み・未適用・却下）"""
        modifications = []
        docs = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('modifications').stream()

        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            modifications.append(data)

        # created_at でソート（アプリ側、降順）
        return sorted(modifications, key=lambda x: x.get('created_at', datetime.min), reverse=True)

    # ===== 検証結果関連 =====
    def save_validation_result(self, company_id, regulation_id, model_used, issues_count, issues=None):
        """検証結果を保存"""
        doc_ref = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('validation_results').document()

        data = {
            'model_used': model_used,
            'issues_count': issues_count,
            'issues': json.dumps(issues, ensure_ascii=False) if issues else None,
            'validation_date': datetime.utcnow()
        }
        doc_ref.set(data)
        print(f"✅ 検証結果を保存: {issues_count}件の問題")

    def get_validation_history(self, company_id, regulation_id):
        """検証履歴を取得"""
        results = []
        docs = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('validation_results').stream()

        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            results.append(data)

        # validation_date でソート（アプリ側、降順）
        return sorted(results, key=lambda x: x.get('validation_date', datetime.min), reverse=True)
