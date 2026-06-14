#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试豆瓣榜单HTML结构"""

import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

url = "https://movie.douban.com/chart/"

print("正在访问豆瓣榜单页面...")
response = requests.get(url, headers=headers, timeout=15)
print(f"状态码: {response.status_code}")

soup = BeautifulSoup(response.text, 'html.parser')

print("\n=== 查找所有h2标题 ===")
for h2 in soup.find_all("h2"):
    print(f"- {h2.get_text().strip()}")

print("\n=== 查找一周口碑榜 ===")
for h2 in soup.find_all("h2"):
    if "一周口碑榜" in h2.get_text():
        print("找到了一周口碑榜！")
        ul = h2.find_next("ul")
        if ul:
            print("找到了ul列表")
            for i, li in enumerate(ul.find_all("li")[:3]):
                print(f"\n--- 第{i+1}个项目 ---")
                print(f"HTML: {str(li)[:500]}")
                img = li.find("img")
                if img:
                    print(f"找到图片: {img}")
                    print(f"src: {img.get('src')}")
                    print(f"data-src: {img.get('data-src')}")
        break

print("\n=== 查找北美票房榜 ===")
for h2 in soup.find_all("h2"):
    if "北美票房榜" in h2.get_text():
        print("找到了北美票房榜！")
        ul = h2.find_next("ul")
        if ul:
            print("找到了ul列表")
            for i, li in enumerate(ul.find_all("li")[:3]):
                print(f"\n--- 第{i+1}个项目 ---")
                print(f"HTML: {str(li)[:500]}")
                img = li.find("img")
                if img:
                    print(f"找到图片: {img}")
                    print(f"src: {img.get('src')}")
                    print(f"data-src: {img.get('data-src')}")
        break

print("\n=== 保存完整HTML到douban_chart.html ===")
with open("douban_chart.html", "w", encoding="utf-8") as f:
    f.write(response.text)
print("已保存到 douban_chart.html")
