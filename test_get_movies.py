#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 get_movies_by_query_count 函数
"""

import logging
from src.db.movies_dao import get_movies_by_query_count

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_get_movies_by_query_count():
    """测试 get_movies_by_query_count 函数"""
    logging.info("开始测试 get_movies_by_query_count 函数")
    
    try:
        # 调用函数获取热门电影
        movies = get_movies_by_query_count(page=1, limit=5, category="电影")
        
        logging.info(f"成功获取 {len(movies)} 部热门电影")
        
        # 显示电影信息
        for i, movie in enumerate(movies):
            logging.info(f"{i+1}. {movie.get('title')} (ID: {movie.get('id')})")
            logging.info(f"   分类: {movie.get('category')}")
            logging.info(f"   评分: {movie.get('rating')}")
            logging.info(f"   上映日期: {movie.get('release_date')}")
            logging.info(f"   图片URL: {movie.get('cover_url')}")
            logging.info(f"   查询次数: {movie.get('query_count')}")
            print()
        
        return movies
        
    except Exception as e:
        logging.error(f"测试 get_movies_by_query_count 函数失败: {e}")
        return []

def main():
    """主函数"""
    print("============================================================")
    print("测试 get_movies_by_query_count 函数")
    print("============================================================")
    
    movies = test_get_movies_by_query_count()
    
    if movies:
        logging.info("测试完成，成功获取热门电影数据")
    else:
        logging.error("测试失败，无法获取热门电影数据")
    
    print("============================================================")
    print("测试完成")
    print("============================================================")

if __name__ == "__main__":
    main()