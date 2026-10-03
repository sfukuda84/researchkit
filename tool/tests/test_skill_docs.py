"""スキルの文書のリンクのテスト。SKILL.md と references/ の相対リンクが実在し、references/ のファイルがどれも SKILL.md から指されていること。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2] / "skills" / "researchkit"
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


class SkillDocsTest(unittest.TestCase):
    def test_relative_links_resolve(self) -> None:
        broken = []
        # テンプレート（templates/）の中のリンクは、写した先のプロジェクトでの位置が基準なので見ない
        docs = sorted(SKILLS.glob("*/SKILL.md")) + sorted(SKILLS.glob("*/references/*.md"))
        for md in docs:
            text = md.read_text(encoding="utf-8")
            text = re.sub(r"(?s)```.*?```", "", text)  # コードの例の中は見ない
            for target in LINK_RE.findall(text):
                if re.match(r"^[a-z]+:", target) or target.startswith("#") or "<" in target or "…" in target \
                        or "NNN" in target:
                    continue
                path = (md.parent / target.split("#")[0]).resolve()
                if not path.exists():
                    broken.append(f"{md.relative_to(SKILLS)} -> {target}")
        self.assertEqual(broken, [])

    def test_references_are_linked_from_skill(self) -> None:
        orphans = []
        for ref in sorted(SKILLS.glob("*/references/*.md")):
            skill = ref.parent.parent / "SKILL.md"
            if f"references/{ref.name}" not in skill.read_text(encoding="utf-8"):
                orphans.append(str(ref.relative_to(SKILLS)))
        self.assertEqual(orphans, [])

    def test_slimmed_skills_keep_section_headings(self) -> None:
        # ほかのスキルが見出しの名前で参照する節は、本文に見出しとして残す
        wt = (SKILLS / "researchkit-worktree" / "SKILL.md").read_text(encoding="utf-8")
        for name in ("ステップ番号", "Q1 準備", "再開", "Q13 片付け", "人のタスクの片付け", "中止", "セッションの区切り",
                     "引数の解釈と複数の RQ の進め方", "自動モード", "止まったときの扱い"):
            self.assertRegex(wt, rf"(?m)^#{{2,3}} (\d+\. )?{re.escape(name)}$", name)


if __name__ == "__main__":
    unittest.main()
