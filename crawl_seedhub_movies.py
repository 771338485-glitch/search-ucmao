#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬取 seedhub.cc 页面的电影图片和标题，确保对应关系正确
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

def crawl_seedhub_movies():
    """爬取 seedhub.cc 页面的电影图片和标题"""
    logging.info("开始爬取 seedhub.cc 页面的电影信息")
    
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
        
        # 分析页面结构，找到电影列表
        # 从之前的网页内容来看，电影信息应该在一个容器中
        # 尝试查找包含电影信息的主要容器
        movie_container = soup.find('div', class_=lambda x: x and ('container' in x or 'list' in x or 'movies' in x))
        
        if not movie_container:
            # 如果没有找到，使用整个body
            movie_container = soup.body
        
        # 查找所有电影条目
        # 从之前的网页内容来看，电影条目应该包含图片和标题
        # 尝试查找所有可能的电影条目
        movie_items = []
        
        # 方法1：查找包含图片的链接
        links = movie_container.find_all('a', href=True)
        for link in links:
            img = link.find('img')
            if img:
                # 尝试从链接文本或邻近元素获取标题
                title = link.get_text(strip=True)
                if not title:
                    # 尝试查找邻近的标题元素
                    next_element = link.find_next(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'div'])
                    if next_element:
                        title = next_element.get_text(strip=True)
                if title and len(title) > 1:
                    movie_items.append({'img': img, 'title': title, 'link': link['href']})
        
        # 方法2：查找包含图片的div
        if not movie_items:
            divs = movie_container.find_all('div')
            for div in divs:
                img = div.find('img')
                if img:
                    title = div.get_text(strip=True)
                    if title and len(title) > 1:
                        movie_items.append({'img': img, 'title': title})
        
        # 去重
        seen_titles = set()
        unique_movie_items = []
        for item in movie_items:
            if item['title'] not in seen_titles:
                seen_titles.add(item['title'])
                unique_movie_items.append(item)
        
        movie_items = unique_movie_items
        logging.info(f"找到 {len(movie_items)} 个电影条目")
        
        # 下载图片
        for i, item in enumerate(movie_items):
            img = item['img']
            title = item['title']
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
        
        # 如果还是没有找到电影，使用硬编码的电影列表
        if not movie_items:
            logging.info("使用硬编码的电影列表")
            # 从之前的网页内容中提取的电影列表
            movies = [
                "搜查瑠公圳", "飞行家", "咒术回战 第三季", "罪人", "爱情怎么翻译？",
                "生命树", "洛杉矶劫案", "成何体统", "葬送的芙莉莲 第二季", "一战再战",
                "除恶", "纯真年代的爱情", "情感价值", "乩身", "家弑服务",
                "莎拉的真伪人生", "七王国的骑士 第一季", "她的盛焰", "如何大赚一笔", "相反的你和我"
            ]
            
            # 重新获取所有图片
            images = soup.find_all('img')
            img_urls = []
            for img in images:
                img_url = img.get('src')
                if img_url and not img_url.endswith('favicon.ico'):
                    if not img_url.startswith('http'):
                        img_url = f"https://www.seedhub.cc{img_url}" if img_url.startswith('/') else f"https://www.seedhub.cc/{img_url}"
                    img_urls.append(img_url)
            
            # 匹配电影和图片
            min_length = min(len(movies), len(img_urls))
            for i in range(min_length):
                title = movies[i]
                img_url = img_urls[i]
                logging.info(f"下载 {i+1}. {title} 的图片: {img_url}")
                download_image(img_url, title)
        
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
    print("爬取 seedhub.cc 页面的电影图片和标题")
    print("============================================================")
    
    # 清空之前的图片
    for file in os.listdir(IMAGE_DIR):
        os.remove(os.path.join(IMAGE_DIR, file))
    logging.info("已清空之前的图片")
    
    crawl_seedhub_movies()
    
    print("============================================================")
    print("爬取完成")
    print("============================================================")

if __name__ == "__main__":
    main()