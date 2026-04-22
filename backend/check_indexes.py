#!/usr/bin/env python
"""检查数据库索引状态"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(".env")
load_dotenv("../.env")

from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # 检查商品表索引
    print("=== mer_product 索引 ===")
    result = db.session.execute(text('SHOW INDEXES FROM mer_product'))
    for row in result:
        print(f"  {row}")

    print("\n=== app_mobile_user 索引 ===")
    result = db.session.execute(text('SHOW INDEXES FROM app_mobile_user'))
    for row in result:
        print(f"  {row}")

    print("\n=== app_mobile_login_password 索引 ===")
    result = db.session.execute(text('SHOW INDEXES FROM app_mobile_login_password'))
    for row in result:
        print(f"  {row}")