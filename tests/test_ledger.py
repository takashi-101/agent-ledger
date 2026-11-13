import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_ledger import __main__ as cli  # noqa: E402
from agent_ledger import jsonc, report, scan  # noqa: E402

EX = ROOT / "examples"


def _by_name(rows):
    return {r["名前"]: r for r in rows}


def _ids(row):
    return {f[0] for f in row["指摘"]}


class JsoncTest(unittest.TestCase):
    def test_comments_and_trailing_commas(self):
        self.assertEqual(jsonc.loads('// c\n{"a": "http://x//y", /* b */ "b": [1,],}'), {"a": "http://x//y", "b": [1]})


class ScanTest(unittest.TestCase):
    def setUp(self):
        owners = json.loads((EX / "owners.json").read_text(encoding="utf-8"))
        self.rows = _by_name(scan.scan([str(EX)], owners)["rows"])

    def test_all_three_formats_are_read(self):
        fmts = {r["書式"] for r in self.rows.values()}
        self.assertEqual(fmts, {"mcpServers", "servers（VS Code）", "SKILL.md"})
        self.assertEqual(len(self.rows), 9)

    def test_secret_literal_is_flagged_but_reference_is_not(self):
        self.assertIn("L01", _ids(self.rows["chat-bot"]))
        self.assertNotIn("L01", _ids(self.rows["tickets"]))  # ${input:...} の参照

    def test_version_pinning(self):
        self.assertIn("L02", _ids(self.rows["filesystem"]))   # 版の指定なし
        self.assertIn("L02", _ids(self.rows["browser"]))      # :latest
        self.assertNotIn("L02", _ids(self.rows["chat-bot"]))  # @1.4.2
        self.assertNotIn("L02", _ids(self.rows["db"]))        # ==0.6.2

    def test_broad_folder_and_shell(self):
        self.assertIn("L03", _ids(self.rows["filesystem"]))
        self.assertTrue(self.rows["ops-shell"]["権限区分（推定）"].startswith("実行"))

    def test_insecure_http_and_missing_auth(self):
        self.assertTrue({"L04", "L08"} <= _ids(self.rows["intranet-search"]))

    def test_skill_fetch_and_execute(self):
        self.assertTrue({"L07", "L05"} <= _ids(self.rows["report-maker"]))

    def test_owner_fields_clear_l06_and_override_tier(self):
        self.assertNotIn("L06", _ids(self.rows["notes-readonly"]))
        self.assertEqual(self.rows["notes-readonly"]["権限区分（推定）"], "読み取り（確認済み）")
        self.assertIn("L06", _ids(self.rows["filesystem"]))

    def test_package_parsing(self):
        self.assertEqual(scan._package("npx", ["-y", "@scope/pkg@2.0.1"]), ("@scope/pkg@2.0.1", True))
        self.assertEqual(scan._package("npx", ["-y", "@scope/pkg"]), ("@scope/pkg", False))
        self.assertEqual(scan._package("npx", ["pkg@latest"]), ("pkg@latest", False))
        self.assertEqual(scan._package("docker", ["run", "-i", "img@sha256:abc"])[1], True)


class OutputTest(unittest.TestCase):
    def test_cli_writes_files_and_fail_on_gate(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cli.main([str(EX), "--out", d, "--fail-on", "高"]), 1)
            csv_text = (Path(d) / "ledger.csv").read_text(encoding="utf-8")
            self.assertTrue(csv_text.startswith("\ufeff種類,名前"))  # Excelで文字化けしないようBOM付き
            data = json.loads((Path(d) / "ledger.json").read_text(encoding="utf-8"))
            self.assertEqual(len(data["rows"]), 9)
            self.assertNotIn("dummy-value-for-test", (Path(d) / "ledger.json").read_text(encoding="utf-8"))

    def test_clean_config_passes_gate(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / ".mcp.json"
            cfg.write_text('{"mcpServers": {"notes": {"command": "python", "args": ["server.py"]}}}', encoding="utf-8")
            owners = Path(d) / "o.json"
            owners.write_text('{"notes": {"管理者": "A", "停止手順": "削除"}}', encoding="utf-8")
            self.assertEqual(cli.main([str(cfg), "--out", str(Path(d) / "o"), "--owners", str(owners), "--fail-on", "情報"]), 0)

    def test_broken_file_is_reported_not_crashed(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".mcp.json").write_text("{ broken", encoding="utf-8")
            res = scan.scan([d])
            self.assertEqual(res["rows"], [])
            self.assertEqual(len(res["errors"]), 1)
            self.assertIn("読めなかったファイル", report.to_markdown(res))


if __name__ == "__main__":
    unittest.main()
