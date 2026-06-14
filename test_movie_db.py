#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从数据库获取影视数据测试
此脚本直接从数据库获取影视数据，绕过API
"""

import sqlite3
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_movies_from_db():
    """从数据库获取影视数据"""
    logging.info("开始从数据库获取影视数据")
    
    try:
        # 连接数据库
        conn = sqlite3.connect('data/search_ucmao.db')
        cursor = conn.cursor()
        
        # 检查所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logging.info(f"数据库中的表: {[table[0] for table in tables]}")
        
        # 查询电影数据
        if 'movies' in [table[0] for table in tables]:
            # 更新一些电影的查询次数
            cursor.execute('UPDATE movies SET query_count = 10 WHERE id IN (74, 75, 76, 77, 78)')
            conn.commit()
            logging.info("已更新部分电影的查询次数")
            
            # 直接查询所有电影，不使用排序
            cursor.execute('SELECT id, title, cover_url, rating, release_date, category, query_count FROM movies LIMIT 20')
            movies = cursor.fetchall()
            
            logging.info(f"成功从 movies 表获取{len(movies)}条影视数据")
            
            # 显示电影信息
            for i, movie in enumerate(movies):
                movie_id, title, cover_url, rating, release_date, category, query_count = movie
                logging.info(f"{i+1}. {title} (ID: {movie_id})")
                logging.info(f"   分类: {category}")
                logging.info(f"   评分: {rating}")
                logging.info(f"   上映日期: {release_date}")
                logging.info(f"   图片URL: {cover_url}")
                logging.info(f"   查询次数: {query_count}")
                print()
        elif 'hot_movies' in [table[0] for table in tables]:
            cursor.execute('SELECT id, name, cover_url, category, movie_rank FROM hot_movies LIMIT 20')
            movies = cursor.fetchall()
            
            logging.info(f"成功从 hot_movies 表获取{len(movies)}条影视数据")
            
            # 显示电影信息
            for i, movie in enumerate(movies):
                movie_id, name, cover_url, category, movie_rank = movie
                logging.info(f"{i+1}. {name} (ID: {movie_id})")
                logging.info(f"   分类: {category}")
                logging.info(f"   排名: {movie_rank}")
                logging.info(f"   图片URL: {cover_url}")
                print()
        else:
            logging.warning("数据库中没有影视相关的表")
            movies = []
        
        # 关闭连接
        conn.close()
        
        return movies
        
    except Exception as e:
        logging.error(f"从数据库获取数据时出错: {e}")
        return []


def main():
    """主函数"""
    print("=" * 60)
    print("从数据库获取影视数据测试")
    print("=" * 60)
    
    # 从数据库获取影视数据
    movies = get_movies_from_db()
    
    if movies:
        logging.info("测试完成，成功获取影视数据")
    else:
        logging.warning("测试完成，未获取到影视数据")
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()