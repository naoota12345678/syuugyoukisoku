# app.pyに追加すべき修正

@app.route('/api/save_modification/<modification_id>', methods=['POST'])
def save_modification(modification_id):
    """個別の修正提案を適用して新バージョンとして保存"""
    try:
        # リクエストデータから表示中のバージョンを取得
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
        
        # ユーザーが表示していたバージョンのデータを取得（重要！）
        if viewing_version:
            content_data = db.get_regulation_content(company_id, regulation_id, version=viewing_version)
        else:
            # viewing_versionが指定されていない場合は最新版
            content_data = db.get_regulation_content(company_id, regulation_id)
            viewing_version = content_data.get('version_number') if content_data else regulation.get('current_version', 1)
        
        if not content_data:
            return jsonify({"success": False, "error": "規程内容が見つかりません"}), 404
        
        # 元のテキストを取得（表示中のバージョンから）
        raw_text = content_data.get('raw_text', '')
        tables = content_data.get('tables', [])
        
        # 修正を適用
        before_text = modification.get('before_text', '')
        after_text = modification.get('after_text', '')
        
        # テキストを置換
        if before_text and before_text in raw_text:
            modified_text = raw_text.replace(before_text, after_text, 1)
        else:
            # before_textが見つからない場合
            modified_text = raw_text + f"\n\n{after_text}"
        
        # 新バージョンとして保存
        current_version = regulation.get('current_version', 1)
        new_version = current_version + 1
        
        # 説明文を生成
        article_number = modification.get('article_number', '')
        mod_type = modification.get('modification_type', '修正')
        description = f"{article_number}の{mod_type} - バージョン{viewing_version}から適用"
        
        # 新バージョンとして保存
        version_id = db.save_regulation_content(
            company_id=company_id,
            regulation_id=regulation_id,
            content_dict=None,
            version=new_version,
            raw_text=modified_text,
            tables=tables,
            based_on_version=viewing_version,
            description=description
        )
        
        # 修正提案のステータスを更新
        db.apply_modification(company_id, regulation_id, modification_id, new_version)
        
        print(f"[修正適用] {description} - バージョン{new_version}として保存")
        
        return jsonify({
            "success": True,
            "message": f"バージョン{new_version}として保存しました",
            "new_version": new_version,
            "based_on_version": viewing_version
        })
        
    except Exception as e:
        print(f"[修正保存エラー] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
