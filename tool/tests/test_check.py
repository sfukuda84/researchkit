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

    def test_manifest_and_raw_files(self) -> None:
        import hashlib
        body = b"a,b\n1,2\n"
        self.write("data/raw/listed.csv", body.decode())
        digest = hashlib.sha256(body).hexdigest()
        manifest = ("# データの目録\n\n## ファイル\n\n"
                    "| ファイル | 置き場所 | 出典 ID | 出所（URL・提供元） | 取得日 | 取得の方法 | ライセンス・利用規約 | SHA-256 | 大きさ | 内容 | 使った RQ |\n"
                    "|---|---|---|---|---|---|---|---|---|---|---|\n"
                    "| <例: data/raw/x.csv> | raw | <S000-0003> | <URL> | <日付> | <方法> | <規約> | <ハッシュ> | <大きさ> | <内容> | <001> |\n"
                    f"| data/raw/listed.csv | raw | S001-0001 | u | 2026-09-01 | curl | 規約 | {digest} | 8 bytes | 表 | 001 |\n"
                    "| data/large/big.parquet | large | S001-0001 | u | 2026-09-01 | 人 | 規約 | " + "0" * 64 + " | 1 GB | 大 | 001 |\n\n"
                    "## 取り扱いの注意\n")
        self.write("data/manifest.md", manifest)
        code, out = self.run_check("--all")
        self.assertEqual(code, 0, out)
        self.assertNotIn("_DATA", out)
        # 目録にないファイル、ハッシュの違い、ないファイル
        self.write("data/raw/orphan.xls", "x")
        self.write("data/raw/listed.csv", "changed")
        self.write("data/manifest.md", manifest.replace("| data/large/big.parquet",
                                                         "| data/raw/gone.csv | raw | S001-0001 | u | d | m | l | - | 1 | g | 001 |\n| data/large/big.parquet"))
        code, out = self.run_check("--rq", "001")
        self.assertEqual(code, 1, out)
        self.assertIn("UNLISTED_DATA", out)
        self.assertIn("data/raw/orphan.xls", out)
        self.assertIn("HASH_MISMATCH", out)
        self.assertIn("MISSING_DATA", out)
        self.assertNotIn("big.parquet", out)  # data/large/ は手元になくてよい
        # 別の RQ を指定したときは、その RQ の行だけを照らす（目録にないファイルは常に出す）
        (self.root / "studies" / "002-other").mkdir(parents=True)
        code, out = self.run_check("--rq", "002")
        self.assertIn("UNLISTED_DATA", out)
        self.assertNotIn("HASH_MISMATCH", out)

    def test_raw_files_without_manifest(self) -> None:
        self.write("data/raw/a.csv", "x")
        code, out = self.run_check("--all")
        self.assertEqual(code, 1)
        self.assertIn("NO_MANIFEST", out)

    def test_exploratory_claims_are_capped(self) -> None:
        text = FINDINGS + (
            "| C3 | 連鎖でつなぐと年 -0.56%{N:analysis/out/c.json#exploratory.coef_chain} である | S001-0001 | 可能性が高い | — |\n"
            "| C4 | 新規需要米を除くと年 -0.65%{N:analysis/out/c.json#exploratory.no_rice} である | S001-0001 | 示唆 | — |\n"
            "| C5 | 主の値は年 -0.56%{N:analysis/out/c.json#cagr.main} である | S001-0001 | 確実 | "
            "探索的な値 -0.65%{N:analysis/out/c.json#exploratory.no_rice} も同じ側 |\n"
            "| C6 | 年 -0.80%{N:analysis/out/c.json#exploratory} の感度もある | S001-0001 | 不明 | — |\n")
        self.write("studies/001-market-size/findings.md", text)
        code, out = self.run_check("--rq", "001")
        self.assertEqual(code, 1, out)
        self.assertEqual(out.count("EXPLORATORY_CONFIDENCE"), 1, out)
        self.assertIn("C3 は探索的な分析の出力", out)
        # 主張の欄だけを見る（C5 の反証・限界で探索的な値に触れるのはよい）。示唆・不明はよい
        self.assertNotIn("C4 は", out)
        self.assertNotIn("C5 は", out)
        self.assertNotIn("C6 は", out)

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
