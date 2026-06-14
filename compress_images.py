#!/usr/bin/env python3
"""
压缩图片文件
"""
import os
from PIL import Image

def compress_image(input_path, output_path, quality=85):
    """压缩单个图片文件"""
    try:
        with Image.open(input_path) as img:
            # 保持图片格式
            img_format = img.format
            
            # 压缩图片
            img.save(output_path, format=img_format, quality=quality, optimize=True)
            
            # 计算压缩率
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(output_path)
            compression_rate = (1 - compressed_size / original_size) * 100
            
            print(f"压缩 {input_path} -> {output_path}")
            print(f"原始大小: {original_size / 1024:.2f} KB")
            print(f"压缩后大小: {compressed_size / 1024:.2f} KB")
            print(f"压缩率: {compression_rate:.2f}%")
            print()
            
            return True
    except Exception as e:
        print(f"压缩 {input_path} 失败: {e}")
        return False

def main():
    """主函数"""
    # 压缩根目录下的图片
    images_dir = 'static/images'
    for file_name in os.listdir(images_dir):
        file_path = os.path.join(images_dir, file_name)
        if os.path.isfile(file_path) and file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            # 备份原始文件
            backup_path = file_path + '.bak'
            os.rename(file_path, backup_path)
            # 压缩图片
            compress_image(backup_path, file_path)
            # 删除备份
            os.remove(backup_path)
    
    # 压缩douban_cache目录下的图片
    douban_cache_dir = 'static/images/douban_cache'
    if os.path.exists(douban_cache_dir):
        for file_name in os.listdir(douban_cache_dir):
            file_path = os.path.join(douban_cache_dir, file_name)
            if os.path.isfile(file_path) and file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                # 备份原始文件
                backup_path = file_path + '.bak'
                os.rename(file_path, backup_path)
                # 压缩图片
                compress_image(backup_path, file_path)
                # 删除备份
                os.remove(backup_path)
    
    print("图片压缩完成！")

if __name__ == '__main__':
    main()
