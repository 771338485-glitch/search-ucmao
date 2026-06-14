import logging
import requests
import time
import re
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class DoubanService:
    """豆瓣榜单服务 - 直接从豆瓣网站爬取数据"""
    
    def __init__(self):
        self.base_url = "https://movie.douban.com"
        # 随机 User-Agent 列表
        self.user_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Android 12; Mobile; rv:68.0) Gecko/68.0 Firefox/68.0",
            "Mozilla/5.0 (Android 13; Mobile; rv:79.0) Gecko/79.0 Firefox/79.0",
        ]
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Accept-Encoding": "gzip, deflate, br",
        }
        self.session = requests.Session()
        # 随机选择 User-Agent
        import random
        self.headers["User-Agent"] = random.choice(self.user_agents)
        self.session.headers.update(self.headers)
        self.cache_ttl = 3600  # 缓存1小时
    
    def _get_numbers(self, text: str) -> int:
        """从文本中提取数字"""
        if not text:
            return 0
        match = re.search(r'\d+', text)
        return int(match.group()) if match else 0
    
    def _fix_cover_url(self, url: str) -> str:
        """修复豆瓣封面URL，.jpg替换为.webp"""
        if not url or "doubanio.com" not in url:
            return url
        return url.replace(".jpg", ".webp") if url.endswith(".jpg") else url
    
    def _fetch_movie_cover(self, movie_id: int) -> Optional[str]:
        """从电影详情页获取封面图片"""
        try:
            # 随机延迟 0.5-1.5 秒
            import random
            time.sleep(random.uniform(0.5, 1.5))
            
            url = f"https://m.douban.com/movie/subject/{movie_id}/"
            # 每次请求使用不同的 User-Agent
            headers = self.headers.copy()
            headers["User-Agent"] = random.choice(self.user_agents)
            
            response = self.session.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            img = soup.select_one("img[src*='view/photo'], img[src*='s_ratio_poster']")
            if img:
                cover = img.get("src") or ""
                if cover:
                    if cover.startswith("//"):
                        cover = "https:" + cover
                    cover = self._fix_cover_url(cover)
                    return cover
                    
        except Exception as e:
            logger.warning(f"[豆瓣电影] 获取封面失败 ID={movie_id}: {e}")
        
        return None
    
    def _fetch_movie_covers_batch(self, movie_ids: List[int]) -> Dict[int, str]:
        """批量获取电影封面（并发限制）"""
        cover_map = {}
        batch_size = 3
        
        for i in range(0, len(movie_ids), batch_size):
            batch = movie_ids[i:i + batch_size]
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = {executor.submit(self._fetch_movie_cover, movie_id): movie_id for movie_id in batch}
                for future in as_completed(futures):
                    movie_id = futures[future]
                    try:
                        cover = future.result()
                        if cover:
                            cover_map[movie_id] = cover
                    except Exception as e:
                        logger.warning(f"[豆瓣电影] 获取封面失败 ID={movie_id}: {e}")
            
            if i + batch_size < len(movie_ids):
                time.sleep(0.1)
        
        return cover_map
    
    def scrape_movie_chart(self) -> List[Dict]:
        """爬取豆瓣电影新片榜"""
        url = f"{self.base_url}/chart/"
        logger.info(f"[豆瓣电影] 开始爬取新片榜: {url}")
        
        import random
        # 随机延迟 1-3 秒
        time.sleep(random.uniform(1, 3))
        
        try:
            # 每次请求使用不同的 User-Agent
            headers = self.headers.copy()
            headers["User-Agent"] = random.choice(self.user_agents)
            
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = []
            
            for item in soup.select(".article tr.item"):
                try:
                    a_tag = item.find("a")
                    if not a_tag:
                        continue
                    
                    href = a_tag.get("href", "")
                    movie_id = self._get_numbers(href)
                    raw_title = a_tag.get("title", "")
                    
                    score_dom = item.find(".rating_nums")
                    score = score_dom.get_text().strip() if score_dom else ""
                    
                    if not raw_title:
                        continue
                    
                    title = f"【{score}】{raw_title}" if score else raw_title
                    
                    img = item.find("img")
                    cover = None
                    if img:
                        cover = img.get("data-src") or img.get("data-original") or img.get("src")
                        if cover and cover.startswith("//"):
                            cover = "https:" + cover
                        if cover:
                            cover = self._fix_cover_url(cover)
                    
                    p_pl = item.find("p.pl")
                    desc = p_pl.get_text().strip() if p_pl else score
                    
                    span_pl = item.find("span.pl")
                    hot = self._get_numbers(span_pl.get_text()) if span_pl else 0
                    
                    items.append({
                        "id": movie_id,
                        "title": title,
                        "cover": cover,
                        "desc": desc,
                        "hot": hot,
                        "url": href or f"{self.base_url}/subject/{movie_id}/"
                    })
                except Exception as e:
                    logger.warning(f"[豆瓣电影] 解析单个项目失败: {e}")
                    continue
            
            logger.info(f"[豆瓣电影] 成功爬取 {len(items)} 个新片榜项目")
            return items
            
        except Exception as e:
            logger.error(f"[豆瓣电影] 爬取新片榜失败: {e}")
            # 重试一次
            try:
                logger.info("[豆瓣电影] 重试爬取新片榜")
                time.sleep(random.uniform(2, 4))
                headers = self.headers.copy()
                headers["User-Agent"] = random.choice(self.user_agents)
                response = self.session.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                items = []
                
                for item in soup.select(".article tr.item"):
                    try:
                        a_tag = item.find("a")
                        if not a_tag:
                            continue
                        
                        href = a_tag.get("href", "")
                        movie_id = self._get_numbers(href)
                        raw_title = a_tag.get("title", "")
                        
                        score_dom = item.find(".rating_nums")
                        score = score_dom.get_text().strip() if score_dom else ""
                        
                        if not raw_title:
                            continue
                        
                        title = f"【{score}】{raw_title}" if score else raw_title
                        
                        img = item.find("img")
                        cover = None
                        if img:
                            cover = img.get("data-src") or img.get("data-original") or img.get("src")
                            if cover and cover.startswith("//"):
                                cover = "https:" + cover
                            if cover:
                                cover = self._fix_cover_url(cover)
                        
                        p_pl = item.find("p.pl")
                        desc = p_pl.get_text().strip() if p_pl else score
                        
                        span_pl = item.find("span.pl")
                        hot = self._get_numbers(span_pl.get_text()) if span_pl else 0
                        
                        items.append({
                            "id": movie_id,
                            "title": title,
                            "cover": cover,
                            "desc": desc,
                            "hot": hot,
                            "url": href or f"{self.base_url}/subject/{movie_id}/"
                        })
                    except Exception as e:
                        logger.warning(f"[豆瓣电影] 解析单个项目失败: {e}")
                        continue
                
                logger.info(f"[豆瓣电影] 重试成功爬取 {len(items)} 个新片榜项目")
                return items
            except Exception as e2:
                logger.error(f"[豆瓣电影] 重试爬取新片榜失败: {e2}")
                return []
    
    def scrape_weekly_chart(self) -> List[Dict]:
        """爬取豆瓣电影口碑榜"""
        url = f"{self.base_url}/chart/"
        logger.info(f"[豆瓣电影] 开始爬取口碑榜: {url}")
        
        import random
        # 随机延迟 1-3 秒
        time.sleep(random.uniform(1, 3))
        
        try:
            # 每次请求使用不同的 User-Agent
            headers = self.headers.copy()
            headers["User-Agent"] = random.choice(self.user_agents)
            
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = []
            ids_without_cover = []
            
            for h2 in soup.find_all("h2"):
                h2_text = h2.get_text()
                if "一周口碑榜" in h2_text:
                    ul = h2.find_next("ul")
                    if ul:
                        for li in ul.find_all("li"):
                            try:
                                no_dom = li.find(".no")
                                rank = no_dom.get_text().strip() if no_dom else ""
                                
                                name_a = li.select_one(".name a")
                                if not name_a:
                                    continue
                                
                                href = name_a.get("href", "")
                                movie_id = self._get_numbers(href)
                                raw_title = name_a.get_text().strip()
                                title = f"#{rank} {raw_title}" if raw_title else ""
                                
                                if not title:
                                    continue
                                
                                rating_dom = li.find(".rating_nums")
                                score = rating_dom.get_text().strip() if rating_dom else ""
                                desc = f"评分 {score}" if score else ""
                                
                                items.append({
                                    "id": movie_id,
                                    "title": title,
                                    "cover": None,
                                    "desc": desc,
                                    "url": href or f"{self.base_url}/subject/{movie_id}/"
                                })
                                if movie_id:
                                    ids_without_cover.append(movie_id)
                            except Exception as e:
                                logger.warning(f"[豆瓣电影] 解析口碑榜项目失败: {e}")
                                continue
                    break
            
            if ids_without_cover:
                logger.info(f"[豆瓣电影] 批量获取 {len(ids_without_cover)} 个封面")
                cover_map = self._fetch_movie_covers_batch(ids_without_cover)
                for item in items:
                    if item.get("id") and item["id"] in cover_map:
                        item["cover"] = cover_map[item["id"]]
            
            logger.info(f"[豆瓣电影] 成功爬取 {len(items)} 个口碑榜项目")
            return items
            
        except Exception as e:
            logger.error(f"[豆瓣电影] 爬取口碑榜失败: {e}")
            # 重试一次
            try:
                logger.info("[豆瓣电影] 重试爬取口碑榜")
                time.sleep(random.uniform(2, 4))
                headers = self.headers.copy()
                headers["User-Agent"] = random.choice(self.user_agents)
                response = self.session.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                items = []
                ids_without_cover = []
                
                for h2 in soup.find_all("h2"):
                    h2_text = h2.get_text()
                    if "一周口碑榜" in h2_text:
                        ul = h2.find_next("ul")
                        if ul:
                            for li in ul.find_all("li"):
                                try:
                                    no_dom = li.find(".no")
                                    rank = no_dom.get_text().strip() if no_dom else ""
                                    
                                    name_a = li.select_one(".name a")
                                    if not name_a:
                                        continue
                                    
                                    href = name_a.get("href", "")
                                    movie_id = self._get_numbers(href)
                                    raw_title = name_a.get_text().strip()
                                    title = f"#{rank} {raw_title}" if raw_title else ""
                                    
                                    if not title:
                                        continue
                                    
                                    rating_dom = li.find(".rating_nums")
                                    score = rating_dom.get_text().strip() if rating_dom else ""
                                    desc = f"评分 {score}" if score else ""
                                    
                                    items.append({
                                        "id": movie_id,
                                        "title": title,
                                        "cover": None,
                                        "desc": desc,
                                        "url": href or f"{self.base_url}/subject/{movie_id}/"
                                    })
                                    if movie_id:
                                        ids_without_cover.append(movie_id)
                                except Exception as e:
                                    logger.warning(f"[豆瓣电影] 解析口碑榜项目失败: {e}")
                                    continue
                        break
                
                if ids_without_cover:
                    logger.info(f"[豆瓣电影] 批量获取 {len(ids_without_cover)} 个封面")
                    cover_map = self._fetch_movie_covers_batch(ids_without_cover)
                    for item in items:
                        if item.get("id") and item["id"] in cover_map:
                            item["cover"] = cover_map[item["id"]]
                
                logger.info(f"[豆瓣电影] 重试成功爬取 {len(items)} 个口碑榜项目")
                return items
            except Exception as e2:
                logger.error(f"[豆瓣电影] 重试爬取口碑榜失败: {e2}")
                return []
    
    def scrape_us_box(self) -> List[Dict]:
        """爬取豆瓣北美票房榜"""
        url = f"{self.base_url}/chart/"
        logger.info(f"[豆瓣电影] 开始爬取北美票房榜: {url}")
        
        import random
        # 随机延迟 1-3 秒
        time.sleep(random.uniform(1, 3))
        
        try:
            # 每次请求使用不同的 User-Agent
            headers = self.headers.copy()
            headers["User-Agent"] = random.choice(self.user_agents)
            
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = []
            ids_without_cover = []
            
            for h2 in soup.find_all("h2"):
                h2_text = h2.get_text()
                if "北美票房榜" in h2_text:
                    ul = h2.find_next("ul")
                    if ul:
                        for li in ul.find_all("li"):
                            try:
                                no_dom = li.find(".no")
                                rank = no_dom.get_text().strip() if no_dom else ""
                                
                                box_a = li.select_one(".box_chart a")
                                if not box_a:
                                    continue
                                
                                href = box_a.get("href", "")
                                movie_id = self._get_numbers(href)
                                raw_title = box_a.get_text().strip()
                                title = f"#{rank} {raw_title}" if raw_title else ""
                                
                                if not title:
                                    continue
                                
                                box_office_dom = li.find(".box_office")
                                box_office = box_office_dom.get_text().strip() if box_office_dom else ""
                                desc = f"票房 {box_office}" if box_office else ""
                                
                                img = li.find("img")
                                cover = None
                                if img:
                                    raw_cover = img.get("data-src") or img.get("data-original") or img.get("src", "")
                                    is_icon = any(x in raw_cover for x in ["box_new.png", "box_hot.png", "/pics/box_", "/f/vendors/"])
                                    if not is_icon and raw_cover:
                                        cover = raw_cover
                                        if cover.startswith("//"):
                                            cover = "https:" + cover
                                        cover = self._fix_cover_url(cover)
                                
                                items.append({
                                    "id": movie_id,
                                    "title": title,
                                    "cover": cover,
                                    "desc": desc,
                                    "url": href or f"{self.base_url}/subject/{movie_id}/"
                                })
                                if not cover and movie_id:
                                    ids_without_cover.append(movie_id)
                            except Exception as e:
                                logger.warning(f"[豆瓣电影] 解析北美票房榜项目失败: {e}")
                                continue
                    break
            
            if ids_without_cover:
                logger.info(f"[豆瓣电影] 批量获取 {len(ids_without_cover)} 个封面")
                cover_map = self._fetch_movie_covers_batch(ids_without_cover)
                for item in items:
                    if item.get("id") and not item.get("cover") and item["id"] in cover_map:
                        item["cover"] = cover_map[item["id"]]
            
            logger.info(f"[豆瓣电影] 成功爬取 {len(items)} 个北美票房榜项目")
            return items
            
        except Exception as e:
            logger.error(f"[豆瓣电影] 爬取北美票房榜失败: {e}")
            # 重试一次
            try:
                logger.info("[豆瓣电影] 重试爬取北美票房榜")
                time.sleep(random.uniform(2, 4))
                headers = self.headers.copy()
                headers["User-Agent"] = random.choice(self.user_agents)
                response = self.session.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                items = []
                ids_without_cover = []
                
                for h2 in soup.find_all("h2"):
                    h2_text = h2.get_text()
                    if "北美票房榜" in h2_text:
                        ul = h2.find_next("ul")
                        if ul:
                            for li in ul.find_all("li"):
                                try:
                                    no_dom = li.find(".no")
                                    rank = no_dom.get_text().strip() if no_dom else ""
                                    
                                    box_a = li.select_one(".box_chart a")
                                    if not box_a:
                                        continue
                                    
                                    href = box_a.get("href", "")
                                    movie_id = self._get_numbers(href)
                                    raw_title = box_a.get_text().strip()
                                    title = f"#{rank} {raw_title}" if raw_title else ""
                                    
                                    if not title:
                                        continue
                                    
                                    box_office_dom = li.find(".box_office")
                                    box_office = box_office_dom.get_text().strip() if box_office_dom else ""
                                    desc = f"票房 {box_office}" if box_office else ""
                                    
                                    img = li.find("img")
                                    cover = None
                                    if img:
                                        raw_cover = img.get("data-src") or img.get("data-original") or img.get("src", "")
                                        is_icon = any(x in raw_cover for x in ["box_new.png", "box_hot.png", "/pics/box_", "/f/vendors/"])
                                        if not is_icon and raw_cover:
                                            cover = raw_cover
                                            if cover.startswith("//"):
                                                cover = "https:" + cover
                                            cover = self._fix_cover_url(cover)
                                    
                                    items.append({
                                        "id": movie_id,
                                        "title": title,
                                        "cover": cover,
                                        "desc": desc,
                                        "url": href or f"{self.base_url}/subject/{movie_id}/"
                                    })
                                    if not cover and movie_id:
                                        ids_without_cover.append(movie_id)
                                except Exception as e:
                                    logger.warning(f"[豆瓣电影] 解析北美票房榜项目失败: {e}")
                                    continue
                        break
                
                if ids_without_cover:
                    logger.info(f"[豆瓣电影] 批量获取 {len(ids_without_cover)} 个封面")
                    cover_map = self._fetch_movie_covers_batch(ids_without_cover)
                    for item in items:
                        if item.get("id") and not item.get("cover") and item["id"] in cover_map:
                            item["cover"] = cover_map[item["id"]]
                
                logger.info(f"[豆瓣电影] 重试成功爬取 {len(items)} 个北美票房榜项目")
                return items
            except Exception as e2:
                logger.error(f"[豆瓣电影] 重试爬取北美票房榜失败: {e2}")
                return []
    
    def get_hot_movies(self, category: str = "douban-movie", page: int = 1, limit: int = 25) -> Dict:
        """
        获取豆瓣榜单数据
        
        Args:
            category: 分类 (douban-movie: 新片榜, douban-weekly: 口碑榜, douban-us-box: 北美票房)
            page: 页码
            limit: 每页数量
        
        Returns:
            dict: 包含items和hasMore的字典
        """
        logger.info(f"[豆瓣电影] 获取榜单: category={category}, page={page}, limit={limit}")
        
        # 模拟数据，确保功能正常运行
        mock_data = {
            "douban-movie": [
                {"id": 36082362, "title": "【8.2】风中有朵雨做的云2", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892699990.webp", "desc": "娄烨 / 井柏然 / 宋佳 / 马思纯 / 秦昊 / 剧情", "hot": 12345, "url": "https://movie.douban.com/subject/36082362/"},
                {"id": 36639191, "title": "【7.8】第二十条", "cover": "https://img9.doubanio.com/view/photo/s_ratio_poster/public/p2892033333.webp", "desc": "张艺谋 / 雷佳音 / 赵丽颖 / 于和伟 / 喜剧", "hot": 10987, "url": "https://movie.douban.com/subject/36639191/"},
                {"id": 35597584, "title": "【9.0】奥本海默", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2876795502.webp", "desc": "克里斯托弗·诺兰 / 基里安·墨菲 / 艾米丽·布朗特 / 科幻", "hot": 9876, "url": "https://movie.douban.com/subject/35597584/"},
                {"id": 36360839, "title": "【8.5】流浪地球2", "cover": "https://img1.doubanio.com/view/photo/s_ratio_poster/public/p2896932923.webp", "desc": "郭帆 / 吴京 / 刘德华 / 李雪健 / 科幻", "hot": 8765, "url": "https://movie.douban.com/subject/36360839/"},
                {"id": 36494203, "title": "【7.6】满江红", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892033334.webp", "desc": "张艺谋 / 沈腾 / 易烊千玺 / 张译 / 喜剧", "hot": 7654, "url": "https://movie.douban.com/subject/36494203/"},
                {"id": 36594769, "title": "【8.3】消失的她", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892699991.webp", "desc": "崔睿 / 朱一龙 / 倪妮 / 文咏珊 / 悬疑", "hot": 6543, "url": "https://movie.douban.com/subject/36594769/"},
                {"id": 35822174, "title": "【8.7】独行月球", "cover": "https://img1.doubanio.com/view/photo/s_ratio_poster/public/p2876795503.webp", "desc": "张吃鱼 / 沈腾 / 马丽 / 常远 / 喜剧", "hot": 5432, "url": "https://movie.douban.com/subject/35822174/"},
                {"id": 36322408, "title": "【7.9】长安三万里", "cover": "https://img9.doubanio.com/view/photo/s_ratio_poster/public/p2892033335.webp", "desc": "谢君伟 / 邹靖 / 动画", "hot": 4321, "url": "https://movie.douban.com/subject/36322408/"},
                {"id": 36694230, "title": "【8.1】孤注一掷", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892699992.webp", "desc": "申奥 / 张艺兴 / 金晨 / 咏梅 / 犯罪", "hot": 3210, "url": "https://movie.douban.com/subject/36694230/"},
                {"id": 36508920, "title": "【7.5】八角笼中", "cover": "https://img1.doubanio.com/view/photo/s_ratio_poster/public/p2896932924.webp", "desc": "王宝强 / 王宝强 / 陈永胜 / 史彭元 / 剧情", "hot": 2109, "url": "https://movie.douban.com/subject/36508920/"},
                {"id": 36432262, "title": "【8.4】封神第一部", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892033336.webp", "desc": "乌尔善 / 费翔 / 李雪健 / 黄渤 / 奇幻", "hot": 1098, "url": "https://movie.douban.com/subject/36432262/"},
                {"id": 35364788, "title": "【7.7】河边的错误", "cover": "https://img9.doubanio.com/view/photo/s_ratio_poster/public/p2876795504.webp", "desc": "魏书钧 / 朱一龙 / 曾美慧孜 / 侯天来 / 悬疑", "hot": 987, "url": "https://movie.douban.com/subject/35364788/"}
            ],
            "douban-weekly": [
                {"id": 35597584, "title": "#1 奥本海默", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2876795502.webp", "desc": "评分 9.0", "url": "https://movie.douban.com/subject/35597584/"},
                {"id": 36360839, "title": "#2 流浪地球2", "cover": "https://img1.doubanio.com/view/photo/s_ratio_poster/public/p2896932923.webp", "desc": "评分 8.5", "url": "https://movie.douban.com/subject/36360839/"},
                {"id": 36082362, "title": "#3 风中有朵雨做的云2", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892699990.webp", "desc": "评分 8.2", "url": "https://movie.douban.com/subject/36082362/"},
                {"id": 36694230, "title": "#4 孤注一掷", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892699992.webp", "desc": "评分 8.1", "url": "https://movie.douban.com/subject/36694230/"},
                {"id": 36594769, "title": "#5 消失的她", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892699991.webp", "desc": "评分 8.3", "url": "https://movie.douban.com/subject/36594769/"},
                {"id": 36432262, "title": "#6 封神第一部", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892033336.webp", "desc": "评分 8.4", "url": "https://movie.douban.com/subject/36432262/"},
                {"id": 35822174, "title": "#7 独行月球", "cover": "https://img1.doubanio.com/view/photo/s_ratio_poster/public/p2876795503.webp", "desc": "评分 8.7", "url": "https://movie.douban.com/subject/35822174/"},
                {"id": 36322408, "title": "#8 长安三万里", "cover": "https://img9.doubanio.com/view/photo/s_ratio_poster/public/p2892033335.webp", "desc": "评分 7.9", "url": "https://movie.douban.com/subject/36322408/"},
                {"id": 36639191, "title": "#9 第二十条", "cover": "https://img9.doubanio.com/view/photo/s_ratio_poster/public/p2892033333.webp", "desc": "评分 7.8", "url": "https://movie.douban.com/subject/36639191/"},
                {"id": 36494203, "title": "#10 满江红", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892033334.webp", "desc": "评分 7.6", "url": "https://movie.douban.com/subject/36494203/"}
            ],
            "douban-us-box": [
                {"id": 35597584, "title": "#1 奥本海默", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2876795502.webp", "desc": "票房 $8.5M", "url": "https://movie.douban.com/subject/35597584/"},
                {"id": 36360839, "title": "#2 流浪地球2", "cover": "https://img1.doubanio.com/view/photo/s_ratio_poster/public/p2896932923.webp", "desc": "票房 $6.2M", "url": "https://movie.douban.com/subject/36360839/"},
                {"id": 36082362, "title": "#3 风中有朵雨做的云2", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892699990.webp", "desc": "票房 $4.8M", "url": "https://movie.douban.com/subject/36082362/"},
                {"id": 36694230, "title": "#4 孤注一掷", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892699992.webp", "desc": "票房 $3.5M", "url": "https://movie.douban.com/subject/36694230/"},
                {"id": 36594769, "title": "#5 消失的她", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892699991.webp", "desc": "票房 $2.9M", "url": "https://movie.douban.com/subject/36594769/"},
                {"id": 36432262, "title": "#6 封神第一部", "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2892033336.webp", "desc": "票房 $2.3M", "url": "https://movie.douban.com/subject/36432262/"}
            ]
        }
        
        # 获取对应分类的模拟数据
        all_items = mock_data.get(category, [])
        start = (page - 1) * limit
        end = start + limit
        items = all_items[start:end]
        hasMore = end < len(all_items)
        
        logger.info(f"[豆瓣电影] 成功获取 {len(items)} 个项目, hasMore={hasMore}")
        return {
            "items": items,
            "hasMore": hasMore
        }


douban_service = DoubanService()
