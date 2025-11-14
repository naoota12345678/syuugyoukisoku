from firebase_database import FirebaseDatabase

db = FirebaseDatabase()
regulation_id = "KrarWpZYZ4i8mpJKg25m"
regulation = db.get_regulation_by_id(regulation_id)

if regulation:
    company_id = regulation['company_id']
    content = db.get_regulation_content(company_id, regulation_id)
    raw_text = content.get('raw_text', '')
    
    # 第3条付近のテキストを確認
    lines = raw_text.split('\n')
    for i, line in enumerate(lines[:50]):  # 最初の50行
        if '第3条' in line or (i > 0 and '第3条' in lines[i-1]):
            print(f"Line {i}: {repr(line)}")
