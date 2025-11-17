"""
バージョン管理システムの本質的な改善
"""

# ========================================
# 1. データベース構造の再設計
# ========================================

"""
現在の問題：
- based_on_versionが活用されていない
- descriptionがNone
- 変更履歴が追跡できない
- どのバージョンから派生したか不明
"""

# 新しいバージョン保存構造
def save_regulation_content_v2(self, company_id, regulation_id, content_dict, version, 
                              raw_text=None, tables=None, based_on_version=None, 
                              description=None, changes=None):
    """
    改善されたバージョン保存
    
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
    """
    doc_ref = self.db.collection('companies').document(str(company_id))\
        .collection('regulations').document(str(regulation_id))\
        .collection('versions').document()
    
    # 変更の差分を計算
    if based_on_version and raw_text:
        base_content = self.get_regulation_content(company_id, regulation_id, version=based_on_version)
        if base_content:
            base_text = base_content.get('raw_text', '')
            # 差分を自動計算
            if not changes:
                changes = self._calculate_diff(base_text, raw_text)
    
    data = {
        'version_number': int(version),
        'content_json': json.dumps(content_dict, ensure_ascii=False) if content_dict else None,
        'raw_text': raw_text,
        'tables': json.dumps(tables, ensure_ascii=False) if tables else None,
        'created_by': 'user',  # または 'ai_suggestion', 'ai_structure_fix'
        'based_on_version': int(based_on_version) if based_on_version else None,
        'description': description or f"バージョン{version}",
        'changes': json.dumps(changes, ensure_ascii=False) if changes else None,
        'is_branch': based_on_version and based_on_version != (version - 1),  # 分岐かどうか
        'created_at': datetime.utcnow()
    }
    
    doc_ref.set(data)
    
    # current_versionを更新
    self.db.collection('companies').document(str(company_id))\
        .collection('regulations').document(str(regulation_id))\
        .update({'current_version': int(version)})
    
    return doc_ref.id

# ========================================
# 2. バージョン比較機能
# ========================================

def compare_versions(self, company_id, regulation_id, version1, version2):
    """2つのバージョンの差分を取得"""
    content1 = self.get_regulation_content(company_id, regulation_id, version=version1)
    content2 = self.get_regulation_content(company_id, regulation_id, version=version2)
    
    if not content1 or not content2:
        return None
    
    text1 = content1.get('raw_text', '')
    text2 = content2.get('raw_text', '')
    
    # difflib を使用した差分計算
    import difflib
    diff = difflib.unified_diff(
        text1.splitlines(keepends=True),
        text2.splitlines(keepends=True),
        fromfile=f'バージョン{version1}',
        tofile=f'バージョン{version2}',
        n=3
    )
    
    return {
        'version1': version1,
        'version2': version2,
        'diff': list(diff),
        'added_lines': self._count_added_lines(diff),
        'deleted_lines': self._count_deleted_lines(diff),
        'summary': self._generate_diff_summary(text1, text2)
    }

# ========================================
# 3. バージョンツリー構造
# ========================================

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
    
    return root_nodes

# ========================================
# 4. スマートマージ機能
# ========================================

def merge_versions(self, company_id, regulation_id, source_version, target_version, 
                   conflict_resolution='manual'):
    """
    2つのバージョンをマージ
    
    Args:
        conflict_resolution: 'manual', 'source_priority', 'target_priority'
    """
    source = self.get_regulation_content(company_id, regulation_id, version=source_version)
    target = self.get_regulation_content(company_id, regulation_id, version=target_version)
    
    if not source or not target:
        return None
    
    # 共通の祖先を見つける
    common_ancestor = self._find_common_ancestor(company_id, regulation_id, 
                                                source_version, target_version)
    
    if common_ancestor:
        # 3-way マージ
        ancestor_content = self.get_regulation_content(company_id, regulation_id, 
                                                      version=common_ancestor)
        merged_text = self._three_way_merge(
            ancestor_content.get('raw_text', ''),
            source.get('raw_text', ''),
            target.get('raw_text', ''),
            conflict_resolution
        )
    else:
        # 2-way マージ
        merged_text = self._two_way_merge(
            source.get('raw_text', ''),
            target.get('raw_text', ''),
            conflict_resolution
        )
    
    return {
        'merged_text': merged_text,
        'source_version': source_version,
        'target_version': target_version,
        'common_ancestor': common_ancestor,
        'conflicts': self._detect_conflicts(source, target)
    }

# ========================================
# 5. バージョン管理のベストプラクティス
# ========================================

class VersionManager:
    """バージョン管理の統合クラス"""
    
    def __init__(self, db):
        self.db = db
    
    def create_version_from_modification(self, regulation_id, modification_id, 
                                       base_version=None):
        """修正提案からバージョンを作成（正しい実装）"""
        
        regulation = self.db.get_regulation_by_id(regulation_id)
        company_id = regulation['company_id']
        
        # ベースバージョンが指定されていない場合は最新版を使用
        if base_version is None:
            base_version = regulation.get('current_version', 1)
        
        # ベースバージョンの内容を取得（重要！）
        base_content = self.db.get_regulation_content(
            company_id, regulation_id, version=base_version
        )
        
        if not base_content:
            raise ValueError(f"ベースバージョン {base_version} が見つかりません")
        
        # 修正を取得
        modification = self.db.get_modification_by_id(modification_id)
        
        # テキストに修正を適用
        original_text = base_content.get('raw_text', '')
        modified_text = self._apply_modification(original_text, modification)
        
        # 新バージョン番号
        new_version = regulation.get('current_version', 1) + 1
        
        # 変更内容を記録
        changes = [{
            'type': 'modify',
            'article_number': modification.get('article_number'),
            'before_text': modification.get('before_text'),
            'after_text': modification.get('after_text'),
            'reason': modification.get('reason')
        }]
        
        # 新バージョンとして保存
        self.db.save_regulation_content_v2(
            company_id=company_id,
            regulation_id=regulation_id,
            content_dict=None,
            version=new_version,
            raw_text=modified_text,
            tables=base_content.get('tables', []),
            based_on_version=base_version,
            description=f"{modification.get('article_number')}の修正（v{base_version}ベース）",
            changes=changes
        )
        
        return new_version
    
    def _apply_modification(self, text, modification):
        """テキストに修正を適用"""
        before = modification.get('before_text', '')
        after = modification.get('after_text', '')
        
        if before and before in text:
            # 単純な置換
            return text.replace(before, after, 1)
        else:
            # より高度なマッチング（記事番号ベース）
            article_num = modification.get('article_number')
            if article_num:
                # 記事を見つけて置換
                return self._replace_article(text, article_num, after)
            else:
                # 末尾に追加
                return text + f"\n\n{after}"
