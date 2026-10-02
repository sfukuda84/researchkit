"""new-researchkit-project: researchkit の調査のプロジェクトを作り、AI エージェントで立ち上げ（researchkit-bootstrap）を始める。

手順:
  1. scaffold を用意する。既定では GitHub から clone する（--ref でブランチやタグ、--repo でリポジトリを指定できる）。
     --scaffold <ディレクトリ> を付けると、手元の scaffold を使う（scaffold の scripts/new-researchkit-project から呼んだときはその scaffold）。
  2. scaffold の scripts/new_project.py でプロジェクトを作る（規則ファイル、スキル、git init、researchkit.py init、
     Web 検索を数えるフック）。調べたい問いは docs/concept/core-question.md に書く。
  3. 問いがあれば、指定のエージェント（既定は claude）を対話モードで起動し、researchkit-bootstrap [--auto|--oneshot] を渡す。

- --link（スキルを scaffold へのシンボリックリンクにする）は、手元の scaffold を使うときだけ使える
  （GitHub から clone した scaffold は一時的な場所にあり、終わると消えるため）。
- --adopt（既存の調査への取り込み）のときはエージェントを起動しない。続きの手順は new_project.py が表示する。
- 作成済みのプロジェクトに scaffold の新しい版を取り込むには `new-researchkit-project update [ディレクトリ]`（手で直したファイルは上書きしない）。
- コマンドの更新は `uv tool upgrade new-researchkit-project`。scaffold は実行のたびに取得するので、スキルも最新の版で作られる。

macOS / Linux / Windows で動くように、標準ライブラリだけで書く（Python 3.9 以上）。
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from . import __version__

KIT = "researchkit"
PROG = "new-researchkit-project"
DEFAULT_REPO = "https://github.com/sfukuda84/researchkit.git"
DEFAULT_REF = "main"
ENV_REPO = "RESEARCHKIT_SCAFFOLD_REPO"
ENV_REF = "RESEARCHKIT_SCAFFOLD_REF"
SKILL = "researchkit-bootstrap"
QUESTION_FILE = "docs/concept/core-question.md"
NATURAL_PROMPT = f"{SKILL} スキルを使って、この調査の立ち上げを進めてください。"


class CliError(Exception):
    """利用者に伝えて終了するエラー。"""


# --- エージェントの起動方法 ---------------------------------------------------

def invocation(prefix: str, mode: str) -> str:
    """スキルの呼び出し文字列（例: "/researchkit-bootstrap --auto"）。"""
    return " ".join([prefix + SKILL, *([f"--{mode}"] if mode else [])])


def natural_prompt(mode: str) -> str:
    """スラッシュコマンドのないエージェントに渡す依頼文。"""
    if not mode:
        return NATURAL_PROMPT
    return f"{SKILL} スキルを --{mode} の指定で使って、この調査の立ち上げを進めてください。"


def _codex_command(exe: str, root: Path, mode: str) -> list[str]:
    # workspace-write のサンドボックスでは .git が読み取り専用になり、コミットやブランチの作成ができない。
    # サンドボックスは保ったまま、.git だけを書き込み可能にする（TOML のリテラル文字列で Windows のパスも扱う）。
    # 調査は出典付きの Web 調査を行うので、Web 検索とネットワークも有効にする。
    git_dir = str((root / ".git").resolve())
    return [exe, "--sandbox", "workspace-write", "--search",
            "-c", f"sandbox_workspace_write.writable_roots=['{git_dir}']",
            "-c", "sandbox_workspace_write.network_access=true",
            invocation("$", mode)]


# エージェント名 -> (実行ファイル名, 起動コマンドを作る関数)
AGENTS: dict[str, tuple[str, Callable[[str, Path, str], list[str]]]] = {
    "claude": ("claude", lambda exe, root, mode: [exe, invocation("/", mode)]),
    "codex": ("codex", _codex_command),
    "agy": ("agy", lambda exe, root, mode: [exe, "--prompt-interactive", invocation("/", mode)]),
    "kiro": ("kiro-cli", lambda exe, root, mode: [exe, "chat", natural_prompt(mode)]),
    "opencode": ("opencode", lambda exe, root, mode: [exe, "--prompt", natural_prompt(mode)]),
}


def manual_invocation(agent: str, mode: str = "") -> str:
    """エージェントを起動しなかったときに案内する、手動での始め方。"""
    return {
        "claude": f'claude "{invocation("/", mode)}"',
        "codex": f"codex を起動して {invocation('$', mode)}（.git への書き込み、Web 検索、ネットワークを許可すること）",
        "agy": f"agy を起動して {invocation('/', mode)}",
        "kiro": f"kiro-cli chat を起動して「{natural_prompt(mode)}」",
        "opencode": f"opencode を起動して「{natural_prompt(mode)}」",
    }[agent]


def agent_command(agent: str, root: Path, mode: str = "",
                  which: Callable[[str], str | None] = shutil.which) -> list[str] | None:
    """エージェントの起動コマンド。CLI が見つからなければ None。"""
    name, build = AGENTS[agent]
    exe = which(name)
    return build(exe, root, mode) if exe else None


# --- 小さな道具 -----------------------------------------------------------------

def info(message: str) -> None:
    print(message, file=sys.stderr)


def remove_tree(path: Path) -> None:
    """Windows の読み取り専用ファイル（.git/objects など）も消せるように削除する。"""

    def on_error(func, target, _exc_info):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if path.exists():
        shutil.rmtree(path, onerror=on_error)


def run_git(args: list[str], cwd: Path | None = None) -> str:
    if shutil.which("git") is None:
        raise CliError("git が見つかりません。Git をインストールしてください。")
    proc = subprocess.run(["git", *args], cwd=str(cwd) if cwd else None, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise CliError(f"git {' '.join(args)} が失敗しました。\n{proc.stderr.strip()}")
    return proc.stdout.strip()


def clone_scaffold(repo: str, ref: str, dest: Path) -> str:
    """scaffold を clone し、コミットの SHA を返す。"""
    info(f"==> scaffold を取得します: {repo}（{ref}）")
    run_git(["clone", "--quiet", "--depth", "1", "--branch", ref, repo, str(dest)])
    return run_git(["rev-parse", "HEAD"], cwd=dest)


def check_scaffold(path: Path) -> Path:
    path = path.expanduser().resolve()
    if not (path / "scripts" / "new_project.py").is_file() or not (path / "skills" / KIT).is_dir():
        raise CliError(f"{path} は {KIT} の scaffold ではありません（scripts/new_project.py と skills/{KIT}/ が要る）。")
    return path


def check_target(target: Path, adopt: bool) -> None:
    """clone の前に確かめる（作れないと分かっているのに scaffold を取得しない）。"""
    if target.exists() and not target.is_dir():
        raise CliError(f"{target} はディレクトリではありません。")
    if not adopt and target.exists() and any(target.iterdir()):
        raise CliError(f"{target} は空ではありません。既存の調査に取り込むなら --adopt を付けてください。")
    if adopt and not target.is_dir():
        raise CliError(f"{target} がありません。--adopt には既存の調査のディレクトリを指定してください。")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog=PROG,
        description=f"{KIT} の調査のプロジェクトを作り、AI エージェントで立ち上げ（{SKILL}）を始める。"
                    f"作成済みのプロジェクトの更新は `{PROG} update [ディレクトリ]`、"
                    f"コマンドの更新は `uv tool upgrade {PROG}`。")
    ap.add_argument("target", help="作るプロジェクトのディレクトリ（存在しないか、空であること。--adopt なら既存の調査）")
    ap.add_argument("--title", default="", help="調査の仮題（.researchkit/config.yaml の title）")
    ap.add_argument("-m", "--message", default=None,
                    help=f"調べたい問い（{QUESTION_FILE} に保存する）。省略時は対話で入力を受ける")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--auto", dest="mode", action="store_const", const="auto", default="",
                      help=f"質問せず推奨案を採用して進める（{SKILL} --auto）")
    mode.add_argument("--oneshot", dest="mode", action="store_const", const="oneshot",
                      help=f"最初に一度だけまとめて質問し、以降は自動で進める（{SKILL} --oneshot）")
    ap.add_argument("--agent", choices=sorted(AGENTS), default="claude",
                    help="立ち上げに使うエージェント（既定: claude）")
    ap.add_argument("--link", action="store_true",
                    help="スキルをコピーせず、scaffold へのシンボリックリンクにする（手元の scaffold を使うときだけ）")
    ap.add_argument("--adopt", action="store_true",
                    help=f"既存の調査に取り込む（上書きしない。エージェントは起動しない。続きは /{SKILL} --adopt）")
    ap.add_argument("--no-launch", action="store_true", help="エージェントを起動せず、次の手順だけを表示する")
    ap.add_argument("--scaffold", default=None, help="GitHub から取得せず、手元の scaffold のディレクトリを使う")
    ap.add_argument("--ref", default=os.environ.get(ENV_REF, DEFAULT_REF),
                    help=f"取得する scaffold のブランチまたはタグ（既定: {DEFAULT_REF}。環境変数 {ENV_REF}）")
    ap.add_argument("--repo", default=os.environ.get(ENV_REPO, DEFAULT_REPO),
                    help=f"scaffold の Git リポジトリ（既定: {DEFAULT_REPO}。環境変数 {ENV_REPO}）")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return ap


def read_question(args: argparse.Namespace) -> str:
    """調べたい問い。-m、対話入力の順に使う。取り込みと --no-launch のときは対話で聞かない。"""
    if args.message is not None:
        return args.message.strip()
    if args.adopt or args.no_launch or not sys.stdin.isatty():
        return ""
    try:
        return input("\n調べたい問い（空のまま Enter で、起動せずに終える）: ").strip()
    except EOFError:
        return ""


def new_project_command(scaffold: Path, target: Path, args: argparse.Namespace, question: str) -> list[str]:
    cmd = [sys.executable, str(scaffold / "scripts" / "new_project.py"), str(target)]
    if args.title:
        cmd += ["--title", args.title]
    if question:
        cmd += ["--question", question]
    if args.link:
        cmd.append("--link")
    if args.adopt:
        cmd.append("--adopt")
    return cmd


def launch(target: Path, args: argparse.Namespace, question: str) -> int:
    if not question:
        # 問いがなければ、new_project.py が表示した「次の手順」で足りる（同じ案内を二度出さない）
        return 0
    command = None if args.no_launch else agent_command(args.agent, target, args.mode)
    if command is None:
        if not args.no_launch:
            print(f"\n{AGENTS[args.agent][0]} コマンドが見つからないため、起動しません。")
        print(f"\n立ち上げの始め方（問いは {QUESTION_FILE} に保存済み）:")
        print(f'  cd "{target}"')
        print(f"  {manual_invocation(args.agent, args.mode)}")
        return 0
    label = f"（--{args.mode}）" if args.mode else ""
    print(f"\n{AGENTS[args.agent][0]} を起動し、{SKILL}{label} を始めます。")
    return subprocess.run(command, cwd=str(target)).returncode


def record_state(target: Path, repo: str, ref: str, sha: str, commit: bool) -> None:
    """使った scaffold の版を記録する（update が使う）。新規のときは初回コミットに続けてコミットする。"""
    from . import update

    update.write_state(target, repo, ref, sha)
    if commit:
        run_git(["add", update.STATE_FILE], cwd=target)
        run_git(["commit", "--quiet", "-m", f"chore: {KIT} の版を記録（{sha[:7]}）",
                 "-m", f"Scaffold: {repo} {ref} ({sha})"], cwd=target)


def run(args: argparse.Namespace, scaffold_dir: Path | None) -> int:
    target = Path(args.target).expanduser().resolve()
    check_target(target, args.adopt)
    local = Path(args.scaffold) if args.scaffold else scaffold_dir
    if args.link and local is None:
        raise CliError("--link は、手元の scaffold を使うとき（--scaffold <ディレクトリ>）だけ使えます。"
                       "GitHub から取得した scaffold は一時的な場所にあり、終わると消えるためです。")
    question = read_question(args)
    if local is not None:
        scaffold = check_scaffold(local)
        code = subprocess.run(new_project_command(scaffold, target, args, question)).returncode
        repo, ref, sha = str(scaffold), "", ""
        if (scaffold / ".git").exists():
            ref = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=scaffold)
            sha = run_git(["rev-parse", "HEAD"], cwd=scaffold)
    else:
        repo, ref = args.repo, args.ref
        tmp = Path(tempfile.mkdtemp(prefix=f"{KIT}-scaffold-"))
        try:
            scaffold = tmp / "scaffold"
            sha = clone_scaffold(repo, ref, scaffold)
            info(f"==> scaffold の版: {sha[:7]}")
            # 一時的な scaffold のパスを案内に出さないよう、uv のコマンドから呼んだことを new_project.py に伝える
            env = {**os.environ, "RESEARCHKIT_LAUNCHER": PROG}
            code = subprocess.run(new_project_command(check_scaffold(scaffold), target, args, question),
                                  env=env).returncode
        finally:
            remove_tree(tmp)
    if code != 0:
        return 1
    if sha:
        record_state(target, repo, ref, sha, commit=not args.adopt)
    if args.adopt:
        return 0
    return launch(target, args, question)


def main(argv: list[str] | None = None, scaffold_dir: Path | None = None) -> int:
    """scaffold_dir は、scaffold の scripts/new-researchkit-project から呼ぶときに、その scaffold を渡す。"""
    for stream in (sys.stdout, sys.stderr):
        if not stream.isatty() and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv and argv[0] == "update":
            from . import update

            return update.run_update(update.build_update_parser().parse_args(argv[1:]), scaffold_dir)
        return run(build_parser().parse_args(argv), scaffold_dir)
    except CliError as error:
        print(f"エラー: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n中断しました。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
