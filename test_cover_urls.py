#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的电影封面URL并测试其可用性
"""

import logging
import sqlite3
import requests

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_movie_cover_urls():
    """检查数据库中的电影封面URL并测试其可用性"""
    logging.info("开始检查数据库中的电影封面URL")
    
    try:
        # 连接数据库
        conn = sqlite3.connect('data/search_ucmao.db')
        cursor = conn.cursor()
        
        # 查询电影数据
        cursor.execute('SELECT id, title, cover_url, category FROM movies LIMIT 10')
        movies = cursor.fetchall()
        
        logging.info(f"成功从 movies 表获取{len(movies)}条影视数据")
        
        # 测试URL可用性
        for i, movie in enumerate(movies):
            movie_id, title, cover_url, category = movie
            logging.info(f"{i+1}. {title} (ID: {movie_id})")
            logging.info(f"   分类: {category}")
            logging.info(f"   封面URL: {cover_url}")
            
            # 测试URL可用性
            if cover_url:
                try:
                    response = requests.get(cover_url, timeout=5)
                    if response.status_code == 200:
                        logging.info("   ✓ URL可访问")
                    else:
                        logging.warning(f"   ✗ URL不可访问，状态码: {response.status_code}")
                except Exception as e:
                    logging.error(f"   ✗ URL访问失败: {e}")
            else:
                logging.warning("   ✗ 封面URL为空")
            print()
        
        # 关闭连接
        conn.close()
        
    except Exception as e:
        logging.error(f"检查数据库失败: {e}")

def main():
    """主函数"""
    print("============================================================")
    print("检查数据库中的电影封面URL并测试其可用性")
    print("============================================================")
    
    test_movie_cover_urls()
    
    print("============================================================")
    print("检查完成")
    print("============================================================")

if __name__ == "__main__":
    main()