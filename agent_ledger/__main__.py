"""使い方：python -m agent_ledger 探すフォルダ [...] --out 出力先 [--owners 管理表.json] [--fail-on 高]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import report, scan


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="agent_ledger", description="MCPの設定とAgent SkillsからAIエージェント台帳を作る")
    p.add_argument("roots", nargs="+", help="探すフォルダまたはファイル")
    p.add_argument("--out", default="ledger", help="出力先のフォルダ（ledger.csv / ledger.md / ledger.json を作る）")
    p.add_argument("--owners", help="人が書く欄（管理者・用途・停止手順・見直し日）を名前ごとに書いたJSON")
    p.add_argument("--fail-on", choices=["高", "中", "低", "情報"], help="この重さ以上の指摘があれば終了コード1（CI用）")
    a = p.parse_args(argv)
    owners = json.loads(Path(a.owners).read_text(encoding="utf-8")) if a.owners else {}
    result = scan.scan(a.roots, owners)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ledger.csv").write_text(report.to_csv(result["rows"]), encoding="utf-8")
    (out / "ledger.md").write_text(report.to_markdown(result), encoding="utf-8")
    (out / "ledger.json").write_text(report.to_json(result), encoding="utf-8")
    fs = report.findings(result["rows"])
    print(f"道具 {len(result['rows'])} 件、指摘 {len(fs)} 件 → {out}/ledger.csv, ledger.md, ledger.json")
    if a.fail_on:
        limit = report.ORDER[a.fail_on]
        return 1 if any(report.ORDER[f["重さ"]] <= limit for f in fs) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
