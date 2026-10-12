# yxpz-tools

简单的DrssionPage运行配置工具集

## 安装

```bash
pip install yxpz-tools
```

## 使用

### 作为库

```python
from yxpz_tools import greet, slugify, random_string

print(greet("世界"))          # 你好, 世界!
print(slugify("Hello World!")) # hello-world
print(random_string(8))        # aB3xY9zQ
```

### 命令行

```bash
yxpz greet 世界
yxpz slug "Hello World"
yxpz rand 16
```

## License

MIT
