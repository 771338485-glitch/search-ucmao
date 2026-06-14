#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用WebFetch获取的内容分析电影数据
"""

# 从WebFetch获取的内容中提取电影数据
webfetch_content = """

最近更新 / 上映时间 /  豆瓣评分 / 近期热门↓



    
      
         呼啸山庄

        2026 / 电影 / 英国 美国 / 英语 / 玛格特·罗比 雅各布·艾洛蒂 
        类型: 爱情 / 剧情
        豆瓣评分: 6.1
      
    
  
    
      
         请求救援

        2026 / 电影 / 美国 加拿大 英国 澳大利亚 泰国 / 英语 / 瑞秋·麦克亚当斯 迪伦·奥布莱恩 
        类型: 恐怖 / 惊悚 / 冒险
        豆瓣评分: 7.1
      
    
  
    
      
         密探

        2026 / 电影 / 巴西 法国 德国 荷兰 / 葡萄牙语 / 瓦格纳·马拉 乌多·基尔 
        类型: 惊悚 / 剧情
        豆瓣评分: 7.8
      
    
  
    
      
         浴血黑帮：不朽传奇

        2026 / 电影 / 英国 法国 美国 / 英语 / 基里安·墨菲 丽贝卡·弗格森 
        类型: 历史 / 犯罪 / 剧情
        豆瓣评分: 7.0
      
    
  
    
      
         至尊马蒂

        2026 / 电影 / 美国 芬兰 / 英语 / 提莫西·查拉梅 格温妮斯·帕特洛 
        类型: 运动 / 剧情
        豆瓣评分: 7.3
      
    
  
    
      
         惊天魔盗团3

        2025 / 电影 / 美国 / 英语 / 杰西·艾森伯格 伍迪·哈里森 
        类型: 动作 / 犯罪 / 剧情
        豆瓣评分: 5.8
      
    
  
    
      
         哈姆奈特

        2025 / 电影 / 英国 美国 / 英语 / 杰西·巴克利 保罗·麦斯卡 
        类型: 历史 / 爱情 / 剧情
        豆瓣评分: 8.1
      
    
  
    
      
         飞行家

        2026 / 电影 / 中国大陆 / 汉语普通话 东北话 / 蒋奇明 李雪琴 
        类型: 喜剧 / 剧情
        豆瓣评分: 7.2
      
    
  
    
      
         搜查瑠公圳

        2026 / 电影 / 中国台湾 / 汉语普通话 闽南语 四川方言 / 朱轩洋 吴卓源 
        类型: 犯罪 / 悬疑 / 剧情
        豆瓣评分: 6.1
      
    
  
    
      
         马腾你别走

        2026 / 电影 / 中国大陆 / 汉语普通话 / 林更新 李幼斌 
        类型: 喜剧 / 剧情
        豆瓣评分: 7.0
      
    
  
    
      
         罪人

        2025 / 电影 / 美国 / 英语 / 迈克尔·B·乔丹 海莉·斯坦菲尔德 
        类型: 恐怖 / 惊悚 / 剧情
        豆瓣评分: 7.8
      
    
  
    
      
         一战再战

        2025 / 电影 / 美国 / 英语 西班牙语 / 莱昂纳多·迪卡普里奥 西恩·潘 
        类型: 动作 / 犯罪 / 惊悚 / 剧情
        豆瓣评分: 8.2
      
    
  
    
      
         洛杉矶劫案

        2026 / 电影 / 美国 英国 / 英语 / 克里斯·海姆斯沃斯 马克·鲁法洛 
        类型: 动作 / 犯罪 / 剧情
        豆瓣评分: 7.2
      
    
  
    
      
         情感价值

        2025 / 电影 / 挪威 德国 丹麦 法国 瑞典 英国 / 挪威语 / 雷娜特·赖因斯夫 斯特兰·斯卡斯加德 
        类型: 喜剧 / 剧情
        豆瓣评分: 7.5
      
    
  
    
      
         家弑服务

        2025 / 电影 / 美国 / 英语 / 西德尼·斯维尼 阿曼达·塞弗里德 
        类型: 惊悚
        豆瓣评分: 7.1
      
    
  
    
      
         如何大赚一笔

        2026 / 电影 / 美国 / 英语 / 格伦·鲍威尔 玛格丽特·库里 
        类型: 喜剧 / 惊悚 / 剧情
        豆瓣评分: 5.8
      
    
  
    
      
         弗兰肯斯坦

        2025 / 电影 / 墨西哥 美国 / 英语 丹麦语 / 奥斯卡·伊萨克 雅各布·艾洛蒂 
        类型: 恐怖 / 科幻 / 剧情
        豆瓣评分: 7.3
      
    
  
    
      
         爱的证明

        2025 / 电影 / 法国 / 法语 / 艾拉·朗夫 莫妮亚·乔柯里 
        类型: 同性 / 喜剧 / 剧情
        豆瓣评分: 8.1
      
    
  
    
      
         局外人

        2025 / 电影 / 法国 / 法语 阿拉伯语 拉丁语 / 本杰明·瓦赞 丽贝卡·马德 
        类型: 犯罪 / 剧情
        豆瓣评分: 7.2
      
    
  
    
      
         137号案件

        2025 / 电影 / 法国 / 法语 / 蕾雅·德吕盖 帕斯卡·桑格拉 
        类型: 犯罪 / 剧情
        豆瓣评分: 7.6
      
    
  

