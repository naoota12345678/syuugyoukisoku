# regulations_list.htmlの修正案

## 現在の問題：
同じ規程の全バージョンが一覧に表示されている
（就業規則 v1, v2, v3, v4, v5 がすべて表示）

## 修正後：
規程ごとに最新版のみ表示
- 就業規則 (最新: v5)
- 賃金規程 (最新: v2)
- 育児休業規程 (最新: v1)

## 実装方法：

### オプション1: データベース側で処理
```python
# app.py または firestore_database.py
def get_regulations_latest_only(company_id):
    """各規程の最新版のみを取得"""
    regulations = []
    
    # すべての規程を取得
    all_regulations = db.collection('companies').document(company_id)\
        .collection('regulations').get()
    
    # 規程名でグループ化して最新版のみ選択
    regulation_groups = {}
    for reg in all_regulations:
        data = reg.to_dict()
        name = data.get('name', '')
        
        if name not in regulation_groups:
            regulation_groups[name] = data
        else:
            # より新しいバージョンがあれば更新
            if data.get('current_version', 0) > regulation_groups[name].get('current_version', 0):
                regulation_groups[name] = data
    
    return list(regulation_groups.values())
```

### オプション2: テンプレート側で処理
```html
<!-- regulations_list.html -->
{% set displayed_names = [] %}
{% for regulation in regulations|sort(attribute='current_version', reverse=True) %}
    {% if regulation.name not in displayed_names %}
        <!-- この規程名は初めて表示（＝最新版） -->
        <div class="regulation-card">
            <h3>{{ regulation.name }}</h3>
            <p>最新版: Version {{ regulation.current_version }}</p>
            <!-- その他の情報 -->
        </div>
        {% set _ = displayed_names.append(regulation.name) %}
    {% endif %}
{% endfor %}
```

## より良い解決策：
データベース構造を改善して、規程マスターと各バージョンを分離

```
companies/
  └── {company_id}/
      └── regulation_masters/  # 新規追加
          └── {master_id}/
              ├── name: "就業規則"
              ├── type: "employment"
              ├── current_version: 5
              ├── created_at: ...
              └── versions/
                  └── {version_id}/
                      ├── version_number: 1
                      ├── content: ...
                      └── created_at: ...
```