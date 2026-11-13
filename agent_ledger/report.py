"""台帳を CSV（Excelで開ける）・Markdown・JSON で書き出す。"""
from __future__ import annotations

import csv
import io
import json

from .scan import RULES, TIERS

COLS = ["種類", "名前", "権限区分（推定）", "接続", "起動するもの", "版の固定", "接続先", "環境変数",
        "管理者", "用途", "停止手順", "見直し日", "無効", "設定ファイル", "指摘ID"]
ORDER = {"高": 0, "中": 1, "低": 2, "情報": 3}


def _flat(rows):
    for r in rows:
        yield {**r, "指摘ID": " ".join(sorted({f[0] for f in r["指摘"]}))}


def to_csv(rows) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, extrasaction="ignore")
    w.writeheader()
    for r in _flat(rows):
        w.writerow(r)
    return "\ufeff" + buf.getvalue()


def findings(rows) -> list[dict]:
    out = []
    for r in rows:
        for rid, detail in r["指摘"]:
            sev, title, why, owasp, guide = RULES[rid]
            out.append({"重さ": sev, "ID": rid, "指摘": title, "対象": r["名前"], "内容": detail, "理由と対応": why,
                        "OWASP": owasp, "AI事業者ガイドライン": guide, "設定ファイル": r["設定ファイル"]})
    return sorted(out, key=lambda f: (ORDER[f["重さ"]], f["ID"], f["対象"]))


def to_markdown(result) -> str:
    rows, fs = result["rows"], findings(result["rows"])
    count = {t: sum(r["権限区分（推定）"].startswith(t) for r in rows) for t in TIERS}
    sev = {k: sum(f["重さ"] == k for f in fs) for k in ORDER}
    md = ["# AIエージェント台帳", "",
          f"道具 {len(rows)} 件（MCPサーバー {sum(r['種類'] == 'MCPサーバー' for r in rows)}、スキル {sum(r['種類'] == 'スキル' for r in rows)}）。"
          f"権限区分：" + "、".join(f"{t} {count[t]}" for t in TIERS) + "。",
          f"指摘：高 {sev['高']}、中 {sev['中']}、低 {sev['低']}、情報 {sev['情報']}。", ""]
    if result["errors"]:
        md += ["## 読めなかったファイル", *[f"- {e}" for e in result["errors"]], ""]
    md += ["## 指摘", "| 重さ | ID | 指摘 | 対象 | 内容 | 理由と対応 | 根拠 |", "|---|---|---|---|---|---|---|"]
    md += [f"| {f['重さ']} | {f['ID']} | {f['指摘']} | {f['対象']} | {f['内容']} | {f['理由と対応']} | {f['OWASP']}／{f['AI事業者ガイドライン']} |" for f in fs]
    md += ["", "## 台帳", "| 種類 | 名前 | 権限区分（推定） | 接続 | 起動するもの | 版の固定 | 管理者 | 停止手順 |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        owner, stop = r["管理者"] or "（未記入）", r["停止手順"] or "（未記入）"
        md.append(f"| {r['種類']} | {r['名前']} | {r['権限区分（推定）']} | {r['接続']} | {r['起動するもの']} | {r['版の固定']} | {owner} | {stop} |")
    return "\n".join(md) + "\n"


def to_json(result) -> str:
    return json.dumps({"rows": [{k: v for k, v in r.items() if k != "指摘"} for r in result["rows"]],
                       "findings": findings(result["rows"]), "errors": result["errors"]}, ensure_ascii=False, indent=2)
