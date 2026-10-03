# researchkit-worktree: 詳細（arguments.md）

[SKILL.md](../SKILL.md) の本文から移した詳細。本文の要点で足りないとき、ここを読む。見出しは本文と同じ番号を使う。

## 6. 引数の解釈と複数の RQ の進め方

| 指定 | 例 | 動作 |
|---|---|---|
| 単一 | `1`、`003`、`003-market-size`、`market-size` | `$HELPER resolve` で 1 件に決める |
| 範囲 | `002-005`、`002..005` | `$HELPER list` の結果から、番号が範囲内のものを着手順に選ぶ |
| 全件 | `all` | `$HELPER next --phase <phase>` を、空になるまで繰り返す |
| なし | （空） | `$HELPER next --phase <phase>` の 1 件。空なら対象なしと報告する |
| 自動モード | `--auto`、`002-005 --auto`、`--auto all` | 上のいずれかと組み合わせる。質問せずに推奨案を採用して進める（§7） |

- `--auto` は位置を問わない。RQ の指定を解釈する前に取り除き、`$HELPER` には渡さない。
- 一覧にない新しい RQ は、`004-short-name` の形の完全名で指定する。ただし、RQ は `researchkit-questions` で `docs/questions/` に足してから進めることを勧める（概要ファイルがないと、状態の更新と `validate.py` の検証ができない）。
- 複数の RQ は 1 件ずつ直列に進める。前の RQ の Q13（マージ）が終わってから、次の RQ の Q1 に進む。後の RQ は、前の RQ の成果（出典、`findings.md`、逆流の更新）を含む最新の `main` から分岐する。
- 各 RQ の Q1 の前に §5 の予算を確かめる。STOP なら、残りの RQ に進まずに止まる。
- `999-research-report` は、ほかのすべての RQ が `完了` か `人の作業待ち` になるまで `next` の候補にならず、`ensure` は `DEPENDENCY_PENDING` で止まる。範囲や `all` の最後に来たときに進める。
- 範囲指定の途中で `ALREADY_DESIGNED` や `ALREADY_EXECUTED` になった RQ は、飛ばしたことを記録して次に進む。それ以外の理由で止まったときは、飛ばして続けるか中断するかをユーザーに確かめる（自動モードでは確かめずに飛ばす。§7『止まったときの扱い』）。
- `all` で飛ばした RQ は、以降の `next` に `--skip <飛ばしたもの,...>` を付けて除く（付けないと、途中の worktree が残っている RQ がまた選ばれる）。
