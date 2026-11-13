"""設定ファイルを見つけて読み、台帳の行と指摘を作る。"""
from __future__ import annotations

import os
import re
from pathlib import Path

from . import jsonc

CONFIG_NAMES = {"claude_desktop_config.json", ".mcp.json", "mcp.json", ".claude.json"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}
MAX_BYTES = 2 * 1024 * 1024

SECRET_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH)", re.I)
REFERENCE = re.compile(r"^\$\{[^}]+\}$|^\$[A-Z_][A-Z0-9_]*$|^%[A-Z_][A-Z0-9_]*%$")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}
SHELLS = {"bash", "sh", "zsh", "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh"}
BROAD_PATHS = {"/", "~", "~/", "c:\\", "c:/", "c:", "%userprofile%", "$home", "${home}", "/home", "/users", "c:\\users"}

# 権限の区分（推定）。上から順に強い。
TIERS = ("実行", "外部送信", "書き込み", "読み取り")
HINTS = {
    "実行": ("shell", "terminal", "exec", "command", "code-runner", "desktop-commander", "python-repl", "sandbox"),
    "外部送信": ("slack", "gmail", "mail", "teams", "discord", "github", "gitlab", "notion", "fetch", "http", "browser",
               "puppeteer", "playwright", "webhook", "salesforce", "jira", "chat", "api"),
    "書き込み": ("filesystem", "postgres", "mysql", "sqlite", "database", "git", "drive", "sheets", "excel", "write"),
}

RULES = {
    "L01": ("高", "秘密情報の直書き", "鍵やトークンが設定ファイルに書かれている。環境変数や入力欄からの参照に替える", "OWASP ASI03", "セキュリティ確保"),
    "L02": ("中", "版の固定なし", "起動のたびに最新版を取りに行く。承認した版と違うものが動きうる", "OWASP ASI04", "セキュリティ確保"),
    "L03": ("高", "広すぎるフォルダ", "ドライブ全体や利用者のフォルダ全体を渡している。業務に要るフォルダだけにする", "OWASP ASI02", "安全性"),
    "L04": ("中", "暗号化されていない接続", "手元以外のサーバーに http で接続している", "-", "セキュリティ確保"),
    "L05": ("中", "コマンド実行の権限", "任意のコマンドを実行できる道具。隔離した環境か、人の承認を挟む", "OWASP ASI05", "安全性"),
    "L06": ("中", "管理者・停止手順の未記入", "誰が管理し、どう止めるかが台帳に無い", "OWASP ASI10", "アカウンタビリティ"),
    "L07": ("高", "取得したスクリプトの実行", "スキルの中で、ネットから取得したスクリプトをそのまま実行している", "OWASP ASI04, ASI05", "セキュリティ確保"),
    "L08": ("情報", "認証の設定が見当たらない", "リモート接続に認証ヘッダーが無い（OAuthで認証する場合は問題ない）", "OWASP ASI03", "セキュリティ確保"),
}


HOME_DIR = re.compile(r"^(/home/[^/]+|/Users/[^/]+|[a-z]:[\\/]users[\\/][^\\/]+)[\\/]?$", re.I)


def _is_broad(arg: str) -> bool:
    a = arg.strip().strip('"')
    if not a or a.startswith("-"):
        return False
    norm = a.lower().rstrip("\\/") or "/"
    return norm in {b.rstrip("\\/") or "/" for b in BROAD_PATHS} or bool(HOME_DIR.match(a))


def find_files(roots: list[str]) -> list[Path]:
    found = []
    for root in roots:
        r = Path(root).expanduser()
        if r.is_file():
            found.append(r)
            continue
        for dirpath, dirnames, filenames in os.walk(r):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in filenames:
                p = Path(dirpath) / f
                if f in CONFIG_NAMES or f == "SKILL.md":
                    if p.stat().st_size <= MAX_BYTES:
                        found.append(p)
    return sorted(set(found))


def _servers(data: dict) -> list[tuple[str, dict, str]]:
    """設定の形式ごとの違いを吸収して (名前, 設定, 書式) を返す。"""
    out = []
    if isinstance(data.get("mcpServers"), dict):
        out += [(k, v, "mcpServers") for k, v in data["mcpServers"].items()]
    if isinstance(data.get("servers"), dict):
        out += [(k, v, "servers（VS Code）") for k, v in data["servers"].items()]
    for proj, pv in (data.get("projects") or {}).items():  # Claude Code の ~/.claude.json
        if isinstance(pv, dict) and isinstance(pv.get("mcpServers"), dict):
            out += [(f"{k}（{proj}）", v, "projects.mcpServers") for k, v in pv["mcpServers"].items()]
    return [(n, s, f) for n, s, f in out if isinstance(s, dict)]


def _package(command: str, args: list[str]) -> tuple[str, bool]:
    """実行する部品の名前と、版が固定されているかを返す。"""
    cmd = Path(command).name.lower()
    rest = [a for a in args if not a.startswith("-")]
    if cmd in ("npx", "npx.cmd", "bunx", "pnpm", "yarn") and rest:
        pkg = rest[0] if rest[0] not in ("dlx", "exec") else (rest[1] if len(rest) > 1 else "")
        name, _, ver = pkg.rpartition("@") if pkg.count("@") > (1 if pkg.startswith("@") else 0) else (pkg, "", "")
        return pkg, bool(ver) and ver != "latest" and bool(re.match(r"^\d", ver))
    if cmd in ("uvx", "pipx") and rest:
        pkg = rest[1] if rest[0] == "run" and len(rest) > 1 else rest[0]
        return pkg, "==" in pkg
    if cmd in ("docker", "podman") and "run" in args:
        img = next((a for a in args[args.index("run") + 1:] if not a.startswith("-") and "=" not in a), "")
        tagged = "@sha256:" in img or (":" in img.rsplit("/", 1)[-1] and not img.endswith(":latest"))
        return img, tagged
    first = next((a for a in args if not a.startswith("-")), "")
    return f"{command} {first}".strip(), True  # 手元のプログラムを直接起動している場合は版の問題は扱わない


