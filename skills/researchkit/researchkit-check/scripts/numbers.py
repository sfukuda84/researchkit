#!/usr/bin/env python3
"""numbers.py - researchkit の数値の突き合わせ（gamekit の balance.py check に当たる）

文書の `{N:<path>#<key>}` の直前の数値と、分析の出力（JSON）の値を突き合わせる。
macOS / Linux / Windows で動くように、標準ライブラリだけで書く（Python 3.9 以上）。

使い方:
  numbers.py [--root R] [--rq <NNN> | --all] [--file <path>]

  --rq <NNN>   studies/<NNN-name>/findings.md を検証する
  --all        すべての RQ の findings.md と reports/report.md（あれば）を検証する（既定）
  --file PATH  任意の文書を検証する

参照の書き方（steering の「数値の参照」）:
  - `1,234 億円{N:analysis/out/market.json#size_2025}`。<path> は RQ のディレクトリからの相対パス
    （studies/ の外の文書、たとえば統合報告では、リポジトリのルートからの相対パス）。<key> はドット区切り（配列は添字）
  - 直前の数値は、参照の直前の同じ行にある最後の数値。数値と参照の間には単位（億円、件、人など）だけを置ける
  - 数値の書式: 1,234 / 12.3% / 1.2万 / 3億 / -0.5（全角の数字・記号も読む）
  - 万・億・兆・千の付いた数値は、JSON の値が「単位込みの値」でも「その単位で数えた値」でも一致とみなす
  - % の数値は、JSON の値が 0〜1 なら 100 倍して比べる
  - 一致の判定: 相対の差が numbers.tolerance（既定 0.005）以内か、JSON の値を表示の桁で丸めると表示の数値になる
  - `{N:calc}` は手で計算した数値の印で、突き合わせない（件数を数え、「計算」の節がなければ WARN）

出力は check.py と同じ形式（`ERROR|WARN <file>:<line> <code> <説明>` と `SUMMARY: ...`）。ERROR があれば終了コード 1。
"""

from __future__ import annotations

import sys
from pathlib import Path

# このファイルの名前は標準ライブラリの numbers と同じなので、標準ライブラリが numbers を読むときに
# このファイルを読まないよう、スクリプトのディレクトリを検索パスから外す。check.py はパスを指定して読む。
_HERE = Path(__file__).resolve().parent
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != _HERE]

import argparse  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import unicodedata  # noqa: E402
from typing import Any  # noqa: E402

_spec = importlib.util.spec_from_file_location("researchkit_check", _HERE / "check.py")
ck = importlib.util.module_from_spec(_spec)
sys.modules["researchkit_check"] = ck
_spec.loader.exec_module(ck)

