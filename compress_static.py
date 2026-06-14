#!/usr/bin/env python3
"""
压缩静态资源文件
"""
import os
import re

def compress_css(css_content):
    """压缩CSS内容"""
    # 移除注释
    css_content = re.sub(r'/\*[\s\S]*?\*/', '', css_content)
    # 移除多余的空白字符
    css_content = re.sub(r'\s+', ' ', css_content)
    # 移除分号前的空白
    css_content = re.sub(r'\s*;\s*', ';', css_content)
    # 移除花括号前后的空白
    css_content = re.sub(r'\s*{\s*', '{', css_content)
    css_content = re.sub(r'\s*}\s*', '}', css_content)
    # 移除冒号前后的空白
    css_content = re.sub(r'\s*:\s*', ':', css_content)
    # 移除逗号前后的空白
    css_content = re.sub(r'\s*,\s*', ',', css_content)
    # 移除行尾的分号
    css_content = re.sub(r';\s*}', '}', css_content)
    return css_content.strip()

def compress_js(js_content):
    """压缩JavaScript内容"""
    # 移除注释
    js_content = re.sub(r'//.*$', '', js_content, flags=re.MULTILINE)
    js_content = re.sub(r'/\*[\s\S]*?\*/', '', js_content)
    # 移除多余的空白字符
    js_content = re.sub(r'\s+', ' ', js_content)
    # 移除分号前的空白
    js_content = re.sub(r'\s*;\s*', ';', js_content)
    # 移除花括号前后的空白
    js_content = re.sub(r'\s*{\s*', '{', js_content)
    js_content = re.sub(r'\s*}\s*', '}', js_content)
    # 移除冒号前后的空白
    js_content = re.sub(r'\s*:\s*', ':', js_content)
    # 移除逗号前后的空白
    js_content = re.sub(r'\s*,\s*', ',', js_content)
    # 移除括号前后的空白
    js_content = re.sub(r'\s*\(\s*', '(', js_content)
    js_content = re.sub(r'\s*\)\s*', ')', js_content)
    # 移除方括号前后的空白
    js_content = re.sub(r'\s*\[\s*', '[', js_content)
    js_content = re.sub(r'\s*\]\s*', ']', js_content)
    return js_content.strip()

def compress_file(file_path):
    """压缩单个文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if file_path.endswith('.css'):
        compressed_content = compress_css(content)
    elif file_path.endswith('.js') and not file_path.endswith('.min.js'):
        compressed_content = compress_js(content)
    else:
        return False
    
    # 保存压缩后的文件
    min_file_path = file_path.replace('.css', '.min.css').replace('.js', '.min.js')
    with open(min_file_path, 'w', encoding='utf-8') as f:
        f.write(compressed_content)
    
    # 计算压缩率
    original_size = len(content)
    compressed_size = len(compressed_content)
    compression_rate = (1 - compressed_size / original_size) * 100
    
    print(f"压缩 {file_path} -> {min_file_path}")
    print(f"原始大小: {original_size} bytes")
    print(f"压缩后大小: {compressed_size} bytes")
    print(f"压缩率: {compression_rate:.2f}%")
    print()
    
    return True

def main():
    """主函数"""
    # 压缩CSS文件
    css_dir = 'static/css'
    for file_name in os.listdir(css_dir):
        if file_name.endswith('.css') and not file_name.endswith('.min.css'):
            file_path = os.path.join(css_dir, file_name)
            compress_file(file_path)
    
    # 压缩JavaScript文件
    js_dir = 'static/js'
    for file_name in os.listdir(js_dir):
        if file_name.endswith('.js') and not file_name.endswith('.min.js'):
            file_path = os.path.join(js_dir, file_name)
            compress_file(file_path)
    
    print("压缩完成！")

if __name__ == '__main__':
    main()
