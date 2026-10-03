---
name: "researchkit-all"
description: "問い（RQ）の設計の工程と実行の工程を 1 つの Git worktree で通して実行する統括スキル。Web 検索の予算の確認、worktree の準備（既存があれば再利用して続きから再開）、researchkit-question の設計の工程（specify・clarify ×2・plan・tasks・analyze ×2）、researchkit-execute の実行の工程（collect・analysis・findings・5 軸レビュー ×2）を途中でマージせずに続けて行い、最後に main へのマージ、引き継ぎ書の更新、後片付けを行う。RQ の工程の Q1〜Q13（--phase all）。範囲や all を指定すると 1 件ずつ直列に進め、予算が足りなくなったら工程の境目で止まる。--auto を付けると、質問せずに推奨案を採用して進める。「次の問いを進めて」「001 を調べて」「全部の RQ を進めて」と言われたとき、または /researchkit-all と打たれたときに使う。"
argument-hint: "RQ の番号または範囲と、任意の --auto（例: 001, 002-005, all, all --auto, 999, または省略して次の未完了）"
compatibility: "Requires git and Python 3.9+, researchkit project structure with .researchkit/config.yaml"
user-invocable: true
disable-model-invocation: false
---

# researchkit-all スキル（通し: Q1 → Q2〜Q12 → Q13）

設計の工程と実行の工程を、1 つの worktree の中で途中マージなしに通して実行する。本体の手順はこのファイルには書かず、次の 2 つのファイルの「§3 本体」をそのまま使う。

- 設計の工程 Q2〜Q7-2: [`researchkit-question` の §3](../researchkit-question/SKILL.md)
- 実行の工程 Q8〜Q12: [`researchkit-execute` の §3](../researchkit-execute/SKILL.md)

**ステップ番号、ヘルパースクリプト（`$HELPER`）、再開、安全規則、対話、引数の解釈、自動モードは [`researchkit-worktree`](../researchkit-worktree/SKILL.md) に従う。** 作業を始める前に、`researchkit-worktree`、`researchkit-question`、`researchkit-execute` の 3 つの SKILL.md を読むこと。この文書では、`researchkit-worktree` の節を「『ステップ番号』の節」のように見出しの名前で参照する。

パスは既定の配置で書いている。`.researchkit/config.yaml` の `paths` で読み替える。`$RK`、`$HELPER` の意味は steering の「エージェントの行動規範」のとおりである。

## 1. ユーザー入力・引数

```text
$ARGUMENTS
```

引数の解釈は、`researchkit-worktree` の『引数の解釈と複数の RQ の進め方』の節に従う。自動検出では `--phase all` を使う。

- 範囲（`002-005`）や `all` を指定したときは、**1 件ずつ直列に**進める。前の RQ の Q13（マージ）が終わってから、次の RQ の Q1 に進む。後の RQ は、前の RQ の `findings.md` と逆流の更新を含む最新の `main` から分岐する。
- `all` は `$HELPER next --phase all` を空になるまで繰り返す。`999-research-report` は、ほかのすべての RQ が `完了` か `人の作業待ち` になるまで `next` の候補にならない。ほかが終わった時点で候補になり、最後に進む。
- 引数に `--auto` があるときは、設計の工程から Q13 までのすべての質問を『自動モード』の節で扱う。`researchkit-question` と `researchkit-execute` の本文にある 💬 の質問も、質問せずに推奨案を採用する。自動モードでも止まる場面（マージの競合、憲章・品質基準・`docs/method.md` の変更が要るとき、`[人]` のタスクが終わらないと先に進めないとき、同じ原因の失敗が 3 回続いたとき、Web 検索の予算が足りないとき）では、『止まったときの扱い』の節に従う。

## 2. 実行の流れ

始める前に、調査全体の工程が終わっていることを確かめる。`$RK bootstrap` の `NEXT_STEP` が `DONE` でなければ、残っているステップを示し、先に `researchkit-bootstrap` を実行するよう案内する。既存の調査に取り込んだ（`--adopt`）などで工程の記録がないときは、`docs/questions/` と憲章があれば、ユーザーに確かめて進めてよい（自動モードでは、両方があれば進める）。同じセッションで調査全体の工程（R12）を終えたばかりなら、ここでは始めずに、新しいセッションで実行するよう案内する（steering の「セッションの区切り」）。

対象の RQ ごとに、次を順に行う。

