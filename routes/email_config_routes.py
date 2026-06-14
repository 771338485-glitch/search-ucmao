"""
邮件配置路由
"""

from flask import Blueprint, jsonify, request
import logging
from datetime import datetime
from src.db.email_config_dao import EmailConfigDAO
from src.services.email_service import get_email_service
from src.db.search_history_dao import (
    get_daily_visitor_count,
    get_yesterday_visitor_count,
    get_last_7_days_visitor_count
)
from utils.auth_utils import api_token_required

logger = logging.getLogger(__name__)

email_config_bp = Blueprint('email_config', __name__)

email_config_dao = EmailConfigDAO()
email_service = get_email_service()


@email_config_bp.route('/api/email/config', methods=['GET'])
@api_token_required
def get_email_config():
    """
    获取邮件配置
    """
    try:
        config = email_config_dao.get_config()
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        logger.error(f"获取邮件配置失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取配置失败: {str(e)}'
        }), 500


@email_config_bp.route('/api/email/config', methods=['POST'])
@api_token_required
def save_email_config():
    """
    保存邮件配置
    """
    try:
        config = request.get_json()
        if not config:
            return jsonify({
                'success': False,
                'message': '请求数据为空'
            }), 400
        
        success, message = email_config_dao.save_config(config)
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"保存邮件配置失败: {e}")
        return jsonify({
            'success': False,
            'message': f'保存配置失败: {str(e)}'
        }), 500


@email_config_bp.route('/api/email/test', methods=['POST'])
@api_token_required
def send_test_email():
    """
    发送测试邮件
    """
    try:
        success, message = email_service.send_test_email()
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"发送测试邮件失败: {e}")
        return jsonify({
            'success': False,
            'message': f'发送失败: {str(e)}'
        }), 500


@email_config_bp.route('/api/email/test-visitor-stats', methods=['POST'])
@api_token_required
def send_visitor_stats_test_email():
    """
    发送访客统计测试邮件
    """
    try:
        today = get_daily_visitor_count()
        yesterday = get_yesterday_visitor_count()
        last_7_days = get_last_7_days_visitor_count()
        
        subject = "桃白白影视 - 每日访客统计（测试）"
        
        body = f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 12px;">
            <div style="background: white; padding: 30px; border-radius: 8px; text-align: center;">
                <h1 style="color: #333; font-size: 28px; margin-bottom: 20px;">🎬 桃白白影视</h1>
                <div style="font-size: 18px; color: #555; margin: 20px 0; line-height: 1.8; text-align: left;">
                    <p style="color: #667eea; font-weight: bold; font-size: 20px; text-align: center;">
                        每日访客统计（测试）
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
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"发送访客统计测试邮件失败: {e}")
        return jsonify({
            'success': False,
            'message': f'发送失败: {str(e)}'
        }), 500
