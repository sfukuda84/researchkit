# researchkit-findings: 詳細（inputs-outputs.md）

[SKILL.md](../SKILL.md) の本文から移した詳細。本文の要点で足りないとき、ここを読む。見出しは本文と同じ番号を使う。

## 2. 入力

| 入力 | 用途 |
|---|---|
| `studies/<NNN-name>/spec.md` | 問い、つながる決定、答えの形、判定の基準、範囲外 |
| `studies/<NNN-name>/plan.md` | 分析の計画、反証条件、計画の変更 |
| `studies/<NNN-name>/tasks.md` | 残作業の照合 |
| `studies/<NNN-name>/analysis/`（`analysis.md`、表、`out/*.json`） | 分析の結果、反証条件の照合の材料 |
| `studies/<NNN-name>/evidence/`、`search-log.md`、`sources/` | 根拠、探した範囲 |
| `docs/study/hypotheses.md`、`issue-tree.md` | 仮説と反証条件、イシューツリー |
| `docs/questions/`、`docs/concept/seed.md`、`premises.md` | 逆流の行き先、決定（`D1`〜） |
| 憲章、`docs/quality.md`、`config.yaml` の `confidence.levels`・`sources.min_grade` | 確度の段階と付け方、最低等級 |

分析（Q9）の成果物がなければ、`researchkit-analysis` を案内する。

## 13. 出力

- `studies/<NNN-name>/findings.md`（様式: [templates/findings.md](../templates/findings.md)）
- 逆流した文書（`docs/study/hypotheses.md`、`issue-tree.md`、`docs/questions/`、`docs/glossary.md`、`docs/concept/backlog.md`）
- `studies/<NNN-name>/tasks.md` の `## 収束` の節（ずれがあったとき）と、収束のタスクで直した成果物

次の工程は `researchkit-review`（Q11、5 軸レビューの 1 回目）である。チェックポイント（`research(<RQ>): 主張をまとめる`）は呼び出し元（`researchkit-execute`・`researchkit-all`）が記録する。単独で実行したときは、最後に `$HELPER checkpoint <RQ_NAME> Q10 "<『ステップ番号』の節の subject>"` を記録する（`researchkit-worktree`）。

## 14. 完了報告

- 答え（1〜3 文）と、判定の基準ごとの結果
- 主張の件数（確度別）と、主な主張
- 仮説ごとの判定（支持・棄却・保留）
- 残った問い
- 逆流で変えた文書と、ユーザーに伝えるべき決定・前提の揺らぎ
- 収束のタスク（足した件数と、残ったもの）
- `$CHECK` と `$NUM` の結果
- 統合モードのとき: 整合の表の要約（直した結論、RQ どうしの食い違い、元の主張に見つけた誤り）
- 次の案内: `researchkit-review`（Q11）
