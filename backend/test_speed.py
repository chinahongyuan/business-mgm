#!/usr/bin/env python
"""测试接口响应时间"""
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(".env")
load_dotenv("../.env")

import requests

BASE_URL = "http://localhost:5000/api"

# 测试 /mobile/meta
start = time.time()
r = requests.get(f"{BASE_URL}/mobile/meta")
print(f"/mobile/meta: {time.time()-start:.3f}s - {r.status_code}")

# 测试 /mobile/products
start = time.time()
r = requests.get(f"{BASE_URL}/mobile/products?page=1&pageSize=20&sort=default")
print(f"/mobile/products: {time.time()-start:.3f}s - {r.status_code}")

# 测试 /mobile/login (需要有效密码)
start = time.time()
r = requests.post(f"{BASE_URL}/mobile/login", json={"password": "123456"})
print(f"/mobile/login: {time.time()-start:.3f}s - {r.status_code}")