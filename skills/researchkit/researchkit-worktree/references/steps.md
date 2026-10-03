# researchkit-worktree: 詳細（steps.md）

[SKILL.md](../SKILL.md) の本文から移した詳細。本文の要点で足りないとき、ここを読む。見出しは本文と同じ番号を使う。

## 2. ステップ番号

ステップ番号は 3 スキルで共通の通し番号であり、進捗の記録と再開の判定に使う。

| ステップ | 内容 | 担当スキル（本体） | チェックポイントの subject |
|---|---|---|---|
| Q1 | 準備（`ensure`） | 3 スキル共通 | （コミットなし） |
| Q2 | 問いの仕様 | researchkit-specify | `docs(<RQ_NAME>): 問いの仕様を作成` |
| Q3 | 明確化 1 回目 | researchkit-clarify | `docs(<RQ_NAME>): 仕様を明確化（1 回目）` |
| Q4 | 明確化 2 回目（調査特有の曖昧さ） | researchkit-clarify | `docs(<RQ_NAME>): 仕様を明確化（2 回目）` |
| Q5 | 調査計画 | researchkit-plan | `docs(<RQ_NAME>): 調査計画を作成` |
| Q6 | タスク | researchkit-tasks | `docs(<RQ_NAME>): タスクを作成` |
| Q7-1 | 整合性の検証 1 回目（検出と修正） | researchkit-analyze | `docs(<RQ_NAME>): 整合性を検証（1 回目）` |
| Q7-2 | 整合性の検証 2 回目（確認） | researchkit-analyze | `docs(<RQ_NAME>): 整合性を検証（2 回目）` |
| Q8 | 収集 | researchkit-collect | `research(<RQ_NAME>): 収集` |
| Q9 | 分析 | researchkit-analysis | `research(<RQ_NAME>): 分析` |
| Q10 | 主張のまとめと逆流 | researchkit-findings | `research(<RQ_NAME>): 主張をまとめる` |
| Q11 | 5 軸レビュー 1 回目と修正 | researchkit-review | `review(<RQ_NAME>): 5 軸レビュー（1 回目）` |
| Q12 | 5 軸レビュー 2 回目と修正 | researchkit-review | `review(<RQ_NAME>): 5 軸レビュー（2 回目）` |
| Q13 | 片付け（`finish`） | 3 スキル共通 | `merge(<RQ_NAME>): <phase>`（自動。進捗の判定に使うため、この形は変えない） |

- フェーズとステップの対応: `design` は Q2〜Q7-2（`researchkit-question`）、`execute` は Q8〜Q12（`researchkit-execute`）、`all` は Q2〜Q12（`researchkit-all`）。どのフェーズも Q1 で始まり Q13 で終わる。
- `999-research-report` では、Q8 の本体が `researchkit-synthesize`、Q9 が `researchkit-publish`（不要なら、その旨を記録して空のチェックポイントにする）、Q10 が `researchkit-findings` の統合モードになる。ステップ番号と subject は変えない。
- `000-research-foundation` は主張を作らない。Q8 で出典台帳・用語集・データの目録・分析環境を整え、Q9 で分析環境が動くことを確かめ、Q10 で残作業をまとめる。ステップ番号と subject は変えない。

`checkpoint` はコミットに trailer `Researchkit-Step: <step>` と `Researchkit-Question: <RQ_NAME>` を付ける。変更がないステップも空コミットで記録する（飛ばさない）。進捗は、`main` とブランチにあるこの trailer、`main` にマージ済みの `studies/<RQ_NAME>/tasks.md`、`merge(<RQ_NAME>): execute|all` のマージコミットから判定する。trailer には RQ の名前が入っているので、競合を手で解消してマージした後に `finish` を再実行しても進捗は失われない。Pull Request などで取り込んだ RQ は、`main` に `findings.md` があり、`tasks.md` の `[人]` 以外のタスクがすべて `- [x]` なら、実行済みとみなす。

RQ の概要ファイル（`docs/questions/<RQ_NAME>.md`）のヘッダ行の `**状態**` と、`docs/questions/README.md` の一覧の「状態」の列は、`finish` が更新する。設計の工程の後は `設計済み`（今の状態が `未着手` のときだけ）、実行の工程（execute / all）の後は `完了` にする。`tasks.md` に未完了の `[人]` のタスクが残っていれば、`完了` ではなく `人の作業待ち` にする。状態を手で書き換える必要はない。
