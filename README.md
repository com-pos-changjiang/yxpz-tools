# yxpz-tools

简单的DrissionPage运行配置工具集

## 安装

### 从 PyPI 安装（稳定版）

```bash
pip install yxpz-tools
```

### 更新到最新版

```bash
pip uninstall yxpz-tools -y
pip install --upgrade yxpz-tools
```

### 从源码安装（开发模式，代码改动即时生效）

```bash
git clone https://github.com/com-pos-changjiang/yxpz-tools.git
cd yxpz-tools
pip uninstall yxpz-tools -y   # 若已安装过，先卸载避免版本冲突
pip install -e .
```

依赖说明：DrissionPage、colorama、python-docx、openpyxl、xlrd 会随安装自动装上。

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
