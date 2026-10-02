"""公開用の文書から、数値の参照の記号と主張の参照を取り除く（researchkit-publish）。

使い方:
    python3 strip_refs.py <in.md> [-o <out.md>] [--claims]
    python3 strip_refs.py <file> --check      # 書き換えずに、{N:...} が残っていないかだけを確かめる

- {N:<path>#<key>} と {N:calc} を取り除く。
- --claims を付けると、括弧で囲んだ主張の参照（例: （003-C2）、(003-C2, 004-C1)、[C3]）も取り除く。
  括弧の中が主張の ID だけのときに限る。出典 ID（S001-0003）は取り除かない。
- -o を省くと、標準出力に書く。

標準ライブラリだけを使う。終了コード: 0 成功、1 --check で記号が残っている、2 引数の誤り。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

NUMBER_REF_RE = re.compile(r"\{N:[^{}\n]*\}")
CLAIM_ID = r"(?:\d{3}-)?C\d+"
CLAIM_REF_RE = re.compile(
    r"\s?[（(［\[]\s*" + CLAIM_ID + r"(?:\s*[,、，]\s*" + CLAIM_ID + r")*\s*[）)］\]]"
)


def strip_refs(text: str, claims: bool = False) -> str:
    text = NUMBER_REF_RE.sub("", text)
    if claims:
        text = CLAIM_REF_RE.sub("", text)
    return text


def remaining(text: str) -> list[tuple[int, str]]:
    """{N: が残っている行（行番号, 行）。"""
    return [(i, line) for i, line in enumerate(text.split("\n"), start=1) if "{N:" in line]


def main(argv: list[str]) -> int:
    args: list[str] = []
    out: str | None = None
    claims = check = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "-o":
            if i + 1 >= len(argv):
                print("ERROR: -o に出力先がない", file=sys.stderr)
                return 2
            out = argv[i + 1]
            i += 2
            continue
        if a == "--claims":
            claims = True
        elif a == "--check":
            check = True
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            args.append(a)
        i += 1
    if len(args) != 1:
        print("ERROR: 入力のファイルを 1 つ指定する", file=sys.stderr)
        return 2
    src = Path(args[0])
    text = src.read_text(encoding="utf-8").replace("\r\n", "\n")
    if check:
        left = remaining(text)
        for n, line in left:
            print(f"ERROR {src}:{n} NUMBER_REF 数値の参照の記号が残っている: {line.strip()[:60]}")
        print(f"SUMMARY: errors={len(left)} warnings=0")
        return 1 if left else 0
    result = strip_refs(text, claims=claims)
    for n, line in remaining(result):
        print(f"WARN {src}:{n} NUMBER_REF 形の崩れた {{N: が残っている: {line.strip()[:60]}", file=sys.stderr)
    if out:
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(result)
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