def _tier(text: str, remote: bool, shell: bool) -> str:
    low = text.lower()
    if shell or any(h in low for h in HINTS["実行"]):
        return "実行"
    if remote or any(h in low for h in HINTS["外部送信"]):
        return "外部送信"
    if any(h in low for h in HINTS["書き込み"]):
        return "書き込み"
    return "読み取り"


def scan_config(path: Path) -> list[dict]:
    data = jsonc.loads(path.read_text(encoding="utf-8"))
    rows = []
    for name, s, fmt in _servers(data):
        cmd, args = str(s.get("command", "")), [str(a) for a in s.get("args", []) or []]
        url = str(s.get("url") or s.get("serverUrl") or "")
        env = {str(k): str(v) for k, v in (s.get("env") or {}).items()}
        headers = {str(k): str(v) for k, v in (s.get("headers") or {}).items()}
        host = re.sub(r"^\w+://", "", url).split("/")[0].split(":")[0].lower() if url else ""
        remote = bool(url) and host not in LOCAL_HOSTS
        shell = Path(cmd).name.lower() in SHELLS
        pkg, pinned = _package(cmd, args) if cmd else (url, True)
        flags = []
        for k, v in {**env, **headers}.items():
            if (SECRET_NAME.search(k) or k.lower() == "authorization") and v and not REFERENCE.match(v.split(" ")[-1]):
                flags.append(("L01", f"{k} に値が直接書かれている"))
        if cmd and not pinned:
            flags.append(("L02", f"{pkg}"))
        for a in args:
            if _is_broad(a):
                flags.append(("L03", f"引数 {a}"))
        if url.startswith("http://") and remote:
            flags.append(("L04", url))
        tier = _tier(" ".join([name, cmd, pkg, url, *args]), remote, shell)
        if tier == "実行":
            flags.append(("L05", f"{name}"))
        if remote and not any(k.lower() == "authorization" for k in headers):
            flags.append(("L08", url))
        rows.append({"種類": "MCPサーバー", "名前": name, "設定ファイル": str(path), "書式": fmt,
                     "接続": "リモート" if remote else "手元で起動", "起動するもの": pkg, "版の固定": "あり" if pinned else "なし",
                     "接続先": url, "環境変数": ", ".join(sorted(env)), "権限区分（推定）": tier,
                     "無効": "はい" if s.get("disabled") else "", "指摘": flags})
    return rows


FETCH_EXEC = re.compile(r"(curl|wget)[^\n|]*\|\s*(ba|z)?sh|iwr[^\n|]*\|\s*iex|invoke-webrequest[^\n|]*\|\s*invoke-expression", re.I)


def scan_skill(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
    scripts = [str(p.relative_to(path.parent)) for p in path.parent.rglob("*") if p.suffix in (".sh", ".py", ".ps1", ".js")]
    body = text + "".join(p.read_text(encoding="utf-8", errors="replace") for p in path.parent.rglob("*")
                          if p.suffix in (".sh", ".py", ".ps1", ".js") and p.stat().st_size <= MAX_BYTES)
    flags = [("L07", "取得して実行する記述がある")] if FETCH_EXEC.search(body) else []
    tools = meta.get("allowed-tools", "")
    tier = _tier(tools + " " + " ".join(scripts), False, bool(re.search(r"\bBash\b", tools)))
    if tier == "実行":
        flags.append(("L05", meta.get("name", path.parent.name)))
    return [{"種類": "スキル", "名前": meta.get("name", path.parent.name), "設定ファイル": str(path), "書式": "SKILL.md",
             "接続": "手元", "起動するもの": ", ".join(scripts), "版の固定": "", "接続先": "", "環境変数": "",
             "権限区分（推定）": tier, "無効": "", "指摘": flags}]


def scan(roots: list[str], owners: dict | None = None) -> dict:
    """台帳の行と、読めなかったファイルを返す。owners は人が書く欄（管理者・用途・停止手順・見直し日）。"""
    owners = owners or {}
    rows, errors = [], []
    for p in find_files(roots):
        try:
            rows += scan_skill(p) if p.name == "SKILL.md" else scan_config(p)
        except (ValueError, OSError, UnicodeDecodeError) as e:
            errors.append(f"{p}：{type(e).__name__}")
    for r in rows:
        o = owners.get(r["名前"], {})
        for k in ("管理者", "用途", "停止手順", "見直し日"):
            r[k] = o.get(k, "")
        if o.get("権限区分") in TIERS:  # 人が確かめた区分で推定を置き換える
            r["権限区分（推定）"] = f"{o['権限区分']}（確認済み）"
        if not (r["管理者"] and r["停止手順"]):
            r["指摘"].append(("L06", r["名前"]))
    return {"rows": rows, "errors": errors}
