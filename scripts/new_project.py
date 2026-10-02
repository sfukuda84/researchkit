#!/usr/bin/env python3
"""new_project.py - researchkit の調査のプロジェクトを作る（既存の調査への取り込みにも使う）

使い方:
  python3 new_project.py <プロジェクトのディレクトリ> [--title <仮題>] [--question <問い>] [--link] [--adopt]
  python3 new_project.py --relink <ディレクトリ>   # 各エージェントのスキルディレクトリのリンクだけを作り直す

- 新しいディレクトリなら、scaffold の規則ファイル（CLAUDE.md、AGENTS.md、GEMINI.md、opencode.json、.gitignore、
  .kiro/steering/）とスキル（skills/researchkit/）を置き、各エージェントのスキルディレクトリ（.claude/skills/ など）
  からリンクし、git init と初回コミットを行う。
- researchkit.py init で .researchkit/config.yaml と既定のディレクトリを作り、researchkit.py hooks install で
  Web 検索の回数を数えるフック（.claude/settings.json）を入れる。
- --question: 調べたい問い（1〜数文）を docs/concept/core-question.md に書く（既にあれば変えない）。
- --adopt: 既存の調査に取り込む。既存のファイルは上書きせず、衝突したものは一覧にするだけにする。
  .gitignore が既にあれば、足りない行だけを末尾に足す。git リポジトリなら初回コミットは作らない
  （変更は人が確かめてからコミットする）。
- --link: スキルをコピーせず、scaffold のスキルへのシンボリックリンクにする（scaffold の更新がすぐ反映される）。
- リンクを作れない環境（Windows で開発者モードがオフなど）では、実体をコピーして警告する。
- scaffold 自体の開発用のもの（tool/、.github/、DESIGN.md、docs/dev/、LICENSE、README.md）は持ち込まない。
標準ライブラリだけで書く（Python 3.9 以上）。
"""

from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parents[1]
KIT = "researchkit"
RULE_FILES = ["CLAUDE.md", "AGENTS.md", "GEMINI.md", "opencode.json",
              ".kiro/steering/language.md", ".kiro/steering/research.md"]
# scaffold のライセンス表示は、調査のリポジトリのルートに置かず .researchkit/ に置く（調査自体のライセンスと混ぜない）
NOTICE = ("THIRD_PARTY_NOTICES.md", ".researchkit/THIRD_PARTY_NOTICES.md")
SKILL_SET = "skills/researchkit"
AGENT_SKILL_DIRS = [".claude/skills", ".agents/skills", ".kiro/skills"]
STEERING_IMPORTS = ["@.kiro/steering/language.md", "@.kiro/steering/research.md"]
QUESTION_FILE = "docs/concept/core-question.md"
CONFIG_TEMPLATE = "researchkit-status/templates/config.yaml"
GITIGNORE_MARK = "# ===== researchkit の取り込みで追加 ====="
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", ".cache")


def warn(message: str) -> None:
    print(f"WARN: {message}", file=sys.stderr)


def link_agent_dirs(target: Path, conflicts: list[str]) -> int:
    """各エージェントのスキルディレクトリから skills/researchkit/<skill> へ相対リンクを張る。作った数を返す。

    すでにある同名のディレクトリや、別の場所へのリンクは残し、conflicts に挙げる。
    リンクを作れない環境（Windows で開発者モードがオフなど）では、実体をコピーする。
    """
    skills_dir = target / SKILL_SET
    if not skills_dir.is_dir():
        sys.exit(f"{skills_dir} がありません。researchkit を取り込んだプロジェクトのディレクトリを指定してください。")
    made = 0
    for base in AGENT_SKILL_DIRS:
        d = target / base
        d.mkdir(parents=True, exist_ok=True)
        for s in sorted(p.name for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith("__")):
            link = d / s
            want = os.path.relpath(skills_dir / s, d)
            if link.is_symlink():
                if os.readlink(link) == want:
                    continue
                conflicts.append(f"{base}/{s}（別の場所へのリンク: {os.readlink(link)}）")
                continue
            if link.exists():
                conflicts.append(f"{base}/{s}（既存のディレクトリ）")
                continue
            try:
                link.symlink_to(want, target_is_directory=True)
            except (OSError, NotImplementedError):
                shutil.copytree(skills_dir / s, link, ignore=IGNORE)
                warn(f"{base}/{s} はリンクを作れなかったため、実体をコピーしました。")
            made += 1
    return made


