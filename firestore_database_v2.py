"""
Firestoreデータベースのバージョン管理改善版
save_regulation_content_v2の実装と差分計算機能
"""

import json
from datetime import datetime
import difflib

# firestore_database.pyに追加する改善されたメソッド

class FirestoreDatabaseV2:
    """バージョン管理が改善されたFirestoreデータベース"""
    
    def save_regulation_content_v2(self, company_id, regulation_id, content_dict, version, 
                                  raw_text=None, tables=None, based_on_version=None, 
                                  description=None, changes=None, created_by='user'):
        """
        改善されたバージョン保存機能
        
        Args:
            changes: 変更内容のリスト
                [
                    {
                        "type": "modify",  # modify, add, delete
                        "article_number": "第23条",
                        "before_text": "元のテキスト",
                        "after_text": "新しいテキスト",
                        "reason": "変更理由"
                    }
                ]
            created_by: 作成者（'user', 'ai_modification', 'ai_structure_fix', 'manual_edit'）
        """
        doc_ref = self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .collection('versions').document()
        
        # 変更の差分を自動計算（changesが提供されていない場合）
        if based_on_version and raw_text and not changes:
            base_content = self.get_regulation_content(company_id, regulation_id, version=based_on_version)
            if base_content:
                base_text = base_content.get('raw_text', '')
                changes = self._calculate_diff(base_text, raw_text)
        
        # ブランチ判定（連続したバージョンではない場合）
        is_branch = False
        if based_on_version:
            is_branch = based_on_version != (version - 1)
        
        data = {
            'version_number': int(version),
            'content_json': json.dumps(content_dict, ensure_ascii=False) if content_dict else None,
            'raw_text': raw_text,
            'tables': json.dumps(tables, ensure_ascii=False) if tables else None,
            'created_by': created_by,
            'based_on_version': int(based_on_version) if based_on_version else None,
            'description': description or f"バージョン{version}",
            'changes': json.dumps(changes, ensure_ascii=False) if changes else None,
            'is_branch': is_branch,
            'created_at': datetime.utcnow()
        }
        
        doc_ref.set(data)
        
        # current_versionを更新
        self.db.collection('companies').document(str(company_id))\
            .collection('regulations').document(str(regulation_id))\
            .update({'current_version': int(version)})
        
        print(f"[保存成功] バージョン{version} - {description}")
        if is_branch:
            print(f"  ⚠️ ブランチバージョン（ベース: v{based_on_version}）")
        
        return doc_ref.id
    
    def _calculate_diff(self, text1, text2):
        """2つのテキストの差分を計算して変更リストを返す"""
        changes = []
        
        # 行単位での差分計算
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)
        
        differ = difflib.unified_diff(lines1, lines2, n=0)
        diff_lines = list(differ)
        
        # 差分から変更を抽出
        i = 0
        while i < len(diff_lines):
            line = diff_lines[i]
            
            if line.startswith('-') and not line.startswith('---'):
                # 削除された行
                deleted_lines = [line[1:]]
                j = i + 1
                while j < len(diff_lines) and diff_lines[j].startswith('-') and not diff_lines[j].startswith('---'):
                    deleted_lines.append(diff_lines[j][1:])
                    j += 1
                
                # 続く追加行を確認
                added_lines = []
                while j < len(diff_lines) and diff_lines[j].startswith('+') and not diff_lines[j].startswith('+++'):
                    added_lines.append(diff_lines[j][1:])
                    j += 1
                
                if added_lines:
                    # 修正
                    changes.append({
                        'type': 'modify',
                        'before_text': ''.join(deleted_lines).strip(),
                        'after_text': ''.join(added_lines).strip()
                    })
                else:
                    # 削除
                    changes.append({
                        'type': 'delete',
                        'before_text': ''.join(deleted_lines).strip(),
                        'after_text': ''
                    })
                
                i = j
            elif line.startswith('+') and not line.startswith('+++'):
                # 追加された行
                added_lines = [line[1:]]
                j = i + 1
                while j < len(diff_lines) and diff_lines[j].startswith('+') and not diff_lines[j].startswith('+++'):
                    added_lines.append(diff_lines[j][1:])
                    j += 1
                
                changes.append({
                    'type': 'add',
                    'before_text': '',
                    'after_text': ''.join(added_lines).strip()
                })
                
                i = j
            else:
                i += 1
        
        return changes
    
    def compare_versions(self, company_id, regulation_id, version1, version2):
        """2つのバージョンの差分を取得"""
        content1 = self.get_regulation_content(company_id, regulation_id, version=version1)
        content2 = self.get_regulation_content(company_id, regulation_id, version=version2)
        
        if not content1 or not content2:
            return None
        
        text1 = content1.get('raw_text', '')
        text2 = content2.get('raw_text', '')
        
        # difflib を使用した差分計算
        diff = list(difflib.unified_diff(
            text1.splitlines(keepends=True),
            text2.splitlines(keepends=True),
            fromfile=f'バージョン{version1}',
            tofile=f'バージョン{version2}',
            n=3
        ))
        
        # 統計情報を計算
        added_lines = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deleted_lines = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        # 変更箇所のサマリーを生成
        changes = self._calculate_diff(text1, text2)
        
        return {
            'version1': version1,
            'version2': version2,
            'diff': diff,
            'added_lines': added_lines,
            'deleted_lines': deleted_lines,
            'changes': changes,
            'summary': self._generate_diff_summary(changes)
        }
    
    def _generate_diff_summary(self, changes):
        """変更内容のサマリーを生成"""
        summary = {
            'total_changes': len(changes),
            'modifications': sum(1 for c in changes if c['type'] == 'modify'),
            'additions': sum(1 for c in changes if c['type'] == 'add'),
            'deletions': sum(1 for c in changes if c['type'] == 'delete')
        }
        
        # 主要な変更を抽出
        major_changes = []
        for change in changes[:5]:  # 最初の5件
            if change['type'] == 'modify':
                major_changes.append(f"修正: {change['before_text'][:30]}... → {change['after_text'][:30]}...")
            elif change['type'] == 'add':
                major_changes.append(f"追加: {change['after_text'][:50]}...")
            elif change['type'] == 'delete':
                major_changes.append(f"削除: {change['before_text'][:50]}...")
        
        summary['major_changes'] = major_changes
        return summary
    
    def get_version_tree(self, company_id, regulation_id):
        """バージョンの派生関係をツリー構造で取得"""
        versions = self.get_all_versions(company_id, regulation_id)
        
        # ツリー構造を構築
        tree = {}
        for v in versions:
            version_num = v.get('version_number')
            based_on = v.get('based_on_version')
            
            node = {
                'version': version_num,
                'based_on': based_on,
                'description': v.get('description'),
                'created_at': v.get('created_at'),
                'created_by': v.get('created_by', 'unknown'),
                'is_branch': v.get('is_branch', False),
                'children': []
            }
            
            tree[version_num] = node
        
        # 親子関係を構築
        root_nodes = []
        for version_num, node in tree.items():
            if node['based_on'] is None:
                root_nodes.append(node)
            else:
                parent = tree.get(node['based_on'])
                if parent:
                    parent['children'].append(node)
        
        return {
            'tree': tree,
            'root_nodes': root_nodes,
            'total_versions': len(versions),
            'branch_count': sum(1 for v in versions if v.get('is_branch', False))
        }
    
    def merge_versions(self, company_id, regulation_id, source_version, target_version, 
                       conflict_resolution='manual'):
        """
        2つのバージョンをマージ（将来の実装用）
        
        Args:
            conflict_resolution: 'manual', 'source_priority', 'target_priority'
        """
        # TODO: 実装予定
        pass
    
    def get_version_history_summary(self, company_id, regulation_id):
        """バージョン履歴のサマリーを取得"""
        versions = self.get_all_versions(company_id, regulation_id)
        
        summary = {
            'total_versions': len(versions),
            'latest_version': versions[0]['version_number'] if versions else 0,
            'first_created': versions[-1]['created_at'] if versions else None,
            'last_updated': versions[0]['created_at'] if versions else None,
            'version_list': []
        }
        
        for v in versions:
            summary['version_list'].append({
                'version': v.get('version_number'),
                'description': v.get('description'),
                'created_at': v.get('created_at'),
                'created_by': v.get('created_by', 'unknown'),
                'based_on': v.get('based_on_version'),
                'is_branch': v.get('is_branch', False)
            })
        
        return summary


# 既存のFirestoreDatabaseクラスに追加するメソッド
# ※実際の実装では、既存のfirestore_database.pyに上記メソッドを追加してください
