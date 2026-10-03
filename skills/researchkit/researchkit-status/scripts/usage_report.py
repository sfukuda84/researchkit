#!/usr/bin/env python3
"""usage_report.py - Claude Code のセッションの記録（jsonl）から、researchkit の RQ・ステップごとの利用量を集計する（開発用）

使い方:
  skills/researchkit/rk usage --session <jsonl> [--session <jsonl> ...] [--project <調査のプロジェクト>] [--since <ISO 時刻>] [--rq 004]
  （python3 <skills>/researchkit-status/scripts/usage_report.py ... と同じ。--project の既定は今のディレクトリ）

- 各メッセージを、その時刻の直後にある checkpoint のコミット（trailer の Researchkit-Step・Researchkit-Question、
  Researchkit-Bootstrap、merge(<RQ>) のコミット）に割り振る。プロジェクトの全ブランチ（rq/* を含む）の履歴を読む。
- 親（セッションの jsonl）とサブエージェント（<jsonl と同じ名前のディレクトリ>/ の下の jsonl）を分けて数える。
- 文脈の読み込み = input_tokens + cache_creation_input_tokens + cache_read_input_tokens（呼び出しのたびに読み直す量）。
- 出力: RQ・ステップ・親子ごとの「呼び出し、文脈の読み込み（百万）、1 回あたりの文脈（千）、出力（千）、WebSearch の回数」の表。
セッションの記録の場所の例: ~/.claude/projects/-Users-<…>-<プロジェクト>/<session>.jsonl（設定ディレクトリを分けていれば ~/.claude-*/）。
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path

STEP_ORDER = ["R%d" % i for i in range(1, 13)] + ["Q2", "Q3", "Q4", "Q5", "Q6", "Q7-1", "Q7-2", "Q8", "Q9", "Q10",
                                                  "Q11", "Q12", "Q13"]


def checkpoints(project: Path) -> list[tuple[int, str, str]]:
    fmt = ("%ct%x09%(trailers:key=Researchkit-Step,valueonly,separator=)%x09"
           "%(trailers:key=Researchkit-Question,valueonly,separator=)%x09"
           "%(trailers:key=Researchkit-Bootstrap,valueonly,separator=)%x09%s")
    log = subprocess.run(["git", "-C", str(project), "log", "--all", f"--format={fmt}"], capture_output=True, text=True,
                         check=True).stdout
    out = []
    for line in log.splitlines():
        t, step, q, boot, subj = (line.split("\t") + [""] * 5)[:5]
        if step.strip():
            out.append((int(t), q.strip()[:3], step.strip()))
        elif boot.strip():
            out.append((int(t), "boot", boot.strip()))
        elif subj.startswith("merge("):
            out.append((int(t), subj[6:9], "Q13"))
    return sorted(out)


def ts(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", default=".", help="調査のプロジェクト（既定: 今のディレクトリ）")
    ap.add_argument("--session", action="append", required=True, help="セッションの jsonl（複数可）")
    ap.add_argument("--since", help="この時刻（ISO）より前のメッセージを数えない")
    ap.add_argument("--rq", help="この RQ の番号だけを出す")
    args = ap.parse_args()
    cps = checkpoints(Path(args.project))
    since = ts(args.since) if args.since else 0.0

    def label(t: float) -> tuple[str, str]:
        for c, rq, step in cps:
            if c >= t:
                return rq, step
        return "-", "after"

    agg: dict[tuple[str, str, str], list[float]] = defaultdict(lambda: [0, 0.0, 0.0, 0])
    seen: set = set()
    for sess in args.session:
        main_path = Path(sess).expanduser()
        files = [(main_path, "親")] + [(p, "子") for p in sorted(main_path.with_suffix("").rglob("*.jsonl"))]
        for path, who in files:
            for line in path.open(encoding="utf-8"):
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") != "assistant":
                    continue
                t = ts(d["timestamp"])
                if t < since:
                    continue
                m = d.get("message", {})
                rq, step = label(t)
                if args.rq and rq != args.rq:
                    continue
                a = agg[(rq, step, who)]
                for c in m.get("content", []) if isinstance(m.get("content"), list) else []:
                    if c.get("type") == "tool_use" and c.get("name") == "WebSearch" and ("ws", c.get("id")) not in seen:
                        seen.add(("ws", c.get("id")))
                        a[3] += 1
                u = m.get("usage")
                key = (str(path), m.get("id"))
                if not u or key in seen or m.get("model") == "<synthetic>":
                    continue
                seen.add(key)
                a[0] += 1
                a[1] += u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                a[2] += u.get("output_tokens", 0)

    def order(k):
        rq, step, who = k
        return (rq, STEP_ORDER.index(step) if step in STEP_ORDER else 99, who)

    print("| RQ | ステップ | 担当 | 呼び出し | 文脈の読み込み（百万） | 1 回あたり（千） | 出力（千） | WebSearch |")
    print("|---|---|---|---|---|---|---|---|")
    for k in sorted(agg, key=order):
        calls, ctx, outp, ws = agg[k]
        if not calls and not ws:
            continue
        avg = ctx / calls / 1e3 if calls else 0
        print(f"| {k[0]} | {k[1]} | {k[2]} | {int(calls)} | {ctx / 1e6:.1f} | {avg:.0f} | {outp / 1e3:.0f} | {int(ws)} |")


if __name__ == "__main__":
    main()
