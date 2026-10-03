#!/usr/bin/env python3
"""rklib.py - researchkit の共通ライブラリ（researchkit.py と、ほかのスキルのスクリプトが使う）

プロジェクトの設定（.researchkit/config.yaml）、Markdown の表とフロントマター、出典台帳、git の呼び出しを扱う。
macOS / Linux / Windows で動くように、標準ライブラリだけで書く（Python 3.9 以上）。
YAML は config.yaml とフロントマターに必要な範囲（入れ子の辞書、ブロックとインラインのリスト、スカラー）だけを解釈する。
（gamekit の gklib.py を移したもの）

ほかのスキルのスクリプトからは、次のように読み込む。

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "researchkit-status" / "scripts"))
    import rklib
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

CONFIG_REL = ".researchkit/config.yaml"
USAGE_REL = ".researchkit/usage"
TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "config.yaml"
SOURCE_ID_RE = re.compile(r"\bS(\d{3})-(\d{4})\b")
SOURCE_FILE_RE = re.compile(r"^S(\d{3})-(\d{4})\.md$")

DEFAULT_CONFIG: dict[str, Any] = {
    "title": "",
    "paths": {
        "concept": "docs/concept",
        "scan": "docs/scan",
        "study": "docs/study",
        "method": "docs/method.md",
        "quality": "docs/quality.md",
        "questions": "docs/questions",
        "glossary": "docs/glossary.md",
        "reviews": "docs/reviews",
        "handover": "docs/handover",
        "sources": "sources",
        "data": "data",
        "studies": "studies",
        "reports": "reports",
        "constitution": ".researchkit/memory/constitution.md",
    },
    "commands": {"analysis": None, "test": None},
    "session": {
        "web_search_limit": 200,
        "reserve": 10,
        "estimates": {"R2": 60, "R6": 30, "Q8": 60, "Q11": 30, "Q12": 15, "rq": 100},
        "estimates_by_method": {
            "data": {"Q8": 20, "Q11": 20, "Q12": 15, "rq": 50},
            "desk": {"Q8": 30, "Q11": 20, "Q12": 15, "rq": 70},
            "literature": {"Q8": 60, "Q11": 30, "Q12": 15, "rq": 120},
            "qualitative": {"Q8": 15, "Q11": 20, "Q12": 15, "rq": 50},
        },
        "stop_after_bootstrap": True,
        "rqs_unmetered": 1,
    },
    "confidence": {"levels": ["確実", "可能性が高い", "示唆", "不明"]},
    "sources": {"grades": ["A", "B", "C", "D"], "min_grade": "C", "check_online": False},
    "data": {"max_file_mb": 5},
    "subagents": {"model": "sonnet", "max_parallel": 3},
    "output": {"max_lines": 40},
    "numbers": {"tolerance": 0.005},
}


# ---------------------------------------------------------------- mini YAML

class YamlError(Exception):
    pass


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


def _scalar(text: str) -> Any:
    t = text.strip()
    if t == "":
        return None
    if (t[0] == t[-1]) and t[0] in ("'", '"') and len(t) >= 2:
        return t[1:-1]
    if t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        if not inner:
            return []
        return [_scalar(p) for p in _split_inline(inner)]
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


def parse_yaml(text: str) -> Any:
    lines = []
    for raw in text.splitlines():
        line = _strip_comment(raw.replace("\t", "  "))
        if line.strip():
            lines.append((len(line) - len(line.lstrip(" ")), line.strip()))
    if not lines:
        return {}
    value, pos = _parse_block(lines, 0, lines[0][0])
    if pos != len(lines):
        raise YamlError(f"解釈できない行があります: {lines[pos][1]}")
    return value


def _parse_block(lines, pos, indent):
    if lines[pos][1].startswith("- ") or lines[pos][1] == "-":
        result: list[Any] = []
        while pos < len(lines) and lines[pos][0] == indent and (lines[pos][1].startswith("- ") or lines[pos][1] == "-"):
            item = lines[pos][1][1:].strip()
            pos += 1
            if item == "":
                if pos < len(lines) and lines[pos][0] > indent:
                    val, pos = _parse_block(lines, pos, lines[pos][0])
                    result.append(val)
                else:
                    result.append(None)
            elif re.match(r"^[^\[\]{}\"']+?:(\s|$)", item) and not item.startswith("["):
                # "- key: value" 形式の辞書の要素
                sub = [(indent + 2, item)]
                while pos < len(lines) and lines[pos][0] > indent:
                    sub.append(lines[pos])
                    pos += 1
                val, _ = _parse_block(sub, 0, indent + 2)
                result.append(val)
            else:
                result.append(_scalar(item))
        return result, pos
    result_d: dict[str, Any] = {}
    while pos < len(lines) and lines[pos][0] == indent:
        text = lines[pos][1]
        m = re.match(r"^(.+?):(\s+(.*))?$", text)
        if not m:
            raise YamlError(f"「キー: 値」の形ではありません: {text}")
        key, rest = m.group(1).strip().strip("'\""), (m.group(3) or "").strip()
        pos += 1
        if rest == "" and pos < len(lines) and lines[pos][0] > indent:
            val, pos = _parse_block(lines, pos, lines[pos][0])
        elif rest == "" and pos < len(lines) and lines[pos][0] == indent and lines[pos][1].startswith("- "):
            val, pos = _parse_block(lines, pos, indent)
        else:
            val = _scalar(rest)
        result_d[key] = val
    return result_d, pos


def deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [p for p in _split_inline(str(value))]


# ---------------------------------------------------------------- プロジェクト

def find_root(start: Path | None = None) -> Path:
    """.researchkit/config.yaml のあるディレクトリ。なければ git のルート、それもなければ start。

    worktree（.worktrees/<name>）の中では、worktree 自身が config.yaml を持つので、worktree がルートになる。
    """
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
    if not path.exists():
        return deep_merge(DEFAULT_CONFIG, {})
    loaded = parse_yaml(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise YamlError(f"{CONFIG_REL} の最上位が辞書ではありません。")
    return deep_merge(DEFAULT_CONFIG, loaded)


def pth(root: Path, cfg: dict, key: str) -> Path:
    return root / (cfg["paths"].get(key) or DEFAULT_CONFIG["paths"][key])


def config_get(cfg: dict, dotted: str) -> Any:
    """"commands.analysis" のようなキーで値を取り出す。なければ None。"""
    cur: Any = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def set_top_scalar(text: str, key: str, value: str) -> str:
    """config.yaml の最上位の「key:」の行の値を書き換える（コメントは残す）。行がなければ末尾に足す。"""
    pat = re.compile(rf"^{re.escape(key)}:[ \t]*([^#\n]*?)([ \t]*#.*)?$", re.MULTILINE)
    m = pat.search(text)
    if not m:
        return text.rstrip("\n") + f"\n{key}: {value}\n"
    comment = (m.group(2) or "").strip()
    comment = f"  {comment}" if comment else ""
    return text[: m.start()] + f"{key}: {value}{comment}" + text[m.end():]


# ---------------------------------------------------------------- Markdown

def read_table(path: Path, require: str | None = None) -> list[dict[str, str]]:
    """Markdown の表を辞書の列にする（見出し行をキーにする）。行番号は "_line" に入れる。

    require を指定すると、その列を見出しに持つ最初の表を読む（説明用の表を読み飛ばすため）。
    指定しなければ、最初の表を読む。
    """
    if not path.exists():
        return []
    tables: list[tuple[list[str], list[dict[str, str]]]] = []
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            if header is not None:
                tables.append((header, rows))
            header, rows = None, []
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = [re.sub(r"\*", "", c) for c in cells]
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        row = {header[i]: (cells[i] if i < len(cells) else "") for i in range(len(header))}
        row["_line"] = str(no)
        rows.append(row)
    if header is not None:
        tables.append((header, rows))
    for hdr, rws in tables:
        if require is None or require in hdr:
            return rws
    return []


def split_frontmatter(text: str) -> tuple[str | None, str, int]:
    """先頭の "---" で囲まれたフロントマターを (フロントマターの本文, 残りの本文, 本文の開始行) に分ける。

    フロントマターがなければ (None, text, 1)。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, 1
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:]), i + 2
    return None, text, 1


