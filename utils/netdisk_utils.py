import re
import requests
import aiohttp
import random
from configs.app_config import user_agents

def match_netdisk_link(link: str) -> str:
    """
    匹配网盘链接，返回对应的网盘名称，未匹配则返回"其他"
    """
    netdisk_rules = [
        # 网盘
        ("百度网盘", r'(?:https?://)?(?:pan\.baidu\.com|bdpan\.com|baiduyun\.com)/'),
        ("夸克网盘", r'(?:https?://)?(?:www\.)?pan\.(?:quark|qoark)\.cn/'),
        ("迅雷网盘", r'(?:https?://)?pan\.xunlei\.com/'),
        ("UC网盘", r'(?:https?://)?(?:pan\.uc\.cn|drive\.uc\.cn)/'),
        ("悟空网盘", r'(?:https?://)?pan\.wkbrowser\.com/'),
        ("快兔网盘", r'(?:https?://)?(?:diskyun\.com|www\.diskyun\.com)/'),
        ("115网盘", r'(?:https?://)?(?:115\.com|115pan\.com|115cdn\.com|anxia\.com)/'),
        # 云盘
        ("阿里云盘", r'(?:https?://)?(?:drive\.aliyun\.com|aliyundrive\.com|alipan\.com)/'),
        ("天翼云盘", r'(?:https?://)?cloud\.189\.cn/'),
        ("移动云盘", r'(?:https?://)?(?:pan\.10086\.cn|caiyun\.139\.com|yun\.139\.com)/'),
        ("联通云盘", r'(?:https?://)?pan\.wo\.cn/'),
        ("123云盘", r'(?:https?://)?(?:123pan\.com|123\d{3}\.com)/'),
        # 其他网盘
        ("PikPak", r'(?:https?://)?(?:www\.)?pikpak\.com/'),
        # 链接类型
        ("磁力链接", r'^magnet:\?xt=urn:btih:'),
        ("迅雷链接", r'thunder://[A-Za-z0-9+/=]+'),
        ("电驴链接", r'^ed2k://')
    ]
    link_lower = link.strip().lower()
    for name, pattern in netdisk_rules:
        if re.search(pattern, link_lower, re.IGNORECASE):
            return name
    return "其他"

import logging

logger = logging.getLogger(__name__)

