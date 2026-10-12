#!/usr/bin/env python3
"""sensitive-data-guard 敏感数据扫描器

扫描范围（对应真实泄露面）:
  1. 工作区文本文件（git 跟踪 + 未忽略的未跟踪文件）
  2. git 提交者元数据（所有分支的作者姓名/邮箱，随每次 push 公开）
  3. git 历史内容（高危模式全文扫描，上限 200 个提交）
  4. 历史中删除过的敏感文件（内容仍在历史中，checkout 旧提交即可拿到）
  5. dist/ 构建产物解包扫描（wheel/sdist 才是真正上传到 PyPI 的内容）
  6. 痕迹文件盘点（.idea/、.claude 本地文件、.ipynb 输出、二进制/图片）

退出码: 0=干净或仅低危提示  1=存在中危(需用户确认)  2=存在高危(禁止发布)  3=运行出错

用法:
  python scan.py [--repo PATH] [--rules PATH] [--json] [--skip-history] [--skip-dist]

自定义规则: --rules 指向 TOML 文件，格式见 sensitive-rules.example.toml
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

try:  # 避免 Windows 控制台 GBK 编码报错
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HIGH, MEDIUM, LOW, INFO = "high", "medium", "low", "info"
SEV_ORDER = {INFO: 0, LOW: 1, MEDIUM: 2, HIGH: 3}
SEV_LABEL = {HIGH: "高危", MEDIUM: "中危", LOW: "低危", INFO: "提示"}

HISTORY_COMMIT_CAP = 200


def pat(pid: str, name: str, regex: str, severity: str) -> dict:
    return {"id": pid, "name": name, "regex": re.compile(regex), "severity": severity}


# 内置规则。宁可误报不可漏报；误报由 allowlist 解决，漏报没有补救机会。
BUILTIN_PATTERNS = [
    pat("private-key", "PEM 私钥", r"-----BEGIN [A-Z ]*PRIVATE KEY( BLOCK)?-----", HIGH),
    pat("pypi-token", "PyPI API Token", r"\bpypi-[A-Za-z0-9_]{20,}", HIGH),
    pat("aws-key", "AWS Access Key", r"\bAKIA[0-9A-Z]{16}\b", HIGH),
    pat("github-token", "GitHub Token", r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", HIGH),
    pat("gitlab-pat", "GitLab PAT", r"\bglpat-[A-Za-z0-9_-]{20,}\b", HIGH),
    pat("slack-token", "Slack Token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", HIGH),
    pat("openai-style", "OpenAI 风格密钥", r"\bsk-[A-Za-z0-9_-]{20,}\b", HIGH),
    pat("conn-password", "连接串内嵌密码", r"\b[a-z]{3,12}://[^/\s:'\"]+:[^@\s]{4,}@", HIGH),
    pat(
        "cred-assign",
        "疑似凭证赋值",
        r"(?i)(?<![a-z0-9])(pass(word|wd)?|secret|token|api[_-]?key|access[_-]?key)\b\s*[:=]\s*[\"'][^\"']{8,}[\"']",
        MEDIUM,
    ),
    pat(
        "personal-email",
        "个人邮箱",
        r"[A-Za-z0-9._%+-]+@(?:qq|foxmail|163|126|gmail|outlook|hotmail)\.(?:com|net)",
        MEDIUM,
    ),
    pat("cn-mobile", "手机号", r"(?<![\dA-Za-z])1[3-9]\d{9}(?![\dA-Za-z])", MEDIUM),
    pat(
        "internal-ip",
        "内网 IP",
        r"(?<![\d.])(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
        r"|192\.168\.\d{1,3}\.\d{1,3})(?![\d.])",
        LOW,
    ),
]

# 文件名命中即为高危：这类文件根本不该出现在仓库里
SENSITIVE_FILENAME = re.compile(
    r"(?i)(^|/)(\.env(\..+)?|\.pypirc|id_rsa[^/]*|id_ed25519[^/]*|id_ecdsa[^/]*"
    r"|[^/]*\.pem|[^/]*\.pfx|[^/]*\.p12|[^/]*credentials[^/]*|[^/]*secret[^/]*|[^/]*password[^/]*)$"
)

# 凭证赋值的常见占位符，命中则豁免（避免把测试样例当真泄露）
PLACEHOLDER_HINTS = ("your", "<", "{{", "$(", "example", "changeme", "xxx", "placeholder", "dummy", "sample")

TRACE_DIRS = (".idea/",)  # 内容已被 gitignore 但仍值得做高危扫描的本地目录
TRACE_PREFIXES = (".claude/",)  # .claude/ 下除 skills 外的本地文件
BINARY_HINT_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico",
    ".pdf", ".xlsx", ".docx", ".pptx", ".zip", ".7z", ".rar", ".mp4", ".mov",
}


# ---------------------------------------------------------------- 工具函数

def mask(text: str, severity: str) -> str:
    """报告里不能原样打印密钥——报告本身可能进入会话记录、issue、截图。"""
    t = text.strip()
    if severity == HIGH:
        return f"{t[:6]}***(len={len(t)})"
    if "@" in t and " " not in t:  # 邮箱: 保留域名，打码本地部分
        loc, _, dom = t.partition("@")
        return f"{loc[:2]}***@{dom}"
    if re.fullmatch(r"1[3-9]\d{9}", t):  # 手机号
        return f"{t[:3]}****{t[7:]}"
    return t[:40] + ("…" if len(t) > 40 else "")


def add_finding(findings: list, severity: str, rule: str, name: str, where: str, line_no, snippet: str) -> None:
    # 中危规则也可能抓到真密钥（如 cred-assign 抓到 pypi-token）——打码级别按内容升级
    mask_level = severity
    if severity != HIGH:
        mask_level = HIGH if any(
            p["severity"] == HIGH and p["regex"].search(snippet) for p in BUILTIN_PATTERNS
        ) else severity
    findings.append(
        {
            "severity": severity,
            "rule": rule,
            "name": name,
            "where": where,
            "line": line_no,
            "snippet": mask(snippet, mask_level),
        }
    )


def is_placeholder_value(value: str) -> bool:
    v = value.strip().strip("\"'").lower()
    return len(v) < 8 or any(h in v for h in PLACEHOLDER_HINTS)


def _parse_simple_toml(text: str) -> dict:
    """Python 3.10 无 tomllib 时的降级解析器。

    只支持本工具用到的 TOML 子集: [section]、[[array-of-tables]]、
    字符串/布尔/整数、字符串数组(允许跨行)。"""
    root: dict = {}
    current: dict = root
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("#"):
            continue
        if line.startswith("[["):
            current = {}
            root.setdefault(line.strip("[]").strip(), []).append(current)
            continue
        if line.startswith("["):
            current = root.setdefault(line.strip("[]").strip(), {})
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip().strip("\"'")
        v = v.strip()
        if v.startswith("["):  # 字符串数组, 允许跨行; 注释行因不含引号被自然忽略
            buf = v
            while "]" not in buf and i < len(lines):
                buf += " " + lines[i].strip()
                i += 1
            current[k] = [a or b for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", buf)]
        elif v.startswith(("'", '"')):
            current[k] = v.strip("'\"")
        elif v in ("true", "false"):
            current[k] = v == "true"
        else:
            try:
                current[k] = int(v)
            except ValueError:
                current[k] = v
    return root


def load_rules(path: Path) -> tuple[list[dict], list[str], list[str]]:
    """读取自定义规则 TOML。返回 (patterns, allow_paths, allow_regexes)。"""
    raw = path.read_text(encoding="utf-8")
    try:
        import tomllib
        data = tomllib.loads(raw)
    except ModuleNotFoundError:
        data = _parse_simple_toml(raw)
    patterns = []
    for p in data.get("patterns", []):
        try:
            patterns.append(pat(p["id"], p.get("name", p["id"]), p["regex"], p.get("severity", MEDIUM)))
        except re.error as e:
            print(f"[警告] 自定义规则 {p.get('id', '?')} 正则无效，已跳过: {e}", file=sys.stderr)
    allow = data.get("allowlist", {})
    return patterns, [re.compile(x) for x in allow.get("paths", [])], [re.compile(x) for x in allow.get("regexes", [])]


# ---------------------------------------------------------------- git 操作

def git(repo: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败: {r.stderr.strip()}")
    return r.stdout


def repo_files(repo: Path) -> list[str]:
    """git 跟踪 + 未忽略的未跟踪文件 = 真正可能被上传的集合。"""
    out = git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return sorted({f for f in out.split("\0") if f})


# ---------------------------------------------------------------- 各扫描阶段

def scan_text_content(findings: list, patterns: list[dict], allow_paths, allow_regexes,
                      rel: str, text: str, high_only: bool = False) -> None:
    norm = rel.replace("\\", "/")
    if any(r.search(norm) for r in allow_paths):
        return
    for p in patterns:
        if high_only and p["severity"] != HIGH:
            continue
        for m in p["regex"].finditer(text):
            if p["id"] == "cred-assign" and is_placeholder_value(m.group(0)):
                continue
            if any(r.search(m.group(0)) for r in allow_regexes):
                continue
            line_no = text.count("\n", 0, m.start()) + 1
            add_finding(findings, p["severity"], p["id"], p["name"], norm, line_no, m.group(0))


def scan_working_tree(findings: list, repo: Path, patterns: list[dict], allow_paths, allow_regexes,
                      stats: dict) -> None:
    files = repo_files(repo)
    stats["worktree_files"] = len(files)
    sensitive_files, binaries, notebooks = [], [], []

    for rel in files:
        norm = rel.replace("\\", "/")
        fpath = repo / rel
        if SENSITIVE_FILENAME.search(norm):
            sensitive_files.append(norm)

        if fpath.suffix.lower() == ".ipynb":
            try:
                nb = json.loads(fpath.read_text(encoding="utf-8"))
                if any(c.get("outputs") for c in nb.get("cells", []) if c.get("cell_type") == "code"):
                    notebooks.append(norm)
            except Exception:
                pass

        try:
            text = fpath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, ValueError, OSError):
            if fpath.suffix.lower() in BINARY_HINT_EXT:
                binaries.append(norm)
            continue

        high_only = norm.startswith(TRACE_DIRS) or (
            norm.startswith(TRACE_PREFIXES) and not norm.startswith(".claude/skills/")
        )
        scan_text_content(findings, patterns, allow_paths, allow_regexes, norm, text, high_only)

    for f in sensitive_files:
        add_finding(findings, HIGH, "sensitive-filename", "敏感文件名", f, None, f)
    for nb in notebooks:
        add_finding(findings, MEDIUM, "nb-outputs", "notebook 输出含运行数据", nb, None, nb)
    stats["binaries"] = binaries


def scan_authors(findings: list, repo: Path, patterns: list[dict], allow_regexes: list,
                 stats: dict) -> None:
    """提交者邮箱随每次 push 公开——个人邮箱默认按中危处理，allowlist 可豁免有意公开的联系方式。"""
    try:
        out = git(repo, "log", "--all", "--format=%an%x09%ae")
    except RuntimeError:
        return
    authors = sorted({tuple(line.split("\t", 1)) for line in out.splitlines() if "\t" in line})
    stats["authors"] = authors
    email_pats = [p for p in patterns if p["id"] in ("personal-email",)] + [
        p for p in patterns if p["id"] not in ("personal-email",) and p["severity"] in (HIGH, MEDIUM)
    ]
    for name, email in authors:
        for p in email_pats:
            m = p["regex"].search(email) or p["regex"].search(name)
            if m:
                if any(r.search(m.group(0)) for r in allow_regexes):
                    continue
                add_finding(findings, p["severity"], "git-author", f"git 提交者信息({p['name']})",
                            "git log(所有提交)", None, f"{name} <{email}>")


def scan_history_content(findings: list, repo: Path, patterns: list[dict], stats: dict) -> None:
    """取全部历史补丁(git log -p)，用 Python 正则扫——git grep -E 不支持 \\b 等语法。"""
    revs = git(repo, "rev-list", "--all").split()
    stats["commits_total"] = len(revs)
    if not revs:
        return
    if len(revs) > HISTORY_COMMIT_CAP:
        print(f"[提示] 提交数 {len(revs)} 超过上限 {HISTORY_COMMIT_CAP}，跳过历史内容扫描"
              f"（建议用 gitleaks 做全量审计）")
        stats["commits_scanned"] = 0
        return
    stats["commits_scanned"] = len(revs)
    high = [p for p in patterns if p["severity"] == HIGH]

    patch = git(repo, "log", "--all", "-p", "-n", str(HISTORY_COMMIT_CAP), "--no-color")
    current_file = None
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            # diff --git a/x b/x —— 取 b/ 侧路径
            seg = line.split(" b/", 1)
            current_file = seg[1] if len(seg) == 2 else None
            continue
        if not current_file or line.startswith(("index ", "--- ", "+++ ", "@@")):
            continue
        content = line[1:] if line[:1] in "+- " else line  # 去掉补丁前缀
        for p in high:
            if p["regex"].search(content):
                add_finding(findings, HIGH, "git-history", f"git 历史({p['name']})",
                            current_file, None, content.strip())
                break


def _safe_extract(archive, dest: Path, kind: str) -> None:
    """解包前校验成员路径，防 zip-slip / 路径逃逸。"""
    if kind == "zip":
        names = archive.namelist()
    else:
        names = [m.name for m in archive.getmembers() if m.isfile() or m.isdir()]
    for n in names:
        norm = n.replace("\\", "/")
        if norm.startswith(("/", "~")) or ".." in Path(norm).parts or ":" in norm.split("/")[0]:
            raise ValueError(f"压缩包内含危险路径: {n}")
    archive.extractall(dest)


def scan_deleted_files(findings: list, repo: Path) -> None:
    out = git(repo, "log", "--all", "--diff-filter=D", "--name-only", "--format=")
    deleted = sorted({f.strip().replace("\\", "/") for f in out.splitlines() if f.strip()})
    for f in deleted:
        if SENSITIVE_FILENAME.search(f):
            add_finding(findings, HIGH, "deleted-in-history", "历史中删除过的敏感文件",
                        f, None, f + "（内容仍在 git 历史中）")


def scan_dist(findings: list, repo: Path, patterns: list[dict], allow_paths, allow_regexes,
              stats: dict) -> None:
    dist = repo / "dist"
    if not dist.is_dir():
        return
    artifacts = sorted(dist.glob("*.whl")) + sorted(dist.glob("*.tar.gz"))
    stats["dist_artifacts"] = [a.name for a in artifacts]
    with tempfile.TemporaryDirectory(prefix="sdg-dist-") as tmp:
        for art in artifacts:
            dest = Path(tmp) / art.stem
            dest.mkdir()
            try:
                if art.suffix == ".whl":
                    with zipfile.ZipFile(art) as z:
                        _safe_extract(z, dest, "zip")
                else:
                    with tarfile.open(art) as t:
                        _safe_extract(t, dest, "tar")
            except Exception as e:
                print(f"[警告] 无法解包 {art.name}: {e}", file=sys.stderr)
                continue
            for f in dest.rglob("*"):
                if not f.is_file():
                    continue
                rel_art = f.relative_to(dest).as_posix()
                try:
                    text = f.read_text(encoding="utf-8")
                except (UnicodeDecodeError, ValueError, OSError):
                    continue
                scan_text_content(findings, patterns, allow_paths, allow_regexes,
                                  f"[dist:{art.name}] {rel_art}", text)


def scan_trace_inventory(findings: list, repo: Path, stats: dict) -> None:
    """盘点本地痕迹文件。已在 .gitignore 里的不会上传，但列出来让使用者心里有数。"""
    try:
        ignored_raw = git(repo, "ls-files", "-z", "--others", "--ignored", "--exclude-standard")
    except RuntimeError:
        return
    ignored = [f.replace("\\", "/") for f in ignored_raw.split("\0") if f.strip()]
    interesting = [f for f in ignored if f.startswith(TRACE_DIRS) or f.startswith(TRACE_PREFIXES)]
    if interesting:
        stats["ignored_trace_files"] = interesting
        add_finding(findings, INFO, "ignored-trace", "本地痕迹文件(已被 gitignore,不会上传)",
                    f"{len(interesting)} 个文件,如 .idea/、.claude/ 本地配置", None,
                    ", ".join(interesting[:5]) + ("…" if len(interesting) > 5 else ""))


# ---------------------------------------------------------------- 报告

def print_report(findings: list, stats: dict, repo: Path) -> int:
    findings.sort(key=lambda f: -SEV_ORDER[f["severity"]])
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in (HIGH, MEDIUM, LOW, INFO)}

    print("=" * 56)
    print(f"敏感数据扫描报告  ({repo.name})")
    print("=" * 56)
    authors = stats.get("authors") or []
    print(f"范围: 工作区 {stats.get('worktree_files', 0)} 个文件 | "
          f"git 提交 {stats.get('commits_scanned', 0)}/{stats.get('commits_total', 0)} 个(历史内容) | "
          f"作者 {len(authors)} 人 | dist 产物 {len(stats.get('dist_artifacts', []))} 个")
    if stats.get("dist_artifacts"):
        print(f"产物: {', '.join(stats['dist_artifacts'])}")

    for sev in (HIGH, MEDIUM, LOW, INFO):
        group = [f for f in findings if f["severity"] == sev]
        if not group:
            continue
        print(f"\n[{SEV_LABEL[sev]}] {len(group)} 项")
        for f in group:
            loc = f"{f['where']}:{f['line']}" if f["line"] else f["where"]
            print(f"  • ({f['rule']}) {f['name']}  {loc}")
            print(f"      {f['snippet']}")

    if stats.get("binaries"):
        print(f"\n[人工审查] 二进制/图片 {len(stats['binaries'])} 个（正则无法识别图片内容，"
              f"请确认截图不含内网系统界面/真实数据）:")
        for b in stats["binaries"][:10]:
            print(f"  • {b}")

    print("\n" + "-" * 56)
    if counts[HIGH]:
        print(f"结论: ❌ 发现 {counts[HIGH]} 项高危 —— 禁止发布/推送。先修复再扫描。")
        return 2
    if counts[MEDIUM]:
        print(f"结论: ⚠️  发现 {counts[MEDIUM]} 项中危 —— 需逐条确认后才能继续。")
        return 1
    print("结论: ✅ 未发现高危/中危问题。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="sensitive-data-guard 敏感数据扫描器")
    ap.add_argument("--repo", default=".", help="仓库路径")
    ap.add_argument("--rules", default=None, help="自定义规则 TOML(默认尝试 .claude/sensitive-rules.local.toml)")
    ap.add_argument("--json", action="store_true", help="输出 JSON(供程序处理)")
    ap.add_argument("--skip-history", action="store_true", help="跳过 git 历史内容扫描")
    ap.add_argument("--skip-dist", action="store_true", help="跳过 dist/ 解包扫描")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"错误: 仓库路径不存在: {repo}", file=sys.stderr)
        return 3

    patterns = list(BUILTIN_PATTERNS)
    allow_paths, allow_regexes = [], []
    # 默认加载两层规则: 项目级(可提交,放"有意公开"的豁免) + 本地级(勿提交,放公司敏感词)
    rule_files = (
        [Path(args.rules)] if args.rules else
        [repo / ".claude" / "sensitive-rules.toml",
         repo / ".claude" / "sensitive-rules.local.toml"]
    )
    for rules_path in rule_files:
        if rules_path.is_file():
            custom, ap, ar = load_rules(rules_path)
            patterns.extend(custom)
            allow_paths.extend(ap)
            allow_regexes.extend(ar)
            print(f"[信息] 已加载规则文件: {rules_path}")

    try:
        findings: list[dict] = []
        stats: dict = {}
        seen: set[tuple] = set()  # 同一内容在多个提交的补丁里重复出现时只报一次
        scan_working_tree(findings, repo, patterns, allow_paths, allow_regexes, stats)
        if repo_files(repo):  # 是 git 仓库才做 git 维度的扫描
            scan_authors(findings, repo, patterns, allow_regexes, stats)
            if not args.skip_history:
                scan_history_content(findings, repo, patterns, stats)
                scan_deleted_files(findings, repo)
            scan_trace_inventory(findings, repo, stats)
        if not args.skip_dist:
            scan_dist(findings, repo, patterns, allow_paths, allow_regexes, stats)
        findings = [f for f in findings
                    if (k := (f["severity"], f["rule"], f["where"], f["line"], f["snippet"]))
                    not in seen and not seen.add(k)]
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps({"repo": str(repo), "stats": stats, "findings": findings},
                         ensure_ascii=False, indent=2))
        return 2 if any(f["severity"] == HIGH for f in findings) else (
            1 if any(f["severity"] == MEDIUM for f in findings) else 0)
    return print_report(findings, stats, repo)


if __name__ == "__main__":
    sys.exit(main())