def place_skills(target: Path, link: bool, added: list[str], skipped: list[str]) -> None:
    src, dst = SCAFFOLD / SKILL_SET, target / SKILL_SET
    if dst.exists() or dst.is_symlink():
        skipped.append(SKILL_SET + "/")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if link:
        try:
            dst.symlink_to(src, target_is_directory=True)
            added.append(SKILL_SET + "/（リンク）")
            return
        except (OSError, NotImplementedError):
            warn(f"{SKILL_SET}/ は scaffold へのリンクを作れなかったため、実体をコピーしました。")
    shutil.copytree(src, dst, ignore=IGNORE)
    added.append(SKILL_SET + "/")


def merge_gitignore(target: Path, added: list[str], skipped: list[str]) -> None:
    """.gitignore がなければコピーし、あれば足りない行だけを末尾に足す。"""
    src, dst = SCAFFOLD / ".gitignore", target / ".gitignore"
    if not dst.exists():
        shutil.copy2(src, dst)
        added.append(".gitignore")
        return
    current = set(dst.read_text(encoding="utf-8", errors="replace").splitlines())
    wanted = [line for line in src.read_text(encoding="utf-8").splitlines()
              if line.strip() and not line.startswith("#") and line not in current]
    if not wanted:
        skipped.append(".gitignore")
        return
    text = dst.read_text(encoding="utf-8", errors="replace")
    if text and not text.endswith("\n"):
        text += "\n"
    dst.write_text(text + f"\n{GITIGNORE_MARK}\n" + "\n".join(wanted) + "\n", encoding="utf-8")
    added.append(f".gitignore（{len(wanted)} 行を追記）")


def write_question(target: Path, question: str, added: list[str], skipped: list[str]) -> None:
    """調べたい問いを docs/concept/core-question.md に書く（researchkit-bootstrap の R0 の入力）。"""
    path = target / QUESTION_FILE
    if path.exists():
        skipped.append(QUESTION_FILE)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    path.write_text(f"# 調べたい問い\n\n**作成日**: {today}\n\n{question.strip()}\n", encoding="utf-8")
    added.append(QUESTION_FILE)


def run_kit_script(target: Path, args: list[str], what: str) -> bool:
    """skills/researchkit/researchkit-status/scripts/researchkit.py を呼ぶ。スクリプトがなければ警告して False。"""
    helper = target / SKILL_SET / "researchkit-status" / "scripts" / "researchkit.py"
    if not helper.is_file():
        warn(f"{helper.relative_to(target).as_posix()} がないため、{what}を行いませんでした。")
        return False
    subprocess.run([sys.executable, str(helper), "--root", str(target), *args], check=True)
    return True


def init_config(target: Path, title: str, adopt: bool, added: list[str]) -> None:
    cmd = ["init"]
    if adopt:
        cmd.append("--config-only")  # paths を既存の配置に合わせる前に、空のディレクトリを作らない
    if title:
        cmd += ["--title", title]
    if run_kit_script(target, cmd, "設定の初期化（researchkit.py init）"):
        added.append(".researchkit/config.yaml")
        return
    # スクリプトがない scaffold でも、設定だけはテンプレートから置く
    src, dst = target / SKILL_SET / CONFIG_TEMPLATE, target / ".researchkit" / "config.yaml"
    if src.is_file() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        if title:
            text = text.replace("\ntitle:\n", f"\ntitle: {title}\n", 1)
        dst.write_text(text, encoding="utf-8")
        added.append(".researchkit/config.yaml（テンプレートから）")


def steering_hints(target: Path) -> list[str]:
    """既存の CLAUDE.md などが researchkit の steering を読み込んでいなければ、足す行を案内する。"""
    hints = []
    for name in ("CLAUDE.md", "GEMINI.md"):
        p = target / name
        if p.exists():
            text = p.read_text(encoding="utf-8", errors="replace")
            missing = [line for line in STEERING_IMPORTS if line not in text]
            if missing:
                hints.append(f"{name} に次の行を足す: " + " / ".join(missing))
    p = target / "AGENTS.md"
    if p.exists():
        text = p.read_text(encoding="utf-8", errors="replace")
        missing = [rel for rel in RULE_FILES if rel.startswith(".kiro/steering/") and rel not in text]
        if missing:
            hints.append("AGENTS.md の読み込みリストに " + "、".join(f"`{m}`" for m in missing) + " を足す")
    return hints


def print_conflicts(conflicts: list[str]) -> None:
    if not conflicts:
        return
    print(f"CONFLICT（同名のスキルが既にあるため残した。{len(conflicts)} 件）:")
    for c in conflicts[:6]:
        print(f"  {c}")
    if len(conflicts) > 6:
        print(f"  ほか {len(conflicts) - 6} 件")


