# app.pyに追加する修正提案保存機能（バージョン管理対応版）

@app.route('/api/save_modification/<modification_id>', methods=['POST'])
def save_modification(modification_id):
    """個別の修正提案を適用して新バージョンとして保存（正しいバージョン管理版）"""
    try:
        # リクエストデータから表示中のバージョンを取得（重要！）
        data = request.json
        viewing_version = data.get('viewing_version')
        
        # 修正提案を取得
        modification = db.get_modification_by_id(modification_id)
        if not modification:
            return jsonify({"success": False, "error": "修正提案が見つかりません"}), 404
        
        regulation_id = modification.get('regulation_id')
        regulation = db.get_regulation_by_id(regulation_id)
        if not regulation:
            return jsonify({"success": False, "error": "規程が見つかりません"}), 404
        
        company_id = regulation.get('company_id')
        
        # ユーザーが表示していたバージョンのデータを取得（最重要！）
        if viewing_version:
            print(f"[DEBUG] ユーザーが表示していたバージョン: {viewing_version}")
            content_data = db.get_regulation_content(company_id, regulation_id, version=viewing_version)
        else:
            # viewing_versionが指定されていない場合は最新版（互換性のため）
            print("[WARNING] viewing_versionが指定されていません。最新版を使用します。")
            content_data = db.get_regulation_content(company_id, regulation_id)
            viewing_version = content_data.get('version_number') if content_data else regulation.get('current_version', 1)
        
        if not content_data:
            return jsonify({"success": False, "error": f"バージョン{viewing_version}の内容が見つかりません"}), 404
        
        # 表示していたバージョンのテキストを取得（ここが重要！）
        raw_text = content_data.get('raw_text', '')
        tables = content_data.get('tables', [])
        
        print(f"[DEBUG] ベーステキストの長さ: {len(raw_text)}文字")
        
        # 修正を適用
        before_text = modification.get('before_text', '')
        after_text = modification.get('after_text', '')
        
        # テキストを置換
        if before_text and before_text in raw_text:
            modified_text = raw_text.replace(before_text, after_text, 1)
            print(f"[DEBUG] テキストを置換しました")
        else:
            # before_textが見つからない場合
            print(f"[WARNING] before_textが見つかりません。記事番号で検索します。")
            article_number = modification.get('article_number', '')
            if article_number:
                # 記事番号ベースで置換を試みる
                modified_text = apply_modification_by_article(raw_text, article_number, after_text)
            else:
                # 末尾に追加
                modified_text = raw_text + f"\n\n{after_text}"
                print(f"[DEBUG] テキストを末尾に追加しました")
        
        # 新バージョン番号（current_version + 1）
        current_version = regulation.get('current_version', 1)
        new_version = current_version + 1
        
        # 説明文を生成（詳細に）
        article_number = modification.get('article_number', '')
        mod_type = modification.get('modification_type', '修正')
        if viewing_version != current_version:
            description = f"{article_number}の{mod_type}（バージョン{viewing_version}から派生）"
        else:
            description = f"{article_number}の{mod_type}"
        
        print(f"[DEBUG] 新バージョン{new_version}を作成: {description}")
        
        # 新バージョンとして保存
        version_id = db.save_regulation_content(
            company_id=company_id,
            regulation_id=regulation_id,
            content_dict=None,
            version=new_version,
            raw_text=modified_text,
            tables=tables,
            based_on_version=viewing_version,  # 重要：表示していたバージョンを記録
            description=description
        )
        
        # 修正提案のステータスを更新
        if hasattr(db, 'apply_modification'):
            db.apply_modification(company_id, regulation_id, modification_id, new_version)
        
        print(f"[SUCCESS] バージョン{new_version}を作成しました（ベース: v{viewing_version}）")
        
        return jsonify({
            "success": True,
            "message": f"バージョン{new_version}として保存しました",
            "new_version": new_version,
            "based_on_version": viewing_version,
            "description": description
        })
        
    except Exception as e:
        print(f"[ERROR] 修正保存エラー: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


def apply_modification_by_article(text, article_number, new_text):
    """記事番号ベースで修正を適用"""
    import re
    
    # 記事番号のパターンを検索
    patterns = [
        rf'({article_number}\s*\n[^第]*?)(?=\n\s*第|\Z)',  # 第X条の形式
        rf'({article_number}[^\n]*\n[^第]*?)(?=\n\s*第|\Z)',  # その他の形式
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if match:
            # 記事全体を新しいテキストで置換
            return text.replace(match.group(1), new_text)
    
    # 見つからない場合は末尾に追加
    return text + f"\n\n{new_text}"


@app.route('/api/compare_versions/<regulation_id>', methods=['POST'])
def compare_versions(regulation_id):
    """2つのバージョンを比較"""
    try:
        data = request.json
        version1 = data.get('version1')
        version2 = data.get('version2')
        
        if not version1 or not version2:
            return jsonify({"success": False, "error": "比較するバージョンを指定してください"}), 400
        
        regulation = db.get_regulation_by_id(regulation_id)
        if not regulation:
            return jsonify({"success": False, "error": "規程が見つかりません"}), 404
        
        company_id = regulation.get('company_id')
        
        # 両バージョンの内容を取得
        content1 = db.get_regulation_content(company_id, regulation_id, version=version1)
        content2 = db.get_regulation_content(company_id, regulation_id, version=version2)
        
        if not content1 or not content2:
            return jsonify({"success": False, "error": "バージョンが見つかりません"}), 404
        
        # テキストの差分を計算
        text1 = content1.get('raw_text', '')
        text2 = content2.get('raw_text', '')
        
        import difflib
        diff = list(difflib.unified_diff(
            text1.splitlines(keepends=True),
            text2.splitlines(keepends=True),
            fromfile=f'バージョン{version1}',
            tofile=f'バージョン{version2}',
            n=3
        ))
        
        # 追加・削除行数を計算
        added_lines = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deleted_lines = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        return jsonify({
            "success": True,
            "diff": diff,
            "added_lines": added_lines,
            "deleted_lines": deleted_lines,
            "version1": version1,
            "version2": version2
        })
        
    except Exception as e:
        print(f"[ERROR] バージョン比較エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/version_tree/<regulation_id>')
def get_version_tree(regulation_id):
    """バージョンツリーを取得"""
    try:
        regulation = db.get_regulation_by_id(regulation_id)
        if not regulation:
            return jsonify({"success": False, "error": "規程が見つかりません"}), 404
        
        company_id = regulation.get('company_id')
        versions = db.get_all_versions(company_id, regulation_id)
        
        # ツリー構造を構築
        tree = {}
        for v in versions:
            version_num = v.get('version_number')
            based_on = v.get('based_on_version')
            
            node = {
                'version': version_num,
                'based_on': based_on,
                'description': v.get('description', f'バージョン{version_num}'),
                'created_at': v.get('created_at'),
                'is_branch': based_on and based_on != (version_num - 1) if based_on else False
            }
            
            tree[version_num] = node
        
        return jsonify({
            "success": True,
            "tree": tree,
            "versions": versions
        })
        
    except Exception as e:
        print(f"[ERROR] バージョンツリー取得エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
