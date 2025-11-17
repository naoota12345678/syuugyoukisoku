"""
バージョン管理改善のデプロイスクリプト
"""
import shutil
import os
from datetime import datetime

def deploy_version_management_improvements():
    """バージョン管理の改善をデプロイ"""
    
    print("=== バージョン管理システムの改善をデプロイ ===")
    print(f"開始時刻: {datetime.now()}")
    
    # バックアップディレクトリ作成
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    try:
        # 1. app.pyのバックアップと更新
        print("\n1. app.pyを更新中...")
        if os.path.exists("app.py"):
            shutil.copy2("app.py", os.path.join(backup_dir, "app.py.backup"))
            
            # app_version_management_additions.pyの内容を読み込み
            with open("app_version_management_additions.py", "r", encoding="utf-8") as f:
                additions = f.read()
            
            # app.pyの末尾に追加
            with open("app.py", "a", encoding="utf-8") as f:
                f.write("\n\n# === バージョン管理改善 (追加: " + datetime.now().strftime('%Y-%m-%d') + ") ===\n")
                f.write(additions)
            
            print("✅ app.pyを更新しました")
        else:
            print("❌ app.pyが見つかりません")
        
        # 2. テンプレートのバックアップと更新の準備
        print("\n2. テンプレートの更新準備...")
        templates_dir = "templates"
        
        # modifications.htmlの更新指示
        print("\n📝 modifications.htmlに以下の変更を手動で適用してください:")
        print("-" * 50)
        with open("modifications_js_update.html", "r", encoding="utf-8") as f:
            print(f.read())
        print("-" * 50)
        
        # 3. 新しいテンプレートのコピー
        if os.path.exists("templates/regulation_view_v2.html"):
            print("\n3. 新しいバージョン管理UIをインストール...")
            shutil.copy2("templates/regulation_view_v2.html", 
                        os.path.join(templates_dir, "regulation_view_v2.html"))
            print("✅ regulation_view_v2.htmlをインストールしました")
            print("   → regulation_view.htmlと置き換えるか、新しいルートを追加してください")
        
        # 4. デプロイ手順の表示
        print("\n=== 次のステップ ===")
        print("1. modifications.htmlに上記のJavaScript変更を適用")
        print("2. firestore_database.pyのsave_regulation_content関数を手動で更新")
        print("3. ローカルでテスト:")
        print("   python app.py")
        print("4. Gitにコミット:")
        print("   git add -A")
        print("   git commit -m 'Add version management improvements'")
        print("5. デプロイ:")
        print("   auto_deploy_en.bat")
        
        print(f"\n完了時刻: {datetime.now()}")
        print("バックアップは以下に保存されました:", backup_dir)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        print("バックアップから復元してください:", backup_dir)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_version_management_improvements()
