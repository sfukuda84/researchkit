"""worktree_helper.py の E2E テスト。一時ディレクトリに Git リポジトリを作り、シナリオを順に実行する。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HELPER = (Path(__file__).resolve().parents[2]
          / "skills" / "researchkit" / "researchkit-worktree" / "scripts" / "worktree_helper.py")
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}
DESIGN = "Q2 Q3 Q4 Q5 Q6 Q7-1 Q7-2"
EXECUTE = "Q8 Q9 Q10 Q11 Q12"

QUESTION = """# {title}

**状態**: 未着手 | **区分**: {kind} | **想定順序**: {order} | **依存**: — | **手法**: desk

## 問い
"""

README = """# 問いの一覧

| # | RQ | 区分 | 状態 | 依存 | 一言 |
|---|---|---|---|---|---|
| 000 | [共通基盤](./000-research-foundation.md) | 基盤 | 未着手 | — | 出典台帳と分析環境 |
| 001 | [市場規模](./001-market-size.md) | 中核 | 未着手 | — | 市場は十分に大きいか |
| 999 | [統合報告](./999-research-report.md) | 統合 | 未着手 | 000, 001 | 報告書 |
"""

ORDER = """# 着手順

1. **[共通基盤](./000-research-foundation.md)**: 出典台帳
2. **[市場規模](./001-market-size.md)**: 中核
3. **[統合報告](./999-research-report.md)**: 最後
"""


class WorktreeHelperScenario(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.env = {**os.environ, **GIT_ENV}
        # クラウドセッションの中でテストを実行しても、ローカルの動作を確かめられるようにする。
        for key in ("CLAUDE_CODE_REMOTE", "RESEARCHKIT_MAIN_BRANCH", "CLAUDE_CODE_SESSION_ID"):
            self.env.pop(key, None)
        self.git("init", "-q", "-b", "main")
        q = self.repo / "docs" / "questions"
        q.mkdir(parents=True)
        (self.repo / ".gitignore").write_text(".worktrees/\ndata/large/\n", encoding="utf-8")
        for name, title, kind, order in (("000-research-foundation", "共通基盤", "基盤", 0),
                                          ("001-market-size", "市場は十分に大きいか", "中核", 1),
                                          ("999-research-report", "統合報告", "統合", 99)):
            (q / f"{name}.md").write_text(QUESTION.format(title=title, kind=kind, order=order), encoding="utf-8")
        (q / "README.md").write_text(README, encoding="utf-8")
        (q / "spec_order.md").write_text(ORDER, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "init")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- helpers ---------------------------------------------------------
    def git(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=self.env, check=True,
                              capture_output=True, text=True, encoding="utf-8").stdout.strip()

    def run_helper(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HELPER), *args], cwd=cwd or self.repo, env=self.env,
                              capture_output=True, text=True, encoding="utf-8")

    def out(self, *args: str, cwd: Path | None = None) -> str:
        proc = self.run_helper(*args, cwd=cwd)
        return (proc.stdout + proc.stderr).strip()

    def code(self, *args: str) -> int:
        return self.run_helper(*args).returncode

    def checkpoints(self, rq: str, steps: str) -> None:
        for step in steps.split():
            proc = self.run_helper("checkpoint", rq, step, f"x: {step}")
            self.assertEqual(proc.returncode, 0, proc.stderr)

    @staticmethod
    def study_files(worktree: Path, name: str, tasks: str = "- [ ] T001 収集する\n") -> Path:
        d = worktree / "studies" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.md").write_text("s\n", encoding="utf-8")
        (d / "plan.md").write_text("p\n", encoding="utf-8")
        (d / "tasks.md").write_text(tasks, encoding="utf-8")
        return d

    def status_of(self, name: str) -> str:
        text = (self.repo / "docs" / "questions" / f"{name}.md").read_text(encoding="utf-8")
        return text.split("**状態**: ", 1)[1].split(" |", 1)[0]

    def finish_all(self, rq: str, tasks: str = "- [x] T001 収集する\n") -> str:
        """ensure から finish（all）まで通す。"""
        self.assertIn("WORKTREE_STATE: created", self.out("ensure", rq, "--phase", "all"))
        name = self.out("resolve", rq)
        wt = self.repo / ".worktrees" / name
        self.study_files(wt, name, tasks)
        (wt / "studies" / name / "findings.md").write_text("f\n", encoding="utf-8")
        self.checkpoints(rq, f"{DESIGN} {EXECUTE}")
        out = self.out("finish", rq, "--phase", "all")
        if "FINISHED:" in out:
            self.assertIn("HANDOVER: 引き継ぎ書を更新し", out)
        return out

    # --- scenario --------------------------------------------------------
    def test_resolve_list_and_order(self) -> None:
        self.assertEqual(self.out("resolve", "1"), "001-market-size")
        self.assertEqual(self.out("resolve", "0"), "000-research-foundation")
        self.assertEqual(self.out("resolve", "market-size"), "001-market-size")
        self.assertEqual(self.out("resolve", "docs/questions/001-market-size.md"), "001-market-size")
        self.assertEqual(self.code("resolve", "7"), 1)
        self.assertEqual(self.out("resolve", "002-competitors"), "002-competitors")
        self.assertEqual(self.code("resolve", "001-other"), 1)
        self.assertEqual(self.code("resolve", "002-005"), 1)
        # spec_order.md にない 005 は番号順で後ろに足し、999 は常に最後に置く
        (self.repo / "docs" / "questions" / "005-pricing.md").write_text(
            QUESTION.format(title="価格", kind="補助", order=5), encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "add 005")
        self.assertEqual(self.out("list").splitlines(),
                         ["000-research-foundation", "001-market-size", "005-pricing", "999-research-report"])

    def test_design_then_execute(self) -> None:
        self.assertEqual(self.out("next", "--phase", "design"), "000-research-foundation")
        self.assertEqual(self.out("next", "--phase", "execute"), "")
        self.assertEqual(self.code("ensure", "1", "--phase", "execute"), 3)
        self.assertIn("DESIGN_MISSING", self.out("ensure", "1", "--phase", "execute"))

        # 設計工程
        self.assertIn("WORKTREE_STATE: created", self.out("ensure", "1", "--phase", "design"))
        w1 = self.repo / ".worktrees" / "001-market-size"
        self.assertEqual(self.git("rev-parse", "--abbrev-ref", "HEAD", cwd=w1), "rq/001-market-size")
        self.assertTrue((w1 / "studies" / "001-market-size").is_dir())
        self.study_files(w1, "001-market-size")
        proc = self.run_helper("checkpoint", "1", "Q2", "docs(001-market-size): 問いの仕様を作成", cwd=w1)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("NEXT_STEP: Q3", proc.stdout)
        body = self.git("log", "-1", "--format=%B", cwd=w1)
        self.assertIn("Researchkit-Step: Q2", body)
        self.assertIn("Researchkit-Question: 001-market-size", body)
        self.assertIn("RQ_NAME: 001-market-size", self.out("state", "1", "--phase", "design", cwd=w1))
        self.assertIn("WORKTREE_STATE: reused", self.out("ensure", "1", "--phase", "design"))
        self.assertEqual(self.code("finish", "1", "--phase", "design"), 1)  # Q3 以降が未完了
        self.assertIn("DESIGN_INCOMPLETE", self.out("ensure", "1", "--phase", "execute"))
        self.assertEqual(self.code("checkpoint", "1", "Q7-3", "x"), 1)  # 不正なステップ
        self.checkpoints("1", "Q3 Q4 Q5 Q6 Q7-1 Q7-2")
        self.assertIn("NEXT_STEP: Q13", self.out("state", "1", "--phase", "design"))
        self.assertIn("NEXT_STEP: Q8", self.out("state", "1", "--phase", "all"))
        self.assertEqual(self.code("finish", "1", "--phase", "design"), 0)
        self.assertFalse(w1.exists())
        self.assertEqual(self.git("branch", "--list", "rq/001-market-size"), "")
        self.assertEqual(self.git("log", "-1", "--format=%s"), "merge(001-market-size): design")
        self.assertEqual(self.status_of("001-market-size"), "設計済み")
        readme = (self.repo / "docs" / "questions" / "README.md").read_text(encoding="utf-8")
        self.assertIn("| 001 | [市場規模](./001-market-size.md) | 中核 | 設計済み |", readme)
        self.assertIn("| 000 | [共通基盤](./000-research-foundation.md) | 基盤 | 未着手 |", readme)
        self.assertIn("ALREADY_DESIGNED", self.out("ensure", "1", "--phase", "design"))
        self.assertEqual(self.out("next", "--phase", "execute"), "001-market-size")

        # 実行工程（main から作り直す）
        self.assertIn("NEXT_STEP: Q8", self.out("ensure", "1", "--phase", "execute"))
        self.checkpoints("1", "Q8 Q9 Q10 Q11")
        self.assertIn("EXECUTE_IN_PROGRESS", self.out("ensure", "1", "--phase", "design"))
        self.checkpoints("1", "Q12")
        # [人] 以外の未完了のタスク
        self.assertIn("UNCHECKED_TASKS", self.out("finish", "1", "--phase", "execute"))
        tasks = w1 / "studies" / "001-market-size" / "tasks.md"
        tasks.write_text("- [x] T001 収集する\n- [ ] T002 [人] 有料レポートを入手する（完了の確かめ方: data/manifest.md）\n",
                         encoding="utf-8")
        # どのステップにも含まれない変更
        self.assertIn("LEFTOVER_CHANGES", self.out("finish", "1", "--phase", "execute"))
        (w1 / "data" / "large").mkdir(parents=True)
        (w1 / "data" / "large" / "big.csv").write_text("a,b\n", encoding="utf-8")
        result = self.out("finish", "1", "--phase", "execute", "--commit-leftovers")
        self.assertIn("FINISHED: 001-market-size (execute)", result)
        self.assertIn("HUMAN_TASKS_PENDING: 1", result)
        self.assertIn("KEPT_LARGE_DATA: data/large/big.csv", result)
        self.assertTrue((self.repo / "data" / "large" / "big.csv").is_file())
        self.assertEqual(self.status_of("001-market-size"), "人の作業待ち")
        self.assertIn("ALREADY_EXECUTED", self.out("ensure", "1", "--phase", "execute"))
        self.assertIn("001-market-size:", self.out("human-tasks"))

        # 人のタスクの片付け
        tasks_main = self.repo / "studies" / "001-market-size" / "tasks.md"
        tasks_main.write_text(tasks_main.read_text(encoding="utf-8").replace("- [ ] T002", "- [x] T002"),
                              encoding="utf-8")
        self.assertIn("RQ_STATUS: 完了", self.out("sync-status", "1"))
        self.assertEqual(self.status_of("001-market-size"), "完了")
        self.assertEqual(self.out("human-tasks"), "")

    def test_ensure_reports_unrecorded_data_on_reuse(self) -> None:
        out = self.out("ensure", "1", "--phase", "all")
        self.assertIn("WORKTREE_STATE: created", out)
        self.assertNotIn("UNCOMMITTED_CHANGES", out)
        wt = self.repo / ".worktrees" / "001-market-size"
        (wt / "data" / "raw").mkdir(parents=True)
        (wt / "data" / "manifest.md").write_text(
            "| ファイル | SHA-256 |\n|---|---|\n| data/raw/listed.csv | x |\n", encoding="utf-8")
        (wt / "data" / "raw" / "listed.csv").write_text("a", encoding="utf-8")
        (wt / "data" / "raw" / "食料需給表_2024.csv").write_text("b", encoding="utf-8")
        out = self.out("ensure", "1", "--phase", "all")
        self.assertIn("WORKTREE_STATE: reused", out)
        self.assertIn("UNCOMMITTED_CHANGES: 3", out)
        self.assertIn("UNRECORDED_DATA: 1", out)
        self.assertIn("  - data/raw/食料需給表_2024.csv", out)
        self.assertNotIn("  - data/raw/listed.csv", out)

    def test_checkpoint_reports_split_session(self) -> None:
        cfg = self.repo / ".researchkit" / "config.yaml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("paths:\n  studies: studies\nsession:\n  web_search_limit: 200\n  split_after: [Q10]  # 区切る\n",
                       encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "config")
        self.assertIn("WORKTREE_STATE: created", self.out("ensure", "1", "--phase", "all"))
        out = self.out("checkpoint", "1", "Q9", "x: Q9")
        self.assertNotIn("SPLIT_SESSION", out)
        out = self.out("checkpoint", "1", "Q10", "x: Q10")
        self.assertIn("SPLIT_SESSION: Q10 の後でセッションを区切る設定", out)
        # ブロックの形のリストも読む
        cfg.write_text("session:\n  split_after:\n    - Q8\n    - Q11\n  rqs_unmetered: 1\n", encoding="utf-8")
        self.assertIn("SPLIT_SESSION: Q11", self.out("checkpoint", "1", "Q11", "x: Q11"))

    def test_checkpoint_default_subject(self) -> None:
        self.assertIn("WORKTREE_STATE: created", self.out("ensure", "1", "--phase", "all"))
        self.assertIn("CHECKPOINT: Q2", self.out("checkpoint", "1", "Q2"))
        wt = self.repo / ".worktrees" / "001-market-size"
        log = subprocess.run(["git", "log", "-1", "--format=%s%n%b"], cwd=wt, capture_output=True, text=True).stdout
        self.assertIn("docs(001-market-size): 問いの仕様を作成", log)
        self.assertIn("Researchkit-Step: Q2", log)

    def test_report_waits_for_other_rqs(self) -> None:
        self.assertIn("DEPENDENCY_PENDING", self.out("ensure", "999", "--phase", "all"))
        self.assertEqual(self.code("ensure", "999", "--phase", "all"), 3)
        self.assertIn("FINISHED: 000-research-foundation (all)", self.finish_all("0"))
        self.assertEqual(self.status_of("000-research-foundation"), "完了")
        self.assertEqual(self.out("next", "--phase", "all"), "001-market-size")
        self.assertIn("DEPENDENCY_PENDING", self.out("ensure", "999", "--phase", "design"))
        result = self.finish_all("1", tasks="- [x] T001 収集する\n- [ ] T002 [人] 専門家に確認する（完了の確かめ方: メモ）\n")
        self.assertIn("HUMAN_TASKS_PENDING: 1", result)
        # 人の作業待ちでも、統合報告に進める
        self.assertEqual(self.out("next", "--phase", "all"), "999-research-report")
        self.assertIn("FINISHED: 999-research-report (all)", self.finish_all("999"))
        self.assertEqual(self.out("next", "--phase", "all"), "")
        status = self.out("status")
        self.assertIn("| 999-research-report | 完了 | 完了 | 完了 | - | - |", status)
        self.assertIn("| 001-market-size | 人の作業待ち | 完了 | 完了 | - | 残り 1 件 |", status)

    def test_status_shows_waiting_report_and_worktree(self) -> None:
        self.out("ensure", "1", "--phase", "all")
        status = self.out("status")
        self.assertIn("| 001-market-size | 未着手 | 未着手 | - | あり（次: Q2） | - |", status)
        self.assertIn("| 999-research-report | 未着手 | 未着手（ほかの RQ の完了待ち） | - | - | - |", status)
        self.assertEqual(self.out("next", "--phase", "design"), "001-market-size")  # 途中の worktree を優先
        self.assertEqual(self.out("next", "--phase", "all", "--skip", "1"), "000-research-foundation")

    def test_abort_requires_yes(self) -> None:
        self.out("ensure", "1", "--phase", "design")
        self.assertIn("確認のみ", self.out("abort", "1"))
        self.assertTrue((self.repo / ".worktrees" / "001-market-size").is_dir())
        self.assertIn("ABORTED: 001-market-size", self.out("abort", "1", "--yes"))
        self.assertFalse((self.repo / ".worktrees" / "001-market-size").exists())
        self.assertEqual(self.git("branch", "--list", "rq/001-market-size"), "")

    def test_not_on_main_and_switch(self) -> None:
        self.out("ensure", "0", "--phase", "design")
        wt = self.repo / ".worktrees" / "000-research-foundation"
        self.study_files(wt, "000-research-foundation")
        self.checkpoints("0", DESIGN)
        self.git("switch", "-q", "-c", "other")
        self.assertIn("NOT_ON_MAIN", self.out("finish", "0", "--phase", "design"))
        self.assertIn("FINISHED", self.out("finish", "0", "--phase", "design", "--switch"))
        self.assertEqual(self.git("rev-parse", "--abbrev-ref", "HEAD"), "main")

    def test_finish_inside_worktree_is_refused(self) -> None:
        self.out("ensure", "0", "--phase", "design")
        wt = self.repo / ".worktrees" / "000-research-foundation"
        self.study_files(wt, "000-research-foundation")
        self.checkpoints("0", DESIGN)
        proc = self.run_helper("finish", "0", "--phase", "design", cwd=wt)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("worktree の外", proc.stderr)

    def test_main_branch_from_env_and_config_paths(self) -> None:
        # paths.questions と paths.studies を読み替える
        (self.repo / ".researchkit").mkdir()
        (self.repo / ".researchkit" / "config.yaml").write_text(
            "paths:\n  questions: rq   # 概要\n  studies: work/studies\n", encoding="utf-8")
        self.git("mv", "docs/questions", "rq")
        self.git("add", "-A")
        self.git("commit", "-qm", "move")
        self.git("branch", "-m", "main", "trunk")
        self.assertEqual(self.code("list"), 1)  # main がない
        self.env["RESEARCHKIT_MAIN_BRANCH"] = "trunk"
        self.assertEqual(self.out("list").splitlines()[0], "000-research-foundation")
        self.out("ensure", "1", "--phase", "design")
        self.assertTrue((self.repo / ".worktrees" / "001-market-size" / "work" / "studies" / "001-market-size").is_dir())


if __name__ == "__main__":
    unittest.main()
