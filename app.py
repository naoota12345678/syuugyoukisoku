import sys
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Disable proxy for Anthropic client (fix for proxies error)
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    if key in os.environ:
        del os.environ[key]

# Version: 2025-11-10-v2 (バージョン履歴エラー修正版)
from flask import Flask, render_template, request, jsonify, redirect
from werkzeug.utils import secure_filename
from pdf_parser import PDFParser
from claude_validator import ClaudeValidator

# データベースを環境変数で切り替え
USE_FIREBASE = os.environ.get('USE_FIREBASE', 'false').lower() == 'true'
USE_FIRESTORE = os.environ.get('USE_FIRESTORE', 'false').lower() == 'true'

if USE_FIREBASE:
    from firebase_database import FirebaseDatabase as Database
    from firebase_admin import firestore
    print("[INFO] 🔥 Using Firebase Admin SDK as database backend")
elif USE_FIRESTORE:
    from firestore_database import FirestoreDatabase as Database
    from firebase_admin import firestore
    print("[INFO] Using Firestore as database backend")
else:
    from database import Database
    print("[INFO] Using SQLite as database backend")

template_dir = os.path.join(BASE_DIR, 'templates')
print("=" * 60)
print(f"TEMPLATE DIR: {template_dir}")
print(f"EXISTS: {os.path.exists(template_dir)}")
if os.path.exists(template_dir):
    files = [f for f in os.listdir(template_dir) if f.endswith('.html')]
    print(f"HTML FILES: {files}")
print("=" * 60)

app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# データベース初期化
if USE_FIREBASE or USE_FIRESTORE:
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'syuugyoukisoku')
    db = Database(project_id=project_id)
else:
    db = Database()

# デバッグモードを環境変数で制御（開発時は PDF_PARSER_DEBUG=1 を設定）
debug_mode = os.environ.get('PDF_PARSER_DEBUG', '0') == '1'
pdf_parser = PDFParser(debug=debug_mode)
if debug_mode:
    print("[OK] PDF Parser Debug Mode: ENABLED")

try:
    validator = ClaudeValidator()
    print("[OK] AI Validation: ENABLED")
except Exception as e:
    print(f"AI Error: {e}")
    validator = None

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    # 会社一覧を取得
    companies = db.get_companies_with_regulation_count()
    return render_template('index.html', companies=companies)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return jsonify({"error": "No file selected"}), 400
        
        file = request.files['pdf_file']
        company_id = request.form.get('company_id', '')
        company_name = request.form.get('company_name', '')
        company_address = request.form.get('company_address', '')
        regulation_name = request.form.get('regulation_name', '')

        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # 既存会社または新規会社
        if company_id:
            # 既存会社を選択（Firebase/Firestoreは文字列ID、SQLiteは整数ID）
            if not USE_FIREBASE and not USE_FIRESTORE:
                company_id = int(company_id)
        elif company_name:
            # 新規会社を作成
            company_id = db.create_company(company_name, company_address)
        else:
            return jsonify({"error": "会社を選択するか、会社名を入力してください"}), 400

        if not regulation_name:
            return jsonify({"error": "規程名は必須です"}), 400

        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(temp_filepath)

            result = pdf_parser.extract_from_pdf(temp_filepath)

            if not result['success']:
                return jsonify({"error": f"PDF error: {result['error']}"}), 500

            # 規程を作成
            regulation_id = db.create_regulation(
                company_id=company_id,
                reg_type='main',
                name=regulation_name,
                source_type='uploaded',
                original_filename=filename
            )

            # 規程専用のディレクトリを作成
            regulation_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"regulation_{regulation_id}")
            os.makedirs(regulation_dir, exist_ok=True)

            # 元のPDFを保存
            original_pdf_path = os.path.join(regulation_dir, "original.pdf")
            import shutil
            shutil.copy2(temp_filepath, original_pdf_path)
            print(f"元のPDFを保存: {original_pdf_path}")

            # 表を保存
            tables = result.get('tables', [])
            if tables:
                tables_dir = os.path.join(regulation_dir, "tables")
                os.makedirs(tables_dir, exist_ok=True)

                # 各表をCSVとして保存
                import csv
                for table_info in tables:
                    page_num = table_info['page']
                    table_data = table_info['data']

                    csv_filename = f"page_{page_num}_table.csv"
                    csv_path = os.path.join(tables_dir, csv_filename)

                    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                        writer = csv.writer(csvfile)
                        for row in table_data:
                            writer.writerow(row)

                    print(f"  表を保存: {csv_filename}")

                # 表のメタデータをJSONで保存
                import json
                json_path = os.path.join(tables_dir, "tables_metadata.json")
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(tables, f, ensure_ascii=False, indent=2)
                print(f"  表メタデータを保存: tables_metadata.json")

            # 一時ファイル削除
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)

            # raw_textを取得
            raw_text = result.get('raw_text', '')
            print(f"[DEBUG] raw_text length: {len(raw_text)}")

            # アップロード時は構造化せず、raw_textのみ保存
            # 構造化は「AI検証を実行」を選択した時のみ行う
            print("raw_textのみ保存します（構造化はスキップ）")
            structure = []

            # raw_textと表データをバージョン0として保存（OCR生データ）
            db.save_regulation_content(company_id, regulation_id, structure, version=0, raw_text=raw_text, tables=tables)

            # 確認ページへリダイレクト
            return jsonify({
                "success": True,
                "company_id": company_id,
                "regulation_id": regulation_id,
                "redirect": f"/regulation/{regulation_id}/confirm",
                "tables_count": len(tables)
            })
        
        return jsonify({"error": "PDF only"}), 400

    # GET リクエスト：会社一覧を取得
    companies = db.get_all_companies()
    return render_template('upload.html', companies=companies)

@app.route('/regulation/<regulation_id>/confirm')
def regulation_confirm(regulation_id):
    """規程確認ページ（アップロード後）"""
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return "規程が見つかりません", 404

    company_id = regulation['company_id']
    company = db.get_company(company_id)
    content_data = db.get_regulation_content(company_id, regulation_id)

    raw_text = ""
    tables = []
    if content_data:
        raw_text = content_data.get('raw_text', '')
        tables = content_data.get('tables', [])

    return render_template('regulation_confirm.html',
                         regulation=regulation,
                         company=company,
                         raw_text=raw_text,
                         text_length=len(raw_text),
                         tables=tables)

@app.route('/regulation/<regulation_id>/save_draft', methods=['POST'])
def save_draft(regulation_id):
    """たたき台として保存（Version 1確定）"""
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return "規程が見つかりません", 404

    company_id = regulation['company_id']
    # ステータスをactiveに更新
    db.update_regulation_status(company_id, regulation_id, 'active')

    return redirect(f'/regulation/{regulation_id}/view')

@app.route('/regulation/<regulation_id>/validate', methods=['POST'])
def validate_regulation(regulation_id):
    """AI検証を実行"""
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return "規程が見つかりません", 404

    company_id = regulation['company_id']
    # 規程内容を取得
    content_data = db.get_regulation_content(company_id, regulation_id)
    if not content_data:
        return "規程内容が見つかりません", 404

    # raw_textを取得（構造化JSONは使わない）
    raw_text = content_data.get('raw_text', '')
    if not raw_text:
        return "規程のテキストが見つかりません", 404

    # AI検証を実行（raw_textを直接使用）
    if validator and raw_text:
        print(f"Starting AI validation for regulation {regulation_id}...")
        print(f"Processing {len(raw_text)} characters...")
        validation_result = validator.validate_main_rules_from_text(raw_text)

        if validation_result['success']:
            modifications = validation_result['modifications']
            print(f"Found {len(modifications)} modifications")

            # 現在のバージョンを取得
            current_version = regulation.get('current_version', 1)

            for mod in modifications:
                db.create_modification(
                    company_id=company_id,
                    regulation_id=regulation_id,
                    article_number=mod['article_number'],
                    mod_type=mod['modification_type'],
                    before_text=mod['before_text'],
                    after_text=mod['after_text'],
                    reason=mod['reason'],
                    target_version=current_version
                )

            db.save_validation_result(company_id, regulation_id, "main_rules_model.txt", len(modifications))

            # 修正提案ページへリダイレクト
            return redirect(f'/modifications/{regulation_id}')
        else:
            print(f"Validation failed: {validation_result.get('error')}")

    # AI検証なしまたは失敗の場合は規程表示ページへ
    return redirect(f'/regulation/{regulation_id}/view')

