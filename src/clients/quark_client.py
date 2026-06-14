import requests
import re
import time
import random
import logging

logger = logging.getLogger(__name__)


def ad_check(file_name):
    """
    检查文件名是否包含广告关键词。

    参数:
    file_name (str): 文件名

    返回:
    bool: 如果文件名包含广告关键词，返回 True；否则返回 False
    """
    # 定义广告关键词列表
    ad_keywords = ['防迷路', '防失联']

    # 将文件名转换为小写，以便不区分大小写
    file_name_lower = file_name.lower()

    # 检查文件名是否包含任何广告关键词
    for keyword in ad_keywords:
        if keyword in file_name_lower:
            return True

    return False


def get_id_from_url(url) -> str:
    """pwd_id"""
    pattern = r"/s/(\w+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return ""


def generate_timestamp(length):
    timestamps = str(time.time() * 1000)
    return int(timestamps[0:length])


class Quark:
    ad_pwd_id = "0df525db2bd0"

    def __init__(self, cookie: str) -> None:
        self.headers = {
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json; charset=utf-8',
            'sec-ch-ua-mobile': '?0',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
            'sec-ch-ua-platform': '"Windows"',
            'origin': 'https://pan.quark.cn',
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://pan.quark.cn/',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cookie': cookie}

    def store(self, url: str, to_dir_path: str = '/'):
        pwd_id = get_id_from_url(url)
        stoken = self.get_stoken(pwd_id)

        if not stoken:
            logger.error(f"获取stoken失败: {pwd_id}")
            return None, None, None

        detail = self.detail(pwd_id, stoken)

        if not detail:
            logger.error(f"获取分享详情失败: {pwd_id}")
            return None, None, None

        original_file_name = detail.get('title')
        first_id = detail.get("fid")
        share_fid_token = detail.get("share_fid_token")

        if not all([first_id, share_fid_token]):
            logger.error(f"分享详情缺少必要信息: fid={first_id}, share_fid_token={share_fid_token}")
            return None, None, None

        # 直接使用原始文件名，不添加时间戳
        file_name = original_file_name

        # 检查文件名唯一性
        # 这里简化处理，实际项目中可能需要更复杂的唯一性检查
        # 例如：检查目标目录中是否已存在同名文件，如果存在则调整时间戳或添加额外标识符
        # 注意：当前实现直接使用原始文件名，可能导致文件覆盖

        # 直接使用目标目录，不创建子目录
        to_pdir_fid = self._get_or_create_dir(to_dir_path)

        task = self.save_task_id(pwd_id, stoken, first_id, share_fid_token, to_pdir_fid)

        if not task:
            logger.error("创建保存任务失败")
            return None, None, None

        data = self.task(task)

        if not data or not data.get("data"):
            logger.error("获取保存任务结果失败")
            return None, None, None

        save_as_data = data.get("data").get("save_as", {})
        save_as_top_fids = save_as_data.get("save_as_top_fids", [])

        if not save_as_top_fids:
            logger.error("保存结果中没有找到文件ID")
            return None, None, None

        file_id = save_as_top_fids[0]

        # if not file_type:
        #     dir_file_list = self.get_dir_file(file_id)
        #     self.del_ad_file(dir_file_list)
        #     self.add_ad(file_id)

        share_task_id = self.share_task_id(file_id, file_name)

        if not share_task_id:
            logger.error("创建分享任务失败")
            return None, None, None

        share_task_result = self.task(share_task_id)

        if not share_task_result or not share_task_result.get("data"):
            logger.error("获取分享任务结果失败")
            return None, None, None

        share_id = share_task_result.get("data").get("share_id")

        if not share_id:
            logger.error("分享结果中没有找到分享ID")
            return None, None, None

        share_link = self.get_share_link(share_id)

        if not share_link:
            logger.error("获取分享链接失败")
            return None, None, None

        return file_id, file_name, share_link

    def get_stoken(self, pwd_id: str):
        url = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token?pr=ucpro&fr=pc&uc_param_str=&__dt=405&__t={generate_timestamp(13)}"
        payload = {"pwd_id": pwd_id, "passcode": ""}
        headers = self.headers
        response = requests.post(url, json=payload, headers=headers).json()
        if response.get("data"):
            return response["data"]["stoken"]
        else:
            return ""

    def detail(self, pwd_id, stoken):
        url = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail"
        headers = self.headers
        params = {
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": 0,
            "_page": 1,
            "_size": "50",
        }
        response = requests.request("GET", url=url, headers=headers, params=params)
        response_data = response.json().get("data", {})
        file_list = response_data.get("list", [])

        if not file_list:
            logger.error(f"获取分享详情失败，列表为空: {pwd_id}")
            return {}

        first_item = file_list[0]
        if not isinstance(first_item, dict):
            logger.error(f"file_list[0] 类型异常: {type(first_item)}")
            return {}

        data = {
            "title": first_item.get("file_name"),
            "file_type": first_item.get("file_type"),
            "fid": first_item.get("fid"),
            "pdir_fid": first_item.get("pdir_fid"),
            "share_fid_token": first_item.get("share_fid_token")
        }
        return data

    def save_task_id(self, pwd_id, stoken, first_id, share_fid_token, to_pdir_fid: str = '0'):
        logger.info("获取保存文件的TASKID")
        url = "https://drive.quark.cn/1/clouddrive/share/sharepage/save"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "__dt": int(random.uniform(1, 5) * 60 * 1000),
            "__t": generate_timestamp(13),
        }
        data = {"fid_list": [first_id],
                "fid_token_list": [share_fid_token],
                "to_pdir_fid": to_pdir_fid, "pwd_id": pwd_id,
                "stoken": stoken, "pdir_fid": "0", "scene": "link"}
        response = requests.request("POST", url, json=data, headers=self.headers, params=params)
        resp_json = response.json()
        logger.info(f"保存文件API响应: {resp_json}")
        if resp_json.get('data'):
            task_id = resp_json.get('data').get('task_id')
            return task_id
        else:
            logger.error(f"保存文件API返回错误: {resp_json}")
            return None

    def task(self, task_id, trice=10):
        """根据task_id进行任务"""
        logger.info("根据TASKID执行任务")
        trys = 0
        for i in range(trice):
            url = f"https://drive-pc.quark.cn/1/clouddrive/task?pr=ucpro&fr=pc&uc_param_str=&task_id={task_id}&retry_index={i}&__dt=21192&__t={generate_timestamp(13)}"
            trys += 1
            try:
                response = requests.get(url, headers=self.headers).json()
                if response and response.get('data') and response.get('data').get('status'):
                    return response
            except Exception as e:
                logger.error(f"执行任务时发生异常: {e}")
        logger.warning(f"任务执行失败或超时: {task_id}")
        return None

    def share_task_id(self, file_id, file_name):
        """创建分享任务ID"""
        url = "https://drive-pc.quark.cn/1/clouddrive/share?pr=ucpro&fr=pc&uc_param_str="
        data = {"fid_list": [file_id],
                "title": file_name,
                "url_type": 1, "expired_type": 1}
        try:
            response = requests.request("POST", url=url, json=data, headers=self.headers, timeout=30)
            response.raise_for_status()
            json_data = response.json()
            if not json_data or not json_data.get("data"):
                logger.error(f"share_task_id 响应格式异常: {json_data}")
                return None
            return json_data["data"].get("task_id")
        except Exception as e:
            logger.error(f"share_task_id 请求失败: {e}")
            return None

    def get_share_link(self, share_id):
        url = "https://drive-pc.quark.cn/1/clouddrive/share/password?pr=ucpro&fr=pc&uc_param_str="
        data = {"share_id": share_id}
        try:
            response = requests.post(url=url, json=data, headers=self.headers, timeout=30)
            response.raise_for_status()
            json_data = response.json()
            if not json_data or not json_data.get("data"):
                logger.error(f"get_share_link 响应格式异常: {json_data}")
                return None
            return json_data["data"].get("share_url")
        except Exception as e:
            logger.error(f"get_share_link 请求失败: {e}")
            return None

    def get_all_file(self) -> list:
        logger.info("正在获取所有文件")
        url = "https://drive-pc.quark.cn/1/clouddrive/file/sort?pr=ucpro&fr=pc&uc_param_str="
        params = {
            "pdir_fid": 0,
            "_page": 1,
            "_size": 50,
            "_fetch_total": 1,
            "_fetch_sub_dirs": 0,
            "_sort": "file_type:asc,updated_at:desc"
        }
        response = requests.get(url=url, headers=self.headers, params=params)
        try:
            json_data = response.json()
            if json_data and json_data.get('data') and json_data.get('data').get('list') is not None:
                return json_data.get('data').get('list')
            logger.warning(f"夸克API返回数据异常: {json_data}")
            return []
        except Exception as e:
            logger.error(f"解析夸克API响应失败: {e}, 响应内容: {response.text[:200]}")
            return []

    def get_dir_file(self, dir_id, page: int = 1, size: int = 100) -> list:
        logger.info("正在遍历父文件夹")
        """获取指定文件夹的文件,后期可能会递归"""
        url = f"https://drive-pc.quark.cn/1/clouddrive/file/sort?pr=ucpro&fr=pc&uc_param_str="
        params = {
            "pdir_fid": dir_id,
            "_page": page,
            "_size": size,
            "_fetch_total": 1,
            "_fetch_sub_dirs": 0,
            "_sort": "file_type:asc,updated_at:desc"
        }
        response = requests.get(url=url, headers=self.headers, params=params)
        try:
            json_data = response.json()
            if json_data and json_data.get('data') and json_data.get('data').get('list') is not None:
                return json_data.get('data').get('list')
            logger.warning(f"夸克API返回数据异常: {json_data}")
            return []
        except Exception as e:
            logger.error(f"解析夸克API响应失败: {e}, 响应内容: {response.text[:200]}")
            return []

    def _get_or_create_dir(self, dir_path: str) -> str:
        """获取或创建目录，返回目录ID"""
        if dir_path == '/' or dir_path == '':
            return '0'
        
        # 分割路径，去除首尾的斜杠
        parts = dir_path.strip('/').split('/')
        current_dir_id = '0'
        
        for part in parts:
            if not part:
                continue
            
            # 查找当前目录下是否已存在该子目录
            dir_files = self.get_dir_file(current_dir_id)
            found = False
            
            for file in dir_files:
                if file.get('file_name') == part and file.get('file_type') == 0:  # 0 表示目录
                    current_dir_id = file.get('fid')
                    found = True
                    logger.info(f"找到已存在的目录: {part}, ID: {current_dir_id}")
                    break
            
            if not found:
                # 创建新目录
                logger.info(f"创建新目录: {part}")
                result = self.create_dir(part, current_dir_id)
                if result.get('code') == 0:
                    current_dir_id = result.get('data', {}).get('fid')
                    logger.info(f"目录创建成功: {part}, ID: {current_dir_id}")
                else:
                    logger.error(f"目录创建失败: {part}, 结果: {result}")
                    return '0'
        
        return current_dir_id

    def create_dir(self, dir_name: str, parent_dir_id: str = "0"):
        logger.info(f"创建新目录: {dir_name}")
        url = "https://drive-pc.quark.cn/1/clouddrive/file?pr=ucpro&fr=pc&uc_param_str="
        data = {
            "pdir_fid": parent_dir_id,
            "file_name": dir_name,
            "dir_path": "",
            "dir_init_lock": False
        }
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()

    def rename_dir(self, dir_id: str, new_name: str):
        logger.info(f"重命名目录: {dir_id} 为 {new_name}")
        url = "https://drive-pc.quark.cn/1/clouddrive/file/rename?pr=ucpro&fr=pc&uc_param_str="
        data = {"fid": dir_id, "file_name": new_name}
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()

    def move_file(self, file_fid: str, to_pdir_fid: str):
        logger.info(f"移动文件: {file_fid} 到 {to_pdir_fid}")
        url = "https://drive-pc.quark.cn/1/clouddrive/file/move?pr=ucpro&fr=pc&uc_param_str="
        data = {
            "action_type": 1,
            "exclude_fids": [],
            "filelist": [file_fid],
            "to_pdir_fid": to_pdir_fid
        }
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()

    def del_file(self, file_id):
        url = "https://drive-pc.quark.cn/1/clouddrive/file/delete?pr=ucpro&fr=pc&uc_param_str="
        data = {"action_type": 2, "filelist": [file_id], "exclude_fids": []}
        response = requests.post(url=url, json=data, headers=self.headers)
        if response.status_code == 200:
            result = response.json()
            code = result.get("code", -1)
            if code == 0:
                return True
            elif code == 32003:
                return True
            else:
                return False
        return False

    def del_ad_file(self, file_list):
        logger.info("删除可能存在广告的文件")
        for file in file_list:
            file_name = file.get("file_name")
            if ad_check(file_name):
                task_id = self.del_file(file.get("fid"))
                self.task(task_id)

    def add_ad(self, dir_id):
        logger.info("添加个人自定义广告")
        pwd_id = self.ad_pwd_id
        stoken = self.get_stoken(pwd_id)
        detail = self.detail(pwd_id, stoken)
        first_id, share_fid_token = detail.get("fid"), detail.get("share_fid_token")
        task_id = self.save_task_id(pwd_id, stoken, first_id, share_fid_token, dir_id)
        self.task(task_id, 1)
        logger.info("广告移植成功")

    def search_file(self, file_name):
        logger.info("正在从网盘搜索文件🔍")
        url = "https://drive-pc.quark.cn/1/clouddrive/file/search?pr=ucpro&fr=pc&uc_param_str=&_page=1&_size=50&_fetch_total=1&_sort=file_type:desc,updated_at:desc&_is_hl=1"
        params = {"q": file_name}
        try:
            response = requests.get(url=url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            json_data = response.json()
            if not json_data or not json_data.get('data'):
                logger.error(f"search_file 响应格式异常: {json_data}")
                return []
            return json_data['data'].get('list', [])
        except Exception as e:
            logger.error(f"search_file 请求失败: {e}")
            return []

    def get_quota(self):
        """获取网盘空间使用情况"""
        logger.info("正在验证夸克网盘Cookie")
        url = "https://drive-pc.quark.cn/1/clouddrive/capacity?pr=ucpro&fr=pc&uc_param_str="
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get('data'):
                total = data['data'].get('total_capacity', 0)
                used = data['data'].get('used_capacity', 0)
                used_percent = (used / total * 100) if total > 0 else 0
                return {
                    'used': used,
                    'total': total,
                    'free': total - used,
                    'used_percent': round(used_percent, 2)
                }
            else:
                logger.warning(f"get_quota 响应格式异常: {data}")
                return {'used': 0, 'total': 0, 'free': 0, 'used_percent': 0}
        except Exception as e:
            logger.error(f"获取夸克网盘配额失败: {e}")
            return {'used': 0, 'total': 0, 'free': 0, 'used_percent': 0}

    def get_oldest_files(self, limit=50):
        """获取最古老的文件（用于清理）"""
        logger.info(f"正在获取最古老的 {limit} 个文件")
        url = "https://drive-pc.quark.cn/1/clouddrive/file/sort?pr=ucpro&fr=pc&uc_param_str="
        params = {
            "pdir_fid": 0,
            "_page": 1,
            "_size": limit,
            "_fetch_total": 1,
            "_fetch_sub_dirs": 0,
            "_sort": "updated_at:asc"  # 按更新时间升序，最旧的在前
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            data = response.json()
            if data.get('code') == 0 and data.get('data'):
                return data['data'].get('list', [])
            return []
        except Exception as e:
            logger.error(f"获取旧文件列表时出错: {e}")
            return []

    def batch_delete_files(self, file_ids):
        """批量删除文件"""
        if not file_ids:
            return True
        logger.info(f"正在批量删除 {len(file_ids)} 个文件")
        url = "https://drive-pc.quark.cn/1/clouddrive/file/delete?pr=ucpro&fr=pc&uc_param_str="
        data = {
            "action_type": 2,
            "filelist": file_ids,
            "exclude_fids": []
        }
        try:
            response = requests.post(url, json=data, headers=self.headers)
            result = response.json()
            if result.get('code') == 0:
                logger.info(f"批量删除成功: {len(file_ids)} 个文件")
                return True
            else:
                logger.error(f"批量删除失败: {result}")
                return False
        except Exception as e:
            logger.error(f"批量删除时出错: {e}")
            return False

    def clean_old_files(self, percent_threshold=80, delete_count=20):
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
        logger.info(f"当前空间使用率: {used_percent}%")

        if used_percent < percent_threshold:
            logger.info(f"空间使用率 {used_percent}% 低于阈值 {percent_threshold}%，无需清理")
            return True, 0, used_percent

        # 获取最旧的文件
        old_files = self.get_oldest_files(delete_count)
        if not old_files:
            logger.warning("没有找到可清理的旧文件")
            return False, 0, used_percent

        # 排除系统文件夹和特殊文件
        file_ids_to_delete = []
        for file in old_files:
            file_name = file.get('file_name', '')
            # 排除常见的系统文件夹
            if file_name in ['我的资源', '来自分享', '夸克相册']:
                continue
            file_ids_to_delete.append(file.get('fid'))

        if not file_ids_to_delete:
            logger.warning("没有符合条件的文件可删除")
            return False, 0, used_percent

        # 执行删除
        success = self.batch_delete_files(file_ids_to_delete)
        if success:
            logger.info(f"成功清理 {len(file_ids_to_delete)} 个旧文件")
            return True, len(file_ids_to_delete), used_percent
        else:
            return False, 0, used_percent


if __name__ == '__main__':
    pass