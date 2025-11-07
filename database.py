# database.py
import sqlite3
from datetime import datetime
import json
import os

class Database:
    def __init__(self, db_path="database/regulations.db"):
        self.db_path = db_path
        # データベースディレクトリを確保
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_db()
    
    def get_connection(self):
        """データベース接続を取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """データベースを初期化"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.executescript('''
            -- 会社情報
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            -- 規程ファイル
            CREATE TABLE IF NOT EXISTS regulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                source_type TEXT,
                original_filename TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            );
            
            -- 規程内容（構造化JSON）
            CREATE TABLE IF NOT EXISTS regulation_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regulation_id INTEGER NOT NULL,
                content_json TEXT NOT NULL,
                raw_text TEXT,
                tables_json TEXT,
                version INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (regulation_id) REFERENCES regulations(id)
            );
            
            -- 修正提案と履歴
            CREATE TABLE IF NOT EXISTS modifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regulation_id INTEGER NOT NULL,
                article_number TEXT NOT NULL,
                modification_type TEXT NOT NULL,
                before_text TEXT NOT NULL,
                after_text TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                applied_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (regulation_id) REFERENCES regulations(id)
            );
            
            -- 検証結果
            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regulation_id INTEGER NOT NULL,
                model_used TEXT NOT NULL,
                issues_count INTEGER DEFAULT 0,
                validation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (regulation_id) REFERENCES regulations(id)
            );
        ''')
        
        conn.commit()
        conn.close()
        print(f"Database initialized at {self.db_path}")
    
    # ===== 会社関連 =====
    def create_company(self, name, address=None):
        """会社を登録"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO companies (name, address) VALUES (?, ?)",
            (name, address)
        )
        company_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return company_id
    
    def get_company(self, company_id):
        """会社情報を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        company = cursor.fetchone()
        conn.close()
        return dict(company) if company else None

    def get_all_companies(self):
        """全ての会社を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM companies ORDER BY name")
        companies = cursor.fetchall()
        conn.close()
        return [dict(company) for company in companies]

    # ===== 規程関連 =====
    def create_regulation(self, company_id, reg_type, name, source_type, original_filename=None):
        """規程を登録"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO regulations 
            (company_id, type, name, source_type, original_filename)
            VALUES (?, ?, ?, ?, ?)
        ''', (company_id, reg_type, name, source_type, original_filename))
        regulation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return regulation_id
    
    def get_regulation(self, regulation_id):
        """規程情報を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM regulations WHERE id = ?", (regulation_id,))
        regulation = cursor.fetchone()
        conn.close()
        return dict(regulation) if regulation else None
    
    def get_company_regulations(self, company_id):
        """会社の全規程を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM regulations 
            WHERE company_id = ? 
            ORDER BY created_at DESC
        ''', (company_id,))
        regulations = cursor.fetchall()
        conn.close()
        return [dict(reg) for reg in regulations]
    
    def update_regulation_status(self, regulation_id, status):
        """規程のステータスを更新"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE regulations 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, regulation_id))
        conn.commit()
        conn.close()
    
    # ===== 規程内容関連 =====
    def save_regulation_content(self, regulation_id, content_dict, version=1, raw_text=None, tables=None):
        """規程内容を保存（JSON形式 + 生テキスト + 表データ）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        content_json = json.dumps(content_dict, ensure_ascii=False)
        tables_json = json.dumps(tables, ensure_ascii=False) if tables else None
        cursor.execute('''
            INSERT INTO regulation_content
            (regulation_id, content_json, raw_text, tables_json, version)
            VALUES (?, ?, ?, ?, ?)
        ''', (regulation_id, content_json, raw_text, tables_json, version))
        conn.commit()
        conn.close()
    
    def get_regulation_content(self, regulation_id, version=None):
        """規程内容を取得（表データを含む）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if version:
            cursor.execute('''
                SELECT * FROM regulation_content
                WHERE regulation_id = ? AND version = ?
            ''', (regulation_id, version))
        else:
            cursor.execute('''
                SELECT * FROM regulation_content
                WHERE regulation_id = ?
                ORDER BY version DESC LIMIT 1
            ''', (regulation_id,))
        content = cursor.fetchone()
        conn.close()
        if content:
            result = dict(content)
            result['content_json'] = json.loads(result['content_json'])
            # 表データをパース（存在する場合）
            if result.get('tables_json'):
                result['tables'] = json.loads(result['tables_json'])
            else:
                result['tables'] = []
            return result
        return None
    
    # ===== 修正提案関連 =====
    def create_modification(self, regulation_id, article_number, mod_type, 
                          before_text, after_text, reason):
        """修正提案を作成"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO modifications 
            (regulation_id, article_number, modification_type, 
             before_text, after_text, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (regulation_id, article_number, mod_type, before_text, after_text, reason))
        mod_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return mod_id
    
    def get_pending_modifications(self, regulation_id):
        """未適用の修正提案を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM modifications 
            WHERE regulation_id = ? AND status = 'pending'
            ORDER BY created_at
        ''', (regulation_id,))
        modifications = cursor.fetchall()
        conn.close()
        return [dict(mod) for mod in modifications]
    
    def apply_modification(self, modification_id):
        """修正を適用"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE modifications 
            SET status = 'applied', applied_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (modification_id,))
        conn.commit()
        conn.close()
    
    def reject_modification(self, modification_id):
        """修正を却下"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE modifications 
            SET status = 'rejected', applied_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (modification_id,))
        conn.commit()
        conn.close()
    
    def get_modification(self, modification_id):
        """特定の修正を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM modifications WHERE id = ?", (modification_id,))
        modification = cursor.fetchone()
        conn.close()
        return dict(modification) if modification else None

    def get_modification_history(self, regulation_id):
        """修正履歴を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM modifications
            WHERE regulation_id = ?
            ORDER BY created_at DESC
        ''', (regulation_id,))
        modifications = cursor.fetchall()
        conn.close()
        return [dict(mod) for mod in modifications]

    def get_latest_version(self, regulation_id):
        """最新のバージョン番号を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MAX(version) as max_version
            FROM regulation_content
            WHERE regulation_id = ?
        ''', (regulation_id,))
        result = cursor.fetchone()
        conn.close()
        return result['max_version'] if result and result['max_version'] else 0
    
    # ===== 検証結果関連 =====
    def save_validation_result(self, regulation_id, model_used, issues_count):
        """検証結果を保存"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO validation_results 
            (regulation_id, model_used, issues_count)
            VALUES (?, ?, ?)
        ''', (regulation_id, model_used, issues_count))
        conn.commit()
        conn.close()
    
    def get_validation_history(self, regulation_id):
        """検証履歴を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM validation_results 
            WHERE regulation_id = ? 
            ORDER BY validation_date DESC
        ''', (regulation_id,))
        results = cursor.fetchall()
        conn.close()
        return [dict(result) for result in results]
