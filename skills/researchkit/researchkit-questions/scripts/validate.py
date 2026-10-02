#!/usr/bin/env python3
"""docs/questions/ の RQ 一式を検証する（researchkit-questions。gamekit-features の validate.py を調査向けにしたもの）。

使い方:
    python3 validate.py <docs/questions のパス>                    # 検証のみ
    python3 validate.py <docs/questions のパス> --graph            # 被参照数と段階分けも表示
    python3 validate.py <docs/questions のパス> --require-reserved # 000 と 999 がなければエラー（R12 の全体の検証で使う）
    python3 validate.py <docs/questions のパス> --lenient          # 既存の調査の取り込み用。エラーを警告に落とし、
                                                                   # 番号のないファイル（NNN-slug.md でないもの）は対象から外す
    python3 validate.py <docs/questions のパス> --seed-file <seed.md> --hypotheses-file <hypotheses.md> --backlog-file <backlog.md>
        # 省略時は docs/questions と同じ階層の concept/seed.md、study/hypotheses.md、concept/backlog.md を読む
        # （.researchkit/config.yaml の paths を変えたときは、これらのオプションで渡す）
    # README.md の「メタ文書（RQ ファイルではない）」の表に載せたファイルは、RQ ファイルとして検証しない

検証すること:
    - ファイル名（NNN-<slug>.md）、H1、ヘッダ行（状態・区分・想定順序・依存・手法）の値、必須の節
    - 番号の重複、想定順序とファイル名の番号の一致
    - 区分: 000 は 基盤、999 は 統合。基盤・統合はそれぞれ 000・999 だけが使う
    - 依存: 存在しない参照、自分への依存、循環。000 はほかに依存しない。999 に依存する RQ はない
    - 「つながる決定」の D が seed.md に、「つながる仮説」の H が hypotheses.md にあるか。
      000 と 999 以外で、どの決定にもつながらない RQ はエラー
    - どの RQ にもつながらない決定・仮説（警告）
    - 000 と 999 の有無（R9 の時点ではまだないので警告。--require-reserved でエラー）
    - README.md の一覧、spec_order.md の並び（依存の順、000 が先頭、999 が末尾）、被参照数の表
    - backlog.md の「RQ化済み」のリンク先（警告）

終了コード: エラーが 1 件以上なら 1、なければ 0（警告は終了コードに影響しない。--lenient では常に 0）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

META_FILES = {"README.md", "spec_order.md"}
REQUIRED_SECTIONS = [
    "## 問い",
    "## つながる決定",
    "## つながる仮説",
    "## 答えの形",
    "## 範囲",
    "## 想定する情報源",
    "## 人の作業の見込み",
]
STATUSES = ("未着手", "設計済み", "完了", "人の作業待ち")
CATEGORIES = ("基盤", "中核", "補助", "統合")
METHODS = ("desk", "literature", "data", "qualitative")
NONE_VALUES = {"—", "-", "なし", ""}
NAME_RE = re.compile(r"^(\d{3})-[a-z0-9]+(-[a-z0-9]+)*$")
FOUNDATION = 0
REPORT = 999
RESERVED = {FOUNDATION: "基盤", REPORT: "統合"}
D_RE = re.compile(r"(?<![A-Za-z0-9])D(\d+)(?![0-9])")
H_RE = re.compile(r"(?<![A-Za-z0-9])H(\d+)(?![0-9])")
ORDER_LINE_RE = re.compile(r"\*\*\s*(\d+)\.\s*\[([^\]]*)\]\(\./([^.)]+)\.md\)")
README_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*\[([^\]]*)\]\(\./([^.)]+)\.md\)\s*\|(.*)\|\s*$")
RANK_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*$")
BACKLOG_DONE_RE = re.compile(r"RQ化済み（(?:docs/questions/)?(\d{3}-[a-z0-9-]+)\.md）")
META_SECTION = "## メタ文書"
LOCAL_LINK_RE = re.compile(r"\]\((?:\./)?([^/()#\s]+\.md)\)")

errors: list[str] = []
warnings: list[str] = []
LENIENT = "--lenient" in sys.argv
all_slugs: set[str] = set()


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def option(name: str) -> str | None:
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def split_values(value: str) -> list[str]:
    value = value.strip()
    if value in NONE_VALUES:
        return []
    return [d.strip() for d in re.split(r"[,、]", value) if d.strip()]


def section_body(text: str, heading: str) -> str:
    lines = text.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return ""
    body = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        body.append(line)
    # HTML コメント（テンプレートの記入の説明）は中身として数えない
    return re.sub(r"<!--.*?-->", "", "\n".join(body), flags=re.S).strip()


def parse_header(path: Path, text: str) -> dict | None:
    """`**状態**: … | **区分**: … | **想定順序**: … | **依存**: … | **手法**: …` 行を読む。"""
    line = next((l for l in text.splitlines() if l.startswith("**状態**")), None)
    if line is None:
        err(f"{path.name}: ヘッダ行（**状態** で始まる行）がない")
        return None
    fields = {}
    for part in line.split(" | "):
        m = re.match(r"\*\*(.+?)\*\*:\s*(.*)$", part.strip())
        if m:
            fields[m.group(1)] = m.group(2).strip()
    keys = ("状態", "区分", "想定順序", "依存", "手法")
    for key in keys:
        if key not in fields:
            err(f"{path.name}: ヘッダ行に **{key}** がない")
    if any(k not in fields for k in keys):
        return None
    if fields["状態"] not in STATUSES:
        err(f"{path.name}: 状態「{fields['状態']}」は {' / '.join(STATUSES)} のいずれかにする")
    if fields["区分"] not in CATEGORIES:
        err(f"{path.name}: 区分「{fields['区分']}」は {' / '.join(CATEGORIES)} のいずれかにする")
    if not fields["想定順序"].isdigit():
        err(f"{path.name}: 想定順序「{fields['想定順序']}」が整数でない")
    return fields


def listed_meta_files(qdir: Path) -> set[str]:
    """README.md の「メタ文書（RQ ファイルではない）」の節に載っている、docs/questions 直下のファイル名。"""
    path = qdir / "README.md"
    if not path.exists():
        return set()
    names: set[str] = set()
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.startswith(META_SECTION)
            continue
        if inside and line.lstrip().startswith("|"):
            first_cell = line.strip().strip("|").split("|")[0]
            names.update(LOCAL_LINK_RE.findall(first_cell))
    return names


def load_questions(qdir: Path) -> dict[str, dict]:
    questions: dict[str, dict] = {}
    meta = META_FILES | listed_meta_files(qdir)
    titles: dict[str, str] = {}
    for path in sorted(qdir.glob("*.md")):
        if path.name in meta:
            continue
        slug = path.stem
        text = path.read_text(encoding="utf-8")
        name_m = NAME_RE.match(slug)
        if not name_m:
            if LENIENT:
                warn(f"{path.name}: 番号のないファイル名（NNN-<slug>.md でない）なので検証の対象から外した")
                continue
            err(f"{path.name}: ファイル名は NNN-<英小文字のケバブケース>.md にする（例: 001-market-size.md）")
        all_slugs.add(slug)
        num = int(name_m.group(1)) if name_m else None
        reserved = num in RESERVED
        lines = text.splitlines()
        title_line = next((l for l in lines if l.startswith("# ")), None)
        title = title_line[2:].strip() if title_line else ""
        if title_line is None:
            err(f"{path.name}: H1 見出し（# 問い）がない")
        elif not reserved and not re.search(r"[？?]$", title):
            warn(f"{path.name}: H1「{title}」が疑問文になっていない（RQ の名前は問いの形にする）")
        if title and not reserved:
            if title in titles:
                warn(f"{path.name}: H1 が {titles[title]} と同じ（問いが重なっていないか確かめる）")
            titles.setdefault(title, path.name)
        header = parse_header(path, text)
        for sec in REQUIRED_SECTIONS:
            if sec not in lines:
                if reserved:
                    warn(f"{path.name}: 見出し「{sec}」がない")
                else:
                    err(f"{path.name}: 見出し「{sec}」がない")
            elif not reserved and not section_body(text, sec):
                warn(f"{path.name}: 「{sec}」の節が空")
        if header is None:
            continue
        methods = split_values(header["手法"])
        for m in methods:
            if m not in METHODS:
                err(f"{path.name}: 手法「{m}」は {', '.join(METHODS)} のいずれかにする")
        if not methods and not reserved:
            err(f"{path.name}: 手法がない（{', '.join(METHODS)} から選ぶ）")
        if len(methods) > 2 and not reserved:
            warn(f"{path.name}: 手法が {len(methods)} つある（1 件の RQ は 1〜2 手法が目安。分けられないか確かめる）")
        if num is not None and header["想定順序"].isdigit() and num != int(header["想定順序"]):
            err(f"{path.name}: ファイル名の番号 {name_m.group(1)} と想定順序 {header['想定順序']} が違う")
        if num in RESERVED and header["区分"] != RESERVED[num]:
            err(f"{path.name}: {num:03d} の区分は「{RESERVED[num]}」にする")
        if num not in RESERVED and header["区分"] in RESERVED.values():
            err(f"{path.name}: 区分「{header['区分']}」は予約番号（000 は 基盤、999 は 統合）だけが使う")
        questions[slug] = {
            "title": title,
            "num": num,
            "status": header["状態"],
            "category": header["区分"],
            "order": int(header["想定順序"]) if header["想定順序"].isdigit() else None,
            "deps_raw": header["依存"],
            "deps": split_values(header["依存"]),
            "methods_raw": header["手法"],
            "decisions": sorted({f"D{n}" for n in D_RE.findall(section_body(text, "## つながる決定"))}, key=lambda x: int(x[1:])),
            "hypotheses": sorted({f"H{n}" for n in H_RE.findall(section_body(text, "## つながる仮説"))}, key=lambda x: int(x[1:])),
        }
    return questions


def check_graph(questions: dict[str, dict]) -> None:
    for slug, q in questions.items():
        for d in q["deps"]:
            if d == slug:
                err(f"{slug}.md: 自分自身に依存している")
            elif d not in questions:
                if d not in all_slugs:
                    err(f"{slug}.md: 依存「{d}」に対応する RQ ファイルがない（完全名 NNN-slug で書く）")
            elif questions[d]["num"] == REPORT:
                err(f"{slug}.md: 統合報告 {d} に依存している（999 はほかの RQ から依存されない）")
        if q["num"] == FOUNDATION and q["deps"]:
            err(f"{slug}.md: 共通基盤（000）はほかの RQ に依存できない")

    color = {s: 0 for s in questions}
    cycles = []

    def dfs(node: str, stack: list[str]) -> None:
        color[node] = 1
        for d in questions[node]["deps"]:
            if d not in questions or d == node:
                continue
            if color[d] == 1:
                cycles.append(stack[stack.index(d):] + [d])
            elif color[d] == 0:
                dfs(d, stack + [d])
        color[node] = 2

    for s in questions:
        if color[s] == 0:
            dfs(s, [s])
    for c in cycles:
        err(f"循環依存: {' -> '.join(c)}")

    nums: dict[int, list[str]] = {}
    for s, q in questions.items():
        if q["num"] is not None:
            nums.setdefault(q["num"], []).append(s)
    for n, slugs in sorted(nums.items()):
        if len(slugs) > 1:
            err(f"番号 {n:03d} が重複している: {', '.join(slugs)}")
    core = sorted(n for n in nums if n not in RESERVED)
    if core and core != list(range(1, len(core) + 1)):
        warn(f"番号が 001 からの連番になっていない: {core}（RQ を取り下げた場合は想定どおり）")


def check_reserved(questions: dict[str, dict]) -> None:
    present = {q["num"] for q in questions.values()}
    strict = "--require-reserved" in sys.argv
    for num, (label, step, skill) in {FOUNDATION: ("共通基盤", "R10", "researchkit-foundation"),
                                      REPORT: ("統合報告", "R11", "researchkit-deliverable")}.items():
        if num not in present:
            msg = f"{num:03d}（{label}）の RQ ファイルがない（{step} の {skill} が作る）"
            err(msg) if strict else warn(msg)


def find_file(qdir: Path, opt: str, *candidates: str) -> Path | None:
    given = option(opt)
    if given:
        return Path(given)
    for c in candidates:
        p = qdir.parent / c
        if p.exists():
            return p
    return None


def defined_ids(path: Path | None, pattern: re.Pattern, prefix: str) -> set[str]:
    if path is None or not path.exists():
        return set()
    return {f"{prefix}{n}" for n in pattern.findall(path.read_text(encoding="utf-8"))}


def check_links(qdir: Path, questions: dict[str, dict]) -> None:
    """つながる決定（seed.md の D）と、つながる仮説（hypotheses.md の H）。"""
    seed = find_file(qdir, "--seed-file", "concept/seed.md")
    hyp = find_file(qdir, "--hypotheses-file", "study/hypotheses.md")
    if seed is None or not seed.exists():
        err("seed.md がない（docs/concept/seed.md。R1 の researchkit-seed が作る。別の場所なら --seed-file で渡す）")
    if hyp is None or not hyp.exists():
        err("hypotheses.md がない（docs/study/hypotheses.md。R5 の researchkit-hypothesis が作る。別の場所なら --hypotheses-file で渡す）")
    known_d = defined_ids(seed, D_RE, "D")
    known_h = defined_ids(hyp, H_RE, "H")
    used_d: set[str] = set()
    used_h: set[str] = set()
    for slug, q in questions.items():
        reserved = q["num"] in RESERVED
        if not q["decisions"] and not reserved:
            err(f"{slug}.md: 「つながる決定」に seed.md の決定（D1 など）がない。答えても決定が変わらない RQ は作らない")
        if not q["hypotheses"] and not reserved:
            warn(f"{slug}.md: 「つながる仮説」に hypotheses.md の仮説（H1 など）がない（探索型の RQ なら、その旨を書く）")
        for d in q["decisions"]:
            used_d.add(d)
            if seed is not None and seed.exists() and d not in known_d:
                err(f"{slug}.md: 決定 {d} が {seed} にない")
        for h in q["hypotheses"]:
            used_h.add(h)
            if hyp is not None and hyp.exists() and h not in known_h:
                err(f"{slug}.md: 仮説 {h} が {hyp} にない")
    if questions:
        for d in sorted(known_d - used_d, key=lambda x: int(x[1:])):
            warn(f"決定 {d} につながる RQ がない（RQ を足すか、seed.md で調査の対象外と書く）")
        for h in sorted(known_h - used_h, key=lambda x: int(x[1:])):
            warn(f"仮説 {h} を確かめる RQ がない（RQ を足すか、hypotheses.md で対象外と書く）")


def check_readme(qdir: Path, questions: dict[str, dict]) -> None:
    path = qdir / "README.md"
    if not path.exists():
        err("README.md がない")
        return
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = README_ROW_RE.match(line)
        if not m:
            continue
        num, title, slug, rest = m.groups()
        cols = [c.strip() for c in rest.split("|")]
        if slug in seen:
            err(f"README.md: {slug} の行が重複している")
        seen.add(slug)
        if slug not in questions:
            if slug not in all_slugs:
                err(f"README.md: 一覧の {slug} に対応する RQ ファイルがない")
            continue
        q = questions[slug]
        if len(cols) < 5:
            err(f"README.md: {slug} の行の列が足りない（# | 問い | 区分 | 状態 | 依存 | 手法 | 一言）")
            continue
        category, status, deps, methods = cols[0], cols[1], cols[2], cols[3]
        if int(num) != q["order"]:
            err(f"README.md: {slug} の # が {num}、ファイルの想定順序は {q['order']}")
        if title != q["title"]:
            err(f"README.md: {slug} のリンク文言「{title}」が H1「{q['title']}」と違う")
        if category != q["category"]:
            err(f"README.md: {slug} の区分「{category}」がファイル（{q['category']}）と違う")
        if status != q["status"]:
            err(f"README.md: {slug} の状態「{status}」がファイル（{q['status']}）と違う")
        if deps != q["deps_raw"]:
            err(f"README.md: {slug} の依存「{deps}」がファイル（{q['deps_raw']}）と違う")
        if methods != q["methods_raw"]:
            err(f"README.md: {slug} の手法「{methods}」がファイル（{q['methods_raw']}）と違う")
    for slug in questions:
        if slug not in seen:
            err(f"README.md: 一覧に {slug} の行がない")
    m = re.search(r"RQ ファイル\s*\*\*(\d+)\s*件\*\*", path.read_text(encoding="utf-8"))
    if m and int(m.group(1)) != len(all_slugs):
        err(f"README.md: 件数が {m.group(1)} 件、実測は {len(all_slugs)} 件")


def check_spec_order(qdir: Path, questions: dict[str, dict]) -> None:
    path = qdir / "spec_order.md"
    if not path.exists():
        err("spec_order.md がない")
        return
    seen: set[str] = set()
    position: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("- **"):
            continue
        m = ORDER_LINE_RE.search(line)
        if not m:
            continue
        num, slug = int(m.group(1)), m.group(3)
        if slug in seen:
            err(f"spec_order.md: {slug} の行が重複している")
        seen.add(slug)
        position.append(slug)
        if slug not in questions:
            if slug not in all_slugs:
                err(f"spec_order.md: {slug} に対応する RQ ファイルがない")
            continue
        if num != questions[slug]["order"]:
            err(f"spec_order.md: {slug} の番号 {num} がファイルの想定順序 {questions[slug]['order']} と違う")
    for slug in questions:
        if slug not in seen:
            err(f"spec_order.md: `- **N. [問い](./{slug}.md)**` 形式の行がない（researchkit-worktree が読めない）")
    idx = {s: i for i, s in enumerate(position)}
    for slug, q in questions.items():
        if slug not in idx:
            continue
        for d in q["deps"]:
            if d in idx and idx[d] > idx[slug]:
                err(f"spec_order.md: {slug} が依存先 {d} より前に並んでいる")
        if q["num"] == FOUNDATION and idx[slug] != 0:
            err(f"spec_order.md: 共通基盤 {slug} は先頭に並べる")
        if q["num"] == REPORT and idx[slug] != len(position) - 1:
            err(f"spec_order.md: 統合報告 {slug} は末尾に並べる")


def check_backlog(qdir: Path) -> None:
    """backlog.md の「RQ化済み（docs/questions/NNN-slug.md）」のリンク先があるか（警告）。"""
    path = find_file(qdir, "--backlog-file", "concept/backlog.md")
    if path is None or not path.exists():
        return
    for m in BACKLOG_DONE_RE.finditer(path.read_text(encoding="utf-8")):
        if m.group(1) not in all_slugs:
            warn(f"backlog.md: RQ化済みの {m.group(1)}.md が docs/questions/ にない")


def ranking(questions: dict[str, dict]) -> list[tuple[str, int]]:
    """被参照数が 1 以上の RQ を、多い順（同数なら番号順）に並べる。"""
    ref = {s: 0 for s in questions}
    for q in questions.values():
        for d in q["deps"]:
            if d in ref:
                ref[d] += 1
    return [(s, n) for s, n in sorted(ref.items(), key=lambda x: (-x[1], questions[x[0]]["order"] or 0)) if n > 0]


def read_rank_table(qdir: Path) -> list[tuple[str, int, str]]:
    path = qdir / "spec_order.md"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = RANK_ROW_RE.match(line)
        if m:
            rows.append((m.group(2), int(m.group(1)), m.group(3)))
    return rows


def check_rank_table(qdir: Path, questions: dict[str, dict]) -> None:
    table = [(s, n) for s, n, _ in read_rank_table(qdir)]
    if table and table != ranking(questions):
        warn("spec_order.md: 被参照数の表が実測と違う（--graph の出力で置き換える）")


def read_oneliners(qdir: Path) -> dict[str, str]:
    path = qdir / "README.md"
    result = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = README_ROW_RE.match(line)
            if m:
                cols = [c.strip() for c in m.group(4).split("|")]
                if len(cols) >= 5:
                    result[m.group(3)] = cols[4]
    return result


def stages(questions: dict[str, dict]) -> dict[str, int]:
    """段階 = 依存の深さ。000 への依存と 999 は数えない（000 は先頭、999 は末尾に置く）。"""
    stage: dict[str, int] = {}

    def depth(s: str, trail: tuple = ()) -> int:
        if s in stage:
            return stage[s]
        if s in trail:
            return 1  # 循環はエラーとして別途報告済み
        deps = [d for d in questions[s]["deps"] if d in questions and questions[d]["num"] not in RESERVED]
        stage[s] = 1 + max((depth(d, trail + (s,)) for d in deps), default=0)
        return stage[s]

    for s, q in questions.items():
        if q["num"] not in RESERVED:
            depth(s)
    return stage


def print_graph(qdir: Path, questions: dict[str, dict]) -> None:
    """spec_order.md にそのまま貼れる形で、被参照数の表と段階ごとの RQ 行を出す。"""
    meanings = {s: m for s, _, m in read_rank_table(qdir)}
    print("\n## 被参照数（spec_order.md「被参照数の多い順」の表にそのまま使う。意味の列は既存の記述を引き継ぐ）\n")
    print("| 被参照 | RQ | 意味 |")
    print("|---|---|---|")
    for s, n in ranking(questions):
        print(f"| {n} | `{s}` | {meanings.get(s, '<なぜ多くの RQ の前提になるか>')} |")
    oneliners = read_oneliners(qdir)

    def row(s: str) -> str:
        q = questions[s]
        return f"- **{q['order']}. [{q['title']}](./{s}.md)**: {oneliners.get(s, '<一言>')}"

    stage = stages(questions)
    print("\n## 段階分け（spec_order.md の RQ 行の形。段階の性格の見出しは手で付ける）")
    base = [s for s, q in questions.items() if q["num"] == FOUNDATION]
    if base:
        print("\n### 基盤\n")
        for s in base:
            print(row(s))
    for st in sorted(set(stage.values())):
        print(f"\n### S{st}: <段階の性格>\n")
        for s in sorted((s for s in stage if stage[s] == st), key=lambda s: questions[s]["order"] or 0):
            print(row(s))
    final = [s for s, q in questions.items() if q["num"] == REPORT]
    if final:
        print("\n### 統合\n")
        for s in final:
            print(row(s))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:]
    valued = ("--seed-file", "--hypotheses-file", "--backlog-file")
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i > 0 and argv[i - 1] in valued)]
    if len(args) != 1:
        print(__doc__)
        return 2
    qdir = Path(args[0]).resolve()
    if not qdir.is_dir():
        print(f"ディレクトリがない: {qdir}")
        return 2

    questions = load_questions(qdir)
    check_graph(questions)
    check_reserved(questions)
    check_links(qdir, questions)
    check_readme(qdir, questions)
    check_spec_order(qdir, questions)
    check_rank_table(qdir, questions)
    check_backlog(qdir)

    if LENIENT and errors:
        warnings.extend(f"（--lenient でエラーから警告に落とした）{e}" for e in errors)
        errors.clear()
    counts = " / ".join(f"{c} {sum(1 for q in questions.values() if q['category'] == c)}" for c in CATEGORIES)
    print(f"RQ ファイル: {len(questions)} 件（{counts}）")
    for w in warnings:
        print(f"[警告] {w}")
    for e in errors:
        print(f"[エラー] {e}")
    print(f"エラー {len(errors)} 件 / 警告 {len(warnings)} 件")
    if "--graph" in sys.argv:
        print_graph(qdir, questions)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
