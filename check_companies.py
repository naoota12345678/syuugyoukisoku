#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import Database

db = Database()
conn = db.get_connection()
cursor = conn.cursor()

cursor.execute('SELECT id, name FROM companies ORDER BY id')
companies = cursor.fetchall()

print('登録されている会社:')
print('ID | 会社名')
print('---|' + '-' * 50)
for c in companies:
    company_dict = dict(c)
    print(f"{company_dict['id']:2} | {company_dict['name']}")

conn.close()