def parse_frontmatter(text: str) -> dict[str, Any]:
    """フロントマターを辞書にする。YAML として読めなければ、最上位の「key: value」の行だけを拾う。"""
    fm, _, _ = split_frontmatter(text)
    if fm is None:
        return {}
    try:
        data = parse_yaml(fm)
        if isinstance(data, dict):
            return data
    except YamlError:
        pass
    data: dict[str, Any] = {}
    for line in fm.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if m:
            data[m.group(1)] = _scalar(_strip_comment(m.group(2)))
    return data


def read_frontmatter(path: Path) -> dict[str, Any]:
    try:
        return parse_frontmatter(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return {}


# ---------------------------------------------------------------- 出典台帳

def normalize_rq_number(value: str) -> str:
    """"3"、"003"、"003-market-size"、"S003" を "003" にする。読めなければ ValueError。"""
    m = re.match(r"^S?(\d{1,3})(?:-.*)?$", str(value).strip())
    if not m:
        raise ValueError(f"RQ の番号として読めません: {value}")
    return f"{int(m.group(1)):03d}"


def load_sources(root: Path, cfg: dict) -> list[dict[str, Any]]:
    """sources/ の出典ファイルを読み、フロントマターの辞書の列にする（"_path" にファイルを入れる）。"""
    base = pth(root, cfg, "sources")
    found: list[dict[str, Any]] = []
    if not base.is_dir():
        return found
    for path in sorted(base.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        meta = read_frontmatter(path)
        meta.setdefault("id", path.stem)
        meta["_path"] = path
        found.append(meta)
    return found


# ---------------------------------------------------------------- git

def git(root: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} が失敗しました: {proc.stderr.strip()}")
    return proc


def is_git_repo(root: Path) -> bool:
    return git(root, ["rev-parse", "--is-inside-work-tree"], check=False).returncode == 0


def main_branch() -> str:
    """マージ先のブランチ名（環境変数 RESEARCHKIT_MAIN_BRANCH、なければ main）。"""
    return os.environ.get("RESEARCHKIT_MAIN_BRANCH") or "main"


def main_worktree(root: Path) -> Path:
    """worktree の中から呼ばれても、メインの作業ツリーのルートを返す（Git でなければ root）。"""
    proc = git(root, ["rev-parse", "--git-common-dir"], check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return root
    common = Path(proc.stdout.strip())
    common = (common if common.is_absolute() else root / common).resolve()
    return common.parent if common.name == ".git" else root
