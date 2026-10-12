"""一键发布脚本：升版本 -> 清理 -> 构建 -> 检查 -> 上传 PyPI。

用法:
    python release.py 0.1.2              # 指定新版本号，构建并上传
    python release.py 0.1.2 -y           # 跳过上传前的确认
    python release.py 0.1.2 --dry-run    # 只升版本并构建，不上传

前置条件（只需一次）:
    pip install -r requirements-dev.txt
    在 C:\\Users\\<用户名>\\.pypirc 中配置好 PyPI API Token
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYPROJECT = ROOT / "pyproject.toml"
INIT = ROOT / "src" / "yxpz_tools" / "__init__.py"


def run(cmd: list[str]) -> None:
    """执行命令，失败时终止脚本。"""
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=ROOT)


def bump_version(new_version: str) -> None:
    """同步修改 pyproject.toml 和 __init__.py 里的版本号。"""
    text = PYPROJECT.read_text(encoding="utf-8")
    text, n = re.subn(r'(?m)^version = ".*"$', f'version = "{new_version}"', text)
    if n != 1:
        sys.exit("错误: 没能在 pyproject.toml 里定位到 version 字段")
    PYPROJECT.write_text(text, encoding="utf-8")

    text = INIT.read_text(encoding="utf-8")
    text, n = re.subn(
        r'(?m)^__version__ = ".*"$', f'__version__ = "{new_version}"', text
    )
    if n != 1:
        sys.exit("错误: 没能在 __init__.py 里定位到 __version__")
    INIT.write_text(text, encoding="utf-8")

    print(f"✓ 版本号已更新为 {new_version} (pyproject.toml + __init__.py)")


def clean() -> None:
    """删除旧的构建产物，避免把旧文件重复上传。"""
    for d in ["dist", "build", "src/yxpz_tools.egg-info"]:
        path = ROOT / d
        if path.exists():
            shutil.rmtree(path)
            print(f"✓ 已清理 {d}/")


def main() -> int:
    parser = argparse.ArgumentParser(description="yxpz-tools 一键发布")
    parser.add_argument("version", help="新版本号，例如 0.1.2")
    parser.add_argument("-y", "--yes", action="store_true", help="跳过上传确认")
    parser.add_argument(
        "--dry-run", action="store_true", help="只升版本并构建，不上传"
    )
    args = parser.parse_args()

    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        sys.exit("错误: 版本号格式应为 x.y.z，例如 0.1.2")

    bump_version(args.version)
    clean()
    run([sys.executable, "-m", "build"])
    run([sys.executable, "-m", "twine", "check", "dist/*"])

    if args.dry_run:
        print("\n✓ dry-run 完成，未上传。产物在 dist/ 目录")
        return 0

    print(f"\n即将上传 yxpz-tools {args.version} 到 PyPI")
    if not args.yes and input("确认上传? [y/N] ").strip().lower() != "y":
        print("已取消（版本号已改，如需回退请手动改回）")
        return 1

    run([sys.executable, "-m", "twine", "upload", "dist/*"])
    print(f"\n🎉 发布完成! https://pypi.org/project/yxpz-tools/{args.version}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