1. **予算の確認**: `$RK budget --step rq --rq <RQ>` を実行する。`VERDICT: STOP`（終了コード 4）なら、この RQ に入らずに止まる。これは失敗ではなく区切りであり、新しいセッションで同じスキルを同じ引数で実行すれば続きから再開する。途中の RQ を再開するときは、残りのステップの分だけを見積もってよい（設計の工程が済んでいれば `--step Q8 --rq <RQ_NAME>`、Q11 から先だけなら `--step Q11 --rq <RQ_NAME>`）。
2. **Q1 準備**: 『Q1 準備』の節に従い、`$HELPER ensure <RQ> --phase all` を実行する。
   - 設計がすでに `main` にマージ済みの RQ は、Q2〜Q7-2 が完了済みと判定され、`NEXT_STEP` が Q8 になる。
   - `999-research-report` で `PRECONDITION: DEPENDENCY_PENDING` が出たら、残っている RQ を示して止まる（範囲指定なら飛ばす）。
3. **設計の工程**: `researchkit-question` の §3 の Q2〜Q7-2 のうち、`NEXT_STEP` 以降を順に実行する。
   - `researchkit-question` の §2（Q1 と Q13）は実行しない。**Q7-2 の後で `finish` を実行せず、マージしないこと。**
4. **実行の工程**: 同じ worktree のまま、`researchkit-execute` の §3 の Q8〜Q12 を順に実行する。
   - **Q8 の前に `$RK budget --step Q8 --rq <RQ_NAME>`、Q11 の前に `$RK budget --step Q11 --rq <RQ_NAME>` を実行する。** STOP なら、そのステップに入らずに止まる。それまでのチェックポイントは記録済みなので、次のセッションでそのステップから再開する。
   - `researchkit-execute` の §2（予算の確認、Q1、Q13）は実行しない。worktree を作り直さないこと。
5. **Q13 片付け**: 『Q13 片付け』の節に従い、`$HELPER finish <RQ_NAME> --phase all` を実行し、引き継ぎ書を更新してコミットする。状態は `完了`、`[人]` のタスクが残れば `人の作業待ち` になる。
6. 次の RQ があれば 1 に戻る。回数を数えられない環境（`budget` が `VERDICT: UNMETERED`）では、このセッションで `session.rqs_unmetered`（既定 1）件の RQ を終えたところで止まる。

`000-research-foundation` と `999-research-report` は、`researchkit-question` と `researchkit-execute` の「000 と 999 の扱い」の節のとおりに読み替えて進める。`000` は主張を作らない基盤づくりである。`999` は、Q8 が `researchkit-synthesize`、Q9 が `researchkit-publish`、Q10 が `researchkit-findings` の統合モードになる。

途中で中断した場合は、もう一度 `researchkit-all` を実行すれば、残っている worktree を使って続きのステップから再開する。設計の工程の途中なら `researchkit-question`、実行の工程の途中なら `researchkit-execute` で再開することもできる。その場合は、再開したスキルの Q13 で `main` にマージされる。

予算や自動モードの止まる場面以外でセッションを区切るとき（コンテキストが長くなった、作業を人に引き継ぐなど）は、ステップの境目で止め、`$RK handover --note "<止めた理由と次の作業>"` で引き継ぎ書を更新する。worktree の中で止めたときは、引き継ぎ書はコミットせずに残してよい（次の Q13 の更新で上書きされる）。

## 3. 完了報告

各 RQ の完了時と、指定範囲の全体の完了時に、`researchkit-question` §4 と `researchkit-execute` §4 の項目をまとめて報告する。

- 完了した RQ の名前と番号、マージコミット
- 設計の工程の要約（問いと答えの形、clarify で確定した決定事項、計画の手法と反証条件、analyze の検証結果）
- 実行の工程の要約（出典の件数〈等級別〉、分析の出力、判定の基準ごとの答えと確度、反証条件に当たった仮説、逆流で直した上流の文書、レビューで直した指摘）
- 残っている `[人]` のタスク（`finish` の `HUMAN_TASKS_PENDING`）と、片付けた後の手順（『人のタスクの片付け』の節）
- 飛ばした、または中断した RQ とその理由。予算で止まったときは、使った回数・残り（`budget` の出力）と、再開の方法（新しいセッションで同じスキルを同じ引数で実行する）
- `--auto` のとき: 自動で採用した判断の要約（各 RQ の `auto-decisions.md`。見直しを勧める判断を先に）と、止まった RQ についてユーザーに判断してほしい事項
- 次の案内: `$HELPER next --phase all` の結果。すべての RQ が終わり `999-research-report` も完了したら、`reports/report.md` と `researchkit-review` による報告書全体のレビューを勧める。仮説や問いの立て方が大きく崩れたときは、`researchkit-hypothesis` や `researchkit-questions` での見直しを勧める
