"""researchkit-check の check.py のテスト。一時ディレクトリに調査プロジェクトを作り、スクリプトを subprocess で呼ぶ。"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parents[2]
CHECK = SCAFFOLD / "skills" / "researchkit" / "researchkit-check" / "scripts" / "check.py"
CONFIG = SCAFFOLD / "skills" / "researchkit" / "researchkit-status" / "templates" / "config.yaml"
TODAY = "2026-10-01"

FINDINGS = """\
# 001 の主張

| ID | 主張 | 根拠 | 確度 | 反証・限界 |
|---|---|---|---|---|
| C1 | 市場は 1,234 億円である | S001-0001, S001-0002 | 可能性が高い | — |
| C2 | C1 から、拡大している | C1 | 示唆 | — |
"""


def source(sid: str, grade: str = "A", used_in: str = "[001]", accessed: str = "2026-09-01", extra: str = "") -> str:
    return textwrap.dedent(f"""\
        ---
        id: {sid}
        type: stat
        title: "〇〇統計: 2025 年版"
        publisher: 〇〇省
        url: https://example.com/{sid}
        accessed: {accessed}
        grade: {grade}
        primary: true
        verified_by: 発表元のページで確認
        used_in: {used_in}
        {extra}
        ---

        # メモ
        """)


class CheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        (self.root / ".researchkit").mkdir()
        shutil.copy(CONFIG, self.root / ".researchkit" / "config.yaml")
        self.write("studies/001-market-size/findings.md", FINDINGS)
        self.write("sources/S001-0001.md", source("S001-0001"))
        self.write("sources/S001-0002.md", source("S001-0002", grade="B"))

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel: str, text: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def run_check(self, *args: str) -> tuple[int, str]:
        proc = subprocess.run([sys.executable, str(CHECK), "--root", str(self.root), "--today", TODAY, *args],
                              capture_output=True, text=True, encoding="utf-8")
        return proc.returncode, proc.stdout + proc.stderr

    def test_clean_project(self) -> None:
        code, out = self.run_check("--all")
        self.assertEqual(code, 0, out)
        self.assertIn("SUMMARY: errors=0 warnings=0", out)

    def test_unknown_source_and_claim(self) -> None:
        self.write("studies/001-market-size/findings.md", FINDINGS.replace("S001-0002", "S001-0009").replace("| C1 | 示唆", "| C7 | 示唆"))
        code, out = self.run_check("--rq", "001")
        self.assertEqual(code, 1, out)
        self.assertIn("UNKNOWN_SOURCE", out)
        self.assertIn("UNKNOWN_CLAIM", out)
        self.assertRegex(out, r"ERROR studies/001-market-size/findings.md:5 UNKNOWN_SOURCE")

    def test_empty_evidence_and_bad_confidence(self) -> None:
        self.write("studies/001-market-size/findings.md", FINDINGS.replace("| C1 | 示唆", "|  | たぶん"))
        code, out = self.run_check("--rq", "1")
        self.assertEqual(code, 1, out)
        self.assertIn("NO_EVIDENCE", out)
        self.assertIn("BAD_CONFIDENCE", out)

    def test_low_grade_only(self) -> None:
        self.write("sources/S001-0001.md", source("S001-0001", grade="D"))
        self.write("sources/S001-0002.md", source("S001-0002", grade="D"))
        code, out = self.run_check("--all")
        self.assertEqual(code, 1, out)
        self.assertIn("LOW_GRADE", out)
        self.assertIn("GRADE_D", out)

    def test_min_grade_from_config(self) -> None:
        cfg = self.root / ".researchkit" / "config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8").replace("min_grade: C", "min_grade: A"), encoding="utf-8")
        self.write("sources/S001-0001.md", source("S001-0001", grade="B"))
        code, out = self.run_check("--all")
        self.assertEqual(code, 1, out)
        self.assertIn("LOW_GRADE", out)

    def test_source_required_fields_and_id(self) -> None:
        self.write("sources/S001-0002.md", "---\nid: S001-0003\ntype: web\ngrade: B\n---\n")
        code, out = self.run_check("--all")
        self.assertEqual(code, 1, out)
        self.assertIn("SOURCE_ID_MISMATCH", out)
        self.assertIn("必須の項目 title", out)
        self.assertIn("必須の項目 accessed", out)
        self.assertIn("url・doi・書誌", out)

    def test_bibliographic_source_is_enough(self) -> None:
        text = source("S001-0002").replace("url: https://example.com/S001-0002\n", "author: 山田太郎\n")
        self.write("sources/S001-0002.md", text)
        code, out = self.run_check("--all")
        self.assertEqual(code, 0, out)

    def test_warnings(self) -> None:
        self.write("sources/S001-0002.md", source("S001-0002", used_in="[001, 002]", accessed="2024-01-01",
                                                  extra="doi: 11.1234/abc"))
        self.write("sources/S000-0001.md", source("S000-0001", used_in="[000]"))
        code, out = self.run_check("--all")
        self.assertEqual(code, 0, out)
        for w in ("STALE_ACCESS", "BAD_DOI", "USED_IN_MISMATCH", "UNUSED_SOURCE"):
            self.assertIn(w, out)
        code, _ = self.run_check("--all", "--strict")
        self.assertEqual(code, 1)

    def test_used_in_block_list(self) -> None:
        text = source("S001-0002").replace("used_in: [001]", "used_in:\n  - 001-market-size")
        self.write("sources/S001-0002.md", text)
        code, out = self.run_check("--all")
        self.assertEqual(code, 0, out)

    def test_report_cross_claims(self) -> None:
        report = textwrap.dedent("""\
            # 統合報告

            | ID | 主張 | 根拠 | 確度 | 反証・限界 |
            |---|---|---|---|---|
            | K1 | 市場は大きい | 001-C1, 001-C2 | 可能性が高い | — |
            | K2 | 競合は少ない | 002-C1 | 示唆 | — |
            | K3 | 価格は高い | 001-C9 | 示唆 | — |
            """)
        self.write("reports/report.md", report)
        code, out = self.run_check("--file", "reports/report.md")
        self.assertEqual(code, 1, out)
        self.assertIn("RQ 002 が studies/ にない", out)
        self.assertIn("001-C9", out)
        self.assertNotIn("001-C1 ", out)
        # --all でも統合報告を検証する
        code, out = self.run_check("--all")
        self.assertEqual(code, 1, out)
        self.assertIn("reports/report.md", out)

    def test_file_mode_checks_body_references(self) -> None:
        self.write("docs/memo.md", "# メモ\n\n市場の規模は S001-0001 と S009-0001 による。\n")
        code, out = self.run_check("--file", "docs/memo.md")
        self.assertEqual(code, 1, out)
        self.assertIn("S009-0001 が出典台帳にない", out)

    def test_custom_confidence_levels(self) -> None:
        cfg = self.root / ".researchkit" / "config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8").replace("[確実, 可能性が高い, 示唆, 不明]", "[高, 中, 低]"),
                       encoding="utf-8")
        code, out = self.run_check("--all")
        self.assertEqual(code, 1, out)
        self.assertIn("高 / 中 / 低", out)

    def test_missing_rq(self) -> None:
        code, out = self.run_check("--rq", "005")
        self.assertEqual(code, 1, out)
        self.assertIn("NO_RQ", out)

    def test_duplicate_claim(self) -> None:
        self.write("studies/001-market-size/findings.md", FINDINGS.replace("| C2 |", "| C1 |").replace("| C1 | 示唆", "| S001-0001 | 示唆"))
        code, out = self.run_check("--rq", "001")
        self.assertEqual(code, 1, out)
        self.assertIn("DUP_CLAIM", out)


if __name__ == "__main__":
    unittest.main()
