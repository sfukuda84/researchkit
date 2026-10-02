"""researchkit-questions の validate.py のテスト。一時ディレクトリに docs/ を作り、スクリプトを subprocess で呼ぶ。"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parents[2]
VALIDATE = SCAFFOLD / "skills" / "researchkit" / "researchkit-questions" / "scripts" / "validate.py"

SEED = "# 問いの種\n\n| ID | 決めたいこと |\n|---|---|\n| D1 | 参入するか |\n| D2 | 価格帯 |\n"
HYP = "# 仮説\n\n### H1 市場は伸びる\n\n### H2 競合は少ない\n"


def rq(title: str, num: int, category: str = "中核", deps: str = "—", methods: str = "desk",
       decisions: str = "- D1: 参入の判断が変わる", hyps: str = "- H1: 伸びる", status: str = "未着手") -> str:
    return (f"# {title}\n\n"
            f"**状態**: {status} | **区分**: {category} | **想定順序**: {num} | **依存**: {deps} | **手法**: {methods}\n\n"
            f"## 問い\n\n{title}\n\n## つながる決定\n\n{decisions}\n\n## つながる仮説\n\n{hyps}\n\n"
            "## 答えの形\n\n規模（億円）\n\n## 範囲\n\n- 含む: 国内\n\n## 想定する情報源\n\n- 公的統計\n\n"
            "## 人の作業の見込み\n\n- なし\n")


class ValidateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.q = self.root / "docs" / "questions"
        self.q.mkdir(parents=True)
        self.write("docs/concept/seed.md", SEED)
        self.write("docs/study/hypotheses.md", HYP)
        self.rqs = {
            "000-research-foundation": ("調査の共通基盤", 0, "基盤", "—", "—", "", ""),
            "001-market-size": ("市場はどこまで伸びるか？", 1, "中核", "000-research-foundation", "desk, data",
                                "- D1: 参入", "- H1: 伸びる"),
            "002-competitors": ("競合はどれだけいるか？", 2, "中核", "000-research-foundation, 001-market-size", "desk",
                                "- D1, D2", "- H2"),
            "999-research-report": ("統合報告", 999, "統合", "001-market-size, 002-competitors", "—", "", ""),
        }
        self.write_all()

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel: str, text: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def write_all(self, order: list[str] | None = None) -> None:
        rows, lines = [], []
        for slug, (title, num, cat, deps, methods, dec, hyp) in self.rqs.items():
            self.write(f"docs/questions/{slug}.md", rq(title, num, cat, deps, methods, dec, hyp))
            rows.append(f"| {num} | [{title}](./{slug}.md) | {cat} | 未着手 | {deps} | {methods} | 一言 |")
        for slug in order or list(self.rqs):
            title, num = self.rqs[slug][0], self.rqs[slug][1]
            lines.append(f"- **{num}. [{title}](./{slug}.md)**: 一言")
        self.write("docs/questions/README.md",
                   "# RQ の一覧\n\n| # | 問い | 区分 | 状態 | 依存 | 手法 | 一言 |\n|---|---|---|---|---|---|---|\n"
                   + "\n".join(rows) + f"\n\n**件数**: RQ ファイル **{len(self.rqs)} 件**\n")
        self.write("docs/questions/spec_order.md", "# 着手順\n\n" + "\n".join(lines) + "\n")

    def run_validate(self, *args: str) -> tuple[int, str]:
        proc = subprocess.run([sys.executable, str(VALIDATE), str(self.q), *args],
                              capture_output=True, text=True, encoding="utf-8")
        return proc.returncode, proc.stdout + proc.stderr

    def test_clean(self) -> None:
        code, out = self.run_validate()
        self.assertEqual(code, 0, out)
        self.assertIn("エラー 0 件 / 警告 0 件", out)

    def test_bad_values(self) -> None:
        self.write("docs/questions/001-market-size.md",
                   rq("市場はどこまで伸びるか？", 1, "主要", "000-research-foundation", "desk, survey", status="途中"))
        code, out = self.run_validate()
        self.assertEqual(code, 1, out)
        self.assertIn("状態「途中」", out)
        self.assertIn("区分「主要」", out)
        self.assertIn("手法「survey」", out)

    def test_dependency_errors(self) -> None:
        self.rqs["001-market-size"] = ("市場はどこまで伸びるか？", 1, "中核", "002-competitors, 005-missing", "desk",
                                       "- D1", "- H1")
        self.write_all()
        code, out = self.run_validate()
        self.assertEqual(code, 1, out)
        self.assertIn("循環依存", out)
        self.assertIn("005-missing", out)

    def test_depends_on_report_and_foundation_deps(self) -> None:
        self.rqs["002-competitors"] = ("競合はどれだけいるか？", 2, "中核", "999-research-report", "desk", "- D2", "- H2")
        self.rqs["000-research-foundation"] = ("調査の共通基盤", 0, "基盤", "001-market-size", "—", "", "")
        self.write_all(order=["001-market-size", "000-research-foundation", "002-competitors", "999-research-report"])
        code, out = self.run_validate()
        self.assertEqual(code, 1, out)
        self.assertIn("999 はほかの RQ から依存されない", out)
        self.assertIn("共通基盤（000）はほかの RQ に依存できない", out)
        self.assertIn("先頭に並べる", out)

    def test_decision_and_hypothesis_refs(self) -> None:
        self.rqs["001-market-size"] = ("市場はどこまで伸びるか？", 1, "中核", "000-research-foundation", "desk",
                                       "- （なし）", "- H9")
        self.rqs["002-competitors"] = ("競合はどれだけいるか？", 2, "中核", "000-research-foundation", "desk",
                                       "- D7", "- H2")
        self.write_all()
        code, out = self.run_validate()
        self.assertEqual(code, 1, out)
        self.assertIn("001-market-size.md: 「つながる決定」に seed.md の決定", out)
        self.assertIn("仮説 H9 が", out)
        self.assertIn("決定 D7 が", out)
        self.assertIn("仮説 H1 を確かめる RQ がない", out)

    def test_duplicate_number_and_category_of_reserved(self) -> None:
        self.rqs["001-other"] = ("別の問いか？", 1, "補助", "—", "literature", "- D2", "- H2")
        self.rqs["999-research-report"] = ("統合報告", 999, "中核", "—", "—", "", "")
        self.write_all()
        code, out = self.run_validate()
        self.assertEqual(code, 1, out)
        self.assertIn("番号 001 が重複している", out)
        self.assertIn("999 の区分は「統合」", out)

    def test_reserved_missing(self) -> None:
        del self.rqs["000-research-foundation"]
        del self.rqs["999-research-report"]
        self.rqs["001-market-size"] = ("市場はどこまで伸びるか？", 1, "中核", "—", "desk", "- D1", "- H1")
        self.rqs["002-competitors"] = ("競合はどれだけいるか？", 2, "中核", "001-market-size", "desk", "- D1, D2", "- H2")
        for name in ("000-research-foundation", "999-research-report"):
            (self.q / f"{name}.md").unlink()
        self.write_all()
        code, out = self.run_validate()
        self.assertEqual(code, 0, out)
        self.assertIn("000（共通基盤）の RQ ファイルがない", out)
        code, out = self.run_validate("--require-reserved")
        self.assertEqual(code, 1, out)

    def test_readme_and_spec_order_mismatch(self) -> None:
        self.write_all(order=["000-research-foundation", "002-competitors", "001-market-size", "999-research-report"])
        readme = self.q / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8").replace("| 中核 | 未着手 | 000-research-foundation | desk, data |",
                                                                     "| 補助 | 完了 | — | desk |"), encoding="utf-8")
        code, out = self.run_validate()
        self.assertEqual(code, 1, out)
        self.assertIn("002-competitors が依存先 001-market-size より前", out)
        self.assertIn("区分「補助」", out)
        self.assertIn("状態「完了」", out)
        self.assertIn("手法「desk」", out)
        code, out = self.run_validate("--lenient")
        self.assertEqual(code, 0, out)

    def test_missing_section_and_bad_filename(self) -> None:
        text = rq("市場はどこまで伸びるか？", 1, deps="000-research-foundation", methods="desk, data", hyps="- H1")
        self.write("docs/questions/001-market-size.md", text.replace("## 答えの形", "## 答え"))
        self.write("docs/questions/notes.md", "# メモ\n")
        code, out = self.run_validate()
        self.assertEqual(code, 1, out)
        self.assertIn("見出し「## 答えの形」がない", out)
        self.assertIn("notes.md: ファイル名", out)

    def test_graph(self) -> None:
        code, out = self.run_validate("--graph")
        self.assertEqual(code, 0, out)
        self.assertIn("| 2 | `000-research-foundation` |", out)
        self.assertIn("| 2 | `001-market-size` |", out)
        self.assertIn("### S1: <段階の性格>\n\n- **1. [市場はどこまで伸びるか？](./001-market-size.md)**: 一言", out)
        self.assertIn("### S2: <段階の性格>\n\n- **2. [競合はどれだけいるか？](./002-competitors.md)**: 一言", out)
        self.assertIn("### 統合\n\n- **999.", out)

    def test_custom_paths(self) -> None:
        shutil.move(str(self.root / "docs" / "concept" / "seed.md"), str(self.root / "seed.md"))
        code, out = self.run_validate()
        self.assertEqual(code, 1, out)
        self.assertIn("seed.md がない", out)
        code, out = self.run_validate("--seed-file", str(self.root / "seed.md"))
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