"""


def parse_movie_data():
    """
    从WebFetch获取的内容中解析电影数据
    """
    try:
        # 按行分割内容
        lines = webfetch_content.strip().split('\n')
        
        # 电影列表
        movies = []
        
        # 临时存储当前电影信息
        current_movie = {}
        
        # 标记是否开始解析电影
        start_parsing = False
        
        # 解析每一行
        for line in lines:
            line = line.strip()
            if not line:
                # 如果遇到空行，并且当前有电影信息，保存并开始新的电影
                if current_movie and 'title' in current_movie:
                    movies.append(current_movie)
                    current_movie = {}
                continue
            
            # 跳过标题行
            if line == '最近更新 / 上映时间 /  豆瓣评分 / 近期热门↓':
                start_parsing = True
                continue
            
            # 开始解析电影数据
            if start_parsing:
                # 检查是否是电影标题（不是年份、类型或评分）
                if not line.startswith('202') and not line.startswith('类型:') and not line.startswith('豆瓣评分:'):
                    # 如果已经有电影信息，保存并开始新的电影
                    if current_movie and 'title' in current_movie:
                        movies.append(current_movie)
                        current_movie = {}
                    current_movie['title'] = line
                
                # 解析年份、类型、国家、语言、演员
                elif line.startswith('202') and '/' in line:
                    info_parts = [p.strip() for p in line.split('/')]
                    if len(info_parts) >= 1:
                        current_movie['year'] = info_parts[0]
                    if len(info_parts) >= 2:
                        current_movie['type'] = info_parts[1]
                    if len(info_parts) >= 3:
                        current_movie['country'] = info_parts[2]
                    if len(info_parts) >= 4:
                        current_movie['language'] = info_parts[3]
                    if len(info_parts) >= 5:
                        current_movie['actors'] = info_parts[4]
                
                # 解析类型标签
                elif line.startswith('类型:'):
                    genre = line.replace('类型:', '').strip()
                    current_movie['genre'] = genre
                    
                # 解析豆瓣评分
                elif line.startswith('豆瓣评分:'):
                    rating = line.replace('豆瓣评分:', '').strip()
                    current_movie['rating'] = rating
        
        # 保存最后一部电影
        if current_movie and 'title' in current_movie:
            movies.append(current_movie)
        
        # 打印解析结果
        print(f"成功解析 {len(movies)} 部电影:")
        for i, movie in enumerate(movies):
            print(f"\n{i+1}. 电影标题: {movie.get('title')}")
            print(f"   年份: {movie.get('year')}")
            print(f"   类型: {movie.get('type')}")
            print(f"   国家: {movie.get('country')}")
            print(f"   语言: {movie.get('language')}")
            print(f"   演员: {movie.get('actors')}")
            print(f"   类型标签: {movie.get('genre')}")
            print(f"   豆瓣评分: {movie.get('rating')}")
            
        return movies
        
    except Exception as e:
        print(f"错误: {e}")
        return []


def generate_placeholder_images(movies):
    """
    为电影生成占位图片链接
    """
    print("\n=== 为电影生成占位图片 ===")
    for i, movie in enumerate(movies):
        # 使用电影标题生成占位图片
        title = movie.get('title', '').replace(' ', '+')
        placeholder_url = f"https://via.placeholder.com/300x450?text={title}"
        print(f"{i+1}. {movie.get('title')}: {placeholder_url}")
        movie['poster'] = placeholder_url
    
    return movies


if __name__ == "__main__":
    print("=== 解析电影数据 ===")
    movies = parse_movie_data()
    print("\n=== 生成占位图片 ===")
    movies_with_posters = generate_placeholder_images(movies)
    
    # 打印最终结果
    print("\n=== 最终结果 ===")
    for i, movie in enumerate(movies_with_posters):
        print(f"\n{i+1}. {movie.get('title')}")
        print(f"   评分: {movie.get('rating')}")
        print(f"   海报: {movie.get('poster')}")

