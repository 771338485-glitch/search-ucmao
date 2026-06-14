"""
邮件配置数据访问层
"""

import json
import logging
import os
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class EmailConfigDAO:
    """邮件配置数据访问类"""
    
    def __init__(self):
        """初始化邮件配置DAO"""
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'configs')
        self.config_file = os.path.join(self.config_dir, 'email_config.json')
        logger.info(f"邮件配置文件路径: {self.config_file}")
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info("成功加载邮件配置")
                    return config
            else:
                logger.info("配置文件不存在，返回默认配置")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"加载邮件配置失败: {e}")
            return self._get_default_config()
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置文件
        
        Args:
            config: 配置字典
            
        Returns:
            是否保存成功
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info("成功保存邮件配置")
            return True
        except Exception as e:
            logger.error(f"保存邮件配置失败: {e}")
            return False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            默认配置字典
        """
        return {
            "notification_email": "",
            "smtp_server": "",
            "smtp_port": 587,
            "smtp_username": "",
            "smtp_password": "",
            "use_tls": True,
            "enabled": False,
            "visitor_stats_enabled": False
        }
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取邮件配置
        
        Returns:
            配置字典
        """
        config = self._load_config()
        # 不返回密码等敏感信息
        safe_config = config.copy()
        if 'smtp_password' in safe_config:
            safe_config['smtp_password'] = '******'
        return safe_config
    
    def get_full_config(self) -> Dict[str, Any]:
        """
        获取完整的邮件配置（包含敏感信息）
        
        Returns:
            完整配置字典
        """
        return self._load_config()
    
    def save_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        保存邮件配置
        
        Args:
            config: 配置字典
            
        Returns:
            (是否成功, 消息)
        """
        try:
            # 验证必要字段
            if 'notification_email' not in config:
                return False, "缺少通知邮箱字段"
            
            # 验证邮箱格式
            if config['notification_email'] and not self._is_valid_email(config['notification_email']):
                return False, "邮箱格式不正确"
            
            # 加载现有配置
            existing_config = self._load_config()
            
            # 更新配置（保留未修改的密码）
            for key, value in config.items():
                if key == 'smtp_password' and value == '******':
                    # 如果密码是掩码，保留原值
                    continue
                existing_config[key] = value
            
            # 保存配置
            if self._save_config(existing_config):
                return True, "配置保存成功"
            else:
                return False, "配置保存失败"
        
        except Exception as e:
            logger.error(f"保存邮件配置时出错: {e}")
            return False, f"保存失败: {str(e)}"
    
    def _is_valid_email(self, email: str) -> bool:
        """
        验证邮箱格式
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否有效
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def get_notification_email(self) -> Optional[str]:
        """
        获取通知邮箱
        
        Returns:
            通知邮箱地址
        """
        config = self._load_config()
        return config.get('notification_email')
    
    def is_enabled(self) -> bool:
        """
        检查邮件通知是否启用
        
        Returns:
            是否启用
        """
        config = self._load_config()
        return config.get('enabled', False)
    
    def is_visitor_stats_enabled(self) -> bool:
        """
        检查访客统计邮件是否启用
        
        Returns:
            是否启用
        """
        config = self._load_config()
        return config.get('visitor_stats_enabled', False)
