#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬取 seedhub.cc 页面的图片和标题，确保对应关系正确
"""

import logging
import requests
from bs4 import BeautifulSoup
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 图片保存目录
IMAGE_DIR = 'seedhub_images'

# 确保保存目录存在
os.makedirs(IMAGE_DIR, exist_ok=True)

def crawl_seedhub_images_with_titles():
    """爬取 seedhub.cc 页面的图片和标题，确保对应关系正确"""
    logging.info("开始爬取 seedhub.cc 页面的图片和标题")
    
    # 目标URL
    url = "https://www.seedhub.cc/?page=2"
    
    try:
        # 设置请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Referer": "https://www.seedhub.cc/"
        }
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找电影卡片
        # 分析页面结构，找到包含电影信息的容器
        # 通常电影卡片会有共同的类名或结构
        movie_cards = []
        
        # 尝试不同的选择器
        # 1. 查找包含电影信息的div
        potential_cards = soup.find_all('div', class_=lambda x: x and ('card' in x or 'movie' in x or 'item' in x))
        
        # 2. 查找包含图片和标题的结构
        for card in potential_cards:
            # 查找图片
            img = card.find('img')
            # 查找标题
            title = card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'span'], text=True)
            
            if img and title:
                movie_cards.append({'img': img, 'title': title.get_text(strip=True)})
        
        # 如果没有找到，尝试其他结构
        if not movie_cards:
            # 查找所有包含图片的元素
            images = soup.find_all('img')
            # 查找所有包含标题的元素
            titles = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a'], text=True)
            
            # 假设图片和标题是一一对应的
            min_length = min(len(images), len(titles))
            for i in range(min_length):
                movie_cards.append({'img': images[i], 'title': titles[i].get_text(strip=True)})
        
        logging.info(f"找到 {len(movie_cards)} 个电影卡片")
        
        # 下载图片并保存对应关系
        for i, card in enumerate(movie_cards):
            img = card['img']
            title = card['title']
            img_url = img.get('src')
            
            if img_url:
                # 处理相对路径
                if not img_url.startswith('http'):
                    img_url = f"https://www.seedhub.cc{img_url}" if img_url.startswith('/') else f"https://www.seedhub.cc/{img_url}"
                
                logging.info(f"下载 {i+1}. {title} 的图片: {img_url}")
                # 下载图片
                download_image(img_url, title)
            else:
                logging.warning(f"{title} 没有图片URL")
        
        logging.info("爬取完成")
        
    except Exception as e:
        logging.error(f"爬取失败: {e}")

def download_image(url, title):
    """下载单个图片"""
    try:
        # 发送请求
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # 获取文件扩展名
        ext = url.split('.')[-1].split('?')[0].split('#')[0]
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            ext = 'jpg'  # 默认扩展名
        
        # 清理文件名
        safe_title = ''.join(c for c in title if c.isalnum() or c in [' ', '-', '_', '（', '）', '(', ')', ':', '：'])
        safe_title = safe_title.strip()
        
        # 保存图片
        filepath = os.path.join(IMAGE_DIR, f"{safe_title}.{ext}")
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        logging.info(f"✓ 成功下载图片: {filepath}")
        
    except Exception as e:
        logging.error(f"✗ 下载图片失败: {e}")

def main():
    """主函数"""
    print("============================================================")
    print("爬取 seedhub.cc 页面的图片和标题")
    print("============================================================")
    
    # 清空之前的图片
    for file in os.listdir(IMAGE_DIR):
        os.remove(os.path.join(IMAGE_DIR, file))
    logging.info("已清空之前的图片")
    
    crawl_seedhub_images_with_titles()
    
    print("============================================================")
    print("爬取完成")
    print("============================================================")

if __name__ == "__main__":
    main()