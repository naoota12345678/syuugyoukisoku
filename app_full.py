# app_full.py (AI機能付き完全版)
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from database import Database
from pdf_parser import PDFParser
from docx_parser import DocxParser
from claude_validator import ClaudeValidator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = Database()
# デバッグモードを環境変数で制御（開発時は PDF_PARSER_DEBUG=1 を設定）
debug_mode = os.environ.get('PDF_PARSER_DEBUG', '0') == '1'
pdf_parser = PDFParser(debug=debug_mode)
docx_parser = DocxParser()
if debug_mode:
    print("✓ PDF Parser Debug Mode: ENABLED")

# ClaudeValidator initialization
try:
    validator = ClaudeValidator()
    print("✓ AI Validation: ENABLED")
except ValueError as e:
    print(f"⚠ Warning: {e}")
    validator = None
except Exception as e:
    print(f"⚠ AI Validation Error: {e}")
    validator = None

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# PDF出力ルート登録
try:
    from pdf_generator import add_pdf_routes
    add_pdf_routes(app, db)
    print("✓ PDF Generator: ENABLED")
except Exception as e:
    print(f"⚠ PDF Generator Error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return jsonify({"error": "ファイルが選択されていません"}), 400

        file = request.files['pdf_file']
        company_name = request.form.get('company_name', '')
        company_address = request.form.get('company_address', '')

        if file.filename == '':
            return jsonify({"error": "ファイルが選択されていません"}), 400

        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()

        if ext not in ('.pdf', '.docx', '.doc'):
            return jsonify({"error": "PDF・Word(.docx/.doc)ファイルのみ対応しています"}), 400

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # ファイル形式に応じてパーサーを選択
        if ext in ('.docx', '.doc'):
            result = docx_parser.extract_from_docx(filepath)
        else:
            result = pdf_parser.extract_from_pdf(filepath)

        if not result['success']:
            return jsonify({"error": f"解析エラー: {result['error']}"}), 500

        extracted_company = result['company_info'].get('company_name')
        final_company_name = company_name or extracted_company or "Company"

        company_id = db.create_company(final_company_name, company_address)
        regulation_id = db.create_regulation(
            company_id=company_id,
            reg_type='main',
            name='Employment Rules',
            source_type='uploaded',
            original_filename=filename
        )
        db.save_regulation_content(
            regulation_id,
            result['structure'],
            raw_text=result.get('raw_text', ''),
            tables=result.get('tables')
        )

        return jsonify({
            "success": True,
            "company_id": company_id,
            "regulation_id": regulation_id,
            "redirect": url_for('validate_regulation', regulation_id=regulation_id)
        })

    companies = db.get_all_companies() if hasattr(db, 'get_all_companies') else []
    return render_template('upload.html', companies=companies)

@app.route('/validate/<int:regulation_id>')
def validate_regulation(regulation_id):
    if not validator:
        return render_template('error.html', 
                             error="Claude API not configured. Set ANTHROPIC_API_KEY in .env file")
    
    regulation = db.get_regulation(regulation_id)
    if not regulation:
        return render_template('error.html', error="Regulation not found")
    
    content = db.get_regulation_content(regulation_id)
    if not content:
        return render_template('error.html', error="Content not found")
    
    validation_result = validator.validate_main_rules(content['content_json'])
    
    if validation_result['success']:
        modifications = validation_result['modifications']
        for mod in modifications:
            db.create_modification(
                regulation_id=regulation_id,
                article_number=mod['article_number'],
                mod_type=mod['modification_type'],
                before_text=mod['before_text'],
                after_text=mod['after_text'],
                reason=mod['reason']
            )
        
        db.save_validation_result(regulation_id, "main_rules_model.txt", len(modifications))
        
        return redirect(url_for('modifications_list', regulation_id=regulation_id))
    else:
        return render_template('error.html', error=validation_result.get('error', 'Validation error'))

@app.route('/modifications/<int:regulation_id>')
def modifications_list(regulation_id):
    regulation = db.get_regulation(regulation_id)
    if not regulation:
        return render_template('error.html', error="規程が見つかりません")
    company = db.get_company(regulation['company_id'])
    modifications = db.get_pending_modifications(regulation_id)

    # 就業規則の全文を取得
    content = db.get_regulation_content(regulation_id)
    raw_text = content.get('raw_text', '') if content else ''

    return render_template('modifications.html',
                         regulation=regulation,
                         company=company,
                         modifications=modifications,
                         raw_text=raw_text)

@app.route('/api/apply_modifications', methods=['POST'])
def apply_modifications():
    data = request.json
    modification_ids = data.get('modification_ids', [])
    regulation_id = data.get('regulation_id')
    
    for mod_id in modification_ids:
        db.apply_modification(mod_id)
    
    all_modifications = db.get_pending_modifications(regulation_id)
    for mod in all_modifications:
        if mod['id'] not in modification_ids:
            db.reject_modification(mod['id'])
    
    db.update_regulation_status(regulation_id, 'active')
    
    return jsonify({"success": True})

@app.route('/regulations/<int:company_id>')
def regulations_list(company_id):
    company = db.get_company(company_id)
    regulations = db.get_company_regulations(company_id)
    
    return render_template('regulations_list.html',
                         company=company,
                         regulations=regulations)

@app.route('/history/<int:regulation_id>')
def modification_history(regulation_id):
    regulation = db.get_regulation(regulation_id)
    company = db.get_company(regulation['company_id'])
    history = db.get_modification_history(regulation_id)
    
    return render_template('history.html',
                         regulation=regulation,
                         company=company,
                         history=history)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if not validator:
        return jsonify({"success": False, "error": "AI機能が無効です（APIキー未設定）"}), 500

    data = request.json
    regulation_id = data.get('regulation_id')
    message = data.get('message', '')
    chat_history = data.get('chat_history', [])

    if not message:
        return jsonify({"success": False, "error": "メッセージが空です"}), 400

    regulation = db.get_regulation(regulation_id)
    if not regulation:
        return jsonify({"success": False, "error": "規程が見つかりません"}), 404

    company = db.get_company(regulation['company_id'])
    company_name = company['name'] if company else "不明"

    content = db.get_regulation_content(regulation_id)
    raw_text = None
    regulation_structure = None
    if content:
        raw_text = content.get('raw_text')
        regulation_structure = content.get('content_json')

    result = validator.chat_about_regulation(
        regulation_structure=regulation_structure,
        company_name=company_name,
        user_message=message,
        chat_history=chat_history,
        raw_text=raw_text
    )

    if result['success']:
        return jsonify({
            "success": True,
            "response": result['response'],
            "has_modification": result.get('has_modification', False),
            "modification": result.get('modification')
        })
    else:
        return jsonify({"success": False, "error": result.get('error', '不明なエラー')}), 500

@app.route('/api/add_chat_modification', methods=['POST'])
def api_add_chat_modification():
    data = request.json
    regulation_id = data.get('regulation_id')

    if not regulation_id:
        return jsonify({"success": False, "error": "regulation_idが必要です"}), 400

    mod_id = db.create_modification(
        regulation_id=regulation_id,
        article_number=data.get('article_number', ''),
        mod_type=data.get('modification_type', 'AI相談'),
        before_text=data.get('before_text', ''),
        after_text=data.get('after_text', ''),
        reason=data.get('reason', '')
    )

    return jsonify({"success": True, "modification_id": mod_id})

@app.route('/test')
def test():
    return f"""
    <html>
    <head><title>System Test</title></head>
    <body>
        <h1>System Status</h1>
        <p>✓ Flask: OK</p>
        <p>✓ Database: OK</p>
        <p>✓ PDF Parser: OK</p>
        <p>{'✓ AI Validation: OK' if validator else '⚠ AI Validation: Disabled'}</p>
        <p><a href="/">Home</a></p>
    </body>
    </html>
    """

if __name__ == '__main__':
    print("="*50)
    print("Employment Rules Management System")
    print("="*50)
    print(f"Directory: {os.getcwd()}")
    print()
    print("✓ Flask: OK")
    print("✓ Database: OK") 
    print("✓ PDF Parser: OK")
    if validator:
        print("✓ AI Validation: ENABLED")
    else:
        print("⚠ AI Validation: Disabled")
    print()
    print("Open: http://localhost:5000")
    print("Test: http://localhost:5000/test")
    print()
    print("Press Ctrl+C to stop")
    print("="*50)
    app.run(debug=True, host='0.0.0.0', port=5000)
