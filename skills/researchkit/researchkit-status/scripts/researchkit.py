#!/usr/bin/env python3
"""researchkit.py - researchkit の進捗確認・引き継ぎ書・環境の診断・Web 検索の予算・出典 ID

使い方:
  python3 researchkit.py [--root <dir>] init [--config-only] [--title T]
  python3 researchkit.py [--root <dir>] config get <key.path>
  python3 researchkit.py [--root <dir>] bootstrap
  python3 researchkit.py [--root <dir>] status
  python3 researchkit.py [--root <dir>] handover [--note <text>]
  python3 researchkit.py [--root <dir>] doctor
  python3 researchkit.py [--root <dir>] pitfall <text>
  python3 researchkit.py [--root <dir>] budget [--step <STEP> | --need <N>]
  python3 researchkit.py [--root <dir>] hooks install
  python3 researchkit.py [--root <dir>] sources next <NNN> [--count <k>]
  python3 researchkit.py [--root <dir>] sources list [--grade A,B] [--rq <NNN>] [--unused]
  python3 researchkit.py [--root <dir>] estat list <政府統計コード|一覧の URL> [--grep <語>]
  python3 researchkit.py [--root <dir>] estat get <statInfId> --kind <0|1|2|4> --out <保存先>
  python3 researchkit.py [--root <dir>] data add <file> --source <ID> --url <URL> --desc <内容> --rq <NNN> [--license <規約>] [--method <取得の方法>]

- 調査全体の工程（researchkit-bootstrap の R1〜R12）の進捗は、コミットの trailer "Researchkit-Bootstrap: R<n>" から判定する。
- RQ の工程（Q1〜Q13）の進捗は、researchkit-worktree の worktree_helper.py に任せる。
- 引き継ぎ書は docs/handover/CURRENT_STATE.md の自動の節と、docs/handover/sessions/<YYYYMMDD-HHMM>.md に書く。コミットはしない。
- Web 検索の回数は、count_search.py（Claude Code のフック）が .researchkit/usage/ に記録したものを読む。
終了コード: 0 成功、1 エラー、3 前提条件を満たさない、4 budget の STOP。
macOS / Linux / Windows で動くように、標準ライブラリだけで書く（Python 3.9 以上）。
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estat  # noqa: E402
import rklib  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL_DIR / "templates"
SKILLS_ROOT = Path(__file__).resolve().parents[2]
WORKTREE_HELPER = SKILLS_ROOT / "researchkit-worktree" / "scripts" / "worktree_helper.py"

BOOTSTRAP_STEPS = [f"R{i}" for i in range(1, 13)]
BOOTSTRAP_TRAILER = "Researchkit-Bootstrap"
BOOTSTRAP_TRAILER_RE = re.compile(r"^%s:[ \t]*(R\d+)[ \t]*$" % BOOTSTRAP_TRAILER, re.MULTILINE)
AUTO_START = "<!-- researchkit:auto:start -->"
AUTO_END = "<!-- researchkit:auto:end -->"
STEERING = (".kiro/steering/language.md", ".kiro/steering/research.md")
AGENT_SKILL_DIRS = (".claude/skills", ".agents/skills", ".kiro/skills")
REQUIRED_SKILLS = ("researchkit-status", "researchkit-worktree")
# フックの登録先（プロジェクトのルートからの相対パス。new-researchkit-project が skills/researchkit/ を置く）
HOOK_SCRIPT = "skills/researchkit/researchkit-status/scripts/count_search.py"
EXIT_STOP = 4


class RkError(Exception):
    pass


def out(line: str = "") -> None:
    print(line)


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


# ---------------------------------------------------------------- init

def is_file_path(rel_path: str) -> bool:
    """paths の値のうち、ディレクトリではなくファイルを指すもの（method.md、憲章など）。"""
    return bool(re.search(r"\.[A-Za-z0-9]+$", rel_path))


def cmd_init(root: Path, args: argparse.Namespace) -> int:
    cfg_path = root / rklib.CONFIG_REL
    created: list[str] = []
    if not cfg_path.exists():
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rklib.TEMPLATE, cfg_path)
        created.append(rklib.CONFIG_REL)
    if args.title:
        text = cfg_path.read_text(encoding="utf-8")
        current = (rklib.parse_yaml(text) or {}).get("title")
        if not current:
            cfg_path.write_text(rklib.set_top_scalar(text, "title", args.title), encoding="utf-8")
            if rklib.CONFIG_REL not in created:
                created.append(f"{rklib.CONFIG_REL}（title を反映）")
        elif str(current) != args.title:
            print(f"SKIPPED: title はすでに '{current}' です（上書きしない）", file=sys.stderr)
    cfg = rklib.load_config(root)
    if not args.config_only:
        for key, rel_path in cfg["paths"].items():
            if not rel_path or is_file_path(str(rel_path)):
                continue
            d = root / str(rel_path)
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                created.append(f"{rel_path}/")
            if d.is_dir() and not any(d.iterdir()):
                (d / ".gitkeep").touch()
        handover = rklib.pth(root, cfg, "handover")
        pit = handover / "PITFALLS.md"
        if not pit.exists():
            handover.mkdir(parents=True, exist_ok=True)
            shutil.copy2(TEMPLATES / "PITFALLS.md", pit)
            gk = handover / ".gitkeep"
            if gk.exists():
                gk.unlink()
            created.append(rel(root, pit))
    for c in created:
        out(f"CREATED: {c}")
    if not created:
        out("CREATED: （なし。すべてそろっている）")
    return 0


# ---------------------------------------------------------------- config

def format_value(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        return ",".join(format_value(v) for v in value)
    if isinstance(value, dict):
        return ",".join(f"{k}={format_value(v)}" for k, v in value.items())
    return str(value)


def cmd_config(root: Path, args: argparse.Namespace) -> int:
    if args.action != "get" or not args.key:
        raise RkError("使い方: config get <key.path>")
    value = rklib.config_get(rklib.load_config(root), args.key)
    if value is None or value == "" or value == [] or value == {}:
        out("")
        return 1
    out(format_value(value))
    return 0


# ---------------------------------------------------------------- bootstrap

def bootstrap_done(root: Path) -> list[str]:
    if not rklib.is_git_repo(root):
        return []
    # 本文全体から探す。git の trailer の解釈は最後の段落しか見ないため、エージェントが
    # Co-Authored-By などを別の段落で足すと、%(trailers) では記録を読めなくなる。
    proc = rklib.git(root, ["log", "--all", "--format=%B"], check=False)
    if proc.returncode != 0:  # コミットがまだない
        return []
    found = set(BOOTSTRAP_TRAILER_RE.findall(proc.stdout))
    return [s for s in BOOTSTRAP_STEPS if s in found]


def bootstrap_state(root: Path) -> tuple[list[str], str]:
    done = bootstrap_done(root)
    for step in BOOTSTRAP_STEPS:
        if step not in done:
            return done, step
    return done, "DONE"


def cmd_bootstrap(root: Path, args: argparse.Namespace) -> int:
    done, nxt = bootstrap_state(root)
    out(f"COMPLETED_STEPS: {' '.join(done)}")
    out(f"NEXT_STEP: {nxt}")
    return 0


# ---------------------------------------------------------------- status

def run_helper(root: Path, *helper_args: str) -> tuple[int, str]:
    if not WORKTREE_HELPER.exists():
        return 1, f"（{WORKTREE_HELPER} がありません）"
    if not rklib.is_git_repo(root):
        return 1, "（Git リポジトリではありません）"
    proc = subprocess.run([sys.executable, str(WORKTREE_HELPER), *helper_args], cwd=str(root),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = (proc.stdout or "").strip()
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        text = (text + "\n" if text else "") + f"（worktree_helper.py {' '.join(helper_args)} が失敗しました: {err}）"
    return proc.returncode, text


def last_handover(root: Path, cfg: dict) -> str:
    path = rklib.pth(root, cfg, "handover") / "CURRENT_STATE.md"
    if not path.exists():
        return "なし"
    if rklib.is_git_repo(root):
        proc = rklib.git(root, ["log", "-1", "--format=%cs %h", "--", rel(root, path)], check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return f"{proc.stdout.strip()}（コミット）"
    return dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M") + "（ファイルの更新日時）"


def sources_line(root: Path, cfg: dict) -> str:
    sources = rklib.load_sources(root, cfg)
    if not sources:
        return "0 件"
    grades = [str(g) for g in rklib.as_list(rklib.config_get(cfg, "sources.grades"))] or ["A", "B", "C", "D"]
    counts = {g: 0 for g in grades}
    other = 0
    for s in sources:
        g = str(s.get("grade") or "").strip()
        if g in counts:
            counts[g] += 1
        else:
            other += 1
    parts = [f"{g} {n}" for g, n in counts.items()]
    if other:
        parts.append(f"等級なし・不明 {other}")
    return f"{len(sources)} 件（{' / '.join(parts)}）"


def budget_line(root: Path, cfg: dict) -> str:
    u = current_usage(root)
    if u is None:
        return "数えていない（UNMETERED）"
    limit = int(rklib.config_get(cfg, "session.web_search_limit") or 200)
    return f"このセッション WebSearch {int(u.get('WebSearch', 0))} / 上限 {limit}（WebFetch {u.get('WebFetch', 0)}）"


def cmd_status(root: Path, args: argparse.Namespace) -> int:
    cfg = rklib.load_config(root)
    done, nxt = bootstrap_state(root)
    out(f"# researchkit の進捗: {cfg.get('title') or root.name}")
    out()
    out("## 調査全体の工程（researchkit-bootstrap）")
    out()
    out(f"- 完了: {' '.join(done) or 'なし'}")
    out(f"- 次: {nxt}")
    out()
    out("## RQ の工程")
    out()
    _, text = run_helper(root, "status")
    out(text or "（RQ なし）")
    out()
    out("## 出典")
    out()
    out(f"- 出典台帳: {sources_line(root, cfg)}")
    out()
    out("## Web 検索")
    out()
    out(f"- {budget_line(root, cfg)}")
    out()
    out("## 引き継ぎ書")
    out()
    out(f"- 最終更新: {last_handover(root, cfg)}")
    return 0


# ---------------------------------------------------------------- handover

def high_priority_decisions(root: Path, cfg: dict) -> list[str]:
    files = [root / "docs" / "auto-decisions.md"]
    files += sorted(rklib.pth(root, cfg, "studies").glob("*/auto-decisions.md"))
    found: list[str] = []
    for f in files:
        if not f.exists():
            continue
        heading = ""
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
            elif re.search(r"優先度[^|\n]*?[:：|]\s*\**高", line) or re.search(r"\|\s*高\s*\|", line):
                label = heading or line.strip()
                entry = f"{rel(root, f)}: {label}"
                if entry not in found:
                    found.append(entry)
    return found


def open_clarifications(root: Path, cfg: dict, limit: int = 20) -> list[str]:
    """[NEEDS CLARIFICATION の残っている箇所（docs/ と studies/ の Markdown）。"""
    bases = [root / "docs", rklib.pth(root, cfg, "studies")]
    handover = rklib.pth(root, cfg, "handover").resolve()
    found: list[str] = []
    for base in bases:
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.md")):
            if handover in p.resolve().parents:
                continue
            try:
                lines = p.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for no, line in enumerate(lines, 1):
                if "[NEEDS CLARIFICATION" in line:
                    found.append(f"`{rel(root, p)}:{no}` {line.strip()[:100]}")
                    if len(found) >= limit:
                        return found
    return found


def commits_since_handover(root: Path, cfg: dict) -> list[str]:
    if not rklib.is_git_repo(root):
        return []
    path = rel(root, rklib.pth(root, cfg, "handover") / "CURRENT_STATE.md")
    last = rklib.git(root, ["log", "-1", "--format=%H", "--", path], check=False).stdout.strip()
    rng = [f"{last}..HEAD"] if last else ["-n", "15"]
    proc = rklib.git(root, ["log", "--format=%h %cs %s", "-n", "30", *rng], check=False)
    return [l for l in proc.stdout.splitlines() if l.strip()] if proc.returncode == 0 else []


def build_state(root: Path, cfg: dict, now: dt.datetime) -> str:
    lines: list[str] = []
    branch, head = "-", "-"
    if rklib.is_git_repo(root):
        branch = rklib.git(root, ["rev-parse", "--abbrev-ref", "HEAD"], check=False).stdout.strip() or "-"
        head = rklib.git(root, ["rev-parse", "--short", "HEAD"], check=False).stdout.strip() or "-"
    done, nxt = bootstrap_state(root)
    lines += [f"- **更新**: {now.strftime('%Y-%m-%d %H:%M')}（ブランチ `{branch}`、`{head}`）",
              f"- **調査全体の工程**: 完了 {' '.join(done) or 'なし'} / 次 {nxt}",
              f"- **出典台帳**: {sources_line(root, cfg)}",
              f"- **Web 検索**: {budget_line(root, cfg)}",
              "", "### RQ", ""]
    _, status = run_helper(root, "status")
    lines += [status or "（RQ なし）", "", "### 残っている人のタスク（[人]）", ""]
    _, human = run_helper(root, "human-tasks")
    lines += [human or "（なし）", "", "### 見直しの優先度が「高」の自動判断", ""]
    decisions = high_priority_decisions(root, cfg)
    lines += [f"- {d}" for d in decisions] or ["（なし）"]
    lines += ["", "### 未決事項（[NEEDS CLARIFICATION]）", ""]
    todo = open_clarifications(root, cfg)
    lines += [f"- {t}" for t in todo] or ["（なし）"]
    lines += ["", "### 前回の引き継ぎ以降のコミット", ""]
    commits = commits_since_handover(root, cfg)
    lines += [f"- {c}" for c in commits] or ["（なし）"]
    return "\n".join(lines)


def cmd_handover(root: Path, args: argparse.Namespace) -> int:
    cfg = rklib.load_config(root)
    now = dt.datetime.now()
    state = build_state(root, cfg, now)
    handover = rklib.pth(root, cfg, "handover")
    handover.mkdir(parents=True, exist_ok=True)
    current = handover / "CURRENT_STATE.md"
    text = (current.read_text(encoding="utf-8") if current.exists()
            else (TEMPLATES / "CURRENT_STATE.md").read_text(encoding="utf-8"))
    block = f"{AUTO_START}\n{state}\n{AUTO_END}"
    # 印は単独の行だけを数える（本文の説明に印の文字列が出てきても取り違えない）
    start = re.search(rf"^{re.escape(AUTO_START)}[ \t]*$", text, re.MULTILINE)
    end = re.search(rf"^{re.escape(AUTO_END)}[ \t]*$", text, re.MULTILINE)
    if start and end and start.start() < end.start():
        text = text[: start.start()] + block + text[end.end():]
    else:
        text = text.rstrip("\n") + "\n\n## 自動で更新する節\n\n" + block + "\n"
    with open(current, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    if not (handover / "PITFALLS.md").exists():
        shutil.copy2(TEMPLATES / "PITFALLS.md", handover / "PITFALLS.md")
    sessions = handover / "sessions"
    sessions.mkdir(exist_ok=True)
    stamp = now.strftime("%Y%m%d-%H%M")
    session = sessions / f"{stamp}.md"
    n = 2
    while session.exists():
        session = sessions / f"{stamp}-{n}.md"
        n += 1
    tmpl = (TEMPLATES / "session.md").read_text(encoding="utf-8")
    with open(session, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(tmpl.replace("{timestamp}", now.strftime("%Y-%m-%d %H:%M"))
                     .replace("{note}", args.note or "（なし）").replace("{state}", state))
    gk = handover / ".gitkeep"
    if gk.exists():
        gk.unlink()
    out(f"UPDATED: {rel(root, current)}")
    out(f"CREATED: {rel(root, session)}")
    return 0


# ---------------------------------------------------------------- pitfall

def cmd_pitfall(root: Path, args: argparse.Namespace) -> int:
    body = " ".join(args.text).strip()
    if not body:
        raise RkError("使い方: pitfall <内容>")
    cfg = rklib.load_config(root)
    handover = rklib.pth(root, cfg, "handover")
    path = handover / "PITFALLS.md"
    if not path.exists():
        handover.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATES / "PITFALLS.md", path)
    text = path.read_text(encoding="utf-8")
    first, _, rest = body.partition("\n")
    entry = f"## {dt.date.today().isoformat()} {first.strip()}\n\n"
    if rest.strip():
        entry += rest.strip() + "\n\n"
    # 最初の項目（## の見出し）か、記入例のコメントの前に入れる。どちらもなければ末尾に足す
    m = re.search(r"^(## |<!--)", text, re.MULTILINE)
    if m:
        text = text[: m.start()] + entry + text[m.start():]
    else:
        text = text.rstrip("\n") + "\n\n" + entry
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.rstrip("\n") + "\n")
    out(f"ADDED: {rel(root, path)}")
    return 0


# ---------------------------------------------------------------- doctor

def first_program(command: str) -> str:
    for t in command.strip().split():
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", t):  # 先頭の環境変数の代入
            continue
        return t.strip("'\"")
    return ""


def gitignore_lines(root: Path) -> list[str]:
    gi = root / ".gitignore"
    if not gi.exists():
        return []
    return [l.strip() for l in gi.read_text(encoding="utf-8").splitlines()]


def cmd_doctor(root: Path, args: argparse.Namespace) -> int:
    results: list[tuple[str, str]] = []
    results.append(("OK", "Git リポジトリ") if rklib.is_git_repo(root)
                   else ("ERROR", "Git リポジトリではありません（git init してから始める）"))
    cfg_path = root / rklib.CONFIG_REL
    cfg = None
    if not cfg_path.exists():
        results.append(("ERROR", f"{rklib.CONFIG_REL} がありません（researchkit.py init で作る）"))
    else:
        try:
            cfg = rklib.load_config(root)
            results.append(("OK", f"{rklib.CONFIG_REL} を解釈できる"))
        except rklib.YamlError as e:
            results.append(("ERROR", f"{rklib.CONFIG_REL} を解釈できません: {e}"))
    if cfg is not None:
        for key in ("analysis", "test"):
            cmd = rklib.config_get(cfg, f"commands.{key}")
            if not cmd:
                if key == "analysis":
                    results.append(("WARN", "commands.analysis が空です（researchkit-method（R7）で決める）"))
                continue
            prog = first_program(str(cmd))
            if prog and (shutil.which(prog) or (root / prog).exists()):
                results.append(("OK", f"commands.{key}: {prog} がある"))
            else:
                results.append(("WARN", f"commands.{key}: '{prog}' が PATH にありません"))
        levels = rklib.as_list(rklib.config_get(cfg, "confidence.levels"))
        results.append(("OK", f"confidence.levels: {', '.join(map(str, levels))}") if levels
                       else ("ERROR", "confidence.levels が空です"))
        grades = [str(g) for g in rklib.as_list(rklib.config_get(cfg, "sources.grades"))]
        min_grade = str(rklib.config_get(cfg, "sources.min_grade") or "")
        if not grades:
            results.append(("ERROR", "sources.grades が空です"))
        elif min_grade not in grades:
            results.append(("ERROR", f"sources.min_grade '{min_grade}' が sources.grades にありません"))
        elif min_grade == grades[-1]:
            results.append(("WARN", f"sources.min_grade が最後の等級（未確認）'{min_grade}' です"))
        else:
            results.append(("OK", f"sources: 等級 {', '.join(grades)}、根拠に使える最低の等級 {min_grade}"))
    for base in AGENT_SKILL_DIRS:
        d = root / base
        if not d.is_dir():
            results.append(("ERROR", f"{base}/ がありません"))
            continue
        broken = [p.name for p in d.iterdir() if p.is_symlink() and not p.exists()]
        names = {p.name for p in d.iterdir()}
        if broken:
            results.append(("ERROR", f"{base}/ のリンクが切れています: {', '.join(sorted(broken))}"))
        missing = [s for s in REQUIRED_SKILLS if s not in names]
        if missing:
            results.append(("ERROR", f"{base}/ に {', '.join(missing)} がありません"))
        if not broken and not missing:
            results.append(("OK", f"{base}/ のスキル {len(names)} 件"))
    for rel_path in STEERING:
        if not (root / rel_path).exists():
            results.append(("ERROR", f"{rel_path} がありません"))
    for name in ("CLAUDE.md", "AGENTS.md", "GEMINI.md"):
        p = root / name
        if not p.exists():
            results.append(("WARN", f"{name} がありません"))
            continue
        body = p.read_text(encoding="utf-8")
        lacking = [s for s in STEERING if s not in body]
        if lacking:
            results.append(("WARN", f"{name} が {', '.join(lacking)} を参照していません"))
        else:
            results.append(("OK", f"{name} が steering を参照している"))
    settings = root / ".claude" / "settings.json"
    if settings.exists() and "count_search.py" in settings.read_text(encoding="utf-8"):
        results.append(("OK", "Web 検索の回数を数えるフックが .claude/settings.json にある"))
    else:
        results.append(("WARN", "Web 検索の回数を数えるフックがありません（researchkit.py hooks install で登録する）"))
    ignored = gitignore_lines(root)
    for line, why in ((".worktrees/", "RQ の worktree を作れない"),
                      (".researchkit/usage/", "検索の回数の記録がコミットに混ざる")):
        if line not in ignored:
            results.append(("WARN", f".gitignore に {line} がありません（{why}）"))
    for level, msg in results:
        out(f"{level}: {msg}")
    errors = sum(1 for level, _ in results if level == "ERROR")
    warns = sum(1 for level, _ in results if level == "WARN")
    out(f"SUMMARY: ERROR {errors} / WARN {warns}")
    return 1 if errors else 0


# ---------------------------------------------------------------- budget / hooks

def current_usage(root: Path) -> dict | None:
    """フックが記録した、今のセッションの回数。記録がなければ None（数えられない環境）。

    フックはメインの作業ツリーに記録するので、worktree の中から呼ばれたときはメインの作業ツリーも見る。
    """
    candidates = []
    for base in dict.fromkeys([root, rklib.main_worktree(root)]):
        cur = base / rklib.USAGE_REL / "current"
        if cur.exists():
            candidates.append(cur)
    if not candidates:
        return None
    cur = max(candidates, key=lambda p: p.stat().st_mtime)
    sid = cur.read_text(encoding="utf-8").strip()
    live = current_session_id()
    if live and live != sid:
        for c in candidates:
            if (c.parent / f"{live}.json").exists():
                cur, sid = c, live
                break
    path = cur.parent / f"{sid}.json"
    if not path.exists():
        return {"session_id": sid, "WebSearch": 0, "WebFetch": 0}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def current_session_id() -> str:
    """今のセッションの ID（Claude Code が Bash に渡す環境変数）。分からなければ空。"""
    return (os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID") or "").strip()


def cmd_budget(root: Path, args: argparse.Namespace) -> int:
    """次の工程に、今のセッションの Web 検索の残りが足りるかを判定する。

    終了コード: 0 = OK（続けてよい）または UNMETERED（数えられない環境）、4 = STOP（工程の区切りで止まる）
    """
    cfg = rklib.load_config(root)
    sc = cfg.get("session") or {}
    limit = int(sc.get("web_search_limit") or 200)
    reserve = int(sc.get("reserve") or 0)
    est = sc.get("estimates") or {}
    if args.need is not None:
        need = args.need
    elif args.step:
        if args.step not in est:
            raise RkError(f"STEP '{args.step}' は session.estimates にありません（有効値: {', '.join(est)}）。")
        need = int(est.get(args.step) or 0)
    else:
        need = 0
    unmetered = sc.get("rqs_unmetered", 1)
    u = current_usage(root)
    out(f"STEP: {args.step or '-'}")
    out(f"NEED: {need}")
    out(f"LIMIT: {limit}（reserve {reserve}）")
    if u is None:
        settings = root / ".claude" / "settings.json"
        main_settings = rklib.main_worktree(root) / ".claude" / "settings.json"
        registered = any(s.exists() and "count_search.py" in s.read_text(encoding="utf-8")
                         for s in (settings, main_settings))
        out("USED: -")
        out("REMAINING: -")
        out("VERDICT: UNMETERED")
        if registered:
            out("NOTE: フックは登録済みだが、まだ記録がない（登録した後に Claude Code を起動し直していない）。"
                f"このセッションは、回数を数えられない環境の規則に従う（1 セッション {unmetered} 件の RQ まで）")
        else:
            out("NOTE: 検索の回数を数えるフックがない（Claude Code 以外、または researchkit.py hooks install の前）。"
                f"回数を数えられない環境の規則に従う（1 セッション {unmetered} 件の RQ まで）")
        return 0
    live = current_session_id()
    if live and u.get("session_id") != live:
        # 記録はあるが、今のセッションのものではない（プロジェクトの外でセッションを始めた、フックが読まれていない）
        out(f"SESSION: {live}（記録なし）")
        out(f"RECORDED_SESSION: {u.get('session_id')}（更新 {u.get('updated', '-')}）")
        out("USED: -")
        out("REMAINING: -")
        out("VERDICT: UNMETERED")
        out("NOTE: 記録は別のセッションのもので、このセッションの回数は数えられていない。プロジェクトのルートで Claude Code を"
            f"起動し直すと数えられる。それまでは、回数を数えられない環境の規則に従う（1 セッション {unmetered} 件の RQ まで）。"
            "使った回数を手で数え、引き継ぎ書に書く")
        return 0
    used = int(u.get("WebSearch", 0))
    remaining = limit - reserve - used
    out(f"SESSION: {u.get('session_id')}")
    out(f"USED: WebSearch {used} / WebFetch {u.get('WebFetch', 0)}")
    out(f"REMAINING: {remaining}")
    if need > remaining:
        out("VERDICT: STOP")
        out("NOTE: 工程の区切りで止まり、新しいセッションで同じスキルを同じ引数で実行して再開する")
        return EXIT_STOP
    out("VERDICT: OK")
    return 0


def cmd_hooks(root: Path, args: argparse.Namespace) -> int:
    """プロジェクトの .claude/settings.json に、検索の回数を数えるフックを登録する（既存の設定は残す）。"""
    path = root / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conf = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except json.JSONDecodeError:
        raise RkError(f"{path} が JSON として読めません。手で直してから、もう一度実行してください。")
    if not isinstance(conf, dict):
        raise RkError(f"{path} の最上位がオブジェクトではありません。")
    command = f'python3 "$CLAUDE_PROJECT_DIR/{HOOK_SCRIPT}"'
    hooks = conf.setdefault("hooks", {})
    added = []
    for event, matcher in (("SessionStart", None), ("PostToolUse", "WebSearch|WebFetch")):
        entries = hooks.setdefault(event, [])
        if any(h.get("command") == command for e in entries for h in e.get("hooks", [])):
            continue
        entry: dict = {"hooks": [{"type": "command", "command": command}]}
        if matcher:
            entry = {"matcher": matcher, **entry}
        entries.append(entry)
        added.append(event)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(conf, ensure_ascii=False, indent=2) + "\n")
    gi = root / ".gitignore"
    line = ".researchkit/usage/"
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if line not in text.splitlines():
        with open(gi, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text.rstrip("\n") + ("\n\n" if text.strip() else "")
                         + "# researchkit の検索回数の記録（セッションごと）\n" + line + "\n")
    out(f"HOOKS: {rel(root, path)}（追加: {', '.join(added) or 'なし（登録済み）'}）")
    out("NOTE: 次に Claude Code を起動したセッションから数え始める")
    return 0


# ---------------------------------------------------------------- sources

def used_numbers(root: Path, cfg: dict, rq: str) -> set[int]:
    """RQ の番号 rq の出典の連番のうち、作業ツリーと main の sources/ にあるもの。"""
    nums: set[int] = set()
    base = rklib.pth(root, cfg, "sources")
    if base.is_dir():
        for p in base.glob("*.md"):
            m = rklib.SOURCE_FILE_RE.match(p.name)
            if m and m.group(1) == rq:
                nums.add(int(m.group(2)))
    if rklib.is_git_repo(root):
        branch = rklib.main_branch()
        sources_rel = str(cfg["paths"].get("sources") or "sources").strip("/")
        proc = rklib.git(root, ["ls-tree", "--name-only", f"{branch}:{sources_rel}"], check=False)
        if proc.returncode == 0:
            for name in proc.stdout.splitlines():
                m = rklib.SOURCE_FILE_RE.match(Path(name.strip()).name)
                if m and m.group(1) == rq:
                    nums.add(int(m.group(2)))
    return nums


def cmd_sources_next(root: Path, args: argparse.Namespace) -> int:
    if not args.rq:
        raise RkError("使い方: sources next <NNN> [--count <k>]")
    try:
        rq = rklib.normalize_rq_number(args.rq)
    except ValueError as e:
        raise RkError(str(e))
    if args.count < 1:
        raise RkError("--count は 1 以上にしてください。")
    cfg = rklib.load_config(root)
    start = max(used_numbers(root, cfg, rq), default=0) + 1
    if start + args.count - 1 > 9999:
        raise RkError(f"S{rq}- の連番が 9999 を超えます。")
    for n in range(start, start + args.count):
        out(f"S{rq}-{n:04d}")
    return 0


def referenced_ids(root: Path, cfg: dict) -> set[str]:
    """studies/ と reports/ の Markdown から参照されている出典 ID。"""
    found: set[str] = set()
    for key in ("studies", "reports"):
        base = rklib.pth(root, cfg, key)
        if not base.is_dir():
            continue
        for p in base.rglob("*.md"):
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            found.update(f"S{a}-{b}" for a, b in rklib.SOURCE_ID_RE.findall(text))
    return found


def cmd_sources_list(root: Path, args: argparse.Namespace) -> int:
    cfg = rklib.load_config(root)
    sources = rklib.load_sources(root, cfg)
    grades = {g.strip() for g in (args.grade or "").split(",") if g.strip()}
    rq = None
    if args.rq:
        try:
            rq = rklib.normalize_rq_number(args.rq)
        except ValueError as e:
            raise RkError(str(e))
    refs = referenced_ids(root, cfg) if args.unused else set()
    rows = []
    for s in sources:
        sid = str(s.get("id") or "")
        used_in = [str(u) for u in rklib.as_list(s.get("used_in"))]
        if grades and str(s.get("grade") or "") not in grades:
            continue
        if rq is not None:
            in_rq = sid.startswith(f"S{rq}-") or any(u == rq or u.startswith(f"{rq}-") for u in used_in)
            if not in_rq:
                continue
        if args.unused and sid in refs:
            continue
        title = str(s.get("title") or "").replace("|", "／")
        rows.append(f"| {sid} | {s.get('grade') or '-'} | {s.get('type') or '-'} | {title or '-'} "
                    f"| {', '.join(used_in) or '-'} |")
    out("| ID | 等級 | 種類 | 題名 | 使った RQ |")
    out("|---|---|---|---|---|")
    for r in rows:
        out(r)
    out(f"TOTAL: {len(rows)}")
    return 0


def cmd_sources(root: Path, args: argparse.Namespace) -> int:
    if args.action == "next":
        return cmd_sources_next(root, args)
    return cmd_sources_list(root, args)


# ---------------------------------------------------------------- e-Stat / データの目録

def cmd_estat(root: Path, args: argparse.Namespace) -> int:
    """e-Stat の一覧を短く表示する（list）、表を取得する（get）。結果はファイルに書き、標準出力は要点だけにする。"""
    if args.action == "list":
        if not args.target:
            raise RkError("estat list には政府統計コードか一覧の URL を指定する")
        url = estat.list_url(args.target)
        status, body, _ = estat.fetch(url)
        page = body.decode("utf-8", "replace")
        rows = estat.parse_files(page)
        out(f"URL: {url}")
        out(f"HTTP: {status}")
        if rows:
            hit = [r for r in rows if not args.grep or args.grep in r["title"] or args.grep in r["group"]]
            out(f"TABLES: {len(rows)}（表示 {len(hit)}）")
            for r in hit[: args.limit]:
                kinds = "/".join(estat.KIND_NAMES.get(k, k) for k in r["kinds"].split(",") if k)
                no = f"表{r['no']} " if r["no"] else ""
                grp = f"［{r['group']}］" if r["group"] and r["group"] != r["title"] else ""
                out(f"{r['statInfId']}\t{kinds}\t{no}{r['title']}{grp}\t{r['period']}\t{r['date']}")
            if len(hit) > args.limit:
                out(f"NOTE: ほかに {len(hit) - args.limit} 件（--grep で絞るか --limit を増やす）")
            return 0
        cls = estat.parse_classes(page)
        hit = [c for c in cls if not args.grep or args.grep in c["name"]]
        out(f"CLASSES: {len(cls)}（表示 {len(hit)}）")
        for c in hit[: args.limit]:
            cyc = f"（{c['cycle']}）" if c["cycle"] else ""
            out(f"{c['name']}{cyc}\t{c['count']}件\t{c['date']}\t{c['url']}")
        if not cls:
            out("NOTE: 表も分類も見つからない。URL を確かめる（layout=datalist を付けると表の一覧になることがある）")
        return 0
    if not (args.target and args.kind is not None and args.out):
        raise RkError("estat get には statInfId、--kind、--out を指定する")
    dest = Path(args.out)
    dest = dest if dest.is_absolute() else root / dest
    info = estat.save(args.target, str(args.kind), dest)
    for key in ("url", "http", "bytes", "format", "sha256", "path", "warning", "error"):
        if info.get(key):
            out(f"{key.upper()}: {info[key] if key != 'path' else rel(root, Path(info[key]))}")
    if info.get("error"):
        return 1
    out(f"NEXT: researchkit.py data add {rel(root, Path(info['path']))} --source <出典 ID> --url \"{info['url']}\" --desc <内容> --rq <NNN>")
    return 0


MANIFEST_HEADER = "| ファイル | 置き場所 | 出典 ID | 出所（URL・提供元） | 取得日 | 取得の方法 | ライセンス・利用規約 | SHA-256 | 大きさ | 内容 | 使った RQ |"


def manifest_path(root: Path, cfg: dict) -> Path:
    return rklib.pth(root, cfg, "data") / "manifest.md"


def cmd_data(root: Path, args: argparse.Namespace) -> int:
    """data/manifest.md の「ファイル」の表に 1 行足す（SHA-256 と大きさはファイルから求める）。"""
    cfg = rklib.load_config(root)
    path = Path(args.file)
    path = path if path.is_absolute() else root / path
    if not path.is_file():
        raise RkError(f"ファイルがない: {args.file}")
    name = rel(root, path)
    manifest = manifest_path(root, cfg)
    if not manifest.exists():
        raise RkError(f"{rel(root, manifest)} がない（researchkit-foundation の templates/manifest.md から作る）")
    text = manifest.read_text(encoding="utf-8")
    rows = rklib.read_table(manifest, require="SHA-256")
    if any(r.get("ファイル", "").strip("` ") == name for r in rows):
        raise RkError(f"{name} はすでに目録にある（行を直すときは手で直す）")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    place = "large" if "/large/" in f"/{name}" else "raw"
    max_mb = float(rklib.config_get(cfg, "data.max_file_mb") or 5)
    if place == "raw" and len(data) > max_mb * 1024 * 1024:
        out(f"WARN: {max_mb:g} MB を超える。data/large/ に置き、コミットしない（data.max_file_mb）")
    method = args.method or f'`curl -sSL -A "<ブラウザの User-Agent>" -o {name} "{args.url}"`'
    cells = [name, place, args.source, args.url, args.accessed or dt.date.today().isoformat(), method,
             args.license or "e-Stat 利用規約（政府標準利用規約 第 2.0 版準拠）。出典の記載が要る",
             digest, f"{len(data):,} bytes", args.desc, rklib.normalize_rq_number(args.rq)]
    row = "| " + " | ".join(c.replace("|", "／") for c in cells) + " |"
    lines = text.splitlines()
    header = next((i for i, l in enumerate(lines) if l.strip().startswith("|") and "SHA-256" in l), None)
    if header is None:
        raise RkError(f"{rel(root, manifest)} に「ファイル」の表（SHA-256 の列）がない。見出し: {MANIFEST_HEADER}")
    end = header + 1
    while end < len(lines) and lines[end].strip().startswith("|"):
        end += 1
    lines.insert(end, row)
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out(f"ADDED: {name}")
    out(f"SHA256: {digest}")
    out(f"BYTES: {len(data)}")
    out(f"MANIFEST: {rel(root, manifest)}（{end + 1} 行目）")
    return 0


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="researchkit.py",
                                 description="researchkit の進捗確認・引き継ぎ書・環境の診断・Web 検索の予算・出典 ID")
    ap.add_argument("--root", default=None,
                    help="プロジェクトのルート（省略時は .researchkit/config.yaml か .git を上へ探す）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help=".researchkit/config.yaml とディレクトリを作る（既存は変えない）")
    p.add_argument("--config-only", action="store_true")
    p.add_argument("--title", default="")
    p = sub.add_parser("config", help="設定の値を読む")
    p.add_argument("action", choices=["get"])
    p.add_argument("key", nargs="?")
    sub.add_parser("bootstrap", help="調査全体の工程（R1〜R12）の進捗")
    sub.add_parser("status", help="調査全体の工程・RQ・出典・引き継ぎ書の状況")
    p = sub.add_parser("handover", help="引き継ぎ書を更新する（コミットしない）")
    p.add_argument("--note", default="")
    sub.add_parser("doctor", help="設定と環境の診断")
    p = sub.add_parser("pitfall", help="PITFALLS.md の先頭に日付つきで足す")
    p.add_argument("text", nargs="+")
    p = sub.add_parser("budget", help="次の工程に Web 検索の残りが足りるかを判定する")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--step")
    g.add_argument("--need", type=int)
    p = sub.add_parser("hooks", help="Web 検索の回数を数えるフックを登録する")
    p.add_argument("action", choices=["install"])
    p = sub.add_parser("sources", help="出典 ID の払い出しと一覧")
    p.add_argument("action", choices=["next", "list"])
    p.add_argument("rq", nargs="?", help="next: RQ の番号（例: 003）")
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--grade", default="")
    p.add_argument("--rq", dest="rq_filter", default="")
    p.add_argument("--unused", action="store_true")
    p = sub.add_parser("estat", help="e-Stat の一覧を短く表示する（list）、表を取得する（get）")
    p.add_argument("action", choices=["list", "get"])
    p.add_argument("target", nargs="?", help="list: 政府統計コード（8 桁）か一覧の URL / get: statInfId")
    p.add_argument("--grep", default="", help="list: 名前・題名に含む語で絞る")
    p.add_argument("--limit", type=int, default=40, help="list: 表示する行の上限（既定 40）")
    p.add_argument("--kind", choices=["0", "1", "2", "3", "4"], help="get: fileKind（0 Excel、1 CSV、2 PDF）")
    p.add_argument("--out", help="get: 保存先（プロジェクトのルートからの相対パス。例: data/raw/xxx.csv）")
    p = sub.add_parser("data", help="データの目録（data/manifest.md）に 1 行足す")
    p.add_argument("action", choices=["add"])
    p.add_argument("file")
    p.add_argument("--source", required=True, help="出典 ID（例: S003-0003）")
    p.add_argument("--url", required=True, help="取得した URL")
    p.add_argument("--desc", required=True, help="内容（表の名前、範囲、単位）")
    p.add_argument("--rq", required=True, help="使った RQ の番号")
    p.add_argument("--license", default="", help="ライセンス・利用規約（既定: e-Stat の利用規約）")
    p.add_argument("--method", default="", help="取得の方法（既定: curl のコマンド）")
    p.add_argument("--accessed", default="", help="取得日（既定: 今日）")
    args = ap.parse_args(argv)
    if args.cmd == "sources" and args.action == "list":
        args.rq = args.rq_filter or args.rq
    root = Path(args.root).expanduser().resolve() if args.root else rklib.find_root()
    handlers = {"init": cmd_init, "config": cmd_config, "bootstrap": cmd_bootstrap, "status": cmd_status,
                "handover": cmd_handover, "doctor": cmd_doctor, "pitfall": cmd_pitfall, "budget": cmd_budget,
                "hooks": cmd_hooks, "sources": cmd_sources, "estat": cmd_estat, "data": cmd_data}
    try:
        return handlers[args.cmd](root, args)
    except (RkError, rklib.YamlError, RuntimeError, ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
