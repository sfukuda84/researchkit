#!/usr/bin/env python3
"""check.py - researchkit の機械検証（出典の参照と出典台帳）

主張の表（findings.md、統合報告 reports/report.md、任意の文書）の根拠の欄と、出典台帳（sources/<ID>.md）を検証する。
主張の欄で探索的な分析の出力（{N:…#exploratory.…}）を使う主張は、確度が段階の下から 2 つでなければ ERROR にする。
--rq と --all では、データの目録（data/manifest.md）と data/raw/ のファイルも突き合わせる（目録にないファイル、目録にあるのにないファイル、SHA-256 の不一致）。
macOS / Linux / Windows で動くように、標準ライブラリだけで書く（Python 3.9 以上）。

使い方:
  check.py [--root R] [--rq <NNN> | --all] [--file <path>] [--online] [--strict]

  --rq <NNN>   RQ の findings.md と、その RQ の出典（S<NNN>-* と used_in に <NNN> を含むもの）を検証する
  --all        すべての RQ の findings.md、reports/report.md（あれば）、すべての出典を検証する（既定）
  --file PATH  任意の文書の主張の表と出典の参照を検証する（--rq・--all と併用しない）
  --online     URL（HEAD、だめなら GET）と DOI（https://doi.org/<doi>）の到達性を確かめる。失敗は WARN
  --strict     WARN があっても終了コード 1 にする

出力: 1 行 1 件 `ERROR|WARN <file>:<line> <code> <説明>` と、最後に `SUMMARY: errors=<n> warnings=<n>`。
終了コード: ERROR があれば 1（--strict では WARN があっても 1）、なければ 0。

numbers.py もこのファイルの共通部分（設定の読み込み、ルートの探索、出力）を使う。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 同じディレクトリの numbers.py が標準ライブラリの numbers の代わりに読まれないよう、検索パスから外す
_HERE = Path(__file__).resolve().parent
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != _HERE]

import argparse  # noqa: E402
import datetime as dt  # noqa: E402
import hashlib  # noqa: E402
import re  # noqa: E402
import urllib.error  # noqa: E402
import urllib.request  # noqa: E402
from typing import Any  # noqa: E402

CONFIG_REL = ".researchkit/config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "paths": {
        "concept": "docs/concept",
        "study": "docs/study",
        "questions": "docs/questions",
        "sources": "sources",
        "studies": "studies",
        "reports": "reports",
        "data": "data",
    },
    "confidence": {"levels": ["確実", "可能性が高い", "示唆", "不明"]},
    "sources": {"grades": ["A", "B", "C", "D"], "min_grade": "C", "check_online": False},
    "numbers": {"tolerance": 0.005},
}

SOURCE_ID_RE = re.compile(r"(?<![A-Za-z0-9])S(\d{3})-(\d{4})(?![0-9])")
CROSS_CLAIM_RE = re.compile(r"(?<![A-Za-z0-9-])(\d{3})-C(\d+)(?![0-9])")
LOCAL_CLAIM_RE = re.compile(r"(?<![A-Za-z0-9-])C(\d+)(?![0-9])")
RQ_DIR_RE = re.compile(r"^(\d{3})-[A-Za-z0-9-]+$")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_TYPES = ("web", "paper", "book", "stat", "report", "dataset", "interview", "internal")
CLAIM_HEADERS = ("ID", "主張", "根拠", "確度")
# 探索的な分析（結果を見た後に足した分析。レビューで足したものを含む）の出力は、JSON の exploratory の下に置く
EXPLORATORY_REF_RE = re.compile(r"\{N:[^}#]*#exploratory(?:\.[^}]*)?\}")


# ---------------------------------------------------------------- 設定（小さな YAML）

def _strip_comment(line: str) -> str:
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _split_inline(inner: str) -> list[str]:
    parts, buf, quote = [], [], None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch in (",", "、"):
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _scalar(text: str) -> Any:
    t = text.strip()
    if t == "":
        return None
    if len(t) >= 2 and t[0] == t[-1] and t[0] in ("'", '"'):
        return t[1:-1]
    if t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        return [_scalar(p) for p in _split_inline(inner)] if inner else []
    if t in ("true", "True", "yes"):
        return True
    if t in ("false", "False", "no"):
        return False
    if t in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", t) and not (len(t) > 1 and t.lstrip("-").startswith("0")):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d+", t):
        return float(t)
    return t


def parse_yaml(text: str, comments: bool = True) -> Any:
    """config.yaml とフロントマターに要る範囲（入れ子の辞書、ブロックとインラインのリスト、スカラー）だけを読む。

    comments=False では # をコメントとして扱わない（出典の題名や URL に # が入るため）。
    """
    lines = []
    for raw in text.splitlines():
        line = raw.replace("\t", "  ").rstrip()
        line = _strip_comment(line) if comments else line
        if line.strip():
            lines.append((len(line) - len(line.lstrip(" ")), line.strip()))
    if not lines:
        return {}
    value, _ = _parse_block(lines, 0, lines[0][0])
    return value


def _parse_block(lines: list, pos: int, indent: int) -> tuple[Any, int]:
    if lines[pos][1].startswith("- ") or lines[pos][1] == "-":
        items: list[Any] = []
        while pos < len(lines) and lines[pos][0] == indent and (lines[pos][1].startswith("- ") or lines[pos][1] == "-"):
            items.append(_scalar(lines[pos][1][1:]))
            pos += 1
            while pos < len(lines) and lines[pos][0] > indent:
                pos += 1  # 要素の入れ子は使わないので読み飛ばす
        return items, pos
    result: dict[str, Any] = {}
    while pos < len(lines) and lines[pos][0] >= indent:
        if lines[pos][0] > indent:
            pos += 1
            continue
        m = re.match(r"^([^:]+?):(?:\s+(.*))?$", lines[pos][1])
        pos += 1
        if not m:
            continue
        key, rest = m.group(1).strip().strip("'\""), (m.group(2) or "").strip()
        if rest == "" and pos < len(lines) and (lines[pos][0] > indent or
                                                 (lines[pos][0] == indent and lines[pos][1].startswith("- "))):
            val, pos = _parse_block(lines, pos, lines[pos][0])
        else:
            val = _scalar(rest)
        result[key] = val
    return result, pos


def deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        elif v is not None:
            out[k] = v
    return out


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return _split_inline(str(value))


def find_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / CONFIG_REL).exists():
            return p
    for p in [cur, *cur.parents]:
        if (p / ".git").exists():
            return p
    return cur


def load_config(root: Path) -> dict[str, Any]:
    path = root / CONFIG_REL
    loaded: Any = {}
    if path.exists():
        loaded = parse_yaml(path.read_text(encoding="utf-8")) or {}
    return deep_merge(DEFAULT_CONFIG, loaded if isinstance(loaded, dict) else {})


def pth(root: Path, cfg: dict, key: str) -> Path:
    return root / str(cfg["paths"].get(key) or DEFAULT_CONFIG["paths"][key])


# ---------------------------------------------------------------- 出力

class Report:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.items: list[tuple[str, str, int, str, str]] = []

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(path)

    def add(self, level: str, path: Path, line: int, code: str, msg: str) -> None:
        item = (level, self.rel(path), line, code, msg)
        if item not in self.items:
            self.items.append(item)

    def error(self, path: Path, line: int, code: str, msg: str) -> None:
        self.add("ERROR", path, line, code, msg)

    def warn(self, path: Path, line: int, code: str, msg: str) -> None:
        self.add("WARN", path, line, code, msg)

    def counts(self) -> tuple[int, int]:
        e = sum(1 for i in self.items if i[0] == "ERROR")
        return e, len(self.items) - e

    def dump(self, extra: str = "") -> tuple[int, int]:
        order = {"ERROR": 0, "WARN": 1}
        for level, f, line, code, msg in sorted(self.items, key=lambda x: (order[x[0]], x[1], x[2], x[3])):
            print(f"{level} {f}:{line} {code} {msg}")
        e, w = self.counts()
        print(f"SUMMARY: errors={e} warnings={w}{extra}")
        return e, w


def setup_stdout() -> None:
    # Windows の日本語環境では標準出力が cp932 になり、— などを出力すると落ちるため UTF-8 に固定する
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- 対象の選び方

def rq_dirs(root: Path, cfg: dict) -> dict[str, Path]:
    """studies/<NNN-name>/ を番号ごとに返す。"""
    base = pth(root, cfg, "studies")
    result: dict[str, Path] = {}
    if base.is_dir():
        for d in sorted(base.iterdir()):
            m = RQ_DIR_RE.match(d.name)
            if d.is_dir() and m:
                result.setdefault(m.group(1), d)
    return result


def rq_of_path(root: Path, cfg: dict, path: Path) -> tuple[str | None, Path | None]:
    """path が studies/<NNN-name>/ の下にあれば、その番号とディレクトリ。"""
    base = pth(root, cfg, "studies").resolve()
    try:
        parts = path.resolve().relative_to(base).parts
    except ValueError:
        return None, None
    if parts and RQ_DIR_RE.match(parts[0]):
        return parts[0][:3], base / parts[0]
    return None, None


def report_file(root: Path, cfg: dict) -> Path:
    return pth(root, cfg, "reports") / "report.md"


def normalize_rq(value: str) -> str:
    m = re.match(r"^\s*(\d{1,3})", value)
    return m.group(1).zfill(3) if m else value.strip()


# ---------------------------------------------------------------- 主張の表

class Claim:
    def __init__(self, cid: str, line: int, cells: dict[str, str]) -> None:
        self.id = cid
        self.line = line
        self.cells = cells


def table_rows(text: str) -> list[tuple[list[str], list[tuple[int, list[str]]]]]:
    """Markdown の表を（見出し、[(行番号, セル)]）の列にする。"""
    tables: list[tuple[list[str], list[tuple[int, list[str]]]]] = []
    header: list[str] | None = None
    rows: list[tuple[int, list[str]]] = []
    for no, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|") and len(s) > 1):
            if header is not None:
                tables.append((header, rows))
            header, rows = None, []
            continue
        cells = [c.strip() for c in s[1:-1].split("|")]
        if header is None:
            header = [re.sub(r"\*", "", c).strip() for c in cells]
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append((no, cells))
    if header is not None:
        tables.append((header, rows))
    return tables


def claim_tables(text: str) -> list[tuple[list[str], list[Claim]]]:
    """「ID | 主張 | 根拠 | 確度」の列を持つ表だけを読む。"""
    result = []
    for header, rows in table_rows(text):
        if not all(h in header for h in CLAIM_HEADERS):
            continue
        claims = []
        for no, cells in rows:
            cells_d = {header[i]: (cells[i] if i < len(cells) else "") for i in range(len(header))}
            cid = cells_d.get("ID", "").strip().strip("`*")
            if cid:
                claims.append(Claim(cid, no, cells_d))
        result.append((header, claims))
    return result


def claim_ids_of(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return {c.id for _, claims in claim_tables(path.read_text(encoding="utf-8")) for c in claims}


# ---------------------------------------------------------------- 出典台帳

class Source:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.meta: dict[str, Any] = {}
        self.lines: dict[str, int] = {}
        self.has_frontmatter = False
        self.parse()

    def parse(self) -> None:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0].strip() != "---":
            return
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is None:
            return
        self.has_frontmatter = True
        body = lines[1:end]
        for i, raw in enumerate(body, 2):
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", raw)
            if m:
                self.lines.setdefault(m.group(1), i)
        meta = parse_yaml("\n".join(body), comments=False)
        self.meta = meta if isinstance(meta, dict) else {}

    def get(self, key: str) -> str:
        v = self.meta.get(key)
        if v is None:
            return ""
        if isinstance(v, list):
            return ", ".join(str(x) for x in v)
        return str(v).strip()

    def line(self, key: str) -> int:
        return self.lines.get(key, 1)

    @property
    def sid(self) -> str:
        return self.path.stem


def load_sources(root: Path, cfg: dict) -> dict[str, Source]:
    base = pth(root, cfg, "sources")
    result: dict[str, Source] = {}
    if base.is_dir():
        for p in sorted(base.rglob("*.md")):
            if p.name.lower() in ("readme.md", "index.md") or p.name.startswith("_"):
                continue
            src = Source(p)
            key = src.get("id") or src.sid
            result.setdefault(key, src)
    return result


def check_source(rep: Report, src: Source, cfg: dict, today: dt.date) -> None:
    p = src.path
    if not src.has_frontmatter:
        rep.error(p, 1, "SOURCE_NO_FRONTMATTER", "フロントマター（--- で囲んだ項目）がない")
        return
    for key in ("id", "type", "title", "accessed", "grade"):
        if not src.get(key):
            rep.error(p, 1, "SOURCE_MISSING_FIELD", f"必須の項目 {key} がない")
    if not (src.get("url") or src.get("doi") or (src.get("author") and src.get("publisher"))):
        rep.error(p, 1, "SOURCE_MISSING_FIELD", "url・doi・書誌（author と publisher）のどれもない")
    sid = src.get("id")
    if sid and sid != src.sid:
        rep.error(p, src.line("id"), "SOURCE_ID_MISMATCH", f"id {sid} とファイル名 {src.sid} が一致しない")
    if sid and not SOURCE_ID_RE.fullmatch(sid):
        rep.error(p, src.line("id"), "SOURCE_ID_FORMAT", f"id {sid} は S<NNN>-<NNNN> の形にする")
    grades = as_list(cfg["sources"].get("grades"))
    grade = src.get("grade")
    if grade and grades and grade not in grades:
        rep.error(p, src.line("grade"), "SOURCE_BAD_GRADE", f"等級 {grade} が sources.grades（{', '.join(grades)}）にない")
    elif grade and grades and grade == grades[-1]:
        rep.warn(p, src.line("grade"), "GRADE_D",
                 f"等級 {grade}（未確認）の出典。根拠に使わない。実在を確かめて等級を上げるか、使わない")
    typ = src.get("type")
    if typ and typ not in SOURCE_TYPES:
        rep.warn(p, src.line("type"), "SOURCE_BAD_TYPE", f"type {typ} は {' / '.join(SOURCE_TYPES)} のどれかにする")
    doi = src.get("doi")
    if doi:
        bare = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
        if not DOI_RE.match(bare):
            rep.warn(p, src.line("doi"), "BAD_DOI", f"DOI の書式が正しくない: {doi}（10.<登録者>/<番号> の形）")
    accessed = src.get("accessed")
    if accessed:
        if not DATE_RE.match(accessed):
            rep.warn(p, src.line("accessed"), "BAD_DATE", f"参照日 {accessed} は YYYY-MM-DD にする")
        else:
            try:
                d = dt.date.fromisoformat(accessed)
            except ValueError:
                rep.warn(p, src.line("accessed"), "BAD_DATE", f"参照日 {accessed} が日付として正しくない")
            else:
                if (today - d).days > 365:
                    rep.warn(p, src.line("accessed"), "STALE_ACCESS", f"参照日 {accessed} が 1 年以上前。内容が変わっていないか確かめる")
                elif d > today:
                    rep.warn(p, src.line("accessed"), "BAD_DATE", f"参照日 {accessed} が未来の日付")


def grade_rank(cfg: dict) -> dict[str, int]:
    return {g: i for i, g in enumerate(as_list(cfg["sources"].get("grades")))}


# ---------------------------------------------------------------- 参照の収集

def references_by_rq(root: Path, cfg: dict) -> dict[str, set[str]]:
    """出典 ID ごとに、参照している RQ の番号（統合報告は 999）の集合。"""
    refs: dict[str, set[str]] = {}
    for num, d in rq_dirs(root, cfg).items():
        for p in d.rglob("*.md"):
            for m in SOURCE_ID_RE.finditer(p.read_text(encoding="utf-8")):
                refs.setdefault(m.group(0), set()).add(num)
    rdir = pth(root, cfg, "reports")
    if rdir.is_dir():
        for p in rdir.rglob("*.md"):
            for m in SOURCE_ID_RE.finditer(p.read_text(encoding="utf-8")):
                refs.setdefault(m.group(0), set()).add("999")
    return refs


# ---------------------------------------------------------------- 文書の検証

def check_document(rep: Report, path: Path, root: Path, cfg: dict, sources: dict[str, Source],
                   rqs: dict[str, Path], required: bool) -> set[str]:
    """文書の主張の表と出典の参照を検証する。参照した出典 ID を返す。"""
    if not path.is_file():
        if required:
            rep.error(path, 1, "NO_FILE", "文書がない")
        return set()
    text = path.read_text(encoding="utf-8")
    levels = as_list(cfg["confidence"].get("levels"))
    ranks = grade_rank(cfg)
    min_grade = str(cfg["sources"].get("min_grade") or "")
    min_rank = ranks.get(min_grade)
    tables = claim_tables(text)
    local_ids: dict[str, int] = {}
    for _, claims in tables:
        for c in claims:
            if c.id in local_ids:
                rep.error(path, c.line, "DUP_CLAIM", f"主張の ID {c.id} が重複している（{local_ids[c.id]} 行目）")
            else:
                local_ids[c.id] = c.line
    cross_cache: dict[str, set[str]] = {}
    referenced: set[str] = set()
    evidence_lines: set[int] = set()
    for _, claims in tables:
        for c in claims:
            evidence_lines.add(c.line)
            ev = c.cells.get("根拠", "")
            src_ids = [m.group(0) for m in SOURCE_ID_RE.finditer(ev)]
            ev_wo_src = SOURCE_ID_RE.sub(" ", ev)
            cross = [(m.group(1), f"C{m.group(2)}") for m in CROSS_CLAIM_RE.finditer(ev_wo_src)]
            local = [f"C{m.group(1)}" for m in LOCAL_CLAIM_RE.finditer(CROSS_CLAIM_RE.sub(" ", ev_wo_src))]
            if not (src_ids or cross or local):
                rep.error(path, c.line, "NO_EVIDENCE", f"{c.id} の根拠の欄が空（出典 ID か主張 ID を書く。根拠がなければ「残った問い」に回す）")
            usable = 0
            graded = []
            for sid in src_ids:
                referenced.add(sid)
                src = sources.get(sid)
                if src is None:
                    rep.error(path, c.line, "UNKNOWN_SOURCE", f"{c.id} の根拠 {sid} が出典台帳にない")
                    continue
                g = src.get("grade")
                graded.append(f"{sid}={g or '?'}")
                if min_rank is None or (g in ranks and ranks[g] <= min_rank):
                    usable += 1
            for cid in local:
                if cid == c.id:
                    rep.error(path, c.line, "SELF_CLAIM", f"{c.id} が自分自身を根拠にしている")
                elif cid not in local_ids:
                    rep.error(path, c.line, "UNKNOWN_CLAIM", f"{c.id} の根拠 {cid} がこの文書の主張の表にない")
                else:
                    usable += 1
            for num, cid in cross:
                if num not in cross_cache:
                    d = rqs.get(num)
                    cross_cache[num] = claim_ids_of(d / "findings.md") if d else set()
                if num not in rqs:
                    rep.error(path, c.line, "UNKNOWN_CLAIM", f"{c.id} の根拠 {num}-{cid} の RQ {num} が studies/ にない")
                elif cid not in cross_cache[num]:
                    rep.error(path, c.line, "UNKNOWN_CLAIM", f"{c.id} の根拠 {num}-{cid} が {rep.rel(rqs[num] / 'findings.md')} にない")
                else:
                    usable += 1
            if src_ids and usable == 0 and graded and len(graded) == len(src_ids):
                rep.error(path, c.line, "LOW_GRADE",
                          f"{c.id} の根拠が最低等級 {min_grade} 未満の出典だけ（{', '.join(graded)}）")
            conf = c.cells.get("確度", "").strip().strip("*")
            if levels and conf not in levels:
                rep.error(path, c.line, "BAD_CONFIDENCE",
                          f"{c.id} の確度「{conf}」が confidence.levels（{' / '.join(levels)}）にない")
            elif (len(levels) >= 2 and conf in levels and levels.index(conf) < len(levels) - 2
                  and EXPLORATORY_REF_RE.search(c.cells.get("主張", ""))):
                rep.error(path, c.line, "EXPLORATORY_CONFIDENCE",
                          f"{c.id} は探索的な分析の出力（#exploratory.…）を主張に使っているのに確度が「{conf}」。"
                          f"探索的な分析の結果は「{levels[-2]}」を超えない（憲章の確認的と探索的の区別）。別の主張にして確度を下げる")
    # 表の外の出典の参照（本文、計算の表など）
    for no, line in enumerate(text.splitlines(), 1):
        if no in evidence_lines:
            continue
        for m in SOURCE_ID_RE.finditer(line):
            referenced.add(m.group(0))
            if m.group(0) not in sources:
                rep.error(path, no, "UNKNOWN_SOURCE", f"出典 {m.group(0)} が出典台帳にない")
    return referenced


# ---------------------------------------------------------------- 到達性（--online）

def reachable(url: str, timeout: float = 10.0) -> tuple[bool, str]:
    headers = {"User-Agent": "researchkit-check/1.0 (+https://doi.org)"}
    last = ""
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (調査の出典の URL を確かめる)
                if resp.status < 400:
                    return True, str(resp.status)
                last = str(resp.status)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
    return False, last


def check_online(rep: Report, src: Source) -> None:
    url = src.get("url")
    if url:
        ok, why = reachable(url)
        if not ok:
            rep.warn(src.path, src.line("url"), "UNREACHABLE", f"URL に到達できない（{why}）: {url}")
    doi = src.get("doi")
    if doi:
        bare = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
        if DOI_RE.match(bare):
            ok, why = reachable(f"https://doi.org/{bare}")
            if not ok:
                rep.warn(src.path, src.line("doi"), "UNREACHABLE", f"DOI を解決できない（{why}）: {bare}")


# ---------------------------------------------------------------- main

# ---------------------------------------------------------------- データの目録（data/manifest.md）

DATA_IGNORE = {".gitkeep", ".DS_Store", "README.md"}


def manifest_rows(text: str) -> list[tuple[int, dict[str, str]]]:
    """目録の「ファイル」の表（SHA-256 の列を持つ表）の行。例の行（< で始まる）は除く。"""
    for header, rows in table_rows(text):
        if "SHA-256" in header and "ファイル" in header:
            out = []
            for no, cells in rows:
                row = {header[i]: (cells[i] if i < len(cells) else "") for i in range(len(header))}
                name = row.get("ファイル", "").strip("` ")
                if name and not name.startswith("<"):
                    out.append((no, dict(row, ファイル=name)))
            return out
    return []


def check_manifest(rep: Report, root: Path, cfg: dict, rq: str | None = None) -> None:
    """data/raw/ のファイルと目録を突き合わせる。

    - UNLISTED_DATA（ERROR）: data/raw/ にあるが目録にない。取得したのに記録していない（途中で切れた収集の跡など）
    - MISSING_DATA（ERROR）: 目録の raw の行のファイルがない
    - HASH_MISMATCH（ERROR）: 目録の SHA-256 と中身が違う（加工した、別の版で上書きした）
    --rq のときは、使った RQ にその番号がある行と、目録にないファイルだけを見る。
    """
    data_dir = pth(root, cfg, "data")
    raw = data_dir / "raw"
    manifest = data_dir / "manifest.md"
    files = sorted(p for p in raw.rglob("*") if p.is_file() and p.name not in DATA_IGNORE
                   and not any(part.startswith(".") for part in p.relative_to(raw).parts)) if raw.is_dir() else []
    if not manifest.is_file():
        if files:
            rep.error(raw, 1, "NO_MANIFEST", f"data/raw/ に {len(files)} 件のファイルがあるのに {rep.rel(manifest)} がない")
        return
    rows = manifest_rows(manifest.read_text(encoding="utf-8"))
    listed = {r["ファイル"] for _, r in rows}
    for f in files:
        name = rep.rel(f)
        if name not in listed:
            rep.error(manifest, 1, "UNLISTED_DATA",
                      f"{name} が目録にない。出どころを確かめて行を足す（researchkit.py data add）か、不要なら人に確かめて取り除く")
    for no, r in rows:
        if rq and rq not in {normalize_rq(x) for x in re.split(r"[,、\s]+", r.get("使った RQ", "")) if re.match(r"^\d", x)}:
            continue
        path = root / r["ファイル"]
        if r.get("置き場所", "raw").strip() == "large" and not path.exists():
            continue  # コミットしない大きなファイル。手元にないことがある
        if not path.is_file():
            rep.error(manifest, no, "MISSING_DATA", f"{r['ファイル']} がない")
            continue
        want = r.get("SHA-256", "").strip().lower()
        if re.fullmatch(r"[0-9a-f]{64}", want):
            got = hashlib.sha256(path.read_bytes()).hexdigest()
            if got != want:
                rep.error(manifest, no, "HASH_MISMATCH", f"{r['ファイル']} の SHA-256 が目録と違う（目録 {want[:12]}…、実際 {got[:12]}…）")


def resolve_file(root: Path, given: str) -> Path:
    """--file のパス。相対パスは、作業ディレクトリから見てなければルートから見る。"""
    path = Path(given)
    if path.is_absolute():
        return path
    return (Path.cwd() / path) if (Path.cwd() / path).exists() else (root / path)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="researchkit の出典の参照と出典台帳の検証")
    ap.add_argument("--root")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--rq")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--file")
    ap.add_argument("--online", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--today", help=argparse.SUPPRESS)  # テスト用
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    setup_stdout()
    args = parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    cfg = load_config(root)
    rep = Report(root)
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    sources = load_sources(root, cfg)
    rqs = rq_dirs(root, cfg)
    online = args.online or cfg["sources"].get("check_online") is True

    if args.file and (args.rq or args.all):
        print("ERROR - USAGE --file は --rq・--all と併用しない")
        return 1

    if args.file:
        path = resolve_file(root, args.file)
        refs = check_document(rep, path, root, cfg, sources, rqs, required=True)
        for sid in sorted(refs):
            if sid in sources:
                check_source(rep, sources[sid], cfg, today)
                if online:
                    check_online(rep, sources[sid])
        rep.dump()
        e, w = rep.counts()
        return 1 if e or (args.strict and w) else 0

    usage = references_by_rq(root, cfg)
    if args.rq:
        num = normalize_rq(args.rq)
        d = rqs.get(num)
        if d is None:
            rep.error(pth(root, cfg, "studies"), 1, "NO_RQ", f"RQ {num} のディレクトリ（studies/{num}-*）がない")
            rep.dump()
            return 1
        targets = [d / "findings.md"]
        in_scope = [s for sid, s in sources.items()
                    if sid.startswith(f"S{num}-") or num in {normalize_rq(u) for u in as_list(s.meta.get("used_in"))}
                    or num in usage.get(sid, set())]
    else:
        targets = [d / "findings.md" for d in rqs.values()]
        if report_file(root, cfg).is_file():
            targets.append(report_file(root, cfg))
        in_scope = list(sources.values())

    for t in targets:
        num, _ = rq_of_path(root, cfg, t)
        if t.is_file():
            if num and num != "000" and not claim_tables(t.read_text(encoding="utf-8")):
                rep.warn(t, 1, "NO_CLAIM_TABLE", "主張の表（| ID | 主張 | 根拠 | 確度 | 反証・限界 |）がない")
            check_document(rep, t, root, cfg, sources, rqs, required=False)

    check_manifest(rep, root, cfg, normalize_rq(args.rq) if args.rq else None)

    for src in in_scope:
        check_source(rep, src, cfg, today)
        sid = src.get("id") or src.sid
        actual = usage.get(sid, set())
        if not actual:
            rep.warn(src.path, 1, "UNUSED_SOURCE", f"{sid} はどの RQ・報告からも参照されていない")
        declared = {normalize_rq(u) for u in as_list(src.meta.get("used_in"))}
        missing = sorted(actual - declared)
        extra = sorted(declared - actual)
        if src.has_frontmatter and (missing or extra) and actual:
            parts = []
            if missing:
                parts.append(f"参照しているのに used_in にない: {', '.join(missing)}")
            if extra:
                parts.append(f"used_in にあるのに参照がない: {', '.join(extra)}")
            rep.warn(src.path, src.line("used_in"), "USED_IN_MISMATCH", f"{sid} の used_in と実際の参照が食い違う（{'。'.join(parts)}）")
        if online:
            check_online(rep, src)

    rep.dump()
    e, w = rep.counts()
    return 1 if e or (args.strict and w) else 0


if __name__ == "__main__":
    sys.exit(main())
