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

    def test_handover_detects_stale_manual_sections(self) -> None:
        self.init_project()
        q = self.repo / "docs" / "questions"
        q.mkdir(parents=True, exist_ok=True)
        (q / "002-farmer-decline.md").write_text("# 002\n\n**状態**: 人の作業待ち | **手法**: data\n", encoding="utf-8")
        current = self.repo / "docs" / "handover" / "CURRENT_STATE.md"
        self.out("handover")
        text = current.read_text(encoding="utf-8")
        self.assertIn("### 次の候補（自動）", text)
        self.assertIn("- 次の RQ:", text)
        self.assertRegex(text, r"<!-- manual: hash=[0-9a-f]{16} since=[0-9a-f]+ -->")
        current.write_text(text.replace("<この調査で今いちばん進めたいこと。決定（D1 など）と RQ の番号で書く>",
                                        "002-farmer-decline を進める"), encoding="utf-8")
        self.commit_all("handover")
        # 手で書く節を変えたら、その時点から数える（マージがなければ警告しない）
        out = self.out("handover")
        self.assertNotIn("STALE_MANUAL", out)
        text = current.read_text(encoding="utf-8")
        self.assertIn("手で書く節が挙げる RQ と今の状態**: 002-farmer-decline（人の作業待ち）", text)
        self.commit_all("handover2")
        # 手で書く節が変わらないまま RQ のマージがあると警告する。直すまで警告は続く
        self.git("commit", "-q", "--allow-empty", "-m", "merge(002-farmer-decline): all")
        out = self.out("handover")
        self.assertIn("WARN STALE_MANUAL", out)
        self.assertIn("002-farmer-decline のマージより前から", out)
        self.assertIn("（`STALE_MANUAL`）", current.read_text(encoding="utf-8"))
        self.commit_all("handover3")
        self.assertIn("WARN STALE_MANUAL", self.out("handover"))
        # 直すと消える
        text = current.read_text(encoding="utf-8")
        current.write_text(text.replace("002-farmer-decline を進める", "003 を進める"), encoding="utf-8")
        out = self.out("handover")
        self.assertNotIn("STALE_MANUAL", out)
        self.assertNotIn("（`STALE_MANUAL`）", current.read_text(encoding="utf-8"))

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

    def test_budget_estimates_from_plan_and_methods(self) -> None:
        self.init_project()
        q = self.repo / "docs" / "questions"
        q.mkdir(parents=True, exist_ok=True)
        (q / "003-volume.md").write_text("# 003\n\n**状態**: 未着手 | **手法**: data, desk | **依存**: 000\n", encoding="utf-8")
        (q / "005-growth.md").write_text("# 005\n\n**状態**: 未着手 | **手法**: desk, literature\n", encoding="utf-8")
        # plan.md がない RQ は、手法の既定のうち最大（desk の Q8 30、literature の rq 120）
        out = self.out("budget", "--step", "Q8", "--rq", "3")
        self.assertIn("NEED: 30", out)
        self.assertIn("SOURCE: estimates_by_method（data, desk）", out)
        self.assertIn("NEED: 120", self.out("budget", "--step", "rq", "--rq", "005"))
        # worktree の中の plan.md を、メインの作業ツリーから読む。WebSearch の値（幅なら上限）を使う
        self.commit_all("q")
        wt = self.repo / ".worktrees" / "003-volume"
        self.git("worktree", "add", "-q", "-b", "rq/003-volume", str(wt), "main")
        plan = wt / "studies" / "003-volume" / "plan.md"
        plan.parent.mkdir(parents=True)
        plan.write_text("# 計画\n\n## 検索数の見積もり\n\n| ステップ | 見積もり（件） | 既定 | 判定 |\n|---|---|---|---|\n"
                        "| Q8 収集 | 15〜28（WebSearch 12〜20、WebFetch 3〜8） | 30 | 収まる |\n"
                        "| Q11 レビュー 1 回目 | 8〜15 | 20 | 収まる |\n", encoding="utf-8")
        out = self.out("budget", "--step", "Q8", "--rq", "003-volume")
        self.assertIn("NEED: 20", out)
        self.assertIn("SOURCE: plan.md", out)
        self.assertIn("plan.md: .worktrees/003-volume/studies/003-volume/plan.md", out)
        # Q11 は Q12 の分を足す（Q12 は plan にないので手法の既定 15）
        out = self.out("budget", "--step", "Q11", "--rq", "3", cwd=wt)
        self.assertIn("NEED: 30（Q11 15 + Q12 15）", out)
        self.assertIn("SOURCE: plan.md / estimates_by_method（data, desk）", out)
        # --rq がなければ session.estimates（Q11 30 + Q12 15）。R2 は --rq があっても session.estimates
        self.assertIn("NEED: 45（Q11 30 + Q12 15）", self.out("budget", "--step", "Q11"))
        out = self.out("budget", "--step", "R2", "--rq", "3")
        self.assertIn("NEED: 60", out)
        self.assertIn("SOURCE: session.estimates", out)
        # --need が最優先。ない RQ はエラー
        self.assertIn("SOURCE: --need", self.out("budget", "--need", "7", "--rq", "3"))
        self.assertEqual(self.rk("budget", "--step", "Q8", "--rq", "9").returncode, 1)

    def test_rk_entry_dispatches(self) -> None:
        self.init_project()
        rk = SKILLS / "rk"

        def run(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run([sys.executable, str(rk), *args], cwd=self.repo, env=self.env, capture_output=True,
                                  text=True, encoding="utf-8")

        self.assertEqual(run("config", "get", "subagents.model").stdout.strip(), "sonnet")
        self.assertEqual(run("budget", "--step", "Q99").returncode, 1)  # 終了コードをそのまま返す
        self.assertEqual(run("budget", "--need", "999999").returncode, 0)  # 記録なし: UNMETERED
        self.assertIn("SUMMARY:", run("check", "--all").stdout)
        self.assertIn("SUMMARY:", run("num", "--all").stdout)
        self.assertEqual(run("helper", "list").returncode, 0)
        self.assertIn("skills/researchkit/rk helper", run("--help").stdout)
        if os.name != "nt":
            self.assertTrue(os.access(rk, os.X_OK))

    def test_brief(self) -> None:
        self.init_project()
        q = self.repo / "docs" / "questions"
        q.mkdir(parents=True, exist_ok=True)
        (q / "003-volume.md").write_text("# 003\n\n**状態**: 設計済み | **手法**: data\n", encoding="utf-8")
        d = self.repo / "studies" / "003-volume"
        d.mkdir(parents=True)
        (d / "spec.md").write_text(
            "# 仕様\n\n## 問い\n\n生産量は保たれているか？\n\n### 小問\n\n| ID | 小問 |\n|---|---|\n| SQ1 | " + "長い" * 200 + " |\n\n"
            "## つながる決定\n\n- **D1**: シナリオを選ぶ\n  - 分かれ目: 1%\n\n## 判定の基準\n\n| ID | 条件 |\n|---|---|\n| AC1 | 計算できる |\n\n"
            "## 範囲\n\n- 全国\n", encoding="utf-8")
        (d / "plan.md").write_text(
            "# 計画\n\n## 確度の付け方\n\n<!-- 注 -->\n\n| 順 | 条件 | 確度 |\n|---|---|---|\n| 1 | 計算できない | 不明 |\n\n"
            "## 検索数の見積もり\n\n| ステップ | 見積もり（件） |\n|---|---|\n| Q8 収集 | 20 |\n\n## 計画の変更\n\n| 日付 | 変えたこと |\n|---|---|\n", encoding="utf-8")
        (d / "tasks.md").write_text("- [x] T001 済み\n- [ ] T002 [人] 入手する\n- [ ] T003 集める\n", encoding="utf-8")
        out = self.out("brief", "3", "--width", "80")
        self.assertIn("# 003-volume（studies/003-volume）", out)
        for head in ("## 問い", "## 小問", "## つながる決定", "## 判定の基準", "## 確度の付け方", "## 検索数の見積もり",
                     "## タスク（完了 1、未完了 2）", "## 成果物"):
            self.assertIn(head, out)
        self.assertIn("生産量は保たれているか？", out)
        self.assertNotIn("### 小問", out)  # 見出しの行は出さない
        self.assertIn("- **D1**: シナリオを選ぶ", out)
        self.assertNotIn("分かれ目", out)  # 決定は見出しの行だけ
        self.assertNotIn("<!--", out)
        self.assertNotIn("## 範囲", out)
        self.assertNotIn("## 計画の変更", out)  # 中身のない節は出さない
        self.assertTrue(all(len(line) <= 80 for line in out.splitlines()))
        self.assertIn("…", out)
        self.assertIn("- [ ] T002 [人] 入手する", out)
        self.assertNotIn("## 主張", out)  # findings.md がなければ出さない
        (d / "findings.md").write_text(
            "# 主張\n\n## 答え\n\n年 0.56% 減った（C1）。\n\n## 主張\n\n| ID | 主張 | 根拠 | 確度 | 反証・限界 |\n|---|---|---|---|---|\n"
            "| C1 | 年 -0.56%{N:analysis/out/c.json#cagr.main} 減った | S003-0001 | 確実 | 長い限界 |\n\n"
            "## 仮説ごとの判定\n\n| 仮説 | 判定 |\n|---|---|\n| H2 | 保留 |\n", encoding="utf-8")
        out = self.out("brief", "3")
        self.assertIn("## 答え（findings.md）", out)
        self.assertIn("年 0.56% 減った（C1）。", out)
        self.assertIn("| C1 | 年 -0.56% 減った | 確実 |", out)  # 数値の参照の記号と根拠・限界の欄は省く
        self.assertIn("| H2 | 保留 |", out)
        # 作業中の worktree の成果物を優先する
        self.commit_all("s")
        wt = self.repo / ".worktrees" / "003-volume"
        self.git("worktree", "add", "-q", "-b", "rq/003-volume", str(wt), "main")
        (wt / "studies" / "003-volume" / "tasks.md").write_text("- [x] T001\n- [x] T002\n- [x] T003\n", encoding="utf-8")
        self.assertIn("## タスク（完了 3、未完了 0）", self.out("brief", "003"))

    def test_usage_report(self) -> None:
        self.init_project()
        self.git("commit", "-q", "--allow-empty", "-m", "docs(003-x): 収集",
                 "-m", "Researchkit-Step: Q8\nResearchkit-Question: 003-x")
        t8 = int(self.git("log", "-1", "--format=%ct"))
        self.env["GIT_COMMITTER_DATE"] = f"@{t8 + 100} +0000"
        self.git("commit", "-q", "--allow-empty", "-m", "docs(003-x): 分析",
                 "-m", "Researchkit-Step: Q9\nResearchkit-Question: 003-x")
        self.env.pop("GIT_COMMITTER_DATE")
        import datetime as _dt

        def iso(t: int) -> str:
            return _dt.datetime.fromtimestamp(t, _dt.timezone.utc).isoformat().replace("+00:00", "Z")

        def msg(t: int, mid: str, ctx: int, tool: str = "") -> str:
            content = [{"type": "tool_use", "id": f"tu-{mid}", "name": tool, "input": {}}] if tool else []
            return json.dumps({"type": "assistant", "timestamp": iso(t), "message": {
                "id": mid, "model": "claude-x", "content": content,
                "usage": {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": ctx, "output_tokens": 10}}})

        sess = self.tmp / "s1.jsonl"
        sess.write_text("\n".join([msg(t8 - 50, "a", 100_000, "WebSearch"), msg(t8 - 40, "a", 100_000),  # 同じ ID は 1 回
                                   msg(t8 + 50, "b", 300_000)]) + "\n", encoding="utf-8")
        sub = self.tmp / "s1" / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-1.jsonl").write_text(msg(t8 - 30, "c", 50_000) + "\n", encoding="utf-8")
        proc = subprocess.run([sys.executable, str(SKILLS / "rk"), "usage", "--session", str(sess), "--rq", "003"],
                              cwd=self.repo, env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("| 003 | Q8 | 親 | 1 | 0.1 | 100 | 0 | 1 |", proc.stdout)
        self.assertIn("| 003 | Q8 | 子 | 1 | 0.1 | 50 | 0 | 0 |", proc.stdout)
        self.assertIn("| 003 | Q9 | 親 | 1 | 0.3 | 300 | 0 | 0 |", proc.stdout)

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
        self.assertEqual(cfg["session"]["estimates_by_method"], self.rklib.DEFAULT_CONFIG["session"]["estimates_by_method"])
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
