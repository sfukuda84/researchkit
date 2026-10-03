# researchkit-analysis: 詳細（special.md）

[SKILL.md](../SKILL.md) の本文から移した詳細。本文の要点で足りないとき、ここを読む。見出しは本文と同じ番号を使う。

## 7. `000-research-foundation` のとき

分析環境が動くことを確かめる（steering「RQ の工程」）。主張は作らない。

1. `studies/000-research-foundation/analysis/00_smoke.py` に、`docs/method.md` で決めたライブラリを読み込み、小さな計算をして `out/smoke.json` に書くスクリプトを作る。
2. `commands.analysis` で実行し、2 回実行して出力が同じことを確かめる。
3. 使ったコマンド、言語とライブラリの版を `analysis/analysis.md` に書く。
4. 動かなければ、`docs/method.md` と `commands.analysis` を直すよう案内する（自動モードでは止まる）。

## 8. 自動モード（`--auto`）

| 場面 | 自動モードでの動作 |
|---|---|
| `plan.md` で決めきれていない分析の細部（図の形、表の並び） | 推奨案を採用する |
| 計画の変更が要る（指標・基準・比較の相手） | 推奨案を採用し、§5 で記録し、元の計画の結果も出す。`studies/<NNN-name>/auto-decisions.md` にも書く |
| 問い・範囲・反証条件を変える必要がある | 止まる |
| `commands.analysis` が空で、スクリプトが要る | 止まる |
| スクリプトの失敗 | 直して再実行する。同じ原因で 3 回失敗したら止まる |

## 9. 出力

- `studies/<NNN-name>/analysis/analysis.md`（様式: [templates/analysis.md](../templates/analysis.md)）
- 手法ごとの表（`analysis.md` の中か、`analysis/extraction.md`・`analysis/coding.md` など）
- スクリプト `studies/<NNN-name>/analysis/*.py`（または `.R`）と、出力 `analysis/out/*.json`、`analysis/out/fig/`
- `plan.md` の「計画の変更」（変えたとき）
- `tasks.md` の分析のタスクの `- [x]`

次の工程は `researchkit-findings`（Q10）である。チェックポイント（`research(<RQ>): 分析`）は呼び出し元（`researchkit-execute`・`researchkit-all`）が記録する。単独で実行したときは、最後に `$HELPER checkpoint <RQ_NAME> Q9 "<『ステップ番号』の節の subject>"` を記録する（`researchkit-worktree`）。

## 10. 完了報告

- 計画との対応（実施・一部・未実施・変更の件数）と、計画の変更（データを見る前か後か）
- 手法ごとの主な結果（数値は出力のキーを添える）
- 反証条件に当たる結果があったか（判定は Q10）
- 再現の確認の結果（スクリプトの数、2 回目の実行で出力が同じだったか）
- `$NUM` の結果
- 自動モードで記録した判断
- 次の案内: `researchkit-findings`（Q10）
