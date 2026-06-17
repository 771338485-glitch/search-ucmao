import concurrent.futures
import json
import logging
import random
import re
import os
import subprocess
import time
import threading

import jmespath
import requests

from configs.app_config import user_agents, SEARCH_MAX_CONCURRENCY, SEARCH_VARIANT_TRIGGER, SEARCH_PLUGIN_TIMEOUT_MS
from src.db.resources_dao import search_resources_by_keyword, search_resources_advanced
from utils.netdisk_utils import match_netdisk_link
from src.pan_operator import create_share

logger = logging.getLogger(__name__)

# API 配置缓存
_api_config_cache = None
_api_config_cache_time = 0
_api_config_cache_lock = threading.Lock()
_API_CONFIG_CACHE_TTL = 60  # 缓存 60 秒


def read_all_api_configs_from_db():
    """从数据库读取所有 API 配置（用于搜索服务，不排序）"""
    from src.db.api_config_dao import get_all_configs
    return get_all_configs(order_by_created=False)


def get_cached_api_configs():
    """获取缓存的 API 配置"""
    global _api_config_cache, _api_config_cache_time
    
    current_time = time.time()
    
    with _api_config_cache_lock:
        # 检查缓存是否过期
        if _api_config_cache is None or (current_time - _api_config_cache_time) > _API_CONFIG_CACHE_TTL:
            logger.debug("刷新 API 配置缓存")
            _api_config_cache = read_all_api_configs_from_db()
            _api_config_cache_time = current_time
        
        return _api_config_cache


read_api_configs = read_all_api_configs_from_db


# API 响应时间记录
api_response_times = {}
api_response_times_lock = threading.Lock()


def _curl_fetch(url, method, request_data, timeout):
    """使用 curl 作为后备方案（解决 Python requests 代理兼容性问题）。"""
    try:
        cmd = ['curl', '-s', '--max-time', str(int(timeout)), '--noproxy', '*']
        # 直连模式，不走代理（系统 SOCKS5 代理会导致超时）
        logger.info(f"curl 直连模式, 超时: {int(timeout)}秒")
        if method.upper() == 'POST' and request_data:
            cmd.extend(['-X', 'POST', '-H', 'Content-Type: application/json', '-d', request_data])
        cmd.append(url)
        logger.info(f"curl 后备请求: {' '.join(cmd[:6])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        logger.info(f"curl 返回: returncode={result.returncode}, stdout长度={len(result.stdout or '')}, stderr={result.stderr[:200] if result.stderr else '无'}")
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        if result.returncode != 0:
            logger.warning(f"curl 返回非零退出码: {result.returncode}, stderr: {result.stderr}")
    except Exception as e:
        logger.warning(f"curl 后备方案异常: {e}")
    return None


def fetch_data(url, method, request_data, timeout=None):
    """根据配置发起 HTTP 请求并返回响应内容。"""
    # 使用配置的超时时间，如果未指定则使用默认值
    if timeout is None:
        from configs.app_config import SEARCH_PLUGIN_TIMEOUT_MS
        timeout = SEARCH_PLUGIN_TIMEOUT_MS / 1000  # 转换为秒

    headers = {
        "User-Agent": random.choice(user_agents),
        "Content-Type": "application/json",
    }

    try:
        data_obj = json.loads(request_data) if request_data else None
    except json.JSONDecodeError:
        data_obj = {}

    start_time = time.time()

    try:
        # 代理环境变量已在 app.py 启动时清除，requests 可直连
        # 禁止跟随重定向：某些 API 返回 301→HTTPS 但 HTTPS 不可达，会导致挂起
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=data_obj, timeout=timeout, allow_redirects=False)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data_obj, timeout=timeout, allow_redirects=False)
        else:
            raise requests.exceptions.RequestException(f"不支持的 HTTP 方法: {method}")

        # 如果是重定向响应，直接返回 None（不浪费时间跟随）
        if 300 <= response.status_code < 400:
            redirect_url = response.headers.get('Location', '未知')
            logger.warning(f"API 返回重定向 {response.status_code}，跳过: {url} -> {redirect_url}")
            return None

        response.raise_for_status()
        json_data = response.json()

        # 记录响应时间
        response_time = time.time() - start_time
        with api_response_times_lock:
            api_response_times[url] = response_time
        logger.debug(f"API 请求成功 ({url}) - 响应时间: {response_time:.2f}秒")

        return json_data

    except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        logger.warning(f"requests 请求失败 ({url}): {e}，尝试 curl 后备方案")
        # curl 回退：缩短超时，避免浪费太多时间
        remaining = min(max(5, timeout - (time.time() - start_time)), 8)
        curl_result = _curl_fetch(url, method, request_data, remaining)
        if curl_result:
            response_time = time.time() - start_time
            with api_response_times_lock:
                api_response_times[url] = response_time
            logger.info(f"curl 后备方案成功 ({url}) - 响应时间: {response_time:.2f}秒")
        return curl_result
    except json.JSONDecodeError:
        logger.error(f"API 响应不是有效的 JSON ({url})")
        return None
    finally:
        pass


