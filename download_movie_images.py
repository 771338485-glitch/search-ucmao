#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载影视图片
"""

import logging
import requests
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 图片保存目录
IMAGE_DIR = 'movie_images'

# 确保保存目录存在
os.makedirs(IMAGE_DIR, exist_ok=True)

def download_movie_images():
    """下载影视图片"""
    logging.info("开始下载影视图片")
    
    # API URL
    api_url = "http://localhost:5005/api/movies/hot?page=1&limit=10&category=%E7%94%B5%E5%BD%B1"
    
    try:
        # 获取影视数据
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('code') == 0 and data.get('data', {}).get('items'):
            movies = data['data']['items']
            logging.info(f"成功获取 {len(movies)} 部影视数据")
            
            # 下载每部影视的图片
            for i, movie in enumerate(movies):
                title = movie.get('title', '未知标题')
                cover_url = movie.get('cover_url', '')
                
                # 使用替代图片源
                if not cover_url or 'placeholder' in cover_url:
                    # 根据电影类型生成不同的图片
                    genres = movie.get('genres', [])
                    if '动作' in genres:
                        image_prompt = 'movie poster action film'
                    elif '喜剧' in genres:
                        image_prompt = 'movie poster comedy'
                    elif '爱情' in genres:
                        image_prompt = 'movie poster romance'
                    else:
                        image_prompt = 'movie poster drama'
                    cover_url = f"https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt={image_prompt}&image_size=portrait_4_3"
                
                if cover_url:
                    logging.info(f"下载 {i+1}. {title} 的图片: {cover_url}")
                    download_image(cover_url, title)
                else:
                    logging.warning(f"{title} 没有图片URL")
        else:
            logging.error("API返回数据格式不正确")
            
    except Exception as e:
        logging.error(f"下载影视图片失败: {e}")

def download_image(url, title):
    """下载单个图片"""
    try:
        # 生成文件名
        filename = f"{title.replace('/', '_').replace('\\', '_')}.jpg"
        filepath = os.path.join(IMAGE_DIR, filename)
        
        # 下载图片
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # 保存图片
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        logging.info(f"✓ 成功下载图片: {filepath}")
        
    except Exception as e:
        logging.error(f"✗ 下载图片失败: {e}")

def main():
    """主函数"""
    print("============================================================")
    print("下载影视图片")
    print("============================================================")
    
    download_movie_images()
    
    print("============================================================")
    print("下载完成")
    print("============================================================")

if __name__ == "__main__":
    main()