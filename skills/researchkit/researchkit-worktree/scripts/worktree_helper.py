#!/usr/bin/env python3
"""worktree_helper.py - researchkit-question / researchkit-execute / researchkit-all 共通の worktree 管理

gamekit の worktree_helper.py を調査向けに移したもの。単位は問い（RQ）である。

各 RQ を .worktrees/<RQ_NAME>（ブランチ rq/<RQ_NAME>）で進め、ステップ完了ごとのコミットに付けた trailer
"Researchkit-Step: <STEP>" と "Researchkit-Question: <RQ_NAME>" で進捗を判定する。RQ 名付きの trailer は main に
マージされた後も残るので、マージ後も進捗を失わない。プロジェクトのルートから実行しても worktree の中から実行しても
同じように動く。macOS / Linux / Windows で動くように、標準ライブラリだけで書く（Python 3.9 以上）。
"""

from __future__ import annotations

import functools
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# マージ先のブランチ。main() で resolve_main_branch() の結果に置き換える（ローカルでは main）。
MAIN_BRANCH = os.environ.get("RESEARCHKIT_MAIN_BRANCH") or "main"
# Claude Code のクラウドセッション（VM 内では CLAUDE_CODE_REMOTE=true）。push できるのはセッションの作業ブランチだけで、
# VM は回収されると消えるため、マージ先を作業ブランチにし、マージ後に push する。
CLOUD_SESSION = os.environ.get("CLAUDE_CODE_REMOTE") == "true"
DESIGN_STEPS = ["Q2", "Q3", "Q4", "Q5", "Q6", "Q7-1", "Q7-2"]
EXECUTE_STEPS = ["Q8", "Q9", "Q10", "Q11", "Q12"]
ALL_STEPS = DESIGN_STEPS + EXECUTE_STEPS
PHASE_STEPS = {"design": DESIGN_STEPS, "execute": EXECUTE_STEPS, "all": ALL_STEPS}
PHASE_LAST_STEP = {"design": "Q7-2", "execute": "Q12", "all": "Q12"}
FINISH_STEP = "Q13"
REPORT_PREFIX = "999-"  # 統合報告の予約番号。ほかのすべての RQ が終わってから始める
ORDER_LINK_RE = re.compile(r"\]\((?:\./)?([0-9]{3}-[a-z0-9][a-z0-9-]*)\.md\)")
STEP_TRAILER_RE = re.compile(r"^Researchkit-Step:\s*(\S+)", re.MULTILINE)
RQ_TRAILER_RE = re.compile(r"^Researchkit-Question:\s*(\S+)", re.MULTILINE)
MERGE_SUBJECT_RE = re.compile(r"^merge\(([^)]+)\): (design|execute|all)$", re.MULTILINE)
UNCHECKED_RE = re.compile(r"^[ \t]*- \[ \].*$", re.MULTILINE)
CHECKED_RE = re.compile(r"^[ \t]*- \[[xX]\].*$", re.MULTILINE)
# 人が行うタスクの印（steering の「人が行うタスク」）。未完了でも AI の作業漏れとして扱わない。
HUMAN_MARKER = "[人]"
COMMIT_SEP = "\x1e"
# RQ の概要ファイル（docs/questions/<RQ_NAME>.md）の状態欄
STATUS_TODO = "未着手"
STATUS_DESIGNED = "設計済み"
STATUS_DONE = "完了"
STATUS_HUMAN_PENDING = "人の作業待ち"
FINISHED_STATUSES = (STATUS_DONE, STATUS_HUMAN_PENDING)
RQ_NAME_RE = re.compile(r"^[0-9]{3}-[a-z0-9][a-z0-9-]*$")
STATUS_FIELD_RE = re.compile(r"(\*\*状態\*\*:\s*)([^|\n]+?)(\s*(?:\||$))", re.MULTILINE)
CONFIG_REL = ".researchkit/config.yaml"

REPO_ROOT: Path = Path()
WORKTREES_DIR: Path = Path()
QUESTIONS_DIR = "docs/questions"  # main() で config.yaml の paths.questions に置き換える
STUDIES_DIR = "studies"           # main() で config.yaml の paths.studies に置き換える
DATA_DIR = "data"                 # main() で config.yaml の paths.data に置き換える


class HelperError(Exception):
    """終了コード 1 で終わるエラー。"""


class Precondition(Exception):
    """前提条件を満たさないときの停止。スキル側で案内を出すため終了コード 3 で終わる。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def info(message: str) -> None:
    print(message, file=sys.stderr)


def run_git(args: list[str], cwd: Path | None = None, check: bool = True,
            quiet: bool = False) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        if not quiet:
            sys.stderr.write(proc.stdout)
            sys.stderr.write(proc.stderr)
        raise HelperError(f"git {' '.join(args)} が失敗しました（終了コード {proc.returncode}）。")
    return proc


def git_out(args: list[str], cwd: Path | None = None) -> str:
    return run_git(args, cwd=cwd).stdout.strip()


def git_ok(args: list[str], cwd: Path | None = None) -> bool:
    return run_git(args, cwd=cwd, check=False).returncode == 0


def git_passthrough(args: list[str], cwd: Path | None = None) -> None:
    """git の出力を stderr に流しながら実行する（進行状況の表示用）。"""
    proc = run_git(args, cwd=cwd, check=False)
    sys.stderr.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise HelperError(f"git {' '.join(args)} が失敗しました（終了コード {proc.returncode}）。")


def find_repo_root() -> Path:
    """worktree の中から実行しても、メインの作業ツリーのルートを返す。"""
    def rev_parse(*args: str) -> str:
        proc = subprocess.run(["git", "rev-parse", *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise HelperError("Git リポジトリの中で実行してください。")
        return proc.stdout.strip()

    toplevel = Path(rev_parse("--show-toplevel")).resolve()
    git_dir = Path(rev_parse("--absolute-git-dir")).resolve()
    common = Path(rev_parse("--git-common-dir"))
    common = (common if common.is_absolute() else Path.cwd() / common).resolve()
    if git_dir == common:
        return toplevel
    if toplevel.parent.name == ".worktrees":
        return toplevel.parent.parent
    proc = subprocess.run(["git", "worktree", "list", "--porcelain"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            return Path(line[len("worktree "):]).resolve()
    raise HelperError("メインの作業ツリーを特定できません。")


def read_config_paths(root: Path) -> dict[str, str]:
    """.researchkit/config.yaml の paths の節から「key: value」を読む（このスクリプトに要る範囲だけ）。"""
    path = root / CONFIG_REL
    if not path.is_file():
        return {}
    found: dict[str, str] = {}
    in_paths = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = re.sub(r"(^|\s)#.*$", "", raw).rstrip()
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            in_paths = line.strip() == "paths:"
            continue
        if in_paths:
            m = re.match(r"^\s+([A-Za-z_]+):\s*(.*)$", line)
            if m and m.group(2):
                found[m.group(1)] = m.group(2).strip().strip("'\"").rstrip("/")
    return found


def resolve_main_branch() -> str:
    """マージ先のブランチ。RESEARCHKIT_MAIN_BRANCH、クラウドセッションの作業ブランチ、main の順に決める。

    クラウドセッションでは、メインの作業ツリーが今いるブランチ（セッションの作業ブランチ）をマージ先にする。
    detached HEAD や RQ のブランチにいるときは作業ブランチを判定できないので、main に戻す。
    """
    explicit = os.environ.get("RESEARCHKIT_MAIN_BRANCH")
    if explicit:
        return explicit
    if CLOUD_SESSION:
        current = run_git(["rev-parse", "--abbrev-ref", "HEAD"], check=False).stdout.strip()
        if current and current != "HEAD" and not current.startswith("rq/"):
            return current
    return "main"


def push_after_merge() -> None:
    """クラウドセッションで、マージ先のブランチを origin に push する（VM が回収されてもマージの結果を残すため）。"""
    if not CLOUD_SESSION:
        return
    if not git_ok(["remote", "get-url", "origin"]):
        print("PUSH_SKIPPED: origin がありません")
        return
    proc = run_git(["push", "-u", "origin", MAIN_BRANCH], check=False)
    if proc.returncode == 0:
        print(f"PUSHED: origin/{MAIN_BRANCH}")
    else:
        # クラウドセッションでは作業ブランチ以外への push は拒否される。マージ自体は済んでいるので止めない。
        info(proc.stderr.strip())
        print(f"PUSH_FAILED: origin/{MAIN_BRANCH}（クラウドセッションで push できるのは作業ブランチだけ）")


def branch_of(name: str) -> str:
    return f"rq/{name}"


def worktree_of(name: str) -> Path:
    return WORKTREES_DIR / name


def study_rel(name: str, filename: str = "") -> str:
    return f"{STUDIES_DIR}/{name}" + (f"/{filename}" if filename else "")


def question_rel(name: str) -> str:
    return f"{QUESTIONS_DIR}/{name}.md"


def branch_exists(name: str) -> bool:
    return git_ok(["rev-parse", "--verify", "-q", f"refs/heads/{branch_of(name)}"])


def main_has_file(name: str, filename: str) -> bool:
    return git_ok(["cat-file", "-e", f"{MAIN_BRANCH}:{study_rel(name, filename)}"])


def main_has_tasks(name: str) -> bool:
    return main_has_file(name, "tasks.md")


def main_has_design(name: str) -> bool:
    return all(main_has_file(name, f) for f in ("spec.md", "plan.md", "tasks.md"))


def is_report(name: str) -> bool:
    return name.startswith(REPORT_PREFIX)


@functools.lru_cache(maxsize=None)
def history(ref: str) -> tuple[dict[str, frozenset], frozenset]:
    """ref から辿れる全コミットを読み、(RQ ごとの完了ステップ, 実行工程までマージ済みの RQ) を返す。"""
    proc = run_git(["log", ref, f"--format=%B{COMMIT_SEP}"], check=False)
    steps: dict[str, set[str]] = {}
    merged: set[str] = set()
    if proc.returncode == 0:
        for body in proc.stdout.split(COMMIT_SEP):
            rq = RQ_TRAILER_RE.search(body)
            if rq:
                steps.setdefault(rq.group(1), set()).update(STEP_TRAILER_RE.findall(body))
            for name, phase in MERGE_SUBJECT_RE.findall(body):
                if phase in ("execute", "all"):
                    merged.add(name)
    return {k: frozenset(v) for k, v in steps.items()}, frozenset(merged)


def forget_history() -> None:
    """コミットやマージで履歴が変わった後に呼ぶ。"""
    history.cache_clear()
    main_text.cache_clear()


@functools.lru_cache(maxsize=None)
def main_text(rel_path: str) -> str:
    proc = run_git(["show", f"{MAIN_BRANCH}:{rel_path}"], check=False)
    return proc.stdout if proc.returncode == 0 else ""


def main_tasks_text(name: str) -> str:
    return main_text(study_rel(name, "tasks.md"))


def split_unchecked(text: str) -> tuple[list[str], list[str]]:
    """未完了のタスク行を (AI のタスク, 人のタスク) に分けて返す。"""
    ai: list[str] = []
    human: list[str] = []
    for line in UNCHECKED_RE.findall(text):
        (human if HUMAN_MARKER in line else ai).append(line.strip())
    return ai, human


def unchecked_tasks(tasks_file: Path) -> tuple[list[str], list[str]]:
    if not tasks_file.is_file():
        return [], []
    return split_unchecked(tasks_file.read_text(encoding="utf-8"))


def design_done(name: str) -> bool:
    """設計工程を終えたか（Q7-2 の記録、または main に tasks.md がある）。"""
    return "Q7-2" in completed_steps(name) or main_has_tasks(name)


def executed(name: str) -> bool:
    """実行工程まで main にマージ済みか。

    main 上の Q12 の記録か、merge(<name>): execute|all のコミットで判定する。これらの記録がない、Pull Request などで
    取り込んだ RQ は、main に findings.md と tasks.md があり、tasks.md の [人] 以外のタスクがすべて完了していれば
    実行済みとみなす。
    """
    steps, merged = history(MAIN_BRANCH)
    if "Q12" in steps.get(name, frozenset()) or name in merged:
        return True
    tasks = main_tasks_text(name)
    return bool(tasks) and main_has_file(name, "findings.md") and not split_unchecked(tasks)[0]


def status_after_execute(tasks_file: Path) -> str:
    """実行を終えた後の状態。人のタスクが残っていれば 人の作業待ち、なければ 完了。"""
    _, human = unchecked_tasks(tasks_file)
    return STATUS_HUMAN_PENDING if human else STATUS_DONE


def completed_steps(name: str) -> list[str]:
    """完了済みのステップ。

    - main とブランチの全履歴にある、この RQ 名付きの trailer
    - ブランチ上の main にないコミットの trailer
    - 設計が main にマージ済み（tasks.md がある）なら Q2〜Q7-2
    - 実行まで main にマージ済みなら全ステップ
    """
    found: set[str] = set(history(MAIN_BRANCH)[0].get(name, frozenset()))
    if branch_exists(name):
        found.update(history(branch_of(name))[0].get(name, frozenset()))
        log = git_out(["log", f"{MAIN_BRANCH}..{branch_of(name)}", "--format=%B"])
        found.update(STEP_TRAILER_RE.findall(log))
    if main_has_tasks(name):
        found.update(DESIGN_STEPS)
    if executed(name):
        found.update(ALL_STEPS)
    return [step for step in ALL_STEPS if step in found]


def next_step(name: str, phase: str) -> str:
    done = set(completed_steps(name))
    for step in PHASE_STEPS[phase]:
        if step not in done:
            return step
    return FINISH_STEP


def read_spec_order() -> str:
    text = main_text(f"{QUESTIONS_DIR}/spec_order.md")
    if text:
        return text
    path = REPO_ROOT / QUESTIONS_DIR / "spec_order.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def ls_main(directory: str, dirs: bool) -> list[str]:
    args = ["ls-tree", "--name-only", MAIN_BRANCH, f"{directory}/"]
    if dirs:
        args.insert(1, "-d")
    proc = run_git(args, check=False)
    if proc.returncode != 0:
        return []
    return [line[len(directory) + 1:] for line in proc.stdout.splitlines() if line.startswith(f"{directory}/")]


def get_all_rqs() -> list[str]:
    """RQ 名を着手順に並べて返す。

    docs/questions/spec_order.md にあるものはその並び順（着手順の正本）で先に置き、そこにない
    main の docs/questions/<NNN-name>.md、studies/<NNN-name>/、.worktrees/ のものは番号順で後ろに足す。
    統合報告（999-*）は、ほかのすべての RQ の後に置く。
    """
    ordered: list[str] = []
    for match in ORDER_LINK_RE.finditer(read_spec_order()):
        if match.group(1) not in ordered:
            ordered.append(match.group(1))
    rest: set[str] = set()
    for filename in ls_main(QUESTIONS_DIR, dirs=False):
        if filename.endswith(".md") and RQ_NAME_RE.match(filename[:-3]):
            rest.add(filename[:-3])
    qdir = REPO_ROOT / QUESTIONS_DIR
    if qdir.is_dir():
        for child in qdir.glob("*.md"):
            if RQ_NAME_RE.match(child.stem):
                rest.add(child.stem)
    for dirname in ls_main(STUDIES_DIR, dirs=True):
        if RQ_NAME_RE.match(dirname):
            rest.add(dirname)
    if WORKTREES_DIR.is_dir():
        for child in WORKTREES_DIR.iterdir():
            if child.is_dir() and RQ_NAME_RE.match(child.name):
                rest.add(child.name)
    names = ordered + sorted(n for n in rest if n not in ordered)
    return [n for n in names if not is_report(n)] + [n for n in names if is_report(n)]


def resolve_rq(query: str | None) -> str:
    """短い番号（1, 002）、スラッグ、完全名（001-market-size）、ファイルパスから RQ 名を決める。"""
    if not query:
        raise HelperError("RQ を指定してください。")
    query = Path(query.replace("\\", "/")).name
    if query.endswith(".md"):
        query = query[:-3]
    padded = f"{int(query):03d}" if query.isdigit() else query

    matches: list[str] = []
    for rq in get_all_rqs():
        if rq == query:
            return rq
        if rq.startswith(f"{padded}-") or rq.endswith(f"-{query}"):
            matches.append(rq)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise HelperError(f"'{query}' に一致する RQ が複数あります: {' '.join(matches)}")
    # 一覧にない新しい RQ は、完全名（NNN-slug）で指定されたときだけ受け付ける。
    if RQ_NAME_RE.match(query):
        number, slug = query.split("-", 1)
        if re.fullmatch(r"[0-9-]+", slug):
            raise HelperError(
                f"'{query}' は範囲指定に見えます。範囲は list の結果から 1 件ずつ選び、完全名か番号で指定してください。")
        taken = [r for r in get_all_rqs() if r.startswith(f"{number}-")]
        if taken:
            raise HelperError(
                f"番号 {number} はすでに {' '.join(taken)} が使っています。綴りを確かめるか、別の番号にしてください。")
        return query
    raise HelperError(
        f"'{query}' に一致する RQ が見つかりません（{QUESTIONS_DIR}/spec_order.md、{QUESTIONS_DIR}/、"
        f"{STUDIES_DIR}/、.worktrees/ を検索）。新しい RQ は 001-short-name の形の完全名で指定してください。"
    )


def worktree_branch(worktree: Path) -> str | None:
    proc = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def question_status(name: str) -> str:
    """RQ の概要ファイルの状態欄（main を優先し、なければ作業ツリー）。ファイルや欄がなければ空文字。"""
    text = main_text(question_rel(name))
    if not text:
        path = REPO_ROOT / question_rel(name)
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
    m = STATUS_FIELD_RE.search(text)
    return m.group(2).strip() if m else ""


def rq_finished(name: str) -> bool:
    """状態が 完了 か 人の作業待ち か。状態欄がなければ、実行工程まで main にマージ済みかで判定する。"""
    status = question_status(name)
    if status:
        return status.startswith(FINISHED_STATUSES)
    return executed(name)


def pending_dependencies(name: str) -> list[str]:
    """統合報告（999）の前に終わっていない、ほかの RQ。統合報告でなければ空。"""
    if not is_report(name):
        return []
    return [rq for rq in get_all_rqs() if rq != name and not is_report(rq) and not rq_finished(rq)]


def update_question_status(base: Path, name: str, status: str, only_from: tuple[str, ...] = ()) -> list[str]:
    """docs/questions/<RQ_NAME>.md の状態欄と、README.md の一覧の状態列を status にする。更新したファイルを返す。

    only_from を指定したときは、今の状態がそのいずれかで始まる場合だけ更新する（状態を後戻りさせないため）。
    概要ファイルがなければ何もしない。
    """
    target = base / question_rel(name)
    if not target.is_file():
        return []
    changed: list[str] = []
    text = target.read_text(encoding="utf-8")
    m = STATUS_FIELD_RE.search(text)
    if m is None:
        return []
    current = m.group(2).strip()
    if current == status or (only_from and not current.startswith(only_from)):
        return []
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text[:m.start(2)] + status + text[m.end(2):])
    changed.append(target.relative_to(base).as_posix())
    readme = target.parent / "README.md"
    if readme.is_file() and update_readme_status(readme, name, status):
        changed.append(readme.relative_to(base).as_posix())
    return changed


def update_readme_status(readme: Path, name: str, status: str) -> bool:
    """README.md の表のうち「状態」の列を持つものから、./<RQ_NAME>.md へのリンクを含む行の状態の列を書き換える。"""
    lines = readme.read_text(encoding="utf-8").split("\n")
    link = re.compile(r"\]\((?:\./)?" + re.escape(name) + r"\.md\)")
    col = None
    updated = False
    for i, line in enumerate(lines):
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            col = None
            continue
        cells = s.strip("|").split("|")
        names = [c.strip().strip("*") for c in cells]
        if col is None:
            col = names.index("状態") if "状態" in names else -1
            continue
        if col < 0 or not link.search(line) or col >= len(cells):
            continue
        cells[col] = f" {status} "
        indent = line[: len(line) - len(line.lstrip())]
        lines[i] = indent + "|" + "|".join(cells) + "|"
        updated = True
    if updated:
        with open(readme, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines))
    return updated


def keep_large_data(wt: Path, ignored: list[str]) -> list[str]:
    """worktree の data/large/ にある無視対象のファイルを、メインの作業ツリーの同じ場所に写す（既存は上書きしない）。

    大きな生データはコミットしないので、worktree を消すと失われる。分析を再実行できるよう、メインの作業ツリーに残す。
    """
    prefix = f"{DATA_DIR}/large/"
    copied: list[str] = []
    for entry in ignored:
        entry = entry.rstrip("/")
        if (entry + "/").startswith(prefix):
            src = wt / entry
        elif prefix.startswith(entry + "/"):  # 中身がすべて無視対象なら、git は上のディレクトリ（data/ など）だけを出す
            src = wt / prefix.rstrip("/")
        else:
            continue
        if not src.exists():
            continue
        files = [src] if src.is_file() else [p for p in src.rglob("*") if p.is_file()]
        for f in files:
            rel = f.relative_to(wt)
            dst = REPO_ROOT / rel
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            copied.append(rel.as_posix())
    return copied


def print_state(name: str, phase: str, wt_state: str) -> None:
    print(f"REPO_ROOT: {REPO_ROOT}")
    print(f"RQ_NAME: {name}")
    print(f"BRANCH: {branch_of(name)}")
    print(f"WORKTREE_DIR: {worktree_of(name)}")
    print(f"WORKTREE_STATE: {wt_state}")
    print(f"PHASE: {phase}")
    print(f"COMPLETED_STEPS: {' '.join(completed_steps(name))}")
    print(f"NEXT_STEP: {next_step(name, phase)}")


def parse_args(args: list[str]) -> tuple[str | None, str | None, list[str]]:
    """(最初の位置引数, --phase の値, その他のフラグ) を返す。"""
    positional: str | None = None
    phase: str | None = None
    flags: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--phase":
            phase = args[i + 1] if i + 1 < len(args) else ""
            i += 2
            continue
        if arg == "--skip":  # 値を取るフラグ。値は cmd_next が読む
            i += 2
            continue
        if arg.startswith("--phase="):
            phase = arg[len("--phase="):]
        elif arg.startswith("--"):
            flags.append(arg)
        elif positional is None:
            positional = arg
        i += 1
    return positional, phase, flags


def require_phase(phase: str | None) -> str:
    if not phase:
        raise HelperError("--phase design|execute|all を指定してください。")
    if phase not in PHASE_STEPS:
        raise HelperError(f"--phase には design / execute / all のいずれかを指定してください（指定値: '{phase}'）。")
    return phase


def check_phase_precondition(name: str, phase: str, wt: Path) -> None:
    pending = pending_dependencies(name)
    if pending:
        raise Precondition(
            "DEPENDENCY_PENDING",
            f"{name} は統合報告です。ほかのすべての RQ が 完了 か 人の作業待ち になってから始めます"
            f"（未完了: {' '.join(pending)}）。",
        )
    done = completed_steps(name)
    if phase == "design":
        if not wt.is_dir() and main_has_tasks(name):
            raise Precondition(
                "ALREADY_DESIGNED",
                f"{name} の設計（tasks.md）はすでに {MAIN_BRANCH} にマージされています。実行は researchkit-execute で行ってください。",
            )
        if "Q8" in done:
            raise Precondition(
                "EXECUTE_IN_PROGRESS",
                f"{name} の worktree はすでに実行工程に入っています。researchkit-execute または researchkit-all で再開してください。",
            )
    elif phase == "execute":
        if "Q7-2" not in done:
            if wt.is_dir() or branch_exists(name):
                raise Precondition(
                    "DESIGN_INCOMPLETE",
                    f"{name} の設計工程（Q2〜Q7-2）が終わっていません（次: {next_step(name, 'design')}）。"
                    "researchkit-question または researchkit-all で再開してください。",
                )
            raise Precondition(
                "DESIGN_MISSING",
                f"{name} の spec.md / plan.md / tasks.md が {MAIN_BRANCH} にも worktree にもありません。"
                "先に researchkit-question または researchkit-all を実行してください。",
            )
        if not wt.is_dir() and not main_has_design(name):
            raise Precondition(
                "DESIGN_MISSING",
                f"{name} の spec.md / plan.md / tasks.md が {MAIN_BRANCH} にそろっていません。"
                "先に researchkit-question または researchkit-all を実行してください。",
            )
    if phase != "design" and not wt.is_dir() and not branch_exists(name) and executed(name):
        raise Precondition("ALREADY_EXECUTED", f"{name} は実行まで {MAIN_BRANCH} にマージ済みです。")


def repo_is_dirty() -> bool:
    return bool(git_out(["status", "--porcelain"]))


def report_leftovers(wt: Path) -> None:
    """再利用する worktree に残った、どのステップのコミットにも入っていない変更を報告する。

    前のセッションが途中で切れると、取得したデータ（data/raw/）が目録に載らないまま残ることがある。
    UNCOMMITTED_CHANGES に件数、UNRECORDED_DATA に目録（data/manifest.md）にないデータのファイルを出す。
    """
    status = run_git(["-c", "core.quotePath=false", "status", "--porcelain", "--untracked-files=all"], cwd=wt).stdout
    paths = [line[3:].strip().strip('"').split(" -> ")[-1] for line in status.splitlines() if len(line) > 3]
    if not paths:
        return
    print(f"UNCOMMITTED_CHANGES: {len(paths)}")
    manifest = wt / DATA_DIR / "manifest.md"
    listed = manifest.read_text(encoding="utf-8") if manifest.is_file() else ""
    data_prefix = f"{DATA_DIR}/raw/"
    unrecorded = [p for p in paths if p.startswith(data_prefix) and f"| {p} |" not in listed
                  and Path(p).name not in (".gitkeep", ".DS_Store")]
    if unrecorded:
        print(f"UNRECORDED_DATA: {len(unrecorded)}")
        for p in unrecorded[:20]:
            print(f"  - {p}")
        if len(unrecorded) > 20:
            print(f"  - ほか {len(unrecorded) - 20} 件")
        print("NOTE: 前のセッションが途中で止まった跡。出どころ（URL・statInfId）を確かめて取り直し、SHA-256 が一致したものを"
              " researchkit.py data add で目録に載せる。出どころが分からないものは使わず、人に確かめてから取り除く")


def cmd_ensure(args: list[str]) -> None:
    positional, phase, _ = parse_args(args)
    phase = require_phase(phase)
    name = resolve_rq(positional)
    branch = branch_of(name)
    wt = worktree_of(name)

    run_git(["worktree", "prune"])
    check_phase_precondition(name, phase, wt)

    if wt.is_dir():
        current = worktree_branch(wt)
        if current is None:
            raise HelperError(f"{wt} は Git の worktree ではありません。手動で確認してください。")
        if current != branch:
            raise HelperError(f"{wt} のブランチが '{current}' です（期待値: '{branch}'）。手動で確認してください。")
        wt_state = "reused"
    else:
        if not git_ok(["check-ignore", "-q", ".worktrees/"]):
            raise HelperError(
                ".worktrees/ が .gitignore に登録されていません。"
                ".gitignore に '.worktrees/' を追加してコミットしてから再実行してください。"
            )
        if repo_is_dirty():
            info(git_out(["status", "--short"]))
            raise HelperError(f"{REPO_ROOT} に未コミットの変更があります。コミットまたは stash してから再実行してください。")
        WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
        if branch_exists(name):
            info(f"==> 既存のブランチ {branch} に worktree を作り直します: {wt}")
            git_passthrough(["worktree", "add", str(wt), branch])
            wt_state = "reattached"
        else:
            info(f"==> {MAIN_BRANCH} から {branch} と worktree を作成します: {wt}")
            git_passthrough(["worktree", "add", "-b", branch, str(wt), MAIN_BRANCH])
            wt_state = "created"

    (wt / STUDIES_DIR / name).mkdir(parents=True, exist_ok=True)
    print_state(name, phase, wt_state)
    if wt_state in ("reused", "reattached"):
        report_leftovers(wt)


def cmd_state(args: list[str]) -> None:
    positional, phase, _ = parse_args(args)
    phase = require_phase(phase)
    name = resolve_rq(positional)
    print_state(name, phase, "present" if worktree_of(name).is_dir() else "absent")


def cmd_checkpoint(args: list[str]) -> None:
    if len(args) < 3:
        raise HelperError("使い方: checkpoint <rq> <step> <subject>")
    name = resolve_rq(args[0])
    step, subject = args[1], args[2]
    if step not in ALL_STEPS:
        raise HelperError(f"ステップ '{step}' は不正です（有効値: {' '.join(ALL_STEPS)}）。")
    wt = worktree_of(name)
    if not wt.is_dir():
        raise HelperError(f"worktree {wt} がありません。先に ensure を実行してください。")
    current = worktree_branch(wt)
    if current != branch_of(name):
        raise HelperError(f"{wt} のブランチが '{current}' です。")
    run_git(["add", "-A"], cwd=wt)
    run_git(["commit", "-q", "--allow-empty", "-m", subject,
             "-m", f"Researchkit-Step: {step}\nResearchkit-Question: {name}"], cwd=wt)
    forget_history()
    print(f"CHECKPOINT: {step} {git_out(['rev-parse', '--short', 'HEAD'], cwd=wt)}")
    print(f"NEXT_STEP: {next_step(name, 'all')}")


def cmd_finish(args: list[str]) -> None:
    positional, phase, flags = parse_args(args)
    phase = require_phase(phase)
    name = resolve_rq(positional)
    branch = branch_of(name)
    wt = worktree_of(name)

    if not wt.is_dir():
        raise HelperError(f"worktree {wt} がありません。")
    # worktree の中で実行すると、削除後にシェルが消えたディレクトリに残る（Windows では削除自体が失敗する）
    cwd = Path.cwd().resolve()
    if cwd == wt.resolve() or wt.resolve() in cwd.parents:
        raise HelperError(f"finish は worktree の外（{REPO_ROOT}）で実行してください。`cd {REPO_ROOT}` してから再実行します。")
    done = completed_steps(name)
    missing = [step for step in PHASE_STEPS[phase] if step not in done]
    if missing:
        raise HelperError(f"{phase} 工程のステップが完了していません（未完了: {' '.join(missing)}）。")
    for filename in ("spec.md", "plan.md", "tasks.md"):
        if not (wt / study_rel(name, filename)).is_file():
            raise HelperError(f"{wt / study_rel(name, filename)} がありません。")
    tasks_file = wt / study_rel(name, "tasks.md")
    human_pending: list[str] = []
    if phase in ("execute", "all"):
        remaining, human_pending = unchecked_tasks(tasks_file)
        if remaining and "--allow-unchecked" not in flags:
            raise Precondition(
                "UNCHECKED_TASKS",
                f"{name} の tasks.md に未完了のタスク（{HUMAN_MARKER} 以外）が {len(remaining)} 件あります。"
                "一覧をユーザーに示し、残したままマージしてよいと確認できたら --allow-unchecked を付けて再実行してください。\n"
                + "\n".join(remaining),
            )

    run_git(["add", "-A"], cwd=wt)
    if not git_ok(["diff", "--cached", "--quiet"], cwd=wt):
        if "--commit-leftovers" not in flags:
            files = git_out(["diff", "--cached", "--name-status"], cwd=wt)
            run_git(["reset", "-q"], cwd=wt)
            raise Precondition(
                "LEFTOVER_CHANGES",
                f"{wt} に、どのステップにも含まれていない変更があります。\n{files}\n"
                "内容をユーザーに示し、マージに含めてよいと確認できたら --commit-leftovers を付けて再実行してください。"
                "含めない変更は、ユーザーの了承を得て取り除いてから再実行してください。",
            )
        info("==> worktree の残りの変更をコミットします。")
        run_git(["commit", "-q", "-m", f"chore({name}): マージ前の残りの変更",
                 "-m", f"Researchkit-Question: {name}"], cwd=wt)

    # マージ後の片付けで止まらないよう、マージの前に worktree がクリーンであることを確かめる。
    leftover = git_out(["status", "--porcelain"], cwd=wt)
    if leftover:
        info(leftover)
        raise HelperError(f"{wt} にコミットできない変更が残っています。確認してから再実行してください。")
    if repo_is_dirty():
        info(git_out(["status", "--short"]))
        raise HelperError(f"{REPO_ROOT} に未コミットの変更があるためマージできません。コミットまたは stash してから再実行してください。")
    current = git_out(["rev-parse", "--abbrev-ref", "HEAD"])
    if current != MAIN_BRANCH and "--switch" not in flags:
        raise Precondition(
            "NOT_ON_MAIN",
            f"{REPO_ROOT} のブランチが {current} です（マージ先は {MAIN_BRANCH}）。"
            f"{MAIN_BRANCH} に切り替えてよいかをユーザーに確認し、よければ --switch を付けて再実行してください。",
        )

    # RQ の概要ファイルの状態欄を進める（設計の後は 設計済み、実行の後は 完了。人のタスクが残れば 人の作業待ち）
    if phase == "design":
        status = STATUS_DESIGNED
        changed = update_question_status(wt, name, status, only_from=(STATUS_TODO,))
    else:
        status = status_after_execute(tasks_file)
        changed = update_question_status(wt, name, status)
    if changed:
        for path in changed:
            info(f"==> 状態を更新しました: {path}")
        run_git(["add", "--", *changed], cwd=wt)
        run_git(["commit", "-q", "-m", f"docs({name}): 状態を「{status}」に更新",
                 "-m", f"Researchkit-Question: {name}"], cwd=wt)

    if current != MAIN_BRANCH:
        info(f"==> {REPO_ROOT} を {MAIN_BRANCH} に切り替えます（現在: {current}）。")
        run_git(["checkout", "-q", MAIN_BRANCH])

    if git_ok(["merge-base", "--is-ancestor", branch, MAIN_BRANCH]):
        # 競合を解消して手でマージした後の再実行など。ブランチはすでに main に入っているので片付けだけ行う。
        info(f"==> {branch} はすでに {MAIN_BRANCH} にマージ済みです。片付けだけを行います。")
    else:
        info(f"==> {branch} を {MAIN_BRANCH} に --no-ff でマージします。")
        try:
            git_passthrough(["merge", "--no-ff", "-m", f"merge({name}): {phase}", branch])
        except HelperError as error:
            raise HelperError(
                f"マージで競合しました。{REPO_ROOT} で競合を解消してマージをコミットし、"
                "もう一度 finish を実行してください（worktree とブランチは残しています）。"
            ) from error
    forget_history()

    info("==> worktree とブランチを削除します。")
    ignored = [line[3:] for line in git_out(["status", "--porcelain", "--ignored", "--untracked-files=normal"], cwd=wt)
               .splitlines() if line.startswith("!! ")]
    kept = keep_large_data(wt, ignored)
    if kept:
        info(f"==> {DATA_DIR}/large/ の大きな生データを、メインの作業ツリーに写しました（コミットはしない）。")
    if ignored:
        info("==> 次の無視対象のファイルは worktree と一緒に削除されます（.env など必要なものはメインの作業ツリーに控えてください）:")
        for path in ignored:
            info(f"      {path}")
    # 変更はすべてマージ済みで、残るのは無視対象のローカル状態だけなので --force で削除する。
    run_git(["worktree", "remove", "--force", str(wt)])
    git_passthrough(["branch", "-d", branch])
    print(f"FINISHED: {name} ({phase})")
    print(f"RQ_STATUS: {question_status(name) or status}")
    if kept:
        print(f"KEPT_LARGE_DATA: {' '.join(kept)}")
    if ignored:
        print(f"REMOVED_IGNORED: {' '.join(ignored)}")
    print(f"MERGE_COMMIT: {git_out(['rev-parse', '--short', 'HEAD'])}")
    push_after_merge()
    if human_pending:
        # 人のタスクだけが残っているときは止めずにマージし、残りを知らせる。
        print(f"HUMAN_TASKS_PENDING: {len(human_pending)}")
        for line in human_pending:
            print(f"  {line}")


def cmd_abort(args: list[str]) -> None:
    positional, _, flags = parse_args(args)
    name = resolve_rq(positional)
    branch = branch_of(name)
    wt = worktree_of(name)
    print(f"対象: {name}")
    if wt.is_dir():
        print(f"  削除する worktree: {wt}（未コミットの変更も失われます）")
    if branch_exists(name):
        print(f"  削除するブランチ: {branch}（{MAIN_BRANCH} に未マージのコミットも失われます）")
    if "--yes" not in flags:
        print("確認のみ行いました。実行するには --yes を付けてください。")
        return
    if wt.is_dir():
        run_git(["worktree", "remove", "--force", str(wt)])
    if branch_exists(name):
        run_git(["branch", "-D", branch])
    run_git(["worktree", "prune"])
    print(f"ABORTED: {name}")


def human_pending_of(name: str) -> list[str]:
    """残っている人のタスク。worktree があればその tasks.md、なければ main の tasks.md を読む。

    メインの作業ツリーが main にいるときは、コミット前の変更も含めて作業ツリーのファイルを読む。
    """
    tasks_file = worktree_of(name) / study_rel(name, "tasks.md")
    if tasks_file.is_file():
        return unchecked_tasks(tasks_file)[1]
    if git_out(["rev-parse", "--abbrev-ref", "HEAD"]) == MAIN_BRANCH:
        return unchecked_tasks(REPO_ROOT / study_rel(name, "tasks.md"))[1]
    return split_unchecked(main_tasks_text(name))[1]


def cmd_status(_: list[str]) -> None:
    print("| RQ | 状態 | 設計 | 実行 | WORKTREE | 人の作業 |")
    print("|---|---|---|---|---|---|")
    for name in get_all_rqs():
        human = human_pending_of(name)
        human_col = f"残り {len(human)} 件" if human else "-"
        done = completed_steps(name)
        has_tasks = main_has_tasks(name)
        if has_tasks:
            design_col = "完了"
        elif "Q7-2" in done:
            design_col = "完了（未マージ）"
        elif done or main_has_file(name, "spec.md"):
            design_col = "作業中"
        else:
            design_col = "未着手"
        if executed(name):
            execute_col = "完了"
        elif any(s in done for s in EXECUTE_STEPS):
            execute_col = "作業中"
        elif has_tasks and CHECKED_RE.search(main_tasks_text(name)):
            execute_col = f"作業中（残り {len(split_unchecked(main_tasks_text(name))[0])} 件）"
        elif "Q7-2" in done:
            execute_col = "未着手"
        else:
            execute_col = "-"
        if not done and not worktree_of(name).is_dir() and pending_dependencies(name):
            design_col = "未着手（ほかの RQ の完了待ち）"
        wt_col = f"あり（次: {next_step(name, 'all')}）" if worktree_of(name).is_dir() else "-"
        print(f"| {name} | {question_status(name) or '-'} | {design_col} | {execute_col} | {wt_col} | {human_col} |")


def cmd_human_tasks(args: list[str]) -> None:
    """残っている人のタスクを、RQ ごとに表示する。"""
    positional, _, _ = parse_args(args)
    names = [resolve_rq(positional)] if positional else get_all_rqs()
    for name in names:
        human = human_pending_of(name)
        if human:
            print(f"{name}:")
            for line in human:
                print(f"  {line}")


def cmd_sync_status(args: list[str]) -> None:
    """main にマージ済みの RQ の状態欄を、main の tasks.md に合わせる（人のタスクを片付けた後に使う）。"""
    positional, _, _ = parse_args(args)
    name = resolve_rq(positional)
    if worktree_of(name).is_dir():
        raise HelperError(f"{name} の worktree があります。worktree の作業は checkpoint と finish で進めてください。")
    if not executed(name):
        raise HelperError(f"{name} は実行まで {MAIN_BRANCH} にマージされていません。")
    current = git_out(["rev-parse", "--abbrev-ref", "HEAD"])
    if current != MAIN_BRANCH:
        raise HelperError(f"{REPO_ROOT} のブランチが {current} です。{MAIN_BRANCH} で実行してください。")
    tasks_file = REPO_ROOT / study_rel(name, "tasks.md")
    status = status_after_execute(tasks_file)
    # 実行後の状態（完了 / 人の作業待ち）どうしでだけ動かし、それ以前の状態を飛び越えない。
    changed = update_question_status(REPO_ROOT, name, status, only_from=FINISHED_STATUSES)
    for path in changed:
        info(f"==> 状態を更新しました: {path}（コミットはしていません）")
    print(f"RQ_STATUS: {status}")
    human = unchecked_tasks(tasks_file)[1]
    if human:
        print(f"HUMAN_TASKS_PENDING: {len(human)}")
        for line in human:
            print(f"  {line}")


def cmd_next(args: list[str]) -> None:
    _, phase, _ = parse_args(args)
    phase = require_phase(phase)
    skip: set[str] = set()
    for i, arg in enumerate(args):
        if arg == "--skip" and i + 1 < len(args):
            skip.update(resolve_rq(n) for n in args[i + 1].split(",") if n)
        elif arg.startswith("--skip="):
            skip.update(resolve_rq(n) for n in arg[len("--skip="):].split(",") if n)
    # 統合報告は、ほかのすべての RQ が終わるまで候補にしない。
    rqs = [r for r in get_all_rqs() if r not in skip and not pending_dependencies(r)]

    # 途中のまま残っている worktree を最優先にする。
    for name in rqs:
        if not worktree_of(name).is_dir():
            continue
        done = completed_steps(name)
        if (phase == "design" and "Q8" not in done) or (phase == "execute" and "Q7-2" in done) or phase == "all":
            print(name)
            return

    for name in rqs:
        has_tasks = main_has_tasks(name)
        if phase == "design" and not has_tasks:
            print(name)
            return
        if phase == "execute" and has_tasks and not executed(name):
            print(name)
            return
        if phase == "all" and (not has_tasks or not executed(name)):
            print(name)
            return
    print("")


def cmd_list(_: list[str]) -> None:
    for name in get_all_rqs():
        print(name)


def cmd_resolve(args: list[str]) -> None:
    print(resolve_rq(args[0] if args else None))


USAGE = f"""Usage: worktree_helper.py <command> [arguments]

Commands:
  ensure <rq> --phase design|execute|all
        Q1 準備。worktree があれば再利用し、なければ {MAIN_BRANCH} から作る。進捗と次のステップを表示する
  state <rq> --phase design|execute|all
        変更せずに進捗と次のステップを表示する
  checkpoint <rq> <step> <subject>
        worktree の変更をすべてコミットし、trailer "Researchkit-Step: <step>" と "Researchkit-Question: <rq>" で
        完了を記録する（変更がなくても空コミットで記録）
  finish <rq> --phase design|execute|all [--allow-unchecked] [--commit-leftovers] [--switch]
        Q13 片付け。最終ステップの完了を確認し、{QUESTIONS_DIR}/<rq>.md の状態欄を更新して、
        {MAIN_BRANCH} に --no-ff でマージし、worktree とブランチを削除する。worktree の外で実行する。
        execute / all では tasks.md に未完了があると止まる（--allow-unchecked で続行）。
        未完了が {HUMAN_MARKER} のタスクだけなら止めずにマージし、HUMAN_TASKS_PENDING で残りを表示する。
        どのステップにも含まれない変更があると止まる（--commit-leftovers で続行）。
        worktree の {DATA_DIR}/large/ の無視対象のファイルは、メインの作業ツリーに写してから消す（KEPT_LARGE_DATA）。
        メインの作業ツリーが {MAIN_BRANCH} 以外にいると止まる（--switch で切り替えて続行）
  abort <rq> [--yes]
        worktree とブランチを破棄する。--yes がなければ対象を表示するだけ
  list
        全 RQ 名を着手順（spec_order.md の並び、その後に番号順。999 は最後）で表示する
  status
        全 RQ の状態欄・設計・実行・worktree の状況と、残っている人のタスクの件数を表示する
  human-tasks [<rq>]
        残っている {HUMAN_MARKER} のタスクを表示する（worktree があればその tasks.md、なければ {MAIN_BRANCH} のもの）
  sync-status <rq>
        {MAIN_BRANCH} にマージ済みの RQ の状態欄を tasks.md に合わせる（完了 / 人の作業待ち）。
        人のタスクを片付けた後に {MAIN_BRANCH} で実行する。変更はコミットしない
  next --phase design|execute|all [--skip <rq,...>]
        次に着手すべき RQ を表示する（途中の worktree を優先。999 はほかがすべて終わるまで出さない）
  resolve <query>
        番号やスラッグから RQ 名を決める

Steps: {' '.join(ALL_STEPS)}（Q1 は ensure、Q13 は finish）
Exit codes: 0 = 成功, 1 = エラー, 3 = 前提条件を満たさない（PRECONDITION: <code> を stderr に出力）
Environment: RESEARCHKIT_MAIN_BRANCH（マージ先のブランチ名。既定値 main）
             CLAUDE_CODE_REMOTE=true（Claude Code のクラウドセッション。RESEARCHKIT_MAIN_BRANCH がなければ、
             メインの作業ツリーの今のブランチをマージ先にし、finish の後に origin へ push する）"""

COMMANDS = {
    "ensure": cmd_ensure,
    "state": cmd_state,
    "checkpoint": cmd_checkpoint,
    "finish": cmd_finish,
    "merge": cmd_finish,
    "abort": cmd_abort,
    "list": cmd_list,
    "status": cmd_status,
    "human-tasks": cmd_human_tasks,
    "sync-status": cmd_sync_status,
    "next": cmd_next,
    "resolve": cmd_resolve,
}


def main(argv: list[str]) -> int:
    global REPO_ROOT, WORKTREES_DIR, MAIN_BRANCH, QUESTIONS_DIR, STUDIES_DIR, DATA_DIR
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    action = argv[0] if argv else "help"
    if action in ("help", "-h", "--help"):
        print(USAGE)
        return 0
    command = COMMANDS.get(action)
    try:
        if command is None:
            raise HelperError(f"不明なコマンド '{action}' です。'worktree_helper.py help' で使い方を確認してください。")
        REPO_ROOT = find_repo_root()
        WORKTREES_DIR = REPO_ROOT / ".worktrees"
        paths = read_config_paths(REPO_ROOT)
        QUESTIONS_DIR = paths.get("questions") or "docs/questions"
        STUDIES_DIR = paths.get("studies") or "studies"
        DATA_DIR = paths.get("data") or "data"
        MAIN_BRANCH = resolve_main_branch()
        if not git_ok(["rev-parse", "--verify", "-q", f"refs/heads/{MAIN_BRANCH}"]):
            raise HelperError(
                f"ブランチ {MAIN_BRANCH} がありません。既定のブランチが別の名前なら、"
                "環境変数 RESEARCHKIT_MAIN_BRANCH にその名前を指定してください。")
        command(argv[1:])
    except Precondition as stop:
        print(f"PRECONDITION: {stop.code}", file=sys.stderr)
        print(str(stop), file=sys.stderr)
        return 3
    except HelperError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
