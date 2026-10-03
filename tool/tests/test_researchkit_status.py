"""researchkit.py と count_search.py のテスト。一時ディレクトリに Git リポジトリを作り、スクリプトを別のプロセスで呼ぶ。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2] / "skills" / "researchkit"
SCRIPTS = SKILLS / "researchkit-status" / "scripts"
RK = SCRIPTS / "researchkit.py"
COUNT = SCRIPTS / "count_search.py"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}

SOURCE = """---
id: {id}
type: {type}
title: "{title}"
author: 経済産業省
publisher: 経済産業省
url: https://example.com/{id}
accessed: 2026-10-01
grade: {grade}
primary: true
verified_by: 発表元のページを開いて確かめた
used_in: [{used_in}]
---

# {title}
"""


class ResearchkitStatusTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "proj"
        self.repo.mkdir()
        self.env = {**os.environ, **GIT_ENV}
        for key in ("CLAUDE_CODE_REMOTE", "RESEARCHKIT_MAIN_BRANCH", "CLAUDE_PROJECT_DIR",
                    "CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"):
            self.env.pop(key, None)
        self.git("init", "-q", "-b", "main")
        (self.repo / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- helpers ---------------------------------------------------------
    def git(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=self.env, check=True,
                              capture_output=True, text=True, encoding="utf-8").stdout.strip()

    def rk(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(RK), *args], cwd=cwd or self.repo, env=self.env,
                              capture_output=True, text=True, encoding="utf-8")

    def out(self, *args: str, cwd: Path | None = None) -> str:
        proc = self.rk(*args, cwd=cwd)
        return (proc.stdout + proc.stderr).strip()

    def commit_all(self, message: str = "x") -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def init_project(self) -> None:
        self.assertEqual(self.rk("init", "--title", "国内市場の調査").returncode, 0)
        self.commit_all("init")

    def hook(self, payload: dict, cwd: Path | None = None) -> None:
        env = {**self.env, "CLAUDE_PROJECT_DIR": str(self.repo)}
        proc = subprocess.run([sys.executable, str(COUNT)], input=json.dumps(payload), cwd=cwd or self.repo,
                              env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def write_source(self, sid: str, grade: str = "A", used_in: str = "", stype: str = "stat",
                     title: str = "工業統計") -> None:
        d = self.repo / "sources"
        d.mkdir(exist_ok=True)
        (d / f"{sid}.md").write_text(SOURCE.format(id=sid, grade=grade, used_in=used_in, type=stype, title=title),
                                     encoding="utf-8")

    # --- init / config ---------------------------------------------------
    def test_init_creates_config_and_directories(self) -> None:
        result = self.out("init", "--title", "国内市場の調査")
        self.assertIn("CREATED: .researchkit/config.yaml", result)
        for d in ("docs/concept", "docs/scan", "docs/study", "docs/questions", "docs/reviews", "sources",
                  "data", "studies", "reports"):
            self.assertTrue((self.repo / d).is_dir(), d)
        for f in ("docs/method.md", "docs/quality.md", "docs/glossary.md", ".researchkit/memory/constitution.md"):
            self.assertFalse((self.repo / f).exists(), f)  # ファイルを指すパスはディレクトリにしない
        self.assertTrue((self.repo / "sources" / ".gitkeep").is_file())
        self.assertTrue((self.repo / "docs" / "handover" / "PITFALLS.md").is_file())
        self.assertFalse((self.repo / "docs" / "handover" / ".gitkeep").exists())
        self.assertEqual(self.out("config", "get", "title"), "国内市場の調査")
        # 2 回目は何も変えない。title も上書きしない
        again = self.rk("init", "--title", "別の題")
        self.assertIn("CREATED: （なし。すべてそろっている）", again.stdout)
        self.assertIn("SKIPPED: title", again.stderr)
        self.assertEqual(self.out("config", "get", "title"), "国内市場の調査")

    def test_init_config_only(self) -> None:
        self.assertIn("CREATED: .researchkit/config.yaml", self.out("init", "--config-only"))
        self.assertFalse((self.repo / "sources").exists())

    def test_config_get(self) -> None:
        self.init_project()
        self.assertEqual(self.out("config", "get", "session.estimates.Q8"), "60")
        self.assertEqual(self.out("config", "get", "confidence.levels"), "確実,可能性が高い,示唆,不明")
        self.assertEqual(self.out("config", "get", "sources.min_grade"), "C")
        self.assertEqual(self.out("config", "get", "session.stop_after_bootstrap"), "true")
        self.assertEqual(self.out("config", "get", "numbers.tolerance"), "0.005")
        self.assertEqual(self.out("config", "get", "paths.studies"), "studies")
        proc = self.rk("config", "get", "commands.analysis")
        self.assertEqual((proc.returncode, proc.stdout), (1, "\n"))
        self.assertEqual(self.rk("config", "get", "no.such.key").returncode, 1)

    # --- bootstrap / status ----------------------------------------------
    def test_bootstrap_progress_from_trailers(self) -> None:
        self.assertEqual(self.out("bootstrap"), "COMPLETED_STEPS: \nNEXT_STEP: R1")
        self.init_project()
        for n in (1, 2, 3):
            self.git("commit", "-q", "--allow-empty", "-m", f"docs(bootstrap): R{n} x",
                     "-m", f"Researchkit-Bootstrap: R{n}")
        self.assertEqual(self.out("bootstrap"), "COMPLETED_STEPS: R1 R2 R3\nNEXT_STEP: R4")
        for n in range(4, 13):
            self.git("commit", "-q", "--allow-empty", "-m", f"docs(bootstrap): R{n} x",
                     "-m", f"Researchkit-Bootstrap: R{n}")
        self.assertIn("NEXT_STEP: DONE", self.out("bootstrap"))

    def test_bootstrap_trailer_followed_by_another_paragraph(self) -> None:
        """Co-Authored-By などが別の段落で足されても、進捗の記録を読める。"""
        self.init_project()
        self.git("commit", "-q", "--allow-empty", "-m", "docs(bootstrap): R1 x",
                 "-m", "Researchkit-Bootstrap: R1",
                 "-m", "Co-Authored-By: Someone <noreply@example.com>")
        self.assertEqual(self.out("bootstrap"), "COMPLETED_STEPS: R1\nNEXT_STEP: R2")

    def test_status_lists_progress_rqs_and_sources(self) -> None:
        self.init_project()
        (self.repo / "docs" / "questions" / "001-market-size.md").write_text(
            "# 市場は十分に大きいか\n\n**状態**: 未着手 | **区分**: 中核 | **想定順序**: 1 | **依存**: — | **手法**: desk\n",
            encoding="utf-8")
        self.write_source("S001-0001", "A")
        self.write_source("S001-0002", "B")
        self.write_source("S001-0003", "D")
        self.commit_all("rq")
        status = self.out("status")
        self.assertIn("# researchkit の進捗: 国内市場の調査", status)
        self.assertIn("- 次: R1", status)
        self.assertIn("| 001-market-size | 未着手 | 未着手 | - | - | - |", status)
        self.assertIn("- 出典台帳: 3 件（A 1 / B 1 / C 0 / D 1）", status)
        self.assertIn("数えていない（UNMETERED）", status)
        self.assertIn("- 最終更新: なし", status)

    # --- handover / pitfall ----------------------------------------------
    def test_handover_keeps_manual_sections(self) -> None:
        self.init_project()
        (self.repo / "docs" / "auto-decisions.md").write_text(
            "# 自動判断\n\n## R3 問いの立て方\n\n- 見直しの優先度: 高\n", encoding="utf-8")
        (self.repo / "docs" / "concept").mkdir(parents=True, exist_ok=True)
        (self.repo / "docs" / "concept" / "seed.md").write_text(
            "- 期限: [NEEDS CLARIFICATION: 期限はいつか]\n", encoding="utf-8")
        result = self.out("handover", "--note", "R3 で止めた")
        self.assertIn("UPDATED: docs/handover/CURRENT_STATE.md", result)
        current = self.repo / "docs" / "handover" / "CURRENT_STATE.md"
        text = current.read_text(encoding="utf-8")
        self.assertIn("**調査全体の工程**: 完了 なし / 次 R1", text)
        self.assertIn("docs/auto-decisions.md: R3 問いの立て方", text)
        self.assertIn("docs/concept/seed.md:1", text)
        sessions = list((self.repo / "docs" / "handover" / "sessions").glob("*.md"))
        self.assertEqual(len(sessions), 1)
        self.assertIn("R3 で止めた", sessions[0].read_text(encoding="utf-8"))
        # 手で書いた節は残し、自動の節だけを作り直す
        current.write_text(text.replace("<この調査で今いちばん進めたいこと。決定（D1 など）と RQ の番号で書く>",
                                        "D1 に答える"), encoding="utf-8")
        self.commit_all("handover")
        self.out("handover")
        text2 = current.read_text(encoding="utf-8")
        self.assertIn("D1 に答える", text2)
        self.assertEqual(text2.count("<!-- researchkit:auto:start -->"), 1)
        self.assertEqual(len(list((self.repo / "docs" / "handover" / "sessions").glob("*.md"))), 2)
        self.assertIn("（コミット）", self.out("status"))

    def test_pitfall_adds_entry_on_top(self) -> None:
        self.init_project()
        self.assertIn("ADDED: docs/handover/PITFALLS.md", self.out("pitfall", "古い統計を使った"))
        self.out("pitfall", "DOI の取り違え")
        text = (self.repo / "docs" / "handover" / "PITFALLS.md").read_text(encoding="utf-8")
        newer = text.index("DOI の取り違え")
        older = text.index("古い統計を使った")
        example = text.index("<!-- 例")
        self.assertLess(newer, older)
        self.assertLess(older, example)
        self.assertRegex(text, r"## \d{4}-\d{2}-\d{2} DOI の取り違え")

    # --- doctor ----------------------------------------------------------
    def test_doctor(self) -> None:
        proc = self.rk("doctor")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("ERROR: .researchkit/config.yaml がありません", proc.stdout)
        self.init_project()
        for base in (".claude/skills", ".agents/skills", ".kiro/skills"):
            d = self.repo / base
            d.mkdir(parents=True)
            for name in ("researchkit-status", "researchkit-worktree"):
                os.symlink(SKILLS / name, d / name)
        steering = self.repo / ".kiro" / "steering"
        steering.mkdir(parents=True)
        for name in ("language.md", "research.md"):
            (steering / name).write_text("x\n", encoding="utf-8")
        for name in ("CLAUDE.md", "AGENTS.md", "GEMINI.md"):
            (self.repo / name).write_text("@.kiro/steering/language.md\n@.kiro/steering/research.md\n",
                                          encoding="utf-8")
        proc = self.rk("doctor")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("WARN: commands.analysis が空です", proc.stdout)
        self.assertIn("WARN: Web 検索の回数を数えるフックがありません", proc.stdout)
        self.assertIn("SUMMARY: ERROR 0", proc.stdout)
        self.assertEqual(self.rk("hooks", "install").returncode, 0)
        cfg = self.repo / ".researchkit" / "config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8").replace("min_grade: C", "min_grade: E"), encoding="utf-8")
        os.symlink(self.tmp / "missing", self.repo / ".claude" / "skills" / "broken")
        proc = self.rk("doctor")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("OK: Web 検索の回数を数えるフック", proc.stdout)
        self.assertIn("ERROR: sources.min_grade 'E'", proc.stdout)
        self.assertIn("ERROR: .claude/skills/ のリンクが切れています: broken", proc.stdout)

    # --- budget / hooks --------------------------------------------------
    def test_hooks_install_is_idempotent(self) -> None:
        self.init_project()
        settings = self.repo / ".claude" / "settings.json"
        settings.parent.mkdir()
        settings.write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]}}), encoding="utf-8")
        self.assertIn("追加: SessionStart, PostToolUse", self.out("hooks", "install"))
        self.assertIn("追加: なし（登録済み）", self.out("hooks", "install"))
        conf = json.loads(settings.read_text(encoding="utf-8"))
        self.assertEqual(conf["permissions"], {"allow": ["Bash(ls)"]})
        self.assertEqual(len(conf["hooks"]["SessionStart"]), 1)
        self.assertEqual(conf["hooks"]["PostToolUse"][0]["matcher"], "WebSearch|WebFetch")
        self.assertIn("count_search.py", conf["hooks"]["PostToolUse"][0]["hooks"][0]["command"])
        gi = (self.repo / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual(gi.count(".researchkit/usage/"), 1)
        self.assertIn(".worktrees/", gi)

    def test_budget_unmetered_ok_and_stop(self) -> None:
        self.init_project()
        proc = self.rk("budget", "--step", "Q8")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("VERDICT: UNMETERED", proc.stdout)
        self.assertIn("NEED: 60", proc.stdout)
        self.assertEqual(self.rk("budget", "--step", "Q99").returncode, 1)
        self.hook({"session_id": "s1", "hook_event_name": "SessionStart"})
        for _ in range(3):
            self.hook({"session_id": "s1", "hook_event_name": "PostToolUse", "tool_name": "WebSearch"})
        self.hook({"session_id": "s1", "hook_event_name": "PostToolUse", "tool_name": "WebFetch"})
        self.hook({"session_id": "s1", "hook_event_name": "PostToolUse", "tool_name": "Read"})
        proc = self.rk("budget", "--step", "rq")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("USED: WebSearch 3 / WebFetch 1", proc.stdout)
        self.assertIn("REMAINING: 187", proc.stdout)
        self.assertIn("VERDICT: OK", proc.stdout)
        proc = self.rk("budget", "--need", "188")
        self.assertEqual(proc.returncode, 4)
        self.assertIn("VERDICT: STOP", proc.stdout)
        # 新しいセッションは 0 件から数える
        self.hook({"session_id": "s2", "hook_event_name": "SessionStart"})
        self.assertIn("REMAINING: 190", self.out("budget", "--need", "188"))

    def test_budget_other_session_is_unmetered(self) -> None:
        self.init_project()
        self.hook({"session_id": "s1", "hook_event_name": "SessionStart"})
        self.hook({"session_id": "s1", "hook_event_name": "PostToolUse", "tool_name": "WebSearch"})
        # 今のセッション（s9）の記録がない: 前のセッション（s1）の回数を使わない
        self.env["CLAUDE_CODE_SESSION_ID"] = "s9"
        proc = self.rk("budget", "--step", "Q8")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("VERDICT: UNMETERED", proc.stdout)
        self.assertIn("RECORDED_SESSION: s1", proc.stdout)
        self.assertIn("USED: -", proc.stdout)
        # 今のセッションの記録があれば、current が別のセッションを指していても今のものを読む
        self.env["CLAUDE_CODE_SESSION_ID"] = "s1"
        self.hook({"session_id": "s2", "hook_event_name": "SessionStart"})
        proc = self.rk("budget", "--step", "Q8")
        self.assertIn("SESSION: s1", proc.stdout)
        self.assertIn("USED: WebSearch 1", proc.stdout)
        self.assertIn("VERDICT: OK", proc.stdout)

    def test_data_add(self) -> None:
        self.init_project()
        tpl = SKILLS / "researchkit-foundation" / "templates" / "manifest.md"
        (self.repo / "data").mkdir(exist_ok=True)
        shutil.copy(tpl, self.repo / "data" / "manifest.md")
        raw = self.repo / "data" / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        (raw / "t.csv").write_bytes(b"a,b\n1,2\n")
        proc = self.rk("data", "add", "data/raw/t.csv", "--source", "S003-0001", "--url", "https://example.com/t.csv",
                       "--desc", "試しの表", "--rq", "3")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("ADDED: data/raw/t.csv", proc.stdout)
        text = (self.repo / "data" / "manifest.md").read_text(encoding="utf-8")
        import hashlib
        digest = hashlib.sha256(b"a,b\n1,2\n").hexdigest()
        row = next(line for line in text.splitlines() if line.startswith("| data/raw/t.csv |"))
        self.assertIn(digest, row)
        self.assertIn("| 003 |", row)
        self.assertIn("| S003-0001 |", row)
        # 行は「ファイル」の表の中に入る（表の後の節より前）
        self.assertLess(text.index(row), text.index("## 取り扱いの注意"))
        dup = self.rk("data", "add", "data/raw/t.csv", "--source", "S003-0001", "--url", "u", "--desc", "d", "--rq", "3")
        self.assertEqual(dup.returncode, 1)
        self.assertIn("すでに目録にある", dup.stderr)
        self.assertEqual(self.rk("data", "add", "data/raw/none.csv", "--source", "S", "--url", "u", "--desc", "d",
                                 "--rq", "3").returncode, 1)

    def test_budget_inside_worktree_reads_main_usage(self) -> None:
        self.init_project()
        self.hook({"session_id": "s1", "hook_event_name": "SessionStart"})
        wt = self.repo / ".worktrees" / "001-x"
        self.git("worktree", "add", "-q", "-b", "rq/001-x", str(wt), "main")
        # worktree の中で動いたツールの記録も、メインの作業ツリーに入る
        self.hook({"session_id": "s1", "hook_event_name": "PostToolUse", "tool_name": "WebSearch"}, cwd=wt)
        proc = self.rk("budget", "--step", "Q8", cwd=wt)
        self.assertIn("USED: WebSearch 1", proc.stdout)
        self.assertFalse((wt / ".researchkit" / "usage").exists())

    def test_count_search_ignores_outside_project(self) -> None:
        outside = self.tmp / "outside"
        outside.mkdir()
        env = {**self.env}
        proc = subprocess.run([sys.executable, str(COUNT)], input="not json", cwd=outside, env=env,
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0)
        proc = subprocess.run([sys.executable, str(COUNT)], input=json.dumps({"session_id": "a"}), cwd=outside,
                              env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0)

    # --- sources ---------------------------------------------------------
    def test_sources_next_reads_worktree_and_main(self) -> None:
        self.init_project()
        self.assertEqual(self.out("sources", "next", "3"), "S003-0001")
        self.write_source("S003-0001")
        self.write_source("S003-0002")
        self.write_source("S001-0009")
        self.commit_all("sources")
        self.assertEqual(self.out("sources", "next", "003-competitors", "--count", "2"), "S003-0003\nS003-0004")
        # main にある出典は、ほかの worktree からも数える
        wt = self.repo / ".worktrees" / "003-x"
        self.git("worktree", "add", "-q", "-b", "rq/003-x", str(wt), "main")
        self.write_source("S003-0005")
        self.git("add", "-A")
        self.git("commit", "-qm", "more")
        (wt / "sources" / "S003-0003.md").write_text("x\n", encoding="utf-8")
        self.assertEqual(self.out("sources", "next", "3", cwd=wt), "S003-0006")
        self.assertEqual(self.out("sources", "next", "1"), "S001-0010")
        self.assertEqual(self.rk("sources", "next", "abc").returncode, 1)
        self.assertEqual(self.rk("sources", "next").returncode, 1)

    def test_sources_list_filters(self) -> None:
        self.init_project()
        self.write_source("S000-0001", "A", used_in="001-market-size, 002-competitors", title="国勢調査")
        self.write_source("S001-0001", "B", used_in="001-market-size", stype="web", title="業界団体: 速報 | 2026")
        self.write_source("S002-0001", "D", used_in="002-competitors")
        d = self.repo / "studies" / "001-market-size"
        d.mkdir(parents=True)
        (d / "findings.md").write_text("| C1 | x | S000-0001, S001-0001 | 示唆 | - |\n", encoding="utf-8")
        lines = self.out("sources", "list").splitlines()
        self.assertEqual(lines[0], "| ID | 等級 | 種類 | 題名 | 使った RQ |")
        self.assertIn("| S001-0001 | B | web | 業界団体: 速報 ／ 2026 | 001-market-size |", lines)
        self.assertEqual(lines[-1], "TOTAL: 3")
        self.assertIn("TOTAL: 2", self.out("sources", "list", "--grade", "A,B"))
        rq2 = self.out("sources", "list", "--rq", "2")
        self.assertIn("S000-0001", rq2)
        self.assertIn("S002-0001", rq2)
        self.assertIn("TOTAL: 2", rq2)
        unused = self.out("sources", "list", "--unused")
        self.assertIn("S002-0001", unused)
        self.assertIn("TOTAL: 1", unused)


class RklibTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(SCRIPTS))
        import rklib  # noqa: E402
        cls.rklib = rklib

    def test_template_parses_and_matches_defaults(self) -> None:
        cfg = self.rklib.parse_yaml(self.rklib.TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(set(cfg["paths"]), set(self.rklib.DEFAULT_CONFIG["paths"]))
        self.assertEqual(cfg["paths"], self.rklib.DEFAULT_CONFIG["paths"])
        self.assertEqual(cfg["session"]["estimates"], self.rklib.DEFAULT_CONFIG["session"]["estimates"])
        self.assertEqual(cfg["subagents"], self.rklib.DEFAULT_CONFIG["subagents"])
        self.assertEqual(cfg["output"], self.rklib.DEFAULT_CONFIG["output"])
        self.assertEqual(cfg["confidence"]["levels"], ["確実", "可能性が高い", "示唆", "不明"])
        self.assertIsNone(cfg["commands"]["analysis"])
        self.assertEqual(cfg["numbers"]["tolerance"], 0.005)

    def test_frontmatter(self) -> None:
        text = "---\nid: S001-0001\ntitle: 題: 副題\nused_in:\n  - 001-a\n  - 002-b\n---\n本文\n"
        meta = self.rklib.parse_frontmatter(text)
        self.assertEqual(meta["title"], "題: 副題")
        self.assertEqual(meta["used_in"], ["001-a", "002-b"])
        self.assertEqual(self.rklib.parse_frontmatter("本文だけ\n"), {})
        self.assertEqual(self.rklib.split_frontmatter(text)[2], 8)

    def test_normalize_rq_number(self) -> None:
        for value in ("3", "003", "003-market", "S003"):
            self.assertEqual(self.rklib.normalize_rq_number(value), "003")
        with self.assertRaises(ValueError):
            self.rklib.normalize_rq_number("x")


if __name__ == "__main__":
    unittest.main()