def relink_command(target: Path) -> str:
    """リンクを張り直すコマンド。uv で入れた new-researchkit-project から呼ばれたときは、scaffold が一時的な場所にあって
    終わると消えるので、このファイルのパスではなく、取り込みをもう一度実行するコマンドを示す（足りないリンクだけを作る）。"""
    launcher = os.environ.get("RESEARCHKIT_LAUNCHER")
    if launcher:
        return f'{launcher} "{target}" --adopt'
    return f'python3 {Path(__file__).resolve()} --relink "{target}"'


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if not stream.isatty() and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="researchkit の調査のプロジェクトを作る")
    ap.add_argument("target")
    ap.add_argument("--title", default="")
    ap.add_argument("--question", default="", help=f"調べたい問い（{QUESTION_FILE} に書く）")
    ap.add_argument("--link", action="store_true", help="スキルを scaffold へのシンボリックリンクにする")
    ap.add_argument("--adopt", action="store_true", help="既存の調査に取り込む（上書きしない）")
    ap.add_argument("--relink", action="store_true", help="各エージェントのスキルディレクトリのリンクだけを作り直す")
    args = ap.parse_args()

    target = Path(args.target).expanduser().resolve()
    if args.relink:
        conflicts: list[str] = []
        made = link_agent_dirs(target, conflicts)
        print(f"LINKED: {made}")
        print_conflicts(conflicts)
        return
    if target.exists() and any(target.iterdir()) and not args.adopt:
        sys.exit(f"{target} は空ではありません。既存の調査に取り込むなら --adopt を付けてください。")
    target.mkdir(parents=True, exist_ok=True)
    added: list[str] = []
    skipped: list[str] = []
    conflicts = []

    for rel in RULE_FILES:
        src, dst = SCAFFOLD / rel, target / rel
        if dst.exists():
            skipped.append(rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        added.append(rel)
    merge_gitignore(target, added, skipped)
    src, dst = SCAFFOLD / NOTICE[0], target / NOTICE[1]
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        added.append(NOTICE[1])

    place_skills(target, args.link, added, skipped)
    link_agent_dirs(target, conflicts)
    added.append("、".join(d + "/" for d in AGENT_SKILL_DIRS) + "（リンク）")

    is_repo = (target / ".git").exists()
    if not is_repo:
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=target, check=True)
    init_config(target, args.title, args.adopt, added)
    # Claude Code のフック（Web 検索の回数を数え、セッションの区切りを判定する。steering「セッションの区切り」）
    if run_kit_script(target, ["hooks", "install"], "フックの登録（researchkit.py hooks install）"):
        added.append(".claude/settings.json（フック）")
    if args.question.strip():
        write_question(target, args.question, added, skipped)

    if not is_repo:
        subprocess.run(["git", "add", "-A"], cwd=target, check=True)
        subprocess.run(["git", "commit", "-q", "-m", f"chore(research): {KIT} を初期化"], cwd=target, check=True)

    print(f"TARGET: {target}")
    print("ADDED: " + ", ".join(added))
    if skipped:
        shown = skipped[:15]
        more = f" ほか {len(skipped) - len(shown)} 件" if len(skipped) > len(shown) else ""
        print("SKIPPED（既存のため変更していない）: " + ", ".join(shown) + more)
    print_conflicts(conflicts)
    print("\n次の手順:")
    if args.adopt:
        step = 1
        print(f"  {step}. 追加されたファイルを確かめてコミットする"); step += 1
        for hint in steering_hints(target):
            print(f"  {step}. {hint}"); step += 1
        if conflicts:
            print(f"  {step}. CONFLICT のスキルは既存のものを残した。researchkit 版に揃えるなら、既存のものを消してから "
                  f"`{relink_command(target)}` を実行する（足りないリンクだけを作る）"); step += 1
        print(f"  {step}. .researchkit/config.yaml の paths を既存の配置に合わせる（ファイルは動かさない）"); step += 1
        print(f"  {step}. python3 {SKILL_SET}/researchkit-status/scripts/researchkit.py init で、"
              "足りないディレクトリだけを作る"); step += 1
        print(f"  {step}. python3 {SKILL_SET}/researchkit-status/scripts/researchkit.py doctor で確かめる"); step += 1
        print(f"  {step}. /researchkit-bootstrap --adopt で、既存の調査の資料から足りない成果物だけを作る")
    elif (target / QUESTION_FILE).exists():
        print(f'  cd "{target}" && claude "/researchkit-bootstrap"')
    else:
        print(f'  cd "{target}" && claude "/researchkit-bootstrap <調べたい問い>"')


if __name__ == "__main__":
    main()
