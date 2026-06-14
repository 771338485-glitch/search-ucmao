#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动采集动漫数据到数据库
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.movie_service import movie_service


def main():
    print("=== 开始采集动漫数据 ===")
    
    # 采集1页动漫数据
    category = "动漫"
    saved_count = movie_service.schedule_seedhub_crawl(pages=1, category=category)
    
    print(f"=== 采集完成，共保存 {saved_count} 部动漫 ===")


if __name__ == "__main__":
    main()
