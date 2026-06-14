import os
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64

from configs.app_config import ENCRYPTION_KEY

logger = logging.getLogger(__name__)

class EncryptionUtils:
    """加密工具类（使用 AES-GCM 模式提供认证加密）"""

    def __init__(self, key=None):
        # 使用配置的密钥
        if key:
            self.key = key
        elif ENCRYPTION_KEY:
            self.key = ENCRYPTION_KEY.encode()
        else:
            raise ValueError("ENCRYPTION_KEY 环境变量必须配置")

        # 确保密钥长度为 16、24 或 32 字节
        if len(self.key) not in [16, 24, 32]:
            raise ValueError(f"ENCRYPTION_KEY 长度必须为 16、24 或 32 字节，当前长度: {len(self.key)}")

    def encrypt(self, plaintext):
        """加密文本（使用 AES-GCM 模式）"""
        if not plaintext:
            return None

        try:
            # 生成随机 nonce（12 字节）
            nonce = os.urandom(12)

            # 创建 AES-GCM 加密器
            aesgcm = AESGCM(self.key)

            # 加密数据（AES-GCM 自动提供认证）
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

            # 将 nonce 和密文组合并 base64 编码
            return base64.b64encode(nonce + ciphertext).decode()
        except Exception as e:
            logger.error(f"加密失败: {e}")
            return None

    def decrypt(self, ciphertext):
        """解密文本（使用 AES-GCM 模式）"""
        if not ciphertext:
            return None

        try:
            # 解码 base64
            encrypted_data = base64.b64decode(ciphertext)

            # 提取 nonce 和密文
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]

            # 创建 AES-GCM 解密器
            aesgcm = AESGCM(self.key)

            # 解密数据（AES-GCM 自动验证认证）
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            return plaintext.decode()
        except Exception as e:
            logger.error(f"解密失败: {e}")
            return None

# 创建全局加密工具实例
encryption_utils = EncryptionUtils()
