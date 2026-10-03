# researchkit-execute: 詳細（special.md）

[SKILL.md](../SKILL.md) の本文から移した詳細。本文の要点で足りないとき、ここを読む。見出しは本文と同じ番号を使う。

### 000 と 999 の扱い

予約番号の RQ は、Q8〜Q10 を次のように読み替える（steering の「RQ の工程」の注記）。Q11・Q12 のレビューは、どちらも行う。

| RQ | Q8 | Q9 | Q10 |
|---|---|---|---|
| `000-research-foundation` | `researchkit-collect` で、出典台帳（共通の出典 `S000-*`）、用語集 `docs/glossary.md`、データの目録 `data/manifest.md`、分析環境（`commands.analysis`）、検索ログの形式を整える | `researchkit-analysis` で、分析環境が動くことを確かめる（小さなスクリプトを `commands.analysis` で実行し、`out/` に出力が出る） | `researchkit-findings` で、残作業を `tasks.md` にまとめる。**主張は作らない**（`findings.md` は基盤の状態の記録にする） |
| `999-research-report` | `researchkit-synthesize` で、全 RQ の `findings.md` を統合し、`reports/report.md` を作る | `researchkit-publish` で、読み手に合わせた形式を作る。不要なら、その旨を記録して空のチェックポイントにする | `researchkit-findings` の統合モードで、報告の結論と各 RQ の `findings.md` の整合を確かめ、逆流を行う |

000 では、Q8 の予算の確認は `--step Q8` のままでよい（検索が少なければ残りは多く残る）。999 の数値の参照は、`reports/report.md` ではリポジトリのルートからの相対パス、`studies/999-research-report/findings.md` では RQ のディレクトリからの相対パス（`../001-.../analysis/out/...`）で書く（steering の「数値の参照」）。

## 4. 完了報告

各 RQ の完了時と、指定範囲の全体の完了時に、次を報告する。

- 完了した RQ の名前と番号、マージコミット
- 収集の要約（出典の件数〈等級別〉、検索の件数、見つからなかったこと、未確認〈`D`〉にした出典）
- 分析の要約（スクリプト、主な出力、計画の変更があればその内容と理由）
- 主張の要約（判定の基準ごとの答え、確度、反証条件に当たった仮説、残った問い）と、逆流で直した上流の文書
- レビュー 2 回で見つかって直した指摘（軸ごと）と、採らなかった指摘とその理由
- `check.py` と `numbers.py` の結果
- 残っている `[人]` のタスク（`finish` の `HUMAN_TASKS_PENDING`）と、片付けた後の手順（`researchkit-worktree` の『人のタスクの片付け』の節）
- 飛ばした、または中断した RQ とその理由。予算で止まったときは、そのことと再開の方法（新しいセッションで同じ引数で実行する）
- `--auto` のとき: 自動で採用した判断の要約（`RQ_DIR/auto-decisions.md`。見直しを勧める判断を先に）と、止まった RQ についてユーザーに判断してほしい事項
- 次の案内: `$HELPER next --phase execute` の結果。すべての RQ が `完了` か `人の作業待ち` になったら、`999-research-report` を `researchkit-all 999` で進めるよう勧める
