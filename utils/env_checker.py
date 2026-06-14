import os
import sys
import logging

logger = logging.getLogger(__name__)


def check_environment_variables():
    """
    检查必需的环境变量是否已配置

    Returns:
        tuple: (是否通过检查, 缺失的环境变量列表)
    """
    required_vars = [
        'SECRET_KEY',
        'API_KEY',
        'ADMIN_USERNAME',    # 管理员凭据为必需
        'ADMIN_PASSWORD',    # 管理员凭据为必需
        'ENCRYPTION_KEY',    # 加密密钥为必需
    ]

    optional_vars = [
        'QUARK_PAN_COOKIE',
        'BAIDU_PAN_COOKIE',
        'DEFAULT_SAVE_DIR',
    ]

    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            logger.error(f"缺少必需的环境变量: {var}")

    if missing_vars:
        logger.error("=" * 60)
        logger.error("环境变量检查失败！")
        logger.error(f"缺少 {len(missing_vars)} 个必需的环境变量:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.error("=" * 60)
        logger.error("请在 .env 文件中配置这些环境变量")
        logger.error("示例 .env 文件内容:")
        logger.error("SECRET_KEY=your-secret-key-here")
        logger.error("API_KEY=your-api-key-here")
        logger.error("ADMIN_USERNAME=admin")
        logger.error("ADMIN_PASSWORD=your-strong-password")
        logger.error("ENCRYPTION_KEY=your-32-byte-encryption-key-here")
        logger.error("=" * 60)
        return False, missing_vars

    logger.info("=" * 60)
    logger.info("环境变量检查通过 ✓")
    logger.info("必需的环境变量已配置:")
    for var in required_vars:
        value = os.getenv(var)
        masked_value = value[:4] + '***' if len(value) > 4 else '***'
        logger.info(f"  ✓ {var}: {masked_value}")

    logger.info("可选的环境变量:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            masked_value = value[:4] + '***' if len(value) > 4 else '***'
            logger.info(f"  ✓ {var}: {masked_value}")
        else:
            logger.info(f"  - {var}: 未配置")
    logger.info("=" * 60)

    return True, []


def validate_environment():
    """
    验证环境变量，如果缺少必需变量则退出程序
    
    Returns:
        bool: 是否通过验证
    """
    passed, missing = check_environment_variables()
    
    if not passed:
        print("\n" + "=" * 60)
        print("❌ 环境变量检查失败！")
        print(f"缺少 {len(missing)} 个必需的环境变量:")
        for var in missing:
            print(f"  - {var}")
        print("=" * 60)
        print("请在项目根目录创建 .env 文件并配置这些环境变量")
        print("示例:")
        print("  SECRET_KEY=your-secret-key-here")
        print("=" * 60 + "\n")
        sys.exit(1)
    
    return True