@app.route('/regulations/<company_id>')
def regulations_list(company_id):
    company = db.get_company(company_id)
    regulations = db.get_company_regulations(company_id)

    # 各規程の最新バージョン情報を取得
    regulations_with_version = []
    for reg in regulations:
        versions = db.get_all_versions(company_id, reg['id'])
        reg_dict = dict(reg)
        if versions:
            reg_dict['latest_version'] = versions[0].get('version_number', 0)
            reg_dict['last_version_date'] = versions[0]['created_at']
        else:
            reg_dict['latest_version'] = 0
            reg_dict['last_version_date'] = None

        regulations_with_version.append(reg_dict)

    return render_template('regulations_list.html', company=company, regulations=regulations_with_version)

@app.route('/regulation/<regulation_id>/view')
def regulation_view(regulation_id):
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return "規程が見つかりません", 404

    company_id = regulation['company_id']
    company = db.get_company(company_id)

    # 最新バージョンを取得
    content_data = db.get_regulation_content(company_id, regulation_id)

    # すべてのバージョンを取得
    versions = db.get_all_versions(company_id, regulation_id)

    content = None
    raw_text = None
    tables = []
    current_version = None
    viewing_version = None

    if content_data:
        current_version = content_data.get('version', 1)
        viewing_version = content_data.get('version_number', current_version)  # 実際に表示中のバージョン番号
        content_json = content_data['content_json']

        # structureの取得
        if isinstance(content_json, dict):
            content = content_json.get('structure') or content_json.get('chapters')
        elif isinstance(content_json, list):
            content = content_json

        # raw_textと表データも取得
        raw_text = content_data.get('raw_text', '')
        tables = content_data.get('tables', [])

    return render_template('regulation_view.html',
                         regulation=regulation,
                         company=company,
                         content=content,
                         raw_text=raw_text,
                         tables=tables,
                         current_version=current_version,
                         viewing_version=viewing_version,
                         versions=versions)

@app.route('/regulation/<regulation_id>/view/version/<int:version>')
def regulation_view_version(regulation_id, version):
    """特定バージョンの規程を表示"""
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return "規程が見つかりません", 404

    company = db.get_company(regulation['company_id'])

    # 指定されたバージョンを取得
    content_data = db.get_regulation_content(regulation['company_id'], regulation_id, version=version)

    # すべてのバージョンを取得
    versions = db.get_all_versions(regulation['company_id'], regulation_id)

    content = None
    raw_text = None
    tables = []
    current_version = regulation.get('current_version', 1)
    viewing_version = version  # 実際に表示しているバージョン

    if content_data:
        content_json = content_data['content_json']

        # structureの取得
        if isinstance(content_json, dict):
            content = content_json.get('structure') or content_json.get('chapters')
        elif isinstance(content_json, list):
            content = content_json

        # raw_textと表データも取得
        raw_text = content_data.get('raw_text', '')
        tables = content_data.get('tables', [])

    return render_template('regulation_view.html',
                         regulation=regulation,
                         company=company,
                         content=content,
                         raw_text=raw_text,
                         tables=tables,
                         current_version=current_version,
                         viewing_version=viewing_version,
                         versions=versions)

@app.route('/modifications/<regulation_id>')
def modifications_list(regulation_id):
    regulation = db.get_regulation_by_id(regulation_id)
    company = db.get_company(regulation['company_id'])
    modifications = db.get_pending_modifications(regulation_id)

    # 元の就業規則テキストを取得
    content_data = db.get_regulation_content(regulation['company_id'], regulation_id)
    raw_text = content_data.get('raw_text', '') if content_data else ''

    return render_template('modifications.html',
                         regulation=regulation,
                         company=company,
                         modifications=modifications,
                         raw_text=raw_text)

