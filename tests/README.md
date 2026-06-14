# 测试说明

## 运行测试

### 方法1：使用 pytest（推荐）

```bash
# 安装 pytest
pip install pytest

# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_example.py

# 显示详细输出
pytest tests/ -v

# 显示打印输出
pytest tests/ -s
```

### 方法2：使用 unittest

```bash
# 运行所有测试
python -m unittest discover tests/

# 运行特定测试文件
python tests/test_example.py
```

## 测试覆盖范围

- `test_example.py`: 基础测试示例
  - 异常类测试
  - 海报清理功能测试
  - 通用工具函数测试

## 添加新测试

1. 在 `tests/` 目录下创建新的测试文件
2. 文件名以 `test_` 开头
3. 测试类以 `Test` 开头
4. 测试方法以 `test_` 开头

示例：

```python
import unittest

class TestMyFeature(unittest.TestCase):
    
    def test_something(self):
        # 测试代码
        self.assertEqual(1 + 1, 2)
```
