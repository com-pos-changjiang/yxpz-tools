# 泄露补救指南

发现敏感数据已进入公开渠道（或即将进入）时，按这个顺序处理。
**顺序很重要：先让凭证失效，再清理历史。** 历史清理期间凭证仍是活的，
任何拿到它的人都能继续用。

## 1. 吊销/轮换凭证（第一优先级）

| 泄露物 | 处理 |
|--------|------|
| PyPI token | https://pypi.org/manage/account/token/ 删除并重建；更新 `~/.pypirc` |
| GitHub token | Settings → Developer settings → 删除并重建 |
| 云厂商 AK/SK | 控制台禁用旧 key → 创建新 key → 检查泄露期间的调用日志（可能已被滥用） |
| 数据库密码 | 改密码 + 检查异常连接日志 |
| SSH 私钥 | 从所有服务器的 `authorized_keys` 移除公钥，重新生成 |

判断依据很简单：**假设它已经被拿走了**。公开后的几分钟足够爬虫抓取
（GitHub 有公开的实时扫描管道，泄露的 AWS key 平均几分钟内就会被利用）。

## 2. 清理 git 历史

只删文件再提交是没用的——历史里还在。用 `git filter-repo`（比 filter-branch 快且安全）：

```bash
pip install git-filter-repo

# 方式 A：按路径删除（适合删整个敏感文件，如 .env）
git filter-repo --invert-paths --path .env --force

# 方式 B：按内容替换（适合把历史里的某个 token 替换掉）
echo 'pypi-实际的token==>***REMOVED***' > replacements.txt
git filter-repo --replace-text replacements.txt --force
```

注意：
- filter-repo 会移除 remote，之后需要重新 `git remote add`
- 强推 `git push --force --all` + `--tags`；有协作者时要提前通知（所有人需要重新克隆）
- GitHub 上旧提交可能仍通过 PR 引用/缓存访问到；彻底清除需联系 GitHub Support
- 平台侧的 fork/clone 不受你控制——这再次说明第 1 步（吊销凭证）才是根治

## 3. 平台特定事项

### PyPI
- **已发布的版本无法删除**，只能 yank（从默认下载中隐藏，但仍可显式安装）
- 如果 wheel/sdist 里带了敏感数据：吊销相关凭证 → 修好源码 → 升版本号重新发布
- 永远不要把 `.pypirc` 放进项目目录

### GitHub
- 开启 Secret scanning + Push protection（Settings → Code security），推送含已知
  token 模式的内容会被直接拦截
- 已泄露进公开仓库的内容可能被 fork、被搜索引擎缓存，联系 GitHub Support 可请求
  清除缓存视图（`https://github.com/<owner>/<repo>/commit/<sha>` 的缓存）

## 4. 复盘：堵住源头

- 凭证一律走环境变量或本地不入库的配置（`.gitignore` + 提供 `.example` 模板）
- 本 skill 的扫描应该成为发布流程的固定一步（见 CLAUDE.md）
- 如果泄露源于构建产物夹带（egg-info、`__pycache__`），发布前清理 `dist/`、`build/`
  并重新构建，确认产物内容后再上传