def check_link_validity(url):
    """
    检查链接是否有效
    返回: bool - 链接是否有效
    """
    try:
        # 针对不同类型的链接采用不同的检查策略
        netdisk_name = match_netdisk_link(url)
        logger.debug(f"开始检查链接有效性: {url} (网盘类型: {netdisk_name})")
        
        # 对于HTTP/HTTPS链接
        if url.startswith(('http://', 'https://')):
            # 使用更真实的浏览器 headers
            browser_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1"
            }
            
            # 对于夸克网盘，使用API接口检查
            if netdisk_name == "夸克网盘":
                try:
                    # 提取分享ID
                    share_id = ""
                    if "/s/" in url:
                        share_id = url.split("/s/")[1].split("#")[0].split("?")[0]
                    
                    if not share_id:
                        logger.debug(f"无法从链接中提取分享ID: {url}")
                        return True
                    
                    # 使用API接口检查
                    api_url = "https://pan.quark.cn/1/clouddrive/share/sharepage/token"
                    api_headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                        "Referer": "https://pan.quark.cn/",
                        "Origin": "https://pan.quark.cn"
                    }
                    
                    post_data = {
                        "pwd_id": share_id,
                        "passcode": ""
                    }
                    
                    # 创建session来维护cookies
                    session = requests.Session()
                    # 先访问主页获取必要的cookies
                    session.get("https://pan.quark.cn", headers=api_headers, timeout=3)
                    
                    # 调用API
                    api_response = session.post(api_url, json=post_data, headers=api_headers, timeout=5)
                    
                    logger.debug(f"夸克网盘API响应状态码: {api_response.status_code}")
                    
                    if api_response.status_code == 200:
                        try:
                            data = api_response.json()
                            if data.get("code") == 0:
                                logger.debug(f"夸克网盘链接有效: {url}")
                                return True
                            else:
                                logger.debug(f"夸克网盘链接无效: {url} (原因: code={data.get('code')}, message={data.get('message')})")
                                return False
                        except Exception as e:
                            logger.debug(f"解析API响应失败: {e}")
                            return True
                    else:
                        # 404或其他状态码表示链接无效
                        try:
                            data = api_response.json()
                            logger.debug(f"夸克网盘链接无效: {url} (原因: code={data.get('code')}, message={data.get('message')})")
                        except:
                            logger.debug(f"夸克网盘链接无效: {url} (原因: 状态码 {api_response.status_code})")
                        return False
                except Exception as e:
                    # 如果API请求失败，认为链接无效
                    logger.debug(f"检查夸克网盘链接失败: {url} (错误: {e})")
                    return False

            # 对于百度网盘，使用GET请求检查
            elif netdisk_name == "百度网盘":
                try:
                    browser_headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9"
                    }

                    logger.debug(f"开始检查百度网盘链接: {url}")
                    get_response = requests.get(url, headers=browser_headers, timeout=10, allow_redirects=True)
                    logger.debug(f"百度网盘链接响应状态码: {get_response.status_code}")

                    # 先检查状态码，再检查内容（统一同步和异步版本的行为）
                    if get_response.status_code not in [200, 301, 302, 303, 307, 308]:
                        logger.debug(f"百度网盘链接无效: {url} (原因: 状态码 {get_response.status_code})")
                        return False

                    # 读取前20000个字符，增加匹配成功率
                    content = get_response.text[:20000]

                    # 先检查响应内容是否包含失效信息（优先检查）
                    failure_keywords = [
                        "分享链接已失效",
                        "链接已过期",
                        "链接不存在",
                        "文件不存在",
                        "分享不存在",
                        "此链接分享内容可能因为涉及侵权、色情、反动、低俗等信息，无法访问",
                        "该分享已取消",
                        "分享已取消",
                        "分享的文件已经被取消",
                        "你来晚了",
                        "链接不存在"
                    ]

                    # 检查是否包含任何失效关键词
                    for keyword in failure_keywords:
                        if keyword in content:
                            logger.debug(f"百度网盘链接无效: {url} (原因: 包含关键词 '{keyword}')")
                            return False

                    # 再检查是否包含有效关键词
                    valid_keywords = [
                        "请输入提取码",
                        "分享文件",
                        "保存到网盘",
                        "下载",
                        "保存",
                        "百度网盘",
                        "网盘",
                        "pwd",
                        "提取码"
                    ]

                    for keyword in valid_keywords:
                        if keyword in content:
                            logger.debug(f"百度网盘链接有效: {url} (原因: 包含关键词 '{keyword}')")
                            return True

                    # 状态码正常但没有匹配到关键词，默认认为有效
                    logger.debug(f"百度网盘链接有效: {url} (原因: 状态码正常)")
                    return True

                except Exception as e:
                    # 如果GET请求失败，认为链接无效
                    logger.debug(f"检查百度网盘链接失败: {url} (错误: {e})")
                    return False
            
            # 对于其他网盘，发送HEAD请求检查状态码
            else:
                headers = {
                    "User-Agent": random.choice(user_agents),
                    "Referer": "https://www.google.com/"
                }
                response = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
                logger.debug(f"其他网盘链接响应状态码: {response.status_code}")
                
                # 对于网盘链接，302重定向通常是正常的
                if response.status_code in [200, 301, 302, 303, 307, 308]:
                    logger.debug(f"其他网盘链接有效: {url}")
                    return True
                
                logger.debug(f"其他网盘链接无效: {url} (原因: 状态码 {response.status_code})")
                return False
        
        # 对于磁力链接、迅雷链接等，认为它们始终有效
        elif url.startswith(('magnet:', 'thunder://', 'ed2k://')):
            logger.debug(f"非HTTP链接有效: {url}")
            return True
            
    except Exception as e:
        # 检查失败时，认为链接无效
        logger.debug(f"检查链接失败: {url} (错误: {e})")
        return False
    
    logger.debug(f"链接有效: {url}")
    return True


