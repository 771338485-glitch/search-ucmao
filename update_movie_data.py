#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
更新影视数据脚本
此脚本会重新爬取影视数据并更新数据库，确保所有影视都有图片URL
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.movie_service import movie_service


def update_movie_data():
    """更新影视数据"""
    print("=== 开始更新影视数据 ===")
    
    # 更新电影数据
    print("\n更新电影数据...")
    movie_count = movie_service.schedule_seedhub_crawl(pages=3, category="电影")
    print(f"电影数据更新完成，共保存 {movie_count} 部电影")
    
    # 更新电视剧数据
    print("\n更新电视剧数据...")
    tv_count = movie_service.schedule_seedhub_crawl(pages=1, category="电视剧")
    print(f"电视剧数据更新完成，共保存 {tv_count} 部电视剧")
    
    # 更新动漫数据
    print("\n更新动漫数据...")
    anime_count = movie_service.schedule_seedhub_crawl(pages=1, category="动漫")
    print(f"动漫数据更新完成，共保存 {anime_count} 部动漫")
    
    print("\n=== 影视数据更新完成 ===")
    print(f"总计更新: {movie_count + tv_count + anime_count} 部影视")


def main():
    """主函数"""
    try:
        update_movie_data()
    except Exception as e:
        print(f"更新影视数据时出错: {e}")


if __name__ == "__main__":
    main()