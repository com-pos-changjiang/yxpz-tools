# CLAUDE.md

本文件为 Claude Code 在此仓库工作时的指引。

## 项目简介

`yxpz-tools`：一个简单的 Python 实用工具集，已发布到 PyPI。
采用 src 布局，构建后端为 setuptools（PEP 621，配置全在 `pyproject.toml`）。

- 源码：`src/yxpz_tools/`（仅 3 个文件：`__init__.py`、`core.py`、`cli.py`）
- 命令行入口：`yxpz`（映射到 `yxpz_tools.cli:main`）
- 运行时依赖：**无**（全部为标准库）
- 开发/发布依赖：`requirements-dev.txt`（build、twine）

## 发布流程（已自动化）

使用根目录的 `release.py` 一键发布：

```bash
python release.py <新版本号>            # 升版本 → 清理 → 构建 → twine check → 确认 → 上传
python release.py <新版本号> --dry-run  # 只升版本并构建，不上传
python release.py <新版本号> -y         # 跳过上传前的确认
```

脚本会自动做这些事：

1. 同步修改 `pyproject.toml` 和 `src/yxpz_tools/__init__.py` 两处版本号
2. 清理旧的 `dist/`、`build/`、`src/yxpz_tools.egg-info/`
3. `python -m build` 构建wheel 和 sdist
4. `twine check` 校验元数据
5. 确认后 `twine upload` 上传

### 发布/推送前的硬门禁（必须遵守）

**任何发布动作之前必须先跑敏感数据扫描**（`git push`、`twine upload`、`release.py`
不带 `--dry-run`、首次公开到 GitHub 等）：

```bash
python .claude/skills/sensitive-data-guard/scripts/scan.py
```

- 退出码 2（高危）：**禁止发布**，除非用户明确说「我已知晓风险，强制继续」
- 退出码 1（中危）：逐条向用户确认后才能继续
- 公司专属敏感词规则写在 `.claude/sensitive-rules.local.toml`（已 gitignore，绝不提交）
- 详细流程见 `.claude/skills/sensitive-data-guard/SKILL.md`

## 发布注意事项

- **版本号必须递增**：PyPI 不允许重复上传相同版本号，传错了只能升号重发
- 版本号格式：`x.y.z`（脚本会校验）
- 首次发布需配置 PyPI API Token 到 `C:\Users\<用户名>\.pypirc`（`username = __token__`）
- 发布后验证：`pip install --upgrade yxpz-tools` 或访问 https://pypi.org/project/yxpz-tools/

## 打包范围（哪些文件会上传到 PyPI）

由 `pyproject.toml` 的 `[tool.setuptools.packages.find] where = ["src"]` 决定：

- **wheel 包含**：`src/yxpz_tools/` 下的 3 个 .py 文件 + 元数据（METADATA、entry_points、LICENSE）
- **sdist 额外包含**：`README.md`、`LICENSE`、`pyproject.toml`、`setup.cfg`（自动生成的空文件）
- **不会上传**：`release.py`、`requirements-dev.txt`、`CLAUDE.md`、`.gitignore`、`.idea/` 等根目录其他文件

## 环境

- Windows + Git Bash；PyCharm 打开
- Python 3.12（本地）