@app.route('/regulation/<regulation_id>/history')
def regulation_history(regulation_id):
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return "規程が見つかりません", 404

    company = db.get_company(regulation['company_id'])

    # バージョン履歴を取得（詳細情報含む）
    versions = db.get_all_versions(regulation['company_id'], regulation_id)

    # 全修正履歴を取得
    all_modifications = db.get_modification_history(regulation['company_id'], regulation_id)

    # 各バージョンに適用された修正を取得（簡略版）
    version_details = []
    for ver in versions:
        version_num = ver.get('version_number', ver.get('version', 1))  # version_numberまたはversionをフォールバック

        # このバージョンで適用された修正を簡易的にフィルタリング
        # （厳密な時系列は簡略化）
        applied_mods = [m for m in all_modifications if m.get('status') == 'applied']

        version_details.append({
            'version': version_num,
            'created_at': ver.get('created_at', ''),
            'modifications': applied_mods[:5],  # 最大5件
            'is_latest': version_num == versions[0].get('version_number', versions[0].get('version', 1)) if versions else False
        })

    # 従来の修正履歴も取得（参考用）
    modifications = all_modifications

    return render_template('regulation_history.html',
                         regulation=regulation,
                         company=company,
                         version_details=version_details,
                         modifications=modifications)

@app.route('/api/apply_modifications', methods=['POST'])
def apply_modifications():
    data = request.json
    modification_ids = data.get('modification_ids', [])
    regulation_id = data.get('regulation_id')

    # 規程情報を取得
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return jsonify({"success": False, "error": "規程が見つかりません"}), 404

    # 会社情報を取得
    company = db.get_company(regulation['company_id'])
    if not company:
        return jsonify({"success": False, "error": "会社情報が見つかりません"}), 404

    # 現在の規程内容を取得
    current_content = db.get_regulation_content(regulation['company_id'], regulation_id)
    if not current_content:
        return jsonify({"success": False, "error": "規程内容が見つかりません"}), 404

    content_structure = current_content['content_json']
    if isinstance(content_structure, dict):
        structure = content_structure.get('structure', [])
    elif isinstance(content_structure, list):
        structure = content_structure
    else:
        structure = []

    # 適用する修正を取得
    modifications_to_apply = []
    for mod_id in modification_ids:
        modification = db.get_modification(mod_id)
        if modification:
            modifications_to_apply.append(modification)

    # Claude APIで規程を再構築
    if validator and modifications_to_apply:
        print(f"Claude APIで{len(modifications_to_apply)}件の修正を適用して規程を再構築します...")
        rebuild_result = validator.rebuild_regulation_with_modifications(
            original_structure=structure,
            modifications=modifications_to_apply,
            company_name=company['name']
        )

        if rebuild_result['success']:
            # 再構築された規程を取得
            rebuilt_regulation = rebuild_result['regulation']
            new_structure = rebuilt_regulation.get('chapters', [])
            changes_summary = rebuild_result.get('changes_summary', [])

            print(f"再構築成功！ {len(changes_summary)}件の変更を適用しました")

            # 適用された修正のステータスを更新
            for mod_id in modification_ids:
                db.apply_modification(mod_id)

            # 却下された修正を処理
            all_modifications = db.get_pending_modifications(regulation_id)
            for mod in all_modifications:
                if mod['id'] not in modification_ids:
                    db.reject_modification(mod['id'])

            # 新しいバージョンとして保存
            latest_version = db.get_latest_version(regulation_id)
            new_version = latest_version + 1

            # 構造を保存
            updated_content = {"structure": new_structure}
            db.save_regulation_content(regulation_id, updated_content, version=new_version)

            # ステータスを更新
            db.update_regulation_status(regulation_id, 'active')

            return jsonify({
                "success": True,
                "changes_summary": changes_summary
            })
        else:
            print(f"再構築失敗: {rebuild_result.get('error')}")
            return jsonify({
                "success": False,
                "error": "規程の再構築に失敗しました: " + rebuild_result.get('error', '不明なエラー')
            }), 500
    else:
        # AI未使用の場合は従来の処理
        return jsonify({
            "success": False,
            "error": "AI検証機能が利用できません"
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """AIチャットエンドポイント"""
    data = request.json
    regulation_id = data.get('regulation_id')
    user_message = data.get('message')
    chat_history = data.get('chat_history', [])

    if not regulation_id or not user_message:
        return jsonify({"success": False, "error": "regulation_idとmessageは必須です"}), 400

    # 規程情報を取得
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return jsonify({"success": False, "error": "規程が見つかりません"}), 404

    # 会社情報を取得
    company = db.get_company(regulation['company_id'])
    if not company:
        return jsonify({"success": False, "error": "会社情報が見つかりません"}), 404

    # 規程内容を取得
    current_content = db.get_regulation_content(regulation['company_id'], regulation_id)
    if not current_content:
        return jsonify({"success": False, "error": "規程内容が見つかりません"}), 404

    content_structure = current_content['content_json']
    if isinstance(content_structure, dict):
        structure = content_structure.get('structure', [])
    elif isinstance(content_structure, list):
        structure = content_structure
    else:
        structure = []

    # raw_textを取得（元の就業規則テキスト）
    raw_text = current_content.get('raw_text', '')

    # AIに相談
    if validator:
        print(f"AIチャット: {user_message}")
        chat_result = validator.chat_about_regulation(
            regulation_structure=structure,
            company_name=company['name'],
            user_message=user_message,
            chat_history=chat_history,
            raw_text=raw_text
        )

        if chat_result['success']:
            return jsonify({
                "success": True,
                "response": chat_result['response'],
                "has_modification": chat_result.get('has_modification', False),
                "modification": chat_result.get('modification')
            })
        else:
            return jsonify({
                "success": False,
                "error": "AIの応答に失敗しました: " + chat_result.get('error', '不明なエラー')
            }), 500
    else:
        return jsonify({
            "success": False,
            "error": "AI機能が利用できません"
        }), 500

@app.route('/api/update_dates/<regulation_id>', methods=['POST'])
def update_dates(regulation_id):
    """提出日・施行日を更新"""
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return jsonify({"success": False, "error": "規程が見つかりません"}), 404

    data = request.json
    submitted_date = data.get('submitted_date')
    effective_date = data.get('effective_date')

    # 更新データを作成
    updates = {}
    if submitted_date:
        updates['submitted_at'] = submitted_date
    if effective_date:
        updates['effective_date'] = effective_date

    # データベースを更新
    if updates:
        db.update_regulation(regulation_id, updates)

    return jsonify({"success": True})

@app.route('/api/mark_as_submitted/<regulation_id>', methods=['POST'])
def mark_as_submitted(regulation_id):
    """規程を提出済みにする（簡易版）"""
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return jsonify({"success": False, "error": "規程が見つかりません"}), 404

    # 提出日時を記録
    from datetime import datetime
    db.update_regulation(regulation_id, {'submitted_at': datetime.utcnow().isoformat()})

    return jsonify({"success": True})

@app.route('/api/add_chat_modification', methods=['POST'])
def add_chat_modification():
    """チャットから提案を追加"""
    data = request.json
    regulation_id = data.get('regulation_id')
    article_number = data.get('article_number')
    modification_type = data.get('modification_type', 'AI相談')
    before_text = data.get('before_text', '')
    after_text = data.get('after_text')
    reason = data.get('reason')

    if not all([regulation_id, article_number, after_text, reason]):
        return jsonify({"success": False, "error": "必須項目が不足しています"}), 400

    # 修正提案を作成
    mod_id = db.create_modification(
        regulation_id=regulation_id,
        article_number=article_number,
        mod_type=modification_type,
        before_text=before_text,
        after_text=after_text,
        reason=reason
    )

    return jsonify({"success": True, "modification_id": mod_id})

@app.route('/test')
def test():
    return "TEST OK - All routes working!"

@app.route('/admin/companies')
def admin_companies():
    """会社管理ページ"""
    companies = db.get_companies_with_regulation_count()
    return render_template('admin_companies.html', companies=companies)

@app.route('/api/delete_company/<company_id>', methods=['POST'])
def delete_company(company_id):
    """会社を削除"""
    # 規程が紐づいているか確認
    regulations = db.get_company_regulations(company_id)
    count = len(regulations)

    if count > 0:
        return jsonify({
            "success": False,
            "error": f"この会社には{count}件の規程が登録されています。先に規程を削除してください。"
        }), 400

    # 会社を削除
    db.delete_company(company_id)

    return jsonify({"success": True})

def apply_fixes_to_text(original_text: str, fixes: list) -> str:
    """
    fixesリストを元のテキストに適用する

    Args:
        original_text: 元のテキスト
        fixes: 修正リスト [{"before_text": "...", "after_text": "..."}]

    Returns:
        修正後のテキスト
    """
    result_text = original_text
    for fix in fixes:
        before = fix.get('before_text', '')
        after = fix.get('after_text', '')
        if before and after:
            # before_textをafter_textに置換
            result_text = result_text.replace(before, after)
    return result_text


@app.route('/structure_fixes/<regulation_id>')
def structure_fixes(regulation_id):
    """AI構造修正の確認画面"""
    regulation = db.get_regulation_by_id(regulation_id)
    if not regulation:
        return "規程が見つかりません", 404

    company_id = regulation['company_id']

    # バージョン指定がある場合はそのバージョンを取得、なければ最新を取得
    version = request.args.get('version', type=int)
    if version:
        content_data = db.get_regulation_content(company_id, regulation_id, version=version)
    else:
        content_data = db.get_regulation_content(company_id, regulation_id)

    if not content_data:
        return "規程内容が見つかりません", 404

    raw_text = content_data.get('raw_text', '')
    if not raw_text:
        return "規程のテキストが見つかりません", 404

    # 実際に表示するバージョン番号
    viewing_version = content_data.get('version_number', regulation.get('current_version', 1))

    # AI構造修正を実行
    from ai_structure_fixer import AIStructureFixer
    structure_fixer = AIStructureFixer()

    print(f"[AI構造分析] 開始: regulation_id={regulation_id}, version={viewing_version}, 文字数={len(raw_text)}")
    result = structure_fixer.analyze_structure(raw_text)
    print(f"[AI構造分析] 完了: {len(result.get('fixes', []))}件の問題を検出")

    if not result.get('success', False):
        return f"エラー: {result.get('error', '不明なエラー')}", 500

    # fixesから修正済みテキストを生成
    fixes = result.get('fixes', [])
    fixed_text = apply_fixes_to_text(raw_text, fixes) if fixes else raw_text

    # Company情報を取得
    company = db.get_company(company_id)

    return render_template('structure_fixes.html',
                         regulation=regulation,
                         company=company,
                         fixes=fixes,
                         fixed_text=fixed_text,
                         raw_text=raw_text,
                         viewing_version=viewing_version)


@app.route('/api/apply_structure_fixes/<regulation_id>', methods=['POST'])
def apply_structure_fixes(regulation_id):
    """選択した構造修正を適用"""
    try:
        data = request.json
        fixed_text = data.get('fixed_text', '')
        viewing_version = data.get('viewing_version')  # フロントエンドから送信されたバージョン

        if not fixed_text:
            return jsonify({"success": False, "error": "修正後のテキストがありません"}), 400

        regulation = db.get_regulation_by_id(regulation_id)
        if not regulation:
            return jsonify({"success": False, "error": "規程が見つかりません"}), 404

        company_id = regulation['company_id']

        # ユーザーが実際に表示していたバージョンのデータを取得
        if viewing_version:
            content_data = db.get_regulation_content(company_id, regulation_id, version=viewing_version)
        else:
            content_data = db.get_regulation_content(company_id, regulation_id)

        # 新バージョンとして保存
        current_version = regulation.get('current_version', 1)
        new_version = current_version + 1

        # viewing_versionが送信されていない場合はcontent_dataから取得
        if not viewing_version:
            viewing_version = content_data.get('version_number', current_version) if content_data else current_version

        db.save_regulation_content(
            company_id=company_id,
            regulation_id=regulation_id,
            content_dict=None,
            version=new_version,
            raw_text=fixed_text,
            tables=content_data.get('tables', []),
            based_on_version=viewing_version,
            description="AI構造修正"
        )

        # regulation documentのcurrent_versionを更新
        db.db.collection('companies').document(company_id).collection('regulations').document(regulation_id).update({
            'current_version': new_version,
            'updated_at': firestore.SERVER_TIMESTAMP
        })

        print(f"[構造修正適用] バージョン{new_version}として保存し、current_versionを更新しました")

        return jsonify({
            "success": True,
            "message": f"バージョン{new_version}として保存しました",
            "new_version": new_version
        })

    except Exception as e:
        print(f"[構造修正適用エラー] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/fix_version/<regulation_id>/<int:version>')
def fix_version(regulation_id, version):
    """一時的なAPI：current_versionを手動で更新"""
    try:
        regulation = db.get_regulation_by_id(regulation_id)
        if not regulation:
            return jsonify({"success": False, "error": "規程が見つかりません"}), 404

        company_id = regulation['company_id']

        # current_versionを更新
        db.db.collection('companies').document(company_id).collection('regulations').document(regulation_id).update({
            'current_version': version
        })

        return jsonify({"success": True, "message": f"current_versionを{version}に更新しました"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/save_full_text/<regulation_id>', methods=['POST'])
def save_full_text(regulation_id):
    """全文を手動編集して新バージョンとして保存"""
    try:
        data = request.json
        full_text = data.get('full_text', '')
        viewing_version = data.get('viewing_version')  # フロントエンドから送信されたバージョン

        if not full_text:
            return jsonify({"success": False, "error": "テキストが空です"}), 400

        regulation = db.get_regulation_by_id(regulation_id)
        if not regulation:
            return jsonify({"success": False, "error": "規程が見つかりません"}), 404

        company_id = regulation['company_id']

        # ユーザーが実際に表示していたバージョンのデータを取得
        if viewing_version:
            content_data = db.get_regulation_content(company_id, regulation_id, version=viewing_version)
        else:
            content_data = db.get_regulation_content(company_id, regulation_id)

        # 新バージョンとして保存
        current_version = regulation.get('current_version', 1)
        new_version = current_version + 1

        # viewing_versionが送信されていない場合はcontent_dataから取得
        if not viewing_version:
            viewing_version = content_data.get('version_number', current_version) if content_data else current_version

        # 説明文を生成
        if viewing_version != current_version:
            description = f"バージョン{viewing_version}からの手動修正"
        else:
            description = "全文の手動修正"

        db.save_regulation_content(
            company_id=company_id,
            regulation_id=regulation_id,
            content_dict=None,
            version=new_version,
            raw_text=full_text,
            tables=content_data.get('tables', []),
            based_on_version=viewing_version,
            description=description
        )

        # current_versionを更新
        db.db.collection('companies').document(company_id).collection('regulations').document(regulation_id).update({
            'current_version': new_version,
            'updated_at': firestore.SERVER_TIMESTAMP
        })

        return jsonify({
            "success": True,
            "new_version": new_version,
            "based_on_version": viewing_version,
            "message": f"バージョン{new_version}として保存しました（{description}）"
        })

    except Exception as e:
        print(f"[全文保存エラー] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    print("Starting Flask app...")
    print("Routes:")
    print("  / - Home")
    print("  /upload - Upload PDF")
    print("  /modifications/<id> - View modifications")
    print("  /test - Test page")
    app.run(debug=True, host='0.0.0.0', port=5000)
