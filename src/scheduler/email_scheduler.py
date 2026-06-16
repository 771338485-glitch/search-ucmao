import logging
import threading
from datetime import datetime, timedelta

from src.services.email_service import EmailService
from src.db.cookie_config_dao import get_cookie_by_cloud_name
from src.db.email_config_dao import EmailConfigDAO
from src.db.search_history_dao import (
    get_daily_visitor_count,
    get_yesterday_visitor_count,
    get_last_7_days_visitor_count
)

logger = logging.getLogger(__name__)

_email_scheduler_thread = None
_email_stop_event = threading.Event()


def send_cookie_expired_email(expired_cookies: list):
    """
    发送云盘Cookie过期通知邮件
    :param expired_cookies: 过期的Cookie列表
    """
    try:
        email_service = EmailService()
        subject = "桃白白影视 - 云盘Cookie过期通知"
        
        cookies_list_html = ""
        for cookie_info in expired_cookies:
            cookies_list_html += f"<p>• <strong>{cookie_info['name']}</strong></p>"
        
        body = f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 12px;">
            <div style="background: white; padding: 30px; border-radius: 8px; text-align: center;">
                <h1 style="color: #333; font-size: 28px; margin-bottom: 20px;">🎬 桃白白影视</h1>
                <div style="font-size: 18px; color: #555; margin: 20px 0; line-height: 1.8; text-align: left;">
                    <p style="color: #e74c3c; font-weight: bold; font-size: 20px; text-align: center;">
                        检测到云盘Cookie已过期！
                    </p>
                    <p><strong>时间:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
                    <p><strong>过期的Cookie:</strong></p>
                    {cookies_list_html}
                    <p style="margin-top: 20px; color: #e74c3c;">
                        请及时更新云盘Cookie，否则洗白功能将无法正常使用！
                    </p>
                </div>
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 14px;">
                    <p>桃白白影视 - 让每一份网盘资源都为你创造价值</p>
                </div>
            </div>
        </div>
        """
        
        success, message = email_service.send_notification(subject, body)
        
        if success:
            logger.info(f"[邮件通知] 云盘Cookie过期通知邮件发送成功")
        else:
            logger.warning(f"[邮件通知] 云盘Cookie过期通知邮件发送失败: {message}")
    except Exception as e:
        logger.error(f"[邮件通知] 发送云盘Cookie过期通知邮件时出错: {e}", exc_info=True)


def check_cookies_expired():
    """
    检查云盘Cookie是否过期
    :return: 过期的Cookie列表
    """
    expired_cookies = []
    
    try:
        # 检查夸克网盘Cookie
        quark_cookie = get_cookie_by_cloud_name("夸克网盘")
        if not quark_cookie:
            expired_cookies.append({"name": "夸克网盘", "cookie": quark_cookie})
            logger.warning("[邮件通知] 夸克网盘Cookie已过期或未配置")
        
        # 检查百度网盘Cookie
        baidu_cookie = get_cookie_by_cloud_name("百度网盘")
        if not baidu_cookie:
            expired_cookies.append({"name": "百度网盘", "cookie": baidu_cookie})
            logger.warning("[邮件通知] 百度网盘Cookie已过期或未配置")
        
    except Exception as e:
        logger.error(f"[邮件通知] 检查Cookie过期状态时出错: {e}", exc_info=True)
    
    return expired_cookies


def send_cookie_reminder_email():
    """
    发送更换云盘Cookie提醒邮件
    """
    try:
        email_service = EmailService()
        subject = "桃白白影视 - 云盘Cookie提醒"
        body = """
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 12px;">
            <div style="background: white; padding: 30px; border-radius: 8px; text-align: center;">
                <h1 style="color: #333; font-size: 28px; margin-bottom: 20px;">🎬 桃白白影视</h1>
                <div style="font-size: 18px; color: #555; margin: 20px 0; line-height: 1.8;">
                    <p>您好！</p>
                    <p>今天是 <strong>{date}</strong>，</p>
                    <p>提醒您：</p>
                    <p style="font-size: 20px; color: #e74c3c; font-weight: bold;">
                        请及时更换云盘Cookie，防止过期！
                    </p>
                </div>
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 14px;">
                    <p>桃白白影视 - 让每一份网盘资源都为你创造价值</p>
                </div>
            </div>
        </div>
        """.format(date=datetime.now().strftime('%Y年%m月%d日'))
        
        success, message = email_service.send_notification(subject, body)
        
        if success:
            logger.info(f"[邮件通知] 云盘Cookie提醒邮件发送成功")
        else:
            logger.warning(f"[邮件通知] 云盘Cookie提醒邮件发送失败: {message}")
    except Exception as e:
        logger.error(f"[邮件通知] 发送云盘Cookie提醒邮件时出错: {e}", exc_info=True)


def send_wash_failed_email(reason: str, url: str, title: str = ""):
    """
    发送洗白失败邮件通知
    :param reason: 失败原因
    :param url: 原始链接
    :param title: 标题
    """
    try:
        email_service = EmailService()
        subject = "桃白白影视 - 洗白失败通知"
        body = """
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 12px;">
            <div style="background: white; padding: 30px; border-radius: 8px; text-align: center;">
                <h1 style="color: #333; font-size: 28px; margin-bottom: 20px;">🎬 桃白白影视</h1>
                <div style="font-size: 18px; color: #555; margin: 20px 0; line-height: 1.8; text-align: left;">
                    <p style="color: #e74c3c; font-weight: bold; font-size: 20px; text-align: center;">
                        洗白失败！
                    </p>
                    <p><strong>时间:</strong> {time}</p>
                    <p><strong>标题:</strong> {title}</p>
                    <p><strong>链接:</strong> {url}</p>
                    <p><strong>原因:</strong> <span style="color: #e74c3c;">{reason}</span></p>
                </div>
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 14px;">
                    <p>桃白白影视 - 让每一份网盘资源都为你创造价值</p>
                </div>
            </div>
        </div>
        """.format(
            time=datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
            title=title or "无标题",
            url=url,
            reason=reason
        )
        
        success, message = email_service.send_notification(subject, body)
        
        if success:
            logger.info(f"[邮件通知] 洗白失败邮件发送成功: {title}")
        else:
            logger.warning(f"[邮件通知] 洗白失败邮件发送失败: {message}")
    except Exception as e:
        logger.error(f"[邮件通知] 发送洗白失败邮件时出错: {e}", exc_info=True)


def check_qr_code_expiry():
    """
    检查二维码是否过期
    :return: 过期的二维码列表
    """
    try:
        from src.db.qr_code_dao import get_expiring_qr_codes, mark_as_notified
        from src.services.email_service import get_email_service
        
        # 获取最新的过期二维码记录（只返回一条）
        expiring_qr_codes = get_expiring_qr_codes(days=5)
        
        if expiring_qr_codes:
            logger.info(f"[邮件通知] 检测到 {len(expiring_qr_codes)} 个过期或已过期的二维码")
            
            # 发送邮件通知
            email_service = get_email_service()
            for qr_code in expiring_qr_codes:
                # 检查是否已通知，避免重复发送
                if qr_code.get('notified') == 1:
                    logger.info(f"[邮件通知] 二维码已通知过，跳过: {qr_code.get('file_name')}")
                    continue
                
                success, message = email_service.send_qr_code_expiry_notification(qr_code)
                if success:
                    logger.info(f"[邮件通知] 二维码到期通知邮件发送成功: {qr_code.get('file_name')}")
                    # 标记为已通知，避免每天重复发送
                    mark_as_notified(qr_code.get('id'))
                else:
                    logger.warning(f"[邮件通知] 二维码到期通知邮件发送失败: {message}")
        else:
            logger.info("[邮件通知] 没有过期的二维码")
            
    except Exception as e:
        logger.error(f"[邮件通知] 检查二维码到期状态时出错: {e}", exc_info=True)


def _email_scheduler_loop():
    """
    邮件通知任务循环
    1. 每天0点检查云盘Cookie是否过期
    2. 每月20号9点发送更换云盘Cookie提醒
    3. 每天0点检查二维码是否即将到期
    4. 每天22点发送访客统计邮件
    """
    _daily_check_executed = False

    while not _email_stop_event.is_set():
        try:
            now = datetime.now()

            # 检查是否是每天0点（使用小时判断，避免分钟精度问题）
            if now.hour == 0 and not _daily_check_executed:
                logger.info(f"[邮件通知] 每天0点检查云盘Cookie过期状态")
                expired_cookies = check_cookies_expired()

                if expired_cookies:
                    logger.info(f"[邮件通知] 检测到 {len(expired_cookies)} 个过期的Cookie，发送邮件通知")
                    send_cookie_expired_email(expired_cookies)
                else:
                    logger.info("[邮件通知] 所有云盘Cookie状态正常")

                # 检查二维码是否即将到期
                logger.info(f"[邮件通知] 每天0点检查二维码到期状态")
                check_qr_code_expiry()

                _daily_check_executed = True
                logger.info("[邮件通知] 每日检查完成")

            # 重置执行标记（当小时不为0时）
            elif now.hour != 0:
                _daily_check_executed = False

            # 检查是否是每月20号9点（只在9点发送一次，不跳过后续的22:00访客统计）
            if now.day == 20 and now.hour == 9:
                logger.info(f"[邮件通知] 今天是每月20号，发送云盘Cookie提醒邮件")
                send_cookie_reminder_email()

            # 检查是否是每天22点
            if now.hour == 22:
                logger.info(f"[邮件通知] 每天22点发送访客统计邮件")
                send_visitor_stats_email()
                
                # 等待到明天再检查
                tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=1)
                seconds_until_tomorrow = (tomorrow - now).total_seconds()
                
                logger.info(f"[邮件通知] 等待到明天再检查，需要等待 {seconds_until_tomorrow:.2f} 秒")
                if _email_stop_event.wait(seconds_until_tomorrow):
                    break
                continue
            
            # 计算到下一个小时的时间
            next_hour = datetime(now.year, now.month, now.day, now.hour) + timedelta(hours=1)
            seconds_until_next_hour = (next_hour - now).total_seconds()
            
            logger.debug(f"[邮件通知] 等待到下一个小时检查，需要等待 {seconds_until_next_hour:.2f} 秒")
            
            if _email_stop_event.wait(seconds_until_next_hour):
                break
                
        except Exception as e:
            logger.error(f"[邮件通知] 邮件通知任务执行异常: {e}", exc_info=True)
            # 出错后等待1小时再继续
            _email_stop_event.wait(3600)


def start_email_scheduler():
    """
    启动邮件通知定时任务
    """
    global _email_scheduler_thread, _email_stop_event
    
    if _email_scheduler_thread and _email_scheduler_thread.is_alive():
        logger.warning("[邮件通知] 邮件通知调度器已在运行中")
        return
    
    _email_stop_event.clear()
    _email_scheduler_thread = threading.Thread(
        target=_email_scheduler_loop,
        daemon=True
    )
    _email_scheduler_thread.start()
    logger.info("[邮件通知] 邮件通知调度器已启动: 每月20号9点发送云盘Cookie提醒，每天0点检查二维码到期状态，每天22点发送访客统计邮件")


def send_visitor_stats_email():
    """
    发送访客统计邮件
    """
    try:
        email_config_dao = EmailConfigDAO()
        
        if not email_config_dao.is_visitor_stats_enabled():
            logger.info("[邮件通知] 访客统计邮件未启用，跳过发送")
            return
        
        today = get_daily_visitor_count()
        yesterday = get_yesterday_visitor_count()
        last_7_days = get_last_7_days_visitor_count()
        
        email_service = EmailService()
        subject = "桃白白影视 - 每日访客统计"
        
        body = f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 12px;">
            <div style="background: white; padding: 30px; border-radius: 8px; text-align: center;">
                <h1 style="color: #333; font-size: 28px; margin-bottom: 20px;">🎬 桃白白影视</h1>
                <div style="font-size: 18px; color: #555; margin: 20px 0; line-height: 1.8; text-align: left;">
                    <p style="color: #667eea; font-weight: bold; font-size: 20px; text-align: center;">
                        每日访客统计
                    </p>
                    <p><strong>时间:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 10px 0; font-size: 16px;">
                            <strong>今日访客:</strong> <span style="color: #667eea; font-size: 24px; font-weight: bold;">{today}</span> 人
                        </p>
                        <p style="margin: 10px 0; font-size: 16px;">
                            <strong>昨日访客:</strong> <span style="color: #3498db; font-size: 24px; font-weight: bold;">{yesterday}</span> 人
                        </p>
                        <p style="margin: 10px 0; font-size: 16px;">
                            <strong>近7天访客:</strong> <span style="color: #2ecc71; font-size: 24px; font-weight: bold;">{last_7_days}</span> 人
                        </p>
                    </div>
                </div>
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 14px;">
                    <p>桃白白影视 - 让每一份网盘资源都为你创造价值</p>
                </div>
            </div>
        </div>
        """
        
        success, message = email_service.send_notification(subject, body)
        
        if success:
            logger.info(f"[邮件通知] 访客统计邮件发送成功")
        else:
            logger.warning(f"[邮件通知] 访客统计邮件发送失败: {message}")
    except Exception as e:
        logger.error(f"[邮件通知] 发送访客统计邮件时出错: {e}", exc_info=True)


def stop_email_scheduler():
    """
    停止邮件通知定时任务
    """
    global _email_stop_event
    
    _email_stop_event.set()
    logger.info("[邮件通知] 邮件通知调度器已停止")
