#!/usr/bin/env python3
"""检查Cookie配置"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.cookie_config_dao import get_all_cookies

print("=" * 60)
print("检查数据库中的Cookie配置")
print("=" * 60)

cookies = get_all_cookies()

if not cookies:
    print("❌ 数据库中没有配置任何Cookie")
else:
    print(f"✅ 找到 {len(cookies)} 个Cookie配置：")
    for cookie in cookies:
        print(f"\n  - 云盘: {cookie['cloud_name']}")
        print(f"  - 创建时间: {cookie['created_at']}")
        print(f"  - 更新时间: {cookie['updated_at']}")
        if cookie['cookie']:
            print(f"  - Cookie长度: {len(cookie['cookie'])} 字符")
            print(f"  - Cookie前50字符: {cookie['cookie'][:50]}...")

print("\n" + "=" * 60)
print("检查前端JavaScript文件")
print("=" * 60)

js_path = "/Users/zhao/Desktop/网盘/search-ucmao/static/js/index.js"
if os.path.exists(js_path):
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if '进度条' in content or '取消' in content:
            print("✅ 前端JavaScript文件已包含新功能")
        else:
            print("❌ 前端JavaScript文件可能没有更新")
        print(f"  文件大小: {len(content)} 字节")
        print(f"  最近修改时间: {os.path.getmtime(js_path)}")
else:
    print("❌ 找不到前端JavaScript文件")

print("\n" + "=" * 60)
print("检查模板文件")
print("=" * 60)

html_path = "/Users/zhao/Desktop/网盘/search-ucmao/templates/index.html"
if os.path.exists(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'index.js?v=' in content:
            print("✅ 模板文件已包含JS版本号")
            for line in content.split('\n'):
                if 'index.js' in line:
                    print(f"  {line.strip()}")
        else:
            print("❌ 模板文件可能没有更新JS版本号")
else:
    print("❌ 找不到模板文件")
