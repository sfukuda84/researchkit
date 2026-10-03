# researchkit-review: 詳細（record.md）

[SKILL.md](../SKILL.md) の本文から移した詳細。本文の要点で足りないとき、ここを読む。見出しは本文と同じ番号を使う。

## 3. レビュー対象の特定

| 指定 | 対象 | 記録の置き場 |
|---|---|---|
| RQ（`001`、`001-market-size`）、または省略（今の worktree の RQ） | `studies/<NNN-name>/findings.md` を中心に、根拠の `evidence/`、`analysis/`、`search-log.md`、`plan.md`、使った `sources/` | `studies/<NNN-name>/reviews/review-<round>.md` |
| `999`、または RQ の工程の中の `reports/report.md` | `reports/report.md`、`reports/publish/`、`studies/999-research-report/findings.md`、報告書が参照する各 RQ の主張 | `studies/999-research-report/reviews/review-<round>.md` |
| ファイルのパス（工程の外。任意の報告書・資料） | そのファイルと、そこに書かれた出典 | `docs/reviews/<YYYYMMDD>-<対象>.md` |

- RQ の工程の外で RQ や報告書を見直すとき（`main` で後から見直すなど）も、記録は `docs/reviews/` に置く。
- 工程の外の資料で出典 ID がないものは、本文の出典の書き方（脚注、参考文献の一覧）を出典として扱い、Source 軸で 1 件ずつ確かめる。

## 5. 記録の様式

様式は [templates/review.md](../templates/review.md)。同じ回のファイルがあれば追記する（上書きしない）。

指摘の ID は `R<回>-<軸の頭文字><連番>`（例: `R1-N03`）。軸の頭文字は Source が `S`、Logic が `L`、Counter が `C`、Bias が `B`、Numbers が `N`、Ethics が `E` である。各指摘に、重大度、軸、場所（ファイルと行、主張の ID）、根拠、直し方、採否を書く。

| 重大度 | 目安 |
|---|---|
| CRITICAL | 出典が実在しない、等級 `D` を根拠にした、引用が原文と違う・原文にない、数値が出力や原文と一致しない、反証条件に当たる結果を無視した判定、個人を特定できる情報、同意や利用規約に反するデータ、憲章の違反 |
| HIGH | 主張と根拠の飛躍、相関を因果として書いた、範囲を越えた一般化、確度の過大、主要な反対の証拠の見落とし、孫引き、単位・母数・期間の誤り、答えの形に答えていない、スクリプトを再実行すると結果が変わる |
| MEDIUM | 古い出典、一次資料に当たれるのに二次資料、検索語の偏り、限界の書き漏れ、主張を変えない等級の付け誤り、計画の変更の記録漏れ |
| LOW | 表記、軽微な改善 |

## 6. 自動モード（`--auto`）

RQ の工程から呼ばれたときは、`researchkit-worktree` の自動モードの規則に従い、自動で決めたことを `studies/<NNN-name>/auto-decisions.md` に記録する。

| 場面 | 自動モードでの動作 |
|---|---|
| 採用した CRITICAL・HIGH・MEDIUM の修正 | 推奨案で直す。主張の結論や確度が変わる修正は、`auto-decisions.md` に見直しの優先度「高」で記録する |
| 指摘に答えて分析を足す（§4.4 の「追加」） | 探索的な分析として足し、反対の側に動きうる分析も同じ回で検討する。`auto-decisions.md` に見直しの優先度「高」で記録する |
| 不採用の判断 | 記録に理由を書いて進む |
| 保留にしたい指摘 | 推奨案を採る。決められないもの（決定・前提が崩れる、憲章・品質基準・`docs/method.md` の変更が要る）は止まる |
| 人の確認へ | `tasks.md` に `[人]` のタスクを足し、自動で完了にしない |
| Counter 軸で見つかった反対の証拠 | 登録して主張に反映する（確度を下げる、反証・限界に書く）。結論が覆るときは止まる |

止まる場面: 予算の STOP、上の表の止まる場合、同じ原因の失敗が 3 回続いた場合。

## 7. 出力

- `studies/<NNN-name>/reviews/review-<round>.md`（工程の外は `docs/reviews/<YYYYMMDD>-<対象>.md`。様式: [templates/review.md](../templates/review.md)）
- 修正した成果物（`findings.md`、`evidence/`、`analysis/`、`sources/`、逆流した文書、報告書）
- `tasks.md` に足した `[人]` のタスク（人の確認へ回したもの）

RQ の工程では、1 回目（Q11）の次は 2 回目のレビュー（Q12）、2 回目の次は `researchkit-worktree` の Q13（マージ）である。チェックポイント（`review(<RQ>): 5 軸レビュー（1 回目）`・`（2 回目）`）は呼び出し元（`researchkit-execute`・`researchkit-all`）が記録する。工程の外で単独で呼ばれたときは、チェックポイントを記録せず、記録と修正を通常のコミット（`review: <対象> のレビュー`）にしてよいかを確かめる。

## 8. 完了報告

- 記録のファイルのパス
- 軸ごとの指摘の件数（重大度別）と採否
- 直した指摘と、変わった主張・確度・判定（あれば）
- Counter 軸の検索の件数と、見つかった反対の証拠
- 保留にした指摘と、ユーザーに判断してほしい事項（選択肢と推奨案）
- 人の確認に回したもの（足した `[人]` のタスク）
- `$CHECK` と `$NUM` の結果、スクリプトの再実行の結果
- 次の案内: 1 回目の後は 2 回目（`--round 2`）、2 回目の後は Q13（`researchkit-worktree` の `finish`）
