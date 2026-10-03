"""new-researchkit-project（作成・取り込み・update）のテスト。作業ツリーの scaffold を一時的な Git リポジトリにして、そこから作る。

researchkit.py（researchkit-status/scripts/）があれば new_project.py はそれで init と hooks install を行い、
なければテンプレートから設定を置いて警告する。researchkit.py は別のテスト（tests/ のほかのファイル）で確かめるので、
ここでは一時的な scaffold の中の researchkit.py を、CONTRACT.md §2 の init と hooks install だけを持つ仮のものに置き換える。
本物の researchkit.py との組み合わせは test_create_with_real_kit_script で確かめる。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCAFFOLD = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCAFFOLD / "tool" / "src"))

from new_researchkit_project import cli, update  # noqa: E402

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}
SKILL = "skills/researchkit/researchkit-bootstrap/SKILL.md"
OTHER = "skills/researchkit/researchkit-seed/SKILL.md"
KIT_SCRIPT = "skills/researchkit/researchkit-status/scripts/researchkit.py"
# プロジェクトに持ち込まない scaffold の開発用のもの
# CONTRACT.md §2 の init と hooks install だけを持つ仮の researchkit.py
STUB_KIT_SCRIPT = '''import argparse, json, pathlib, sys
ap = argparse.ArgumentParser()
ap.add_argument("--root")
ap.add_argument("cmd", nargs="+")
ap.add_argument("--title", default="")
ap.add_argument("--config-only", action="store_true")
a = ap.parse_args()
root = pathlib.Path(a.root)
if a.cmd == ["init"]:
    cfg = root / ".researchkit" / "config.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    if not cfg.exists():
        cfg.write_text("title: " + a.title + "\\n", encoding="utf-8")
elif a.cmd == ["hooks", "install"]:
    st = root / ".claude" / "settings.json"
    st.parent.mkdir(parents=True, exist_ok=True)
    st.write_text(json.dumps({"hooks": {}}), encoding="utf-8")
else:
    sys.exit(1)
'''
NOT_CARRIED = ("tool", ".github", "DESIGN.md", "docs/dev", "LICENSE", "README.md", "scripts")


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def call(*argv: str, scaffold_dir: Path | None = None) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = cli.main(list(argv), scaffold_dir=scaffold_dir)
    return code, out.getvalue()


def run_cli(*argv: str) -> tuple[int, str]:
    """子プロセス（new_project.py）の出力も含めて捕まえるため、コマンドを別のプロセスで実行する。"""
    env = {**os.environ, "PYTHONPATH": str(SCAFFOLD / "tool" / "src")}
    proc = subprocess.run([sys.executable, "-m", "new_researchkit_project", *argv], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)
    return proc.returncode, proc.stdout + proc.stderr


def load_new_project(scaffold: Path):
    spec = importlib.util.spec_from_file_location("rk_new_project", scaffold / "scripts" / "new_project.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ToolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.env_backup = dict(os.environ)
        os.environ.update(GIT_ENV)
        for key in (cli.ENV_REPO, cli.ENV_REF, update.MAIN_BRANCH_ENV, "RESEARCHKIT_LAUNCHER"):
            os.environ.pop(key, None)
        cls.tmp = Path(tempfile.mkdtemp()).resolve()
        os.environ["GIT_CONFIG_GLOBAL"] = str(cls.tmp / "gitconfig")
        Path(os.environ["GIT_CONFIG_GLOBAL"]).write_text("[user]\n\tname = t\n\temail = t@example.com\n",
                                                        encoding="utf-8")
        cls.repo = cls.tmp / "scaffold"
        shutil.copytree(SCAFFOLD, cls.repo, symlinks=True,
                        ignore=shutil.ignore_patterns(".git", ".worktrees", "__pycache__", ".scaffold-new"))
        # スキルの本文が揃う前でも動くよう、テストで使うスキルがなければ仮のものを置く（一時的な scaffold の中だけ）
        for rel in (SKILL, OTHER):
            path = cls.repo / rel
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("---\nname: stub\n---\n\n# stub\n", encoding="utf-8")
        stub = cls.repo / KIT_SCRIPT
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(STUB_KIT_SCRIPT, encoding="utf-8")
        git("init", "-q", "-b", "main", cwd=cls.repo)
        git("add", "-A", cwd=cls.repo)
        git("commit", "-qm", "scaffold", cwd=cls.repo)
        cls.url = cls.repo.as_uri()

    @classmethod
    def tearDownClass(cls) -> None:
        os.environ.clear()
        os.environ.update(cls.env_backup)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def work(self, name: str) -> Path:
        return Path(tempfile.mkdtemp(dir=self.tmp)) / name

    # --- 作成 -------------------------------------------------------------------

    def test_create_from_repo_records_state(self) -> None:
        target = self.work("p")
        code, out = call(str(target), "--repo", self.url, "--no-launch")
        self.assertEqual(code, 0, out)
        self.assertTrue((target / SKILL).is_file())
        self.assertTrue((target / ".claude" / "skills" / "researchkit-bootstrap").is_symlink())
        self.assertTrue((target / ".agents" / "skills" / "researchkit-status").is_symlink())
        self.assertTrue((target / ".kiro" / "steering" / "research.md").is_file())
        self.assertTrue((target / "opencode.json").is_file())
        self.assertTrue((target / ".researchkit" / "config.yaml").is_file())
        self.assertIn('"sha"', (target / update.STATE_FILE).read_text(encoding="utf-8"))
        self.assertEqual(git("status", "--porcelain", cwd=target), "")
        self.assertIn("版を記録", git("log", "-1", "--format=%s", cwd=target))
        self.assertIn("researchkit を初期化", git("log", "--format=%s", cwd=target))
        for rel in NOT_CARRIED:
            self.assertFalse((target / rel).exists(), rel)
        self.assertTrue((target / ".claude" / "settings.json").is_file())  # Web 検索を数えるフック

    def test_create_with_question_and_title(self) -> None:
        target = self.work("p")
        code, out = call(str(target), "--repo", self.url, "--no-launch", "--title", "国内市場の調査",
                         "-m", "国内の〇〇市場に参入すべきか")
        self.assertEqual(code, 0, out)
        question = (target / cli.QUESTION_FILE).read_text(encoding="utf-8")
        self.assertIn("国内の〇〇市場に参入すべきか", question)
        self.assertIn("国内市場の調査", (target / ".researchkit" / "config.yaml").read_text(encoding="utf-8"))
        self.assertIn(cli.QUESTION_FILE, git("ls-files", cwd=target))
        self.assertIn("/researchkit-bootstrap", out)

    def test_launch_passes_mode_to_agent(self) -> None:
        target = self.work("p")
        seen: list[tuple[str, str]] = []

        def fake_command(agent: str, root: Path, mode: str = "", which=None):
            seen.append((agent, mode))
            return [sys.executable, "-c", "open('launched.txt', 'w').write('ok')"]

        with mock.patch.object(cli, "agent_command", side_effect=fake_command):
            code, out = call(str(target), "--repo", self.url, "-m", "問い", "--oneshot", "--agent", "codex")
        self.assertEqual(code, 0, out)
        self.assertEqual(seen, [("codex", "oneshot")])
        self.assertTrue((target / "launched.txt").is_file())  # プロジェクトのディレクトリで起動する

    def test_agent_commands(self) -> None:
        root = self.tmp
        which = lambda name: f"/bin/{name}"  # noqa: E731
        self.assertEqual(cli.agent_command("claude", root, "auto", which=which),
                         ["/bin/claude", "/researchkit-bootstrap --auto"])
        self.assertEqual(cli.agent_command("codex", root, "", which=which)[-1], "$researchkit-bootstrap")
        self.assertIn("--oneshot", cli.agent_command("kiro", root, "oneshot", which=which)[-1])
        self.assertIsNone(cli.agent_command("opencode", root, "", which=lambda name: None))

    def test_missing_agent_prints_manual_steps(self) -> None:
        target = self.work("p")
        with mock.patch.object(cli, "agent_command", return_value=None):
            code, out = call(str(target), "--repo", self.url, "-m", "問い", "--auto")
        self.assertEqual(code, 0, out)
        self.assertIn("見つからないため", out)
        self.assertIn('claude "/researchkit-bootstrap --auto"', out)

    def test_link_requires_local_scaffold(self) -> None:
        code, out = call(str(self.work("p")), "--repo", self.url, "--link", "--no-launch")
        self.assertEqual(code, 1)
        self.assertIn("--link", out)

    def test_link_with_local_scaffold(self) -> None:
        target = self.work("p")
        code, out = call(str(target), "--link", "--no-launch", scaffold_dir=self.repo)
        self.assertEqual(code, 0, out)
        self.assertTrue((target / "skills" / "researchkit").is_symlink())
        self.assertTrue((target / ".claude" / "skills" / "researchkit-bootstrap" / "SKILL.md").is_file())

    def test_nonempty_target_without_adopt(self) -> None:
        target = self.work("p")
        target.mkdir(parents=True)
        (target / "x.txt").write_text("x", encoding="utf-8")
        code, out = call(str(target), "--repo", self.url, "--no-launch")
        self.assertEqual(code, 1)
        self.assertIn("--adopt", out)

    def test_create_without_kit_script_falls_back_to_template(self) -> None:
        """researchkit.py がない scaffold でも作れる（テンプレートから設定を置き、警告する）。"""
        scaffold = self.work("sc")
        git("clone", "-q", self.url, str(scaffold), cwd=self.tmp)
        scripts = scaffold / "skills" / "researchkit" / "researchkit-status" / "scripts"
        if scripts.exists():
            shutil.rmtree(scripts)
        target = self.work("p")
        code, out = run_cli(str(target), "--scaffold", str(scaffold), "--no-launch", "--title", "T")
        self.assertEqual(code, 0, out)
        self.assertIn("WARN", out)
        self.assertIn("title: T", (target / ".researchkit" / "config.yaml").read_text(encoding="utf-8"))

    @unittest.skipUnless((SCAFFOLD / KIT_SCRIPT).is_file(), "researchkit.py がまだない")
    def test_create_with_real_kit_script(self) -> None:
        """本物の researchkit.py で init と hooks install が通る（作業ツリーの scaffold を手元の scaffold として使う）。"""
        scaffold = self.work("real")
        shutil.copytree(SCAFFOLD, scaffold, symlinks=True,
                        ignore=shutil.ignore_patterns(".git", ".worktrees", "__pycache__", ".scaffold-new"))
        target = self.work("p")
        code, out = run_cli(str(target), "--scaffold", str(scaffold), "--no-launch", "--title", "T")
        self.assertEqual(code, 0, out)
        self.assertTrue((target / ".researchkit" / "config.yaml").is_file())
        self.assertTrue((target / ".claude" / "settings.json").is_file())
        self.assertEqual(git("status", "--porcelain", cwd=target), "")
        # 入口 rk は実行できるファイルで、スキルとしてはリンクしない。プロジェクトの中から 1 語で呼べる
        rk = target / "skills" / "researchkit" / "rk"
        self.assertTrue(rk.is_file())
        self.assertFalse((target / ".claude" / "skills" / "rk").exists())
        if os.name != "nt":
            self.assertTrue(os.access(rk, os.X_OK))
            proc = subprocess.run([str(rk), "config", "get", "subagents.model"], cwd=target, capture_output=True,
                                  text=True, encoding="utf-8")
            self.assertEqual((proc.returncode, proc.stdout.strip()), (0, "sonnet"), proc.stderr)
            proc = subprocess.run([str(rk), "helper", "list"], cwd=target, capture_output=True, text=True,
                                  encoding="utf-8")
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_symlink_failure_falls_back_to_copy(self) -> None:
        new_project = load_new_project(self.repo)
        target = self.work("p")
        shutil.copytree(self.repo / "skills" / "researchkit", target / "skills" / "researchkit")

        def refuse(*_args, **_kwargs):
            raise OSError("symlink not permitted")

        err = io.StringIO()
        with mock.patch.object(pathlib.Path, "symlink_to", refuse), contextlib.redirect_stderr(err):
            made = new_project.link_agent_dirs(target, [])
        link = target / ".claude" / "skills" / "researchkit-bootstrap"
        self.assertGreater(made, 0)
        self.assertTrue(link.is_dir())
        self.assertFalse(link.is_symlink())
        self.assertIn("実体をコピー", err.getvalue())

    # --- 取り込み ------------------------------------------------------------------

    def test_adopt_merges_gitignore_and_keeps_files(self) -> None:
        target = self.work("p")
        target.mkdir(parents=True)
        git("init", "-q", "-b", "main", cwd=target)
        (target / ".gitignore").write_text("mine/\n", encoding="utf-8")
        (target / "CLAUDE.md").write_text("# mine\n", encoding="utf-8")
        git("add", "-A", cwd=target)
        git("commit", "-qm", "init", cwd=target)
        code, out = run_cli(str(target), "--adopt", "--repo", self.url, "-m", "既存の問い")
        self.assertEqual(code, 0, out)
        gi = (target / ".gitignore").read_text(encoding="utf-8")
        self.assertTrue(gi.startswith("mine/\n"))
        self.assertIn(".worktrees/", gi)
        self.assertEqual((target / "CLAUDE.md").read_text(encoding="utf-8"), "# mine\n")
        self.assertIn("@.kiro/steering/research.md", out)  # steering を読み込む行を案内する
        self.assertIn("/researchkit-bootstrap --adopt", out)
        self.assertTrue((target / cli.QUESTION_FILE).is_file())
        self.assertEqual(git("log", "--format=%s", cwd=target), "init")  # 取り込みではコミットしない

    def test_adopt_relink_hint_points_to_command(self) -> None:
        target = self.work("p")
        own = target / ".claude" / "skills" / "researchkit-bootstrap"
        own.mkdir(parents=True)
        (own / "SKILL.md").write_text("mine\n", encoding="utf-8")
        git("init", "-q", "-b", "main", cwd=target)
        git("add", "-A", cwd=target)
        git("commit", "-qm", "init", cwd=target)
        code, out = run_cli(str(target), "--adopt", "--repo", self.url)
        self.assertEqual(code, 0, out)
        self.assertIn(f'{cli.PROG} "{target}" --adopt', out)
        self.assertNotIn("researchkit-scaffold-", out)  # 消える一時的な scaffold のパスを案内しない
        # 案内どおり、既存のものを消して取り込みをもう一度実行すると、足りないリンクだけを作る
        shutil.rmtree(own)
        code, out = call(str(target), "--adopt", "--repo", self.url)
        self.assertEqual(code, 0, out)
        self.assertTrue(own.is_symlink())

    def test_relink(self) -> None:
        target = self.work("p")
        self.assertEqual(call(str(target), "--repo", self.url, "--no-launch")[0], 0)
        link = target / ".kiro" / "skills" / "researchkit-seed"
        link.unlink()
        proc = subprocess.run([sys.executable, str(self.repo / "scripts" / "new_project.py"), "--relink", str(target)],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("LINKED: 1", proc.stdout)
        self.assertTrue(link.is_symlink())

    # --- update ------------------------------------------------------------------

    def test_update_flow(self) -> None:
        scaffold = self.work("sc")
        git("clone", "-q", self.url, str(scaffold), cwd=self.tmp)
        target = self.work("p")
        self.assertEqual(call(str(target), "--repo", scaffold.as_uri(), "--no-launch")[0], 0)
        # プロジェクト側で 1 つ手で直す
        with (target / OTHER).open("a", encoding="utf-8") as f:
            f.write("\n手直し\n")
        git("commit", "-qam", "hand", cwd=target)
        # scaffold の新しい版
        with (scaffold / SKILL).open("a", encoding="utf-8") as f:
            f.write("\n新しい版\n")
        with (scaffold / OTHER).open("a", encoding="utf-8") as f:
            f.write("\n新しい版\n")
        (scaffold / "skills" / "researchkit" / "researchkit-bootstrap" / "added.md").write_text("added\n",
                                                                                                encoding="utf-8")
        (scaffold / "DESIGN.md").write_text("changed\n", encoding="utf-8")  # 持ち込まないもの
        tool = scaffold / "skills" / "researchkit" / "rk-extra"
        tool.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        tool.chmod(0o755)
        git("add", "-A", cwd=scaffold)
        git("commit", "-qm", "B", cwd=scaffold)

        code, out = call("update", str(target), "--repo", scaffold.as_uri(), "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertNotIn("新しい版", (target / SKILL).read_text(encoding="utf-8"))

        code, out = call("update", str(target), "--repo", scaffold.as_uri())
        self.assertEqual(code, 0, out)
        self.assertIn("新しい版", (target / SKILL).read_text(encoding="utf-8"))
        self.assertTrue((target / "skills" / "researchkit" / "researchkit-bootstrap" / "added.md").is_file())
        if os.name != "nt":  # 実行権も持ち込む
            self.assertTrue(os.access(target / "skills" / "researchkit" / "rk-extra", os.X_OK))
        self.assertFalse((target / "DESIGN.md").exists())
        other = (target / OTHER).read_text(encoding="utf-8")
        self.assertIn("手直し", other)
        self.assertNotIn("新しい版", other)
        self.assertTrue((target / update.NEW_VERSIONS_DIR / OTHER).is_file())
        self.assertEqual(git("status", "--porcelain", cwd=target), "")
        self.assertIn("を更新", git("log", "-1", "--format=%s", cwd=target))
        code, out = call("update", str(target), "--repo", scaffold.as_uri())
        self.assertIn("すでに最新", out)

    def test_update_keeps_adopted_conflicts(self) -> None:
        target = self.work("p")
        target.mkdir(parents=True)
        git("init", "-q", "-b", "main", cwd=target)
        own = target / ".claude" / "skills" / "researchkit-bootstrap"
        own.mkdir(parents=True)
        (own / "SKILL.md").write_text("mine\n", encoding="utf-8")
        (target / "CLAUDE.md").write_text("# mine\n", encoding="utf-8")
        git("add", "-A", cwd=target)
        git("commit", "-qm", "init", cwd=target)
        code, out = call(str(target), "--adopt", "--repo", self.url)
        self.assertEqual(code, 0, out)
        git("add", "-A", cwd=target)
        git("commit", "-qm", "adopt", cwd=target)
        code, out = call("update", str(target), "--repo", self.url)
        self.assertEqual(code, 0, out)
        self.assertEqual((own / "SKILL.md").read_text(encoding="utf-8"), "mine\n")
        self.assertEqual((target / "CLAUDE.md").read_text(encoding="utf-8"), "# mine\n")

    def test_update_skips_linked_skills(self) -> None:
        target = self.work("p")
        self.assertEqual(call(str(target), "--link", "--no-launch", scaffold_dir=self.repo)[0], 0)
        code, out = call("update", str(target), "--repo", self.url, "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("scaffold へのリンクなので更新しない", out)

    def test_update_stops_on_dirty_tree(self) -> None:
        target = self.work("p")
        self.assertEqual(call(str(target), "--repo", self.url, "--no-launch")[0], 0)
        (target / "dirty.txt").write_text("x", encoding="utf-8")
        code, out = call("update", str(target), "--repo", self.url)
        self.assertEqual(code, 1)
        self.assertIn("未コミット", out)

    def test_update_requires_main_branch(self) -> None:
        target = self.work("p")
        self.assertEqual(call(str(target), "--repo", self.url, "--no-launch")[0], 0)
        git("checkout", "-qb", "rq/001-x", cwd=target)
        code, out = call("update", str(target), "--repo", self.url)
        self.assertEqual(code, 1)
        self.assertIn(update.MAIN_BRANCH_ENV, out)


if __name__ == "__main__":
    unittest.main()