def extract_from_json(json_data, jmespath_query):
    """使用 JMESPath 表达式从 JSON 数据中提取结果。"""
    if not json_data or not jmespath_query:
        return []

    try:
        results = jmespath.search(jmespath_query, json_data)

        if not results:
            logger.debug("JMESPath 查询未找到结果")
            return []
            
        if not isinstance(results, list):
            logger.debug("JMESPath 查询结果不是列表")
            return []
            
        # 支持两种格式：
        # 1. [ [title, url], ... ] - 旧格式
        # 2. [ [title, url, datetime], ... ] - 新格式（带日期）
        formatted_results = []
        for item in results:
                if not isinstance(item, (list, tuple)):
                    logger.debug(f"搜索结果项不是列表或元组: {item}")
                    continue
                    
                if len(item) >= 3:
                    # 新格式：带日期
                    try:
                        formatted_results.append([str(item[0]), str(item[1]), str(item[2])])
                    except (IndexError, TypeError, ValueError) as e:
                        logger.debug(f"格式化搜索结果失败: {e}")
                        continue
                elif len(item) >= 2:
                    # 旧格式：不带日期
                    try:
                        formatted_results.append([str(item[0]), str(item[1]), ""])
                    except (IndexError, TypeError, ValueError) as e:
                        logger.debug(f"格式化搜索结果失败: {e}")
                        continue
                else:
                    logger.debug(f"搜索结果项长度不足: {item}")
                    continue
        return formatted_results

    except Exception as e:
        logger.error(f"JMESPath 提取失败 (Query: {jmespath_query}): {e}")
        return []


def replace_keyword_in_config(configs, placeholder, keyword):
    """用实际关键词替换 API 配置中的占位符（如 '[[keyword]]'）。"""
    updated_configs = []
    placeholder = str(placeholder)
    keyword = str(keyword)

    for config in configs:
        new_config = config.copy()

        # 替换 URL
        if "url" in new_config and isinstance(new_config["url"], str):
            new_config["url"] = new_config["url"].replace(placeholder, keyword)

        # 替换 Request Body (JSON 字符串)
        if "request" in new_config and isinstance(new_config["request"], str):
            new_config["request"] = new_config["request"].replace(placeholder, keyword)

        updated_configs.append(new_config)
    return updated_configs


def filter_output(extracted_data, keyword):
    """根据关键词过滤结果，实现模糊匹配。"""
    separator_pattern = r"[,、|;+\-/	\n*#\s]"
    processed_keyword = re.sub(separator_pattern, " ", keyword)

    keyword_list = [kw.strip() for kw in processed_keyword.split() if kw.strip()]

    filtered_list = []

    for item in extracted_data:
        title = item[0]

        for kw in keyword_list:
            if kw in title:
                filtered_list.append(item)
                break

    return filtered_list


def clean_and_extract_data(data):
    """
    清洗并提取数据，并新增网盘信息。
    输入格式: [[source, title, url], ...] 或 [[source, title, url, datetime], ...]
    输出格式: [[source, title, url, netdisk_name, datetime, is_valid], ...]
    注意: 这里先默认所有链接都是有效的，后续会通过异步任务检查并更新
    """

    def extract_url(url):
        """ 清洗URL冗余内容后，提取http/磁力/迅雷等常见链接，无匹配则返回清洗后原文 """
        url = str(url).strip()
        url = re.sub(r"</?br\s*/?>.*分享", "", url, flags=re.IGNORECASE)
        url = re.sub(r"</?br\s*/?>", " ", url, flags=re.IGNORECASE)
        url_pattern = re.compile(r"(magnet:|thunder://|ed2k://|https?:\/\/).*?(?=\s|$)", re.IGNORECASE)
        match = url_pattern.search(url)
        if match:
            return match.group(0)
        return url

    def extract_title(title):
        """ 移除标题中的所有 HTML 标签（通用版），并轻量格式化 """
        title = str(title)
        title = re.sub(r"</?\w+[^>]*>", "", title)
        title = re.sub(r"(\[?(描述|简介|介绍)\]?)\s*[：:]\s*.*?$", "", title)
        title = re.sub(r"\s+", " ", title)
        return title.strip()

    def format_datetime(dt_str):
        """格式化日期时间字符串"""
        if not dt_str:
            return ""
        try:
            from datetime import datetime
            dt_str = str(dt_str).strip()
            # 过滤无效日期
            if dt_str == '0001-01-01T00:00:00Z' or dt_str == '0001-01-01':
                return ""
            if 'T' in dt_str:
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                # 过滤年份小于 2000 的日期
                if dt.year < 2000:
                    return ""
                return dt.strftime('%Y-%m-%d %H:%M')
            # 处理纯日期格式，检查年份
            if len(dt_str) >= 10:
                date_part = dt_str[:10]
                # 尝试解析日期
                try:
                    dt = datetime.strptime(date_part, '%Y-%m-%d')
                    if dt.year < 2000:
                        return ""
                    return date_part
                except ValueError as e:
                    logger.debug(f"日期解析失败: {date_part}, 错误: {e}")
                    return date_part
            return dt_str
        except Exception as e:
            logger.debug(f"日期时间格式化失败: {dt_str}, 错误: {e}")
            return dt_str

    cleaned_data = []
    for d_lst in data:
        source = d_lst[0]
        title = extract_title(d_lst[1])
        url = extract_url(d_lst[2])
        
        # 过滤掉空链接
        if not url or url.strip() == '':
            continue
        
        netdisk_name = match_netdisk_link(url)
        datetime_str = format_datetime(d_lst[3]) if len(d_lst) > 3 else ""

        # 不设置默认值，保持 undefined 状态，前端会显示"检查中"
        cleaned_data.append([source, title, url, netdisk_name, datetime_str, None])

    # 优化：不在搜索时检查链接有效性，避免阻塞
    # 链接有效性检查改为用户点击时再进行
    # 这样可以大幅提高搜索响应速度

    return cleaned_data


def process_config(config, keyword):
    """
    处理单个 API 配置，获取、筛选数据，并返回包含网盘名称的结果。
    """
    config_name = config.get("name", "未知 API")
    final_results = []

    try:
        logger.debug(f"开始调用 API: '{config_name}' ({config['url']})")
        response_data = fetch_data(config["url"], config["method"], config["request"])

        if not response_data:
            logger.debug(f"API '{config_name}' 没有返回数据")
            return []

        extracted_data = extract_from_json(response_data, config["response"])
        
        if not extracted_data or not isinstance(extracted_data, list):
            logger.debug(f"API '{config_name}' 提取的数据为空或格式不正确")
            return []

        filtered_data = filter_output(extracted_data, keyword)
        
        if not filtered_data:
            logger.debug(f"API '{config_name}' 过滤后没有匹配的结果")
            return []

        filtered_data_with_keyword = [["other", item[0], item[1], item[2]] for item in filtered_data]
        final_results = clean_and_extract_data(filtered_data_with_keyword)

        num_results = len(final_results)
        logger.debug(f"API '{config_name}' 搜索到 {num_results} 条资源")

    except Exception as e:
        logger.error(f"处理配置 '{config_name}' ({config['url']}) 时发生异常: {e}")
        return []

    return final_results


def generate_search_keyword_variants(keyword: str) -> list:
    """
    生成关键词变体，用于提升搜索命中率
    只有关键词里包含空格才进行变体搜索
    """
    keyword = keyword.strip()
    if not keyword:
        return []

    variants = [keyword]

    # 优化：禁用变体搜索，只搜索原始关键词
    # 变体搜索会导致多次调用外部 API，大幅增加响应时间
    # 如果需要变体搜索，可以取消下面的注释
    return variants

    # # 只有检测到空格才进行变体搜索
    # if ' ' not in keyword:
    #     return variants

    # # 尝试分词（按空格）
    # parts = keyword.split()
    # parts = [p.strip() for p in parts if p.strip()]

    # # 如果有多个部分，生成部分关键词
    # if len(parts) > 1:
    #     # 添加前2个词
    #     if len(parts) >= 2:
    #         variants.append(' '.join(parts[:2]))
    #     # 添加第一个词
    #     if parts:
    #         variants.append(parts[0])

    # # 去重
    # seen = set()
    # unique_variants = []
    # for v in variants:
    #     if v and v not in seen:
    #         seen.add(v)
    #         unique_variants.append(v)

    # # 最多返回3个变体
    # return unique_variants[:3]


