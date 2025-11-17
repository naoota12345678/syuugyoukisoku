# バージョン管理改善のテストシナリオ

## テスト1: 基本的なバージョン作成
1. バージョン3を表示
2. 修正提案を適用
3. バージョン6が作成されることを確認
4. バージョン6の`based_on_version`が3であることを確認

## テスト2: 分岐の確認
1. バージョン2から修正を適用
2. 新バージョンの`is_branch`がtrueになることを確認

## テスト3: 差分表示
1. `/api/compare_versions/[regulation_id]`にPOST
   ```json
   {
     "version1": 3,
     "version2": 5
   }
   ```
2. 差分が返されることを確認

## テスト4: バージョンツリー
1. `/api/version_tree/[regulation_id]`にGET
2. ツリー構造が返されることを確認

## 確認コマンド
```python
# Pythonコンソールで実行
import requests

# ローカルテスト
base_url = "http://localhost:5000"

# バージョンツリー取得
response = requests.get(f"{base_url}/api/version_tree/KrarWpZYZ4i8mpJKg25m")
print(response.json())

# バージョン比較
response = requests.post(f"{base_url}/api/compare_versions/KrarWpZYZ4i8mpJKg25m", 
                       json={"version1": 3, "version2": 5})
print(response.json())
```

## デバッグ用ログ確認
アプリケーションログで以下を確認：
- `[DEBUG] ユーザーが表示していたバージョン: X`
- `[DEBUG] ベーステキストの長さ: XXXX文字`
- `[SUCCESS] バージョンXを作成しました（ベース: vX）`
