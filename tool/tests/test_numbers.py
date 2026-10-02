"""researchkit-check の numbers.py のテスト。一時ディレクトリに調査プロジェクトを作り、スクリプトを subprocess で呼ぶ。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parents[2]
NUM = SCAFFOLD / "skills" / "researchkit" / "researchkit-check" / "scripts" / "numbers.py"
CONFIG = SCAFFOLD / "skills" / "researchkit" / "researchkit-status" / "templates" / "config.yaml"
RQ = "studies/001-market-size"

OUT = {
    "size_2025": 123_400_000_000,
    "size_oku": 1234,
    "share": 0.123,
    "share_pct": 12.3,
    "growth": -0.5,
    "users": 12345,
    "count": 1234,
    "by_year": [{"year": 2024, "n": 980}, {"year": 2025, "n": 1020}],
    "label": "abc",
}


class NumbersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        (self.root / ".researchkit").mkdir()
        shutil.copy(CONFIG, self.root / ".researchkit" / "config.yaml")
        out = self.root / RQ / "analysis" / "out"
        out.mkdir(parents=True)
        (out / "market.json").write_text(json.dumps(OUT), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def findings(self, body: str) -> None:
        (self.root / RQ / "findings.md").write_text("# 主張\n\n" + body + "\n", encoding="utf-8")

    def run_num(self, *args: str) -> tuple[int, str]:
        proc = subprocess.run([sys.executable, str(NUM), "--root", str(self.root), *args],
                              capture_output=True, text=True, encoding="utf-8")
        return proc.returncode, proc.stdout + proc.stderr

    def test_formats_match(self) -> None:
        ref = "{N:analysis/out/market.json#%s}"
        lines = [
            "市場は 2025 年に 1,234 億円" + ref % "size_2025" + "である。",
            "単位を億円で持つ場合も 1,234 億円" + ref % "size_oku" + "と書ける。",
            "シェアは 12.3%" + ref % "share" + "、別の表記で 12.3％" + ref % "share_pct" + "。",
            "伸びは -0.5" + ref % "growth" + "、利用者は 1.2万人" + ref % "users" + "。",
            "件数は 1234 件" + ref % "count" + "、2025 年は 1,020" + ref % "by_year.1.n" + "。",
            "全角でも １，２３４件" + ref % "count" + "。",
            "手で計算した値 3.5 倍{N:calc}",
            "",
            "## 計算",
        ]
        self.findings("\n".join(lines))
        code, out = self.run_num("--rq", "001")
        self.assertEqual(code, 0, out)
        self.assertIn("checked=9 calc=1", out)

    def test_mismatch_and_errors(self) -> None:
        ref = "{N:analysis/out/market.json#%s}"
        lines = [
            "市場は 1,300 億円" + ref % "size_2025" + "。",
            "シェアは 15%" + ref % "share" + "。",
            "キーがない 10" + ref % "nothing" + "。",
            "数値でない 10" + ref % "label" + "。",
            "ファイルがない 10{N:analysis/out/none.json#a}。",
            "数値がない{N:analysis/out/market.json#count}。",
            "書式が違う 10{N:analysis/out/market.json}。",
            "期間は 2020-2025 年で、伸びは 0.5" + ref % "growth" + "。",
        ]
        self.findings("\n".join(lines))
        code, out = self.run_num("--rq", "001")
        self.assertEqual(code, 1, out)
        for c in ("MISMATCH", "MISSING_KEY", "NOT_NUMBER", "MISSING_FILE", "NO_NUMBER", "BAD_REF"):
            self.assertIn(c, out)
        self.assertEqual(out.count("MISMATCH"), 3, out)
        self.assertIn(f"ERROR {RQ}/findings.md:3 MISMATCH", out)

    def test_tolerance_from_config(self) -> None:
        self.findings("利用者は 12,300 人{N:analysis/out/market.json#users}。")
        code, out = self.run_num("--rq", "001")
        self.assertEqual(code, 0, out)  # 差は 0.36%（既定の 0.5% 以内）
        cfg = self.root / ".researchkit" / "config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8").replace("tolerance: 0.005", "tolerance: 0.001"), encoding="utf-8")
        code, out = self.run_num("--rq", "001")
        self.assertEqual(code, 1, out)

    def test_calc_without_section_warns(self) -> None:
        self.findings("比は 2.5 倍{N:calc}。")
        code, out = self.run_num("--all")
        self.assertEqual(code, 0, out)
        self.assertIn("NO_CALC_SECTION", out)

    def test_report_paths_from_root(self) -> None:
        report = self.root / "reports" / "report.md"
        report.parent.mkdir()
        report.write_text(f"市場は 1,234 億円{{N:{RQ}/analysis/out/market.json#size_2025}}。\n"
                          "誤り 99{N:analysis/out/market.json#count}。\n", encoding="utf-8")
        code, out = self.run_num("--file", "reports/report.md")
        self.assertEqual(code, 1, out)
        self.assertIn("reports/report.md:2 MISSING_FILE", out)
        self.assertNotIn("report.md:1", out)
        code, out = self.run_num("--all")
        self.assertIn("reports/report.md:2", out)

    def test_missing_rq(self) -> None:
        code, out = self.run_num("--rq", "002")
        self.assertEqual(code, 1, out)
        self.assertIn("NO_RQ", out)


if __name__ == "__main__":
    unittest.main()