async def check_link_validity_async(url):
    """
    异步检查链接是否有效
    返回: bool - 链接是否有效
    """
    try:
        # 针对不同类型的链接采用不同的检查策略
        netdisk_name = match_netdisk_link(url)
        logger.debug(f"开始异步检查链接有效性: {url} (网盘类型: {netdisk_name})")
        
        # 对于HTTP/HTTPS链接
        if url.startswith(('http://', 'https://')):
            # 使用更真实的浏览器 headers
            browser_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1"
            }
            
            # 对于夸克网盘，使用API接口检查
            if netdisk_name == "夸克网盘":
                try:
                    # 提取分享ID
                    share_id = ""
                    if "/s/" in url:
                        share_id = url.split("/s/")[1].split("#")[0].split("?")[0]
                    
                    if not share_id:
                        logger.debug(f"无法从链接中提取分享ID: {url}")
                        return False
                    
                    # 使用API接口检查
                    api_url = "https://pan.quark.cn/1/clouddrive/share/sharepage/token"
                    api_headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                        "Referer": "https://pan.quark.cn/",
                        "Origin": "https://pan.quark.cn"
                    }
                    
                    post_data = {
                        "pwd_id": share_id,
                        "passcode": ""
                    }
                    
                    # 创建session来维护cookies
                    async with aiohttp.ClientSession() as session:
                        # 先访问主页获取必要的cookies
                        await session.get("https://pan.quark.cn", headers=api_headers, timeout=aiohttp.ClientTimeout(total=3))
                        
                        # 调用API
                        async with session.post(api_url, json=post_data, headers=api_headers, timeout=aiohttp.ClientTimeout(total=5)) as api_response:
                            logger.debug(f"夸克网盘API响应状态码: {api_response.status}")
                            
                            if api_response.status == 200:
                                try:
                                    data = await api_response.json()
                                    if data.get("code") == 0:
                                        logger.debug(f"夸克网盘链接有效: {url}")
                                        return True
                                    else:
                                        logger.debug(f"夸克网盘链接无效: {url} (原因: code={data.get('code')}, message={data.get('message')})")
                                        return False
                                except Exception as e:
                                    logger.debug(f"解析API响应失败: {e}")
                                    return False
                            else:
                                # 404或其他状态码表示链接无效
                                try:
                                    data = await api_response.json()
                                    logger.debug(f"夸克网盘链接无效: {url} (原因: code={data.get('code')}, message={data.get('message')})")
                                except Exception as e:
                                    logger.debug(f"夸克网盘链接无效: {url} (原因: 状态码 {api_response.status}, 解析响应失败: {e})")
                                return False
                except Exception as e:
                    # 如果API请求失败，认为链接无效
                    logger.debug(f"检查夸克网盘链接失败: {url} (错误: {e})")
                    return False
            
            # 对于百度网盘，使用GET请求检查
            elif netdisk_name == "百度网盘":
                try:
                    browser_headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9"
                    }
                    
                    logger.debug(f"开始检查百度网盘链接: {url}")
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=browser_headers, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=True) as get_response:
                            logger.debug(f"百度网盘链接响应状态码: {get_response.status}")
                            
                            # 读取前20000个字符，增加匹配成功率
                            content = await get_response.text()
                            content = content[:20000]
                            
                            # 打印响应内容的前1000个字符，以便我们能够更好地理解检测过程中发生了什么
                            logger.debug(f"百度网盘链接响应内容前1000个字符: {content[:1000]}")
                            
                            # 如果状态码正常，直接认为链接有效
                            if get_response.status in [200, 301, 302, 303, 307, 308]:
                                logger.debug(f"百度网盘链接有效: {url} (原因: 状态码正常)")
                                return True
                            
                            # 先检查响应内容是否包含失效信息（优先检查）
                            failure_keywords = [
                                "分享链接已失效",
                                "链接已过期",
                                "链接不存在",
                                "文件不存在",
                                "分享不存在",
                                "此链接分享内容可能因为涉及侵权、色情、反动、低俗等信息，无法访问",
                                "该分享已取消",
                                "分享已取消",
                                "分享的文件已经被取消",
                                "你来晚了",
                                "链接不存在"
                            ]
                            
                            # 检查是否包含任何失效关键词
                            for keyword in failure_keywords:
                                if keyword in content:
                                    logger.debug(f"百度网盘链接无效: {url} (原因: 包含关键词 '{keyword}')")
                                    return False
                            
                            # 再检查是否包含有效关键词
                            valid_keywords = [
                                "请输入提取码",
                                "分享文件",
                                "保存到网盘",
                                "下载",
                                "保存",
                                "百度网盘",
                                "网盘",
                                "pwd",
                                "提取码"
                            ]
                            
                            for keyword in valid_keywords:
                                if keyword in content:
                                    logger.debug(f"百度网盘链接有效: {url} (原因: 包含关键词 '{keyword}')")
                                    return True
                            
                            logger.debug(f"百度网盘链接无效: {url} (原因: 状态码 {get_response.status})")
                            return False
                except Exception as e:
                    # 如果GET请求失败，默认认为链接有效
                    logger.debug(f"检查百度网盘链接失败: {url} (错误: {e})")
                    return True
            
            # 对于其他HTTP/HTTPS链接，使用简单的HEAD请求检查
            else:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.head(url, headers=browser_headers, timeout=aiohttp.ClientTimeout(total=5), allow_redirects=True) as response:
                            logger.debug(f"其他HTTP链接响应状态码: {response.status}")
                            # 2xx和3xx状态码都认为是有效的
                            if response.status < 400:
                                logger.debug(f"链接有效: {url} (状态码: {response.status})")
                                return True
                            else:
                                logger.debug(f"链接无效: {url} (状态码: {response.status})")
                                return False
                except Exception as e:
                    logger.debug(f"检查链接失败: {url} (错误: {e})")
                    return False
        
        # 对于磁力链接、迅雷链接等，认为它们始终有效
        elif url.startswith(('magnet:', 'thunder://', 'ed2k://')):
            logger.debug(f"非HTTP链接有效: {url}")
            return True
            
    except Exception as e:
        # 检查失败时，认为链接无效
        logger.debug(f"检查链接失败: {url} (错误: {e})")
        return False
    
    logger.debug(f"链接无效: {url}")
    return False
