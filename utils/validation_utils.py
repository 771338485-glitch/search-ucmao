import re
import logging
from typing import Optional, Union

logger = logging.getLogger(__name__)

# 安全的关键词验证模式
SAFE_KEYWORD_PATTERN = re.compile(r'^[\w\s\-\u4e00-\u9fa5]+$')

# 安全的标签名称验证模式
SAFE_TAG_PATTERN = re.compile(r'^[\w\-\u4e00-\u9fa5]+$')

# 安全的分类名称验证模式
SAFE_CATEGORY_PATTERN = re.compile(r'^[\w\-\u4e00-\u9fa5]+$')

# URL验证模式
URL_PATTERN = re.compile(
    r'^(https?://)?'  # 协议
    r'(([a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,})'  # 域名
    r'(:\d+)?'  # 端口
    r'(/[^\s]*)?$'  # 路径
)

# 数字验证模式
DIGIT_PATTERN = re.compile(r'^\d+$')

# 安全的标题验证模式（允许更多字符，但过滤危险字符）
SAFE_TITLE_PATTERN = re.compile(r'^[\w\s\-\u4e00-\u9fa5\(\)\[\]\{\}\.,!\?\'"&]+$')


def validate_keyword(keyword: Optional[str]) -> Optional[str]:
    """
    验证搜索关键词，防止SQL注入和XSS攻击
    :param keyword: 搜索关键词
    :return: 验证后的关键词，或None如果验证失败
    """
    if not keyword:
        return None
    
    # 修复 Latin-1 编码问题：curl 发送中文字符时，Flask/Werkzeug 可能以 Latin-1 解码
    # 尝试将 Latin-1 编码的文本还原为 UTF-8
    try:
        keyword = keyword.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass  # 不是 Latin-1 编码的 UTF-8，保持原样
    
    # 移除首尾空格
    keyword = keyword.strip()
    
    # 限制关键词长度
    if len(keyword) > 100:
        keyword = keyword[:100]
        logger.warning(f"关键词过长，已截断: {keyword}")
    
    # 检查是否包含危险字符
    if not SAFE_KEYWORD_PATTERN.match(keyword):
        # 清理危险字符
        keyword = re.sub(r'[^\w\s\-\u4e00-\u9fa5]', '', keyword)
        logger.warning(f"关键词包含危险字符，已清理: {keyword}")
    
    return keyword if keyword else None


def validate_tag_name(tag_name: Optional[str]) -> Optional[str]:
    """
    验证标签名称，防止SQL注入和XSS攻击
    :param tag_name: 标签名称
    :return: 验证后的标签名称，或None如果验证失败
    """
    if not tag_name:
        return None
    
    # 移除首尾空格
    tag_name = tag_name.strip()
    
    # 限制标签长度
    if len(tag_name) > 50:
        tag_name = tag_name[:50]
        logger.warning(f"标签名称过长，已截断: {tag_name}")
    
    # 检查是否包含危险字符
    if not SAFE_TAG_PATTERN.match(tag_name):
        # 清理危险字符
        tag_name = re.sub(r'[^\w\-\u4e00-\u9fa5]', '', tag_name)
        logger.warning(f"标签名称包含危险字符，已清理: {tag_name}")
    
    return tag_name if tag_name else None


def validate_category(category: Optional[str]) -> Optional[str]:
    """
    验证分类名称，防止SQL注入和XSS攻击
    :param category: 分类名称
    :return: 验证后的分类名称，或None如果验证失败
    """
    if not category:
        return None
    
    # 移除首尾空格
    category = category.strip()
    
    # 限制分类长度
    if len(category) > 50:
        category = category[:50]
        logger.warning(f"分类名称过长，已截断: {category}")
    
    # 检查是否包含危险字符
    if not SAFE_CATEGORY_PATTERN.match(category):
        # 清理危险字符
        category = re.sub(r'[^\w\-\u4e00-\u9fa5]', '', category)
        logger.warning(f"分类名称包含危险字符，已清理: {category}")
    
    return category if category else None


def validate_url(url: Optional[str]) -> Optional[str]:
    """
    验证URL，防止XSS攻击
    :param url: URL地址
    :return: 验证后的URL，或None如果验证失败
    """
    if not url:
        return None
    
    # 移除首尾空格
    url = url.strip()
    
    # 限制URL长度
    if len(url) > 1000:
        logger.warning(f"URL过长，可能是恶意输入")
        return None
    
    # 检查是否是有效的URL格式
    if not URL_PATTERN.match(url):
        # 对于磁力链接、迅雷链接等特殊格式，进行单独处理
        if not (url.startswith('magnet:') or url.startswith('thunder://') or url.startswith('ed2k://')):
            logger.warning(f"无效的URL格式: {url}")
            return None
    
    # 移除可能的XSS攻击代码
    url = re.sub(r'<script[^>]*>.*?</script>', '', url, flags=re.DOTALL)
    url = re.sub(r'<iframe[^>]*>.*?</iframe>', '', url, flags=re.DOTALL)
    
    return url


def validate_integer(value: Union[str, int], min_value: int = None, max_value: int = None) -> Optional[int]:
    """
    验证整数值，防止SQL注入
    :param value: 整数值
    :param min_value: 最小值
    :param max_value: 最大值
    :return: 验证后的整数，或None如果验证失败
    """
    if value is None:
        return None
    
    try:
        # 转换为整数
        if isinstance(value, str):
            # 检查是否只包含数字
            if not DIGIT_PATTERN.match(value):
                logger.warning(f"无效的整数值: {value}")
                return None
            value = int(value)
        
        # 检查范围
        if min_value is not None and value < min_value:
            logger.warning(f"整数值小于最小值 {min_value}: {value}")
            return min_value
        
        if max_value is not None and value > max_value:
            logger.warning(f"整数值大于最大值 {max_value}: {value}")
            return max_value
        
        return value
    except (ValueError, TypeError):
        logger.warning(f"无法转换为整数: {value}")
        return None


def validate_title(title: Optional[str]) -> Optional[str]:
    """
    验证标题，防止XSS攻击
    :param title: 标题
    :return: 验证后的标题，或None如果验证失败
    """
    if not title:
        return None
    
    # 移除首尾空格
    title = title.strip()
    
    # 限制标题长度
    if len(title) > 255:
        title = title[:255]
        logger.warning(f"标题过长，已截断: {title}")
    
    # 移除可能的XSS攻击代码
    title = re.sub(r'<script[^>]*>.*?</script>', '', title, flags=re.DOTALL)
    title = re.sub(r'<iframe[^>]*>.*?</iframe>', '', title, flags=re.DOTALL)
    
    # 清理危险字符
    if not SAFE_TITLE_PATTERN.match(title):
        title = re.sub(r'[^\w\s\-\u4e00-\u9fa5\(\)\[\]\{\}\.,!\?\'"&]', '', title)
        logger.warning(f"标题包含危险字符，已清理: {title}")
    
    return title if title else None


def validate_page(page: Union[str, int]) -> int:
    """
    验证页码，确保为正整数
    :param page: 页码
    :return: 验证后的页码，默认为1
    """
    validated_page = validate_integer(page, min_value=1)
    return validated_page if validated_page else 1


def validate_limit(limit: Union[str, int]) -> int:
    """
    验证限制数量，确保为正整数且不超过最大值
    :param limit: 限制数量
    :return: 验证后的限制数量，默认为10
    """
    validated_limit = validate_integer(limit, min_value=1, max_value=100)
    return validated_limit if validated_limit else 10
