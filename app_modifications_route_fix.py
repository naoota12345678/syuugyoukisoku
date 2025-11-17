# app.pyのmodificationsルートの修正

@app.route('/modifications/<regulation_id>')
def modifications(regulation_id):
    """修正提案画面（バージョン対応版）"""
    # URLパラメータからバージョンを取得
    viewing_version = request.args.get('version', None)
    
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return "規程が見つかりません", 404
    
    # viewing_versionが指定されていない場合は最新版
    if not viewing_version:
        viewing_version = regulation.get('current_version', 1)
    else:
        viewing_version = int(viewing_version)
    
    print(f"[DEBUG] Modifications page - viewing version: {viewing_version}")
    
    company_id = regulation.get('company_id')
    company = db.get_company(company_id)
    
    # 修正提案リストを取得
    modifications = db.get_modifications(company_id, regulation_id)
    
    # 表示中のバージョンの内容を取得
    content_data = db.get_regulation_content(company_id, regulation_id, version=viewing_version)
    
    return render_template('modifications.html',
                         regulation=regulation,
                         company=company,
                         modifications=modifications,
                         viewing_version=viewing_version,  # 重要：viewing_versionを渡す
                         content_data=content_data)
