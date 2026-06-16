import requests
import re
import time
import json
import random
import logging
import urllib.parse
from typing import Tuple, List, Optional
import subprocess
import os
import tempfile

logger = logging.getLogger(__name__)


class Baidu:
    """
    百度网盘客户端封装
    """

    def __init__(self, cookie: str) -> None:
        self.session = requests.Session()
        # 绕过系统代理（如 Clash），直连百度网盘
        self.session.trust_env = False
        self.headers = {
            'Host': 'pan.baidu.com',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Referer': 'https://pan.baidu.com/disk/home',
            'Cookie': cookie
        }
        self.session.headers.update(self.headers)
        # 获取 bdstoken 用于后续操作（部分操作需要，部分不需要，预留）
        self.bdstoken = self._get_bdstoken()
        # 目录结构缓存
        self.directory_cache = {}
        self.directory_cache_ttl = 600  # 10分钟缓存

    def store(self, share_url: str, to_dir: str = '/') -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        转存分享链接并重新分享
        :param share_url: 原始分享链接 (支持标准格式和带空格提取码格式)
        :param to_dir: 转存目标目录，默认为根目录
        :return: (文件路径, 文件名, 新分享链接)
        """
        try:
            # 1. 解析链接和提取码
            surl, pwd = self._parse_share_url(share_url)
            if not surl:
                logger.error(f"百度链接解析失败: {share_url}")
                return None, None, None

            randsk = None
            # 2. 验证提取码 (如果有)
            if pwd:
                verify_result = self._verify_pwd(surl, pwd)
                if not verify_result.get('success'):
                    logger.error(f"百度提取码验证失败: {surl} {pwd}")
                    return None, None, None
                randsk = verify_result.get('randsk')
            
            # 3. 访问分享页面获取信息（只调用一次）
            info = self._get_share_page_info(surl)
            if not info:
                logger.error("无法获取百度分享页面详情")
                return None, None, None
            
            # 解析返回的信息
            if len(info) == 4:
                # 旧格式：没有 isdir_list
                shareid, from_uk, fs_id_list, file_names = info
                isdir_list = ['0'] * len(fs_id_list)  # 默认都是文件
            else:
                # 新格式：包含 isdir_list
                shareid, from_uk, fs_id_list, file_names, isdir_list = info

            # 处理文件名，移除时间戳
            clean_file_names = []
            for file_name in file_names:
                # 移除类似 _20260329_220639 的时间戳
                cleaned_name = re.sub(r'_\d{8}_\d{6}$', '', file_name)
                clean_file_names.append(cleaned_name)

            # 目前逻辑只处理单文件/文件夹转存，取第一个
            if not fs_id_list:
                logger.error("百度分享页面返回空的文件ID列表")
                return None, None, None

            if not clean_file_names:
                logger.error("百度分享页面返回空的文件名列表")
                return None, None, None

            target_fs_id = fs_id_list[0]
            original_file_name = clean_file_names[0]
            is_dir = isdir_list[0] == '1' if len(isdir_list) > 0 else False

            # 直接使用原始文件名，不添加时间戳
            file_name = original_file_name

            # 检查文件名唯一性
            # 这里简化处理，实际项目中可能需要更复杂的唯一性检查
            # 例如：检查目标目录中是否已存在同名文件，如果存在则调整时间戳或添加额外标识符
            # 注意：当前实现直接使用原始文件名，可能导致文件覆盖

            # 5. 获取或创建目标目录（如果不是根目录）
            if to_dir != '/' and to_dir != '':
                self._get_or_create_dir(to_dir)

            # 6. 构建目标路径
            full_path = f"{to_dir.rstrip('/')}/{file_name}" if to_dir != '/' else f"/{file_name}"
            
            # 确保路径以/开头（百度API要求绝对路径）
            if not full_path.startswith('/'):
                full_path = '/' + full_path
            
            # 7. 直接转存逻辑（跳过删除操作）
            if is_dir:
                # 文件夹：直接转存（跳过删除操作）
                logger.info(f"[百度网盘] 开始转存文件夹: {original_file_name} 到 {to_dir}")
                # 直接执行转存
                if not self._transfer_file(shareid, from_uk, surl, [target_fs_id], to_dir, randsk, is_dir):
                    logger.error(f"[百度网盘] 转存文件夹失败: {file_name}")
                    return None, None, None
                logger.info(f"[百度网盘] 文件夹转存成功: {original_file_name}")
            else:
                # 文件：直接使用overwrite参数转存
                logger.info(f"[百度网盘] 开始转存文件: {original_file_name} 到 {to_dir}")
                if not self._transfer_file(shareid, from_uk, surl, [target_fs_id], to_dir, randsk, is_dir):
                    logger.error(f"[百度网盘] 转存文件失败: {file_name}")
                    return None, None, None
                logger.info(f"[百度网盘] 文件转存成功: {original_file_name}")

            # 8. 清除目标目录的缓存，确保能获取到最新的文件夹结构
            if to_dir in self.directory_cache:
                del self.directory_cache[to_dir]
                logger.debug(f"清除目录缓存: {to_dir}")

            # 9. 等待并查询新文件 ID（使用指数退避策略）
            import time
            new_fs_id = None
            max_get_id_attempts = 5
            retry_delay = 2

            for get_id_attempt in range(max_get_id_attempts):
                logger.info(f"[百度网盘] 第{get_id_attempt + 1}次尝试获取文件ID: {full_path}")
                time.sleep(retry_delay)
                new_fs_id = self._get_file_id_by_path(full_path)
                if new_fs_id:
                    logger.info(f"[百度网盘] 第{get_id_attempt + 1}次尝试成功获取文件ID: {new_fs_id}")
                    break
                if get_id_attempt < max_get_id_attempts - 1:
                    logger.warning(f"[百度网盘] 第{get_id_attempt + 1}次尝试获取文件ID失败，等待后重试")
                    retry_delay *= 1.5  # 指数退避

            if not new_fs_id:
                logger.error(f"[百度网盘] 无法获取转存后的{'文件夹' if is_dir else '文件'}ID: {full_path}")
                # 尝试用原始路径返回，虽然可能导致后续分享失败，但文件已存
                return full_path, file_name, ""

            # 8. 创建新的分享链接
            new_share_link = self._create_share(new_fs_id)
            if not new_share_link:
                logger.error("创建新分享失败")
                return full_path, file_name, ""

            # 9. 清理根目录下可能创建的带时间戳的空文件夹
            self._cleanup_timestamp_folders()

            # 注意：这里返回 full_path 作为 file_id，因为百度的删除接口通常需要路径
            return full_path, file_name, new_share_link

        except Exception as e:
            logger.error(f"百度网盘 Store 操作异常: {e}")
            return None, None, None

    def _get_captcha(self) -> tuple:
        """
        获取百度验证码图片和token
        :return: (vcode_token, captcha_text) or (None, None)
        """
        try:
            url = "https://pan.baidu.com/api/getvcode"
            params = {
                "prod": "filemanager",
                "tpl": "filemanager",
                "vcode_type": 1,
            }
            res = self.session.get(url, params=params, timeout=10)
            data = res.json()
            vcode = data.get("vcode", "")
            img_url = data.get("img", "")
            if not vcode or not img_url:
                logger.error(f"[百度网盘] 获取验证码失败: {data}")
                return None, None
            # 下载验证码图片
            img_res = self.session.get(img_url, timeout=10)
            if img_res.status_code != 200:
                logger.error(f"[百度网盘] 下载验证码图片失败: {img_res.status_code}")
                return None, None
            # 保存到临时文件
            fd, img_path = tempfile.mkstemp(suffix=".jpg")
            os.close(fd)
            with open(img_path, "wb") as f:
                f.write(img_res.content)
            logger.info(f"[百度网盘] 验证码图片已下载: {img_path}")
            return vcode, img_path
        except Exception as e:
            logger.error(f"[百度网盘] 获取验证码异常: {e}")
            return None, None

    def _ocr_captcha(self, img_path: str) -> str:
        """
        用 tesseract 识别验证码图片
        :param img_path: 图片路径
        :return: 识别出的文字
        """
        try:
            result = subprocess.run(
                ['tesseract', img_path, 'stdout', '--psm', '7',
                 '-c', 'tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'],
                capture_output=True, timeout=10
            )
            text = result.stdout.decode('utf-8', errors='ignore').strip()
            # 清理多余空格和换行
            text = re.sub(r'\s+', '', text)
            logger.info(f"[百度网盘] 验证码OCR识别结果: {text}")
            return text
        except Exception as e:
            logger.error(f"[百度网盘] OCR识别异常: {e}")
            return ""
        finally:
            # 清理临时文件
            try:
                os.remove(img_path)
            except:
                pass

    def del_file(self, file_path_list: List[str], max_retries: int = 3) -> bool:
        """
        删除文件，遇到 errno 132 (验证码) 时自动获取验证码并重试
        :param file_path_list: 文件路径列表 ["/我的资源/1.mp4"]
        :param max_retries: 验证码重试次数
        """
        logger.debug(f"正在删除百度网盘文件: {file_path_list}")
        url = "https://pan.baidu.com/api/filemanager"
        
        for attempt in range(max_retries + 1):
            params = {
                "async": 0,
                "onnest": "fail",
                "opera": "delete",
                "bdstoken": self.bdstoken,
                "newVerify": 1,
                "verify_scene": 0,
                "clienttype": 0,
                "web": 1,
                "app_id": 250528,
            }
            payload = {"filelist": json.dumps(file_path_list, ensure_ascii=False)}

            try:
                res = self.session.post(url, params=params, data=payload)
                data = res.json()
                errno = data.get("errno")

                if errno == 0:
                    logger.debug(f"文件删除请求提交成功 (Task ID: {data.get('taskid')})")
                    return True
                elif errno == 2:
                    logger.debug(f"文件不存在 (errno: 2)，可能已被删除: {file_path_list}")
                    return True
                elif errno == 132:
                    # 安全验证，需要验证码
                    logger.warning(f"[百度网盘] 删除触发安全验证 (errno 132), 第 {attempt + 1}/{max_retries + 1} 次尝试")
                    
                    if attempt >= max_retries:
                        logger.error(f"[百度网盘] 验证码重试次数用尽，删除失败: {file_path_list}")
                        return False
                    
                    # 获取验证码
                    vcode_token, img_path = self._get_captcha()
                    if not vcode_token or not img_path:
                        logger.error("[百度网盘] 获取验证码失败，跳过本次重试")
                        time.sleep(2)
                        continue
                    
                    # OCR 识别验证码
                    captcha_text = self._ocr_captcha(img_path)
                    if not captcha_text:
                        logger.error("[百度网盘] 验证码OCR识别为空，跳过本次重试")
                        time.sleep(2)
                        continue
                    
                    # 带验证码重试
                    logger.info(f"[百度网盘] 带验证码重试删除: vcode={vcode_token[:10]}..., input={captcha_text}")
                    params["vcode"] = vcode_token
                    params["input"] = captcha_text
                    # 重试时使用同步模式
                    params["async"] = 0
                    
                    try:
                        res = self.session.post(url, params=params, data=payload)
                        data = res.json()
                        if data.get("errno") == 0:
                            logger.debug(f"[百度网盘] 验证码重试删除成功")
                            return True
                        elif data.get("errno") == 2:
                            logger.debug(f"[百度网盘] 文件已不存在，视为成功")
                            return True
                        else:
                            logger.warning(f"[百度网盘] 验证码重试失败: errno={data.get('errno')}, data={data}")
                    except Exception as e:
                        logger.error(f"[百度网盘] 验证码重试请求异常: {e}")
                    
                    time.sleep(2)
                else:
                    logger.error(f"文件删除请求失败, errno: {errno}, 错误详情: {data}")
                    return False
            except Exception as e:
                logger.error(f"删除请求异常: {e}")
                return False
        
        return False
            
    def move_file(self, from_path: str, to_path: str) -> bool:
        """
        移动文件或文件夹
        :param from_path: 源路径
        :param to_path: 目标路径
        """
        logger.debug(f"正在移动文件: {from_path} -> {to_path}")
        url = "https://pan.baidu.com/api/filemanager"
        params = {
            "async": 2,
            "onnest": "fail",
            "opera": "move",
            "bdstoken": self.bdstoken,
            "newVerify": 1,
            "clienttype": 0,
            "web": 1,
            "app_id": 250528
        }
        
        # 构建移动操作的payload
        payload = {
            "filelist": json.dumps([from_path], ensure_ascii=False),
            "target": to_path
        }
        
        try:
            res = self.session.post(url, params=params, data=payload)
            data = res.json()
            
            if data.get("errno") == 0:
                logger.debug(f"文件移动成功: {from_path} -> {to_path}")
                return True
            else:
                logger.error(f"文件移动失败, errno: {data.get('errno')}, 错误详情: {data}")
                return False
        except Exception as e:
            logger.error(f"移动请求异常: {e}")
            return False

    # ================= 内部辅助方法 =================

    def _get_bdstoken(self) -> str:
        """简单的获取 bdstoken，如果失败返回空字符串，不影响大部分操作"""
        try:
            url = "https://pan.baidu.com/api/gettemplatevariable?fields=[%22bdstoken%22]"
            res = self.session.get(url)
            bdstoken = res.json().get("result", {}).get("bdstoken", "")
            if bdstoken:
                logger.info(f"[百度网盘] bdstoken 获取成功: {bdstoken[:10]}...")
            else:
                logger.warning(f"[百度网盘] bdstoken 获取失败，响应: {res.text[:200]}")
            return bdstoken
        except Exception as e:
            logger.error(f"[百度网盘] bdstoken 获取异常: {e}")
            return ""

    def _parse_share_url(self, url: str) -> Tuple[str, str]:
        """解析链接，返回 (surl, pwd)"""
        # 提取 surl (1xxxxxx)
        m_surl = re.search(r's/1([a-zA-Z0-9-_]+)', url)
        if not m_surl:
            m_surl = re.search(r'surl=([a-zA-Z0-9-_]+)', url)  # 兼容 old format

        surl = m_surl.group(1) if m_surl else ""
        if not surl:
            # 尝试直接从完整链接截取
            if 'baidu.com/s/' in url:
                surl = url.split('baidu.com/s/')[-1].split(' ')[0]
                if surl.startswith('1'):
                    surl = surl[1:]  # 百度API通常只要 s/1 后面的部分

        # 提取提取码
        pwd = ""
        if 'pwd=' in url:
            pwd = url.split('pwd=')[-1].split('&')[0].strip()[:4]
        elif '提取码' in url:
            # 简单粗暴提取最后4位，或按空格分割
            parts = url.split(' ')
            for p in parts:
                if len(p.strip()) == 4 and p.isalnum():
                    pwd = p.strip()

        return surl, pwd

    def _verify_pwd(self, surl: str, pwd: str) -> dict:
        """验证提取码并设置 Cookie"""
        url = "https://pan.baidu.com/share/verify"
        params = {
            "surl": surl,
            "t": int(time.time() * 1000),
            "bdstoken": self.bdstoken,
            "channel": "chunlei",
            "clienttype": 0,
            "web": 1
        }
        data = {"pwd": pwd, "vcode": "", "vcode_str": ""}
        
        # 添加正确的Referer
        headers = self.session.headers.copy()
        headers["Referer"] = f"https://pan.baidu.com/s/1{surl}"
        
        try:
            res = self.session.post(url, params=params, data=data, headers=headers)
            js = res.json()
            if js.get("errno") == 0:
                randsk = js.get("randsk")
                if randsk:
                    randsk = urllib.parse.unquote(randsk)
                return {
                    "success": True,
                    "randsk": randsk
                }
            logger.error(f"验证码错误: {js}")
            return {"success": False, "error": js}
        except Exception as e:
            logger.debug(f"验证请求异常: {e}")
            return {"success": False}

    def _get_share_page_info(self, surl: str) -> Optional[tuple]:
        """访问分享页 HTML 提取必要参数"""
        # 尝试两种URL格式
        urls_to_try = [
            f"https://pan.baidu.com/s/1{surl}",
            f"https://pan.baidu.com/share/init?surl={surl}"
        ]
        
        for url in urls_to_try:
            try:
                res = self.session.get(url)
                html = res.text

                # 正则提取
                shareid = re.search(r'"shareid":(\d+),', html)
                uk = re.search(r'"share_uk":"?(\d+)"?,', html)
                fs_ids = re.findall(r'"fs_id":(\d+),', html)
                filenames = re.findall(r'"server_filename":"(.+?)",', html)
                # 提取文件类型（isdir: 1 表示文件夹，0 表示文件）
                isdir_list = re.findall(r'"isdir":(\d+),', html)

                if shareid and uk and fs_ids:
                    # 去重 fs_ids 和 filenames
                    fs_ids = list(dict.fromkeys(fs_ids))
                    filenames = list(dict.fromkeys(filenames))
                    # 确保 isdir_list 长度与 fs_ids 一致
                    while len(isdir_list) < len(fs_ids):
                        isdir_list.append('0')  # 默认是文件
                    return shareid.group(1), uk.group(1), fs_ids, filenames, isdir_list
            except Exception as e:
                logger.debug(f"解析页面异常: {e}")
        
        return None

    def _transfer_file(self, shareid: str, from_uk: str, surl: str, fs_id_list: list, to_path: str, randsk: str = None, is_dir: bool = False) -> bool:
        """转存文件，带重试机制"""
        url = "https://pan.baidu.com/share/transfer"
        
        # 确保fs_id是整数类型
        fs_id_list = [int(fs_id) for fs_id in fs_id_list]
        
        # 确保to_path与_get_or_create_dir使用相同的格式（不带/结尾）
        if to_path.endswith('/'):
            to_path = to_path[:-1]
        
        # 确保路径以/开头（百度API要求绝对路径）
        if not to_path.startswith('/'):
            to_path = '/' + to_path
        
        # 如果有randsk，添加到参数中
        sekey_param = {}
        if randsk:
            sekey_param["sekey"] = randsk
        
        data = {
            "fsidlist": json.dumps(fs_id_list),
            "path": to_path
        }
        
        logger.debug(f"转存类型: {'文件夹' if is_dir else '文件'}, 目标路径: {to_path}")
        
        # 更新headers，添加正确的Referer
        headers = self.session.headers.copy()
        headers["Referer"] = f"https://pan.baidu.com/s/1{surl}"
        
        # 重试策略
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # 对于文件夹转存，使用更严格的参数
                params = {
                    "shareid": shareid,
                    "from": from_uk,
                    "ondup": "overwrite",
                    "async": 0,
                    "bdstoken": self.bdstoken,
                    "channel": "chunlei",
                    "clienttype": 0,
                    "web": 1,
                    "app_id": 250528,
                    "dp-logid": f"{int(time.time() * 1000)}",
                    "timestamp": int(time.time() * 1000),
                    **sekey_param
                }
                
                res = self.session.post(url, params=params, data=data, headers=headers, timeout=30)
                js = res.json()
                
                if js.get("errno") == 0:
                    logger.debug("转存成功")
                    return True
                # 处理重复文件的情况：errno=4 且有 duplicated 字段
                elif js.get("errno") == 4 and js.get("duplicated"):
                    logger.debug(f"转存成功（文件已存在）: {js['duplicated']}")
                    return True
                # 处理超时错误，尝试重试
                elif js.get("errno") == 4 and attempt < max_retries - 1:
                    logger.warning(f"转存API返回超时错误，第 {attempt + 1} 次重试: {js}")
                    time.sleep(retry_delay)
                    continue
                
                logger.error(f"转存API返回错误: {js}")
                return False
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"转存请求异常，第 {attempt + 1} 次重试: {e}")
                    time.sleep(retry_delay)
                    continue
                logger.error(f"转存请求异常: {e}")
                return False
        
        return False

    def _find_file_id_by_name(self, file_list: list, target_name: str) -> Optional[int]:
        """根据文件名查找文件ID，支持忽略时间戳"""
        import re
        # 移除目标文件名中的时间戳（仅对文件）
        if '.' in target_name:
            clean_target_name = re.sub(r'_\d{14}\.[^.]+$', '', target_name)
        else:
            # 文件夹不需要移除时间戳
            clean_target_name = target_name
        
        for f in file_list:
            server_filename = f.get("server_filename")
            if not server_filename:
                continue
            
            # 移除服务器文件名中的时间戳（仅对文件）
            if '.' in server_filename:
                clean_server_name = re.sub(r'_\d{14}\.[^.]+$', '', server_filename)
            else:
                # 文件夹不需要移除时间戳
                clean_server_name = server_filename
            
            if clean_server_name == clean_target_name:
                logger.debug(f"找到匹配的文件: {server_filename} (清理后: {clean_server_name})")
                return f.get("fs_id")
        
        logger.debug(f"未找到匹配的文件: {target_name}")
        return None

    def _get_file_id_by_path(self, path: str) -> Optional[int]:
        """根据路径获取文件的 fs_id (用于转存后分享)"""
        # 获取父目录和文件名
        if path == '/': return None
        if path.endswith('/'): path = path[:-1]

        dir_path, filename = path.rsplit('/', 1)
        if not dir_path: dir_path = '/'

        # 检查目录缓存
        import time
        current_time = time.time()
        
        if dir_path in self.directory_cache:
            cached_data = self.directory_cache[dir_path]
            if current_time - cached_data['timestamp'] < self.directory_cache_ttl:
                logger.debug(f"使用缓存的目录结构: {dir_path}")
                file_list = cached_data['file_list']
                return self._find_file_id_by_name(file_list, filename)

        # 缓存未命中，从API获取
        url = "https://pan.baidu.com/api/list"
        params = {
            "dir": dir_path,
            "bdstoken": self.bdstoken,
            "clienttype": 0,
            "web": 1,
            "page": 1,
            "num": 1000,  # 假设文件在前1000个
            "order": "time",
            "desc": 1
        }
        try:
            res = self.session.get(url, params=params)
            js = res.json()
            if js.get("errno") != 0:
                return None

            file_list = js.get("list", [])
            
            # 缓存目录结构
            self.directory_cache[dir_path] = {
                'file_list': file_list,
                'timestamp': current_time
            }
            logger.debug(f"缓存目录结构: {dir_path} ({len(file_list)} 个文件)")

            return self._find_file_id_by_name(file_list, filename)
        except Exception as e:
            logger.error(f"查询文件ID异常: {e}")
            return None

    def _create_share(self, fs_id: int) -> Optional[str]:
        """创建分享链接"""
        url = "https://pan.baidu.com/share/set"
        params = {
            "bdstoken": self.bdstoken,
            "channel": "chunlei",
            "clienttype": 0,
            "web": 1,
            "app_id": 250528
        }
        data = {
            "fid_list": f"[{fs_id}]",
            "schannel": 4,
            "channel_list": "[]",
            "period": 0  # 0 为永久
        }

        # 生成4位随机提取码
        pwd = ''.join(random.sample('0123456789abcdefghijklmnopqrstuvwxyz', 4))
        data["pwd"] = pwd

        try:
            res = self.session.post(url, params=params, data=data)
            js = res.json()
            if js.get("errno") == 0:
                short_link = js.get("shorturl")
                # 组合成完整链接
                return f"{short_link}?pwd={pwd}"  # 或者返回 "link pwd" 格式，根据需求调整
            logger.error(f"创建分享失败: {js}")
            return None
        except Exception as e:
            logger.error(f"创建分享请求异常: {e}")
            return None

    def _create_dir(self, dir_path: str) -> bool:
        """创建目录"""
        logger.debug(f"正在创建目录: {dir_path}")

        # 先检查目录是否已存在
        if self._check_dir_exists(dir_path):
            logger.debug(f"目录已存在: {dir_path}")
            return True

        url = "https://pan.baidu.com/api/create"
        params = {
            "a": "commit",
            "bdstoken": self.bdstoken,
            "channel": "chunlei",
            "clienttype": 0,
            "web": 1,
            "app_id": 250528
        }
        data = {
            "path": dir_path,
            "isdir": 1,
            "block_list": "[]"
        }
        try:
            logger.info(f"[百度网盘] 创建目录请求: {dir_path}, bdstoken: {self.bdstoken[:10] if self.bdstoken else '空'}")
            res = self.session.post(url, params=params, data=data)
            js = res.json()
            logger.info(f"[百度网盘] 创建目录响应: {js}")
            if js.get("errno") == 0:
                logger.debug(f"目录创建成功: {dir_path}")
                return True
            elif js.get("errno") == -8:
                logger.debug(f"目录已存在: {dir_path}")
                return True
            logger.error(f"目录创建失败: {dir_path}, 错误: {js}")
            return False
        except Exception as e:
            logger.error(f"创建目录请求异常: {e}")
            return False

    def _check_dir_exists(self, dir_path: str) -> bool:
        """检查目录是否已存在"""
        try:
            # 获取父目录路径
            parent_path = '/'.join(dir_path.rstrip('/').split('/')[:-1]) or '/'
            dir_name = dir_path.rstrip('/').split('/')[-1]

            url = "https://pan.baidu.com/api/list"
            params = {
                "dir": parent_path,
                "bdstoken": self.bdstoken,
                "clienttype": 0,
                "web": 1,
                "page": 1,
                "num": 100,
                "order": "time",
                "desc": 1
            }

            res = self.session.get(url, params=params)
            data = res.json()

            if data.get("errno") != 0:
                logger.debug(f"获取目录列表失败: {data}")
                return False

            file_list = data.get("list", [])
            if not file_list:
                return False

            # 检查目录是否存在
            for file in file_list:
                file_name = file.get("server_filename", "")
                is_dir = file.get("isdir", 0) == 1
                if is_dir and file_name == dir_name:
                    logger.debug(f"找到已存在的目录: {dir_name}")
                    return True

            return False
        except Exception as e:
            logger.debug(f"检查目录是否存在时出错: {e}")
            return False

    def _get_or_create_dir(self, dir_path: str) -> bool:
        """获取或创建目录"""
        logger.info(f"[百度网盘] _get_or_create_dir 调用: {dir_path}")
        if dir_path == '/' or dir_path == '':
            return True

        # 确保dir_path不以/结尾（百度API要求）
        if dir_path.endswith('/'):
            dir_path = dir_path[:-1]

        # 分割路径，逐步创建
        parts = dir_path.strip('/').split('/')
        current_path = ''

        for part in parts:
            if not part:
                continue
            current_path += '/' + part
            logger.info(f"[百度网盘] 创建目录: {current_path}")
            if not self._create_dir(current_path):
                logger.error(f"[百度网盘] 创建目录失败: {current_path}")
                return False

        logger.info(f"[百度网盘] 目录创建成功: {dir_path}")
        return True
        
    def _cleanup_timestamp_folders(self):
        """清理根目录下可能创建的带时间戳的空文件夹"""
        try:
            url = "https://pan.baidu.com/api/list"
            params = {
                "dir": "/",
                "bdstoken": self.bdstoken,
                "clienttype": 0,
                "web": 1,
                "page": 1,
                "num": 100,
                "order": "time",
                "desc": 1
            }
            
            res = self.session.get(url, params=params)
            data = res.json()
            
            if data.get("errno") != 0:
                logger.debug(f"获取根目录文件列表失败: {data}")
                return
            
            file_list = data.get("list", [])
            if not file_list:
                logger.debug("根目录文件列表为空，无需清理")
                return
            
            folders_to_delete = []
            
            # 检查是否有带时间戳的文件夹
            for file in file_list:
                file_name = file.get("server_filename", "")
                if not file_name:
                    continue
                is_dir = file.get("isdir", 0) == 1
                
                if is_dir:
                    # 匹配桃白白影视_YYYYMMDD_HHMMSS格式
                    if re.match(r'^桃白白影视_\d{8}_\d{6}$', file_name):
                        folder_path = file.get("path", "")
                        if folder_path:
                            folders_to_delete.append(folder_path)
            
            # 删除找到的文件夹
            if folders_to_delete:
                success = self.del_file(folders_to_delete)
                if success:
                    logger.debug(f"已清理 {len(folders_to_delete)} 个带时间戳的文件夹")
                
        except Exception as e:
            logger.debug(f"清理带时间戳文件夹时出错: {e}")

    def get_quota(self) -> Optional[dict]:
        """获取网盘空间信息"""
        logger.debug("正在获取百度网盘空间信息")
        url = "https://pan.baidu.com/api/quota"
        params = {
            "bdstoken": self.bdstoken,
            "channel": "chunlei",
            "clienttype": 0,
            "web": 1,
            "app_id": 250528
        }
        try:
            res = self.session.get(url, params=params)
            data = res.json()
            if data.get("errno") == 0:
                quota = data.get("quota", {})
                used = quota.get("used", 0)
                total = quota.get("total", 0)
                free = total - used if total > 0 else 0
                used_percent = round((used / total) * 100, 2) if total > 0 else 0
                
                result = {
                    "used": used,
                    "total": total,
                    "free": free,
                    "used_percent": used_percent
                }
                logger.debug(f"空间信息: 已用={used}字节, 总空间={total}字节, 剩余={free}字节, 使用率={used_percent}%")
                return result
            logger.error(f"获取空间信息失败: {data}")
            return None
        except Exception as e:
            logger.error(f"获取空间信息时出错: {e}")
            return None

    def get_oldest_files(self, limit=50) -> List[dict]:
        """获取最古老的文件（用于清理）"""
        logger.debug(f"正在获取最古老的 {limit} 个文件")
        url = "https://pan.baidu.com/api/list"
        params = {
            "dir": "/",
            "bdstoken": self.bdstoken,
            "clienttype": 0,
            "web": 1,
            "page": 1,
            "num": limit,
            "order": "time",
            "desc": 0  # 0表示升序，最旧的在前
        }
        try:
            res = self.session.get(url, params=params)
            data = res.json()
            if data.get("errno") == 0:
                return data.get("list", [])
            logger.error(f"获取旧文件列表失败: {data}")
            return []
        except Exception as e:
            logger.error(f"获取旧文件列表时出错: {e}")
            return []

    def clean_old_files(self, percent_threshold=80, delete_count=20) -> Tuple[bool, int, float]:
        """
        自动清理旧文件
        :param percent_threshold: 空间使用率达到此阈值时触发清理
        :param delete_count: 每次清理的文件数量
        :return: (是否清理成功, 清理的文件数量, 清理前的使用率)
        """
        quota = self.get_quota()
        if not quota:
            return False, 0, 0

        used_percent = quota['used_percent']
        logger.debug(f"当前空间使用率: {used_percent}%")

        if used_percent < percent_threshold:
            logger.debug(f"空间使用率 {used_percent}% 低于阈值 {percent_threshold}%，无需清理")
            return True, 0, used_percent

        # 获取最旧的文件
        old_files = self.get_oldest_files(delete_count)
        if not old_files:
            logger.debug("没有找到可清理的旧文件")
            return False, 0, used_percent

        # 排除系统文件夹和特殊文件
        file_paths_to_delete = []
        for file in old_files:
            file_name = file.get('server_filename', '')
            # 排除常见的系统文件夹
            if file_name in ['我的资源', '来自分享', '我的应用数据']:
                continue
            # 排除我们创建的桃白白影视目录
            if file_name == '桃白白影视':
                continue
            # 获取文件完整路径
            path = file.get('path', '')
            if path:
                file_paths_to_delete.append(path)

        if not file_paths_to_delete:
            logger.debug("没有符合条件的文件可删除")
            return False, 0, used_percent

        # 执行删除
        success = self.del_file(file_paths_to_delete)
        if success:
            logger.debug(f"成功清理 {len(file_paths_to_delete)} 个旧文件")
            return True, len(file_paths_to_delete), used_percent
        else:
            return False, 0, used_percent
