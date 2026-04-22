#!/usr/bin/env python
"""测试 API 响应时间"""
import os
import sys
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(".env")
load_dotenv("../.env")

import requests

BASE_URL = "http://localhost:5000/api"

# 预热请求（Flask 第一次请求会比较慢）
print("=== 预热请求 ===")
r = requests.get(f"{BASE_URL}/mobile/meta", timeout=30)
print(f"预热 /mobile/meta: {r.status_code}")

# 测试商品列表
print("\n=== 测试商品列表 ===")
for i in range(3):
    start = time.time()
    r = requests.get(f"{BASE_URL}/mobile/products?page=1&pageSize=20", timeout=30)
    elapsed = time.time() - start
    print(f"请求 {i+1}: {elapsed:.3f}s - {r.status_code}")

# 测试商品详情
print("\n=== 测试商品详情 ===")
for i in range(3):
    start = time.time()
    r = requests.get(f"{BASE_URL}/mobile/products/1", timeout=30)
    elapsed = time.time() - start
    print(f"请求 {i+1}: {elapsed:.3f}s - {r.status_code}")