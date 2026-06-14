"""
邮件服务类
实现邮件发送功能
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple
from src.db.email_config_dao import EmailConfigDAO

logger = logging.getLogger(__name__)


class EmailService:
    """邮件服务类"""
    
    def __init__(self):
        """初始化邮件服务"""
        self.config_dao = EmailConfigDAO()
        logger.info("邮件服务初始化完成")
    
    def send_test_email(self) -> Tuple[bool, str]:
        """
        发送测试邮件
        
        Returns:
            (是否成功, 消息)
        """
        try:
            config = self.config_dao.get_full_config()
            
            if not config.get('enabled'):
                return False, "邮件通知未启用"
            
            if not config.get('notification_email'):
                return False, "未配置通知邮箱"
            
            if not config.get('smtp_server'):
                return False, "未配置SMTP服务器"
            
            # 构建测试邮件
            subject = "桃白白影视 - 测试邮件"
            body = """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #FFA500; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
                    .content { padding: 20px; background-color: #f9f9f9; border-radius: 0 0 8px 8px; }
                    .footer { margin-top: 20px; text-align: center; color: #666; font-size: 12px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>🎬 桃白白影视</h2>
                    </div>
                    <div class="content">
                        <h3>测试邮件</h3>
                        <p>您好！</p>
                        <p>这是一封来自桃白白影视的测试邮件。</p>
                        <p>如果您收到了这封邮件，说明您的邮件通知配置已经成功！</p>
                        <p>祝您使用愉快！</p>
                    </div>
                    <div class="footer">
                        <p>桃白白影视 - 让每一份网盘资源都为你创造价值</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self._send_email(config, subject, body)
        
        except Exception as e:
            logger.error(f"发送测试邮件失败: {e}")
            return False, f"发送失败: {str(e)}"
    
    def send_notification(self, subject: str, body: str) -> Tuple[bool, str]:
        """
        发送通知邮件
        
        Args:
            subject: 邮件主题
            body: 邮件内容（HTML格式）
            
        Returns:
            (是否成功, 消息)
        """
        try:
            config = self.config_dao.get_full_config()
            
            if not config.get('enabled'):
                logger.warning("邮件通知未启用，跳过发送")
                return False, "邮件通知未启用"
            
            if not config.get('notification_email'):
                logger.warning("未配置通知邮箱，跳过发送")
                return False, "未配置通知邮箱"
            
            return self._send_email(config, subject, body)
        
        except Exception as e:
            logger.error(f"发送通知邮件失败: {e}")
            return False, f"发送失败: {str(e)}"
    
    def send_qr_code_expiry_notification(self, qr_code_info: dict) -> Tuple[bool, str]:
        """
        发送二维码到期通知邮件
        
        Args:
            qr_code_info: 二维码信息字典，包含id, upload_time, file_name, expires_at等字段
            
        Returns:
            (是否成功, 消息)
        """
        try:
            config = self.config_dao.get_full_config()
            
            if not config.get('enabled'):
                logger.warning("邮件通知未启用，跳过发送")
                return False, "邮件通知未启用"
            
            if not config.get('notification_email'):
                logger.warning("未配置通知邮箱，跳过发送")
                return False, "未配置通知邮箱"
            
            # 构建邮件内容
            subject = "【桃白白影视】二维码即将到期提醒"
            
            # 格式化时间
            upload_time = qr_code_info.get('upload_time')
            expires_at = qr_code_info.get('expires_at')
            
            if isinstance(upload_time, str):
                upload_time_str = upload_time
            else:
                upload_time_str = upload_time.strftime('%Y-%m-%d %H:%M:%S') if upload_time else '未知'
            
            if isinstance(expires_at, str):
                expires_at_str = expires_at
            else:
                expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S') if expires_at else '未知'
            
            file_name = qr_code_info.get('file_name', '未知')
            
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #FFA500; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; border-radius: 0 0 8px 8px; }}
                    .footer {{ margin-top: 20px; text-align: center; color: #666; font-size: 12px; }}
                    .info-item {{ margin-bottom: 10px; }}
                    .info-label {{ font-weight: bold; color: #555; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>🎬 桃白白影视</h2>
                    </div>
                    <div class="content">
                        <h3>二维码即将到期提醒</h3>
                        <p>您好！</p>
                        <p>您上传的二维码图片即将到期，请及时更新。</p>
                        <div class="info-item">
                            <span class="info-label">二维码文件：</span>
                            {file_name}
                        </div>
                        <div class="info-item">
                            <span class="info-label">上传时间：</span>
                            {upload_time_str}
                        </div>
                        <div class="info-item">
                            <span class="info-label">到期时间：</span>
                            {expires_at_str}
                        </div>
                        <p>请登录热门资源管理页面，重新上传新的二维码图片以确保服务正常运行。</p>
                    </div>
                    <div class="footer">
                        <p>桃白白影视 - 让每一份网盘资源都为你创造价值</p>
                    </div>
                </div>
            </body>
            </html>
            """

            
            return self._send_email(config, subject, body)
        
        except Exception as e:
            logger.error(f"发送二维码到期通知邮件失败: {e}")
            return False, f"发送失败: {str(e)}"

    def _send_email(self, config: dict, subject: str, body: str) -> Tuple[bool, str]:
        """
        实际发送邮件

        Args:
            config: 邮件配置
            subject: 邮件主题
            body: 邮件内容（HTML格式）

        Returns:
            (是否成功, 消息)
        """
        smtp_server = config.get('smtp_server')
        smtp_port = config.get('smtp_port', 587)
        smtp_username = config.get('smtp_username', config.get('notification_email'))
        smtp_password = config.get('smtp_password')
        use_tls = config.get('use_tls', True)
        to_email = config.get('notification_email')

        logger.info(f"正在发送邮件到: {to_email}")
        logger.info(f"SMTP服务器: {smtp_server}:{smtp_port}")

        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['From'] = smtp_username
        msg['To'] = to_email
        msg['Subject'] = subject

        # 添加HTML内容
        html_part = MIMEText(body, 'html', 'utf-8')
        msg.attach(html_part)

        # 连接SMTP服务器
        server = None
        try:
            if use_tls:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)

            # 登录
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)

            # 发送邮件
            server.send_message(msg)

            logger.info(f"邮件发送成功: {to_email}")
            return True, "邮件发送成功"

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP认证失败")
            return False, "SMTP认证失败，请检查用户名和密码"
        except smtplib.SMTPConnectError:
            logger.error("SMTP连接失败")
            return False, "SMTP连接失败，请检查服务器地址和端口"
        except Exception as e:
            logger.error(f"发送邮件时出错: {e}")
            return False, f"发送失败: {str(e)}"
        finally:
            # 确保 SMTP 连接被关闭
            if server:
                try:
                    server.quit()
                except Exception as e:
                    logger.error(f"关闭 SMTP 连接失败: {e}")


# 创建邮件服务单例
_email_service_instance = None


def get_email_service() -> EmailService:
    """
    获取邮件服务实例（单例模式）
    
    Returns:
        邮件服务实例
    """
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance
