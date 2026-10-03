# researchkit-collect: 詳細（special.md）

[SKILL.md](../SKILL.md) の本文から移した詳細。本文の要点で足りないとき、ここを読む。見出しは本文と同じ番号を使う。

## 9. `000-research-foundation` のとき

主張は作らない。次を整える（steering「RQ の工程」）。

- `sources/` の共通の出典（`S000-*`。複数の RQ で使う統計や基本文献）の登録
- 用語集（`docs/glossary.md`）の項目の定義と、その出典
- `data/manifest.md` の表の用意と、共通のデータの取得
- 分析環境の用意（`commands.analysis` が実行できること。確かめるのは Q9）
- `search-log.md` の形式の見本（`000-research-foundation.md` の定め）

## 10. 自動モード（`--auto`）

| 場面 | 自動モードでの動作 |
|---|---|
| 検索式の言い換え・追加（`plan.md` の範囲の中） | 行い、`search-log.md` に書く。範囲（地域・期間・対象）を変える追加はしない |
| 検索式・データ源の変更 | 推奨案を採用し、`plan.md` の「計画の変更」と `studies/<NNN-name>/auto-decisions.md` に記録する |
| 等級の判断に迷う出典 | 低い方の等級にし、`auto-decisions.md` に記録する |
| 有料・会員限定の資料 | 入手しない。`[人]` のタスクを足す提案を完了報告に書く |
| `[人]` のタスク | 実行せず、`[x]` にしない（§8） |

止まる場面: 予算の STOP、§8 の最後の場合、`docs/method.md` や憲章の変更が要る場合、同じ原因の取得の失敗が 3 回続いた場合。

## 12. 出力

- `sources/<ID>.md`（新規と、`used_in` を足した既存のもの）
- `studies/<NNN-name>/evidence/<ID>.md`（様式: [templates/evidence.md](../templates/evidence.md)）
- `studies/<NNN-name>/search-log.md`
- `data/raw/`、`data/manifest.md`（データを取得したとき）
- `studies/<NNN-name>/tasks.md`（収集のタスクの `- [x]`）
- `studies/<NNN-name>/plan.md` の「計画の変更」（変えたとき）

次の工程は `researchkit-analysis`（Q9）である。チェックポイント（`research(<RQ>): 収集`）は呼び出し元（`researchkit-execute`・`researchkit-all`）が記録する。単独で実行したときは、最後に `$HELPER checkpoint <RQ_NAME> Q8 "<『ステップ番号』の節の subject>"` を記録する（`researchkit-worktree`）。RQ の工程として続けるときは `researchkit-execute` を案内する。

## 13. 完了報告

- 実行したタスクと、残った `[人]` のタスク（人が行うことと、完了の確かめ方）
- 登録した出典の件数（等級別、一次資料の数）と、`used_in` を足した既存の出典
- 実在を確かめられなかった候補（等級 `D`）
- 検索の件数（ログの行数、うち反証の検索）と、見つからなかったことの要約
- 取得したデータと目録の行
- `plan.md` の計画の変更（あれば）と、自動モードで記録した判断
- `$CHECK` の結果
- 次の案内: `researchkit-analysis`（Q9）
