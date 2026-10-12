"""核心工具函数。"""

import random
import re
import string


def greet(name: str = "World") -> str:
    """返回一句问候语。"""
    return f"你好, {name}!"


def slugify(text: str) -> str:
    """把文本转换成 URL 友好的 slug，例如 "Hello World!" -> "hello-world"。"""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def random_string(length: int = 8) -> str:
    """生成指定长度的随机字符串（字母 + 数字）。"""
    if length <= 0:
        raise ValueError("length 必须大于 0")
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))