def search_in_database(keyword):
    """
    从内部数据库搜索，并新增网盘信息。
    返回格式: [[source, title, url, netdisk_name, datetime, is_valid], ...]
    注意: 这里先默认所有链接都是有效的，后续会通过异步任务检查并更新
    """
    try:
        # 使用 DAO 搜索资源
        results = search_resources_by_keyword(keyword)

        final_results = []
        for name, link, cloud_name in results:
            netdisk_name = cloud_name if cloud_name else match_netdisk_link(link)
            # 不设置默认值，保持 None 状态，前端会显示"检查中"
            # 添加空的日期时间字段和有效性字段，保持与 API 结果格式一致
            final_results.append(["hot", name, link, netdisk_name, "", None])

        num_results = len(final_results)
        logger.debug(f"内部数据库搜索到 {num_results} 条资源")

        # 优化：不在搜索时检查链接有效性
        # 链接有效性检查由前端异步进行，避免阻塞搜索响应
        return final_results

    except Exception as err:
        logger.error(f"数据库错误: {err}")
        return []


def generate_search_stream_events(keyword):
    """
    生成搜索结果的 SSE 事件流 (生成字符串, 不直接返回 Response
    参考 PanHub 的实现：
    1. 先使用原始关键词搜索
    2. 如果结果太少，尝试关键词变体
    3. 限制并发数
    """

    def _event_generator():
        db_results = search_in_database(keyword)
        total_results_count = len(db_results) if db_results else 0
        
        if db_results:
            yield json.dumps({"type": "initial", "results": db_results})

        urls_config = get_cached_api_configs()
        enabled_configs = [c for c in urls_config if c.get("status", False) and c.get("is_enabled", False)]

        # 根据API响应时间排序，优先调用响应快的API
        def get_api_response_time(config):
            url = config.get("url", "")
            with api_response_times_lock:
                return api_response_times.get(url, 9999)
        
        enabled_configs.sort(key=get_api_response_time)

        enabled_urls = [c["url"] for c in enabled_configs]
        logger.debug(f"本次搜索启用的 API 数量: {len(enabled_urls)} 个")
        logger.debug(f"API 响应时间排序: {[(c['url'], get_api_response_time(c)) for c in enabled_configs]}")

        # 生成关键词变体
        keyword_variants = generate_search_keyword_variants(keyword)
        logger.info(f"关键词 '{keyword}' 的变体列表: {keyword_variants}")
        logger.info(f"变体搜索触发阈值: {SEARCH_VARIANT_TRIGGER} 条结果")

        # 先尝试原始关键词
        current_variant_index = 0
        processed_keywords = set()

        while current_variant_index < len(keyword_variants):
            current_keyword = keyword_variants[current_variant_index]
            
            # 避免重复搜索相同关键词
            if current_keyword in processed_keywords:
                current_variant_index += 1
                continue
            processed_keywords.add(current_keyword)

            logger.info(f"===== 开始使用关键词 '{current_keyword}' 搜索 (变体 {current_variant_index + 1}/{len(keyword_variants)}) =====")

            urls_config_search = replace_keyword_in_config(enabled_configs, "[[keyword]]", current_keyword)

            # 使用配置的并发数
            logger.info(f"使用 {SEARCH_MAX_CONCURRENCY} 个并发请求 API")
            with concurrent.futures.ThreadPoolExecutor(max_workers=SEARCH_MAX_CONCURRENCY) as executor:
                futures = [executor.submit(process_config, config, current_keyword) for config in urls_config_search]
                pending_futures = set(futures)

                while pending_futures:
                    done, pending_futures = concurrent.futures.wait(
                        pending_futures, timeout=None, return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    for future in done:
                        try:
                            results = future.result()
                            if results:
                                total_results_count += len(results)
                                yield json.dumps({"type": "update", "results": results})
                        except Exception as e:
                            logger.error(f"SSE 收集结果时发生异常: {e}")

                    time.sleep(0.01)

            # 检查是否需要尝试下一个变体
            if total_results_count >= SEARCH_VARIANT_TRIGGER:
                logger.info(f"✅ 已找到 {total_results_count} 条结果，达到阈值 {SEARCH_VARIANT_TRIGGER}，停止变体搜索")
                break

            current_variant_index += 1
            if current_variant_index < len(keyword_variants):
                logger.info(f"⚠️ 结果数量不足 ({total_results_count}/{SEARCH_VARIANT_TRIGGER})，尝试下一个关键词变体")

        logger.info(f"🎉 关键词 '{keyword}' 所有搜索完成，共找到 {total_results_count} 条结果")
        yield json.dumps({"type": "end"})

    return _event_generator()


def search_resources(name="", cloud_name="", resource_type="", limit=100, sort="default"):
    """
    通过名称、云名称或类型搜索资源
    返回: (success: bool, message: str, results: list)
    """
    try:
        return search_resources_advanced(name=name, cloud_name=cloud_name, resource_type=resource_type, limit=limit, sort=sort)
    except Exception as e:
        logger.error(f"API错误: {e}")
        return False, f"API错误: {e}", []