REF_RE = re.compile(r"\{N:([^}]*)\}")
NUM_RE = re.compile(r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(万|億|兆|千)?\s*(%|ポイント|pt)?")
MULTIPLIERS = {"千": 1e3, "万": 1e4, "億": 1e8, "兆": 1e12}
MINUS = ("-", "−", "▲", "△", "－")
MAX_UNIT_CHARS = 12


class Shown:
    """文書に書かれた数値。"""

    def __init__(self, text: str, mantissa: float, decimals: int, mult: str | None, percent: bool) -> None:
        self.text = text
        self.mantissa = mantissa
        self.decimals = decimals
        self.mult = mult
        self.percent = percent


def preceding_number(before: str) -> Shown | None:
    """参照の直前の数値を読む。数値の後には単位だけが続いていること（数字を含まない短い文字列）。"""
    norm = unicodedata.normalize("NFKC", before)
    matches = list(NUM_RE.finditer(norm))
    if not matches:
        return None
    m = matches[-1]
    tail = norm[m.end():]
    if len(tail.strip()) > MAX_UNIT_CHARS or re.search(r"\d", tail) or REF_RE.search(tail):
        return None
    raw = m.group(1)
    value = float(raw.replace(",", ""))
    start = m.start()
    # 符号: 直前が負の記号で、さらにその前が数字・英字でなければ負の数（「2020-2025」の - は符号にしない）
    if start > 0 and norm[start - 1] in MINUS and not (start > 1 and re.match(r"[0-9A-Za-z]", norm[start - 2])):
        value = -value
        start -= 1
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    return Shown(norm[start:m.end()].strip(), value, decimals, m.group(2), bool(m.group(3) == "%"))


def lookup(doc: Any, key: str) -> Any:
    cur = doc
    for part in key.split("."):
        if isinstance(cur, list):
            if not re.fullmatch(r"\d+", part) or int(part) >= len(cur):
                raise KeyError(part)
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            if part not in cur:
                raise KeyError(part)
            cur = cur[part]
        else:
            raise KeyError(part)
    return cur


def is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def candidates(shown: Shown, value: float) -> list[float]:
    """JSON の値を、表示の数値（倍数を除いた部分）と比べられる形にした候補。"""
    base = [value]
    if shown.percent and abs(value) <= 1:
        base.append(value * 100)
    out = list(base)
    if shown.mult:
        out.extend(v / MULTIPLIERS[shown.mult] for v in base)
    return out


def matches(shown: Shown, value: float, tolerance: float) -> bool:
    for c in candidates(shown, value):
        if abs(shown.mantissa - c) <= max(tolerance * abs(c), 1e-12):
            return True
        if round(c, shown.decimals) == round(shown.mantissa, shown.decimals):
            return True
    return False


def check_numbers(rep: ck.Report, path: Path, root: Path, cfg: dict, required: bool) -> tuple[int, int]:
    """文書の数値の参照を検証する。（突き合わせた件数, {N:calc} の件数）を返す。"""
    if not path.is_file():
        if required:
            rep.error(path, 1, "NO_FILE", "文書がない")
        return 0, 0
    _, rq_dir = ck.rq_of_path(root, cfg, path)
    base = rq_dir if rq_dir is not None else root
    tol = cfg["numbers"].get("tolerance")
    tolerance = float(tol) if is_number(tol) else 0.005
    cache: dict[Path, Any] = {}
    checked = calc = 0
    text = path.read_text(encoding="utf-8")
    for no, line in enumerate(text.splitlines(), 1):
        for m in REF_RE.finditer(line):
            ref = m.group(1).strip()
            if ref == "calc":
                calc += 1
                continue
            if "#" not in ref:
                rep.error(path, no, "BAD_REF", f"{{N:{ref}}} は {{N:<path>#<key>}} か {{N:calc}} にする")
                continue
            rel, key = ref.split("#", 1)
            shown = preceding_number(line[:m.start()])
            if shown is None:
                rep.error(path, no, "NO_NUMBER", f"{{N:{ref}}} の直前に数値がない（数値と参照の間は単位だけにする）")
                continue
            target = (base / rel).resolve()
            if target not in cache:
                if not target.is_file():
                    cache[target] = FileNotFoundError()
                else:
                    try:
                        cache[target] = json.loads(target.read_text(encoding="utf-8"))
                    except (ValueError, UnicodeDecodeError) as e:
                        cache[target] = e
            doc = cache[target]
            if isinstance(doc, FileNotFoundError):
                rep.error(path, no, "MISSING_FILE", f"{rel} がない（{rep.rel(target)}。分析のスクリプトを再実行する）")
                continue
            if isinstance(doc, Exception):
                rep.error(path, no, "BAD_JSON", f"{rel} を JSON として読めない")
                continue
            try:
                value = lookup(doc, key)
            except KeyError:
                rep.error(path, no, "MISSING_KEY", f"{rel} にキー {key} がない")
                continue
            if not is_number(value):
                rep.error(path, no, "NOT_NUMBER", f"{rel}#{key} の値が数値でない（{value!r}）")
                continue
            checked += 1
            if not matches(shown, float(value), tolerance):
                rep.error(path, no, "MISMATCH",
                          f"文書の {shown.text} と {rel}#{key} の値 {value} が一致しない（許容 {tolerance * 100:g}%）")
    if calc and not re.search(r"^#{2,4}\s*.*計算", text, flags=re.M):
        rep.warn(path, 1, "NO_CALC_SECTION", f"{{N:calc}} が {calc} 件あるのに「計算」の節（計算式と入力の表）がない")
    return checked, calc


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="researchkit の数値の突き合わせ")
    ap.add_argument("--root")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--rq")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--file")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ck.setup_stdout()
    args = parse_args(argv)
    root = Path(args.root).resolve() if args.root else ck.find_root()
    cfg = ck.load_config(root)
    rep = ck.Report(root)
    if args.file and (args.rq or args.all):
        print("ERROR - USAGE --file は --rq・--all と併用しない")
        return 1
    rqs = ck.rq_dirs(root, cfg)
    if args.file:
        targets = [(ck.resolve_file(root, args.file), True)]
    elif args.rq:
        num = ck.normalize_rq(args.rq)
        if num not in rqs:
            rep.error(ck.pth(root, cfg, "studies"), 1, "NO_RQ", f"RQ {num} のディレクトリ（studies/{num}-*）がない")
            rep.dump()
            return 1
        targets = [(rqs[num] / "findings.md", True)]
    else:
        targets = [(d / "findings.md", False) for d in rqs.values()]
        targets.append((ck.report_file(root, cfg), False))
    checked = calc = 0
    for path, required in targets:
        c, k = check_numbers(rep, path, root, cfg, required)
        checked += c
        calc += k
    e, _ = rep.dump(extra=f" checked={checked} calc={calc}")
    return 1 if e else 0


if __name__ == "__main__":
    sys.exit(main())
