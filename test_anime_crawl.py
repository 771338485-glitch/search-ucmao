#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试动漫数据采集
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.movie_service import movie_service


def main():
    print("=== 开始测试动漫数据采集 ===")
    
    # 测试采集1页动漫数据
    category = "动漫"
    movies = movie_service.crawl_seedhub_movies(page=1, category=category)
    
    print(f"\n成功获取 {len(movies)} 部动漫:")
    for i, movie in enumerate(movies, 1):
        print(f"{i}. {movie.get('title')} - 类型: {', '.join(movie.get('genres', []))}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    main()
