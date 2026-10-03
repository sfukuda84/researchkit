# researchkit-worktree: 詳細（finish.md）

[SKILL.md](../SKILL.md) の本文から移した詳細。本文の要点で足りないとき、ここを読む。見出しは本文と同じ番号を使う。

### Q13 片付け

1. **worktree の外に出てから**、`$HELPER finish <RQ_NAME> --phase <phase>` を実行する（`cd "$REPO_ROOT"`）。worktree の中で実行すると、スクリプトは止まる。スクリプトは次を行う。
   - 担当範囲の最終ステップ（design は Q7-2、execute と all は Q12）が完了し、`RQ_DIR` に `spec.md`・`plan.md`・`tasks.md` があることを確かめる。
   - execute と all では、`tasks.md` に `[人]` 以外の未完了のタスクがないことを確かめる（あれば `UNCHECKED_TASKS` で止まる。`[人]` だけなら続けて、最後に `HUMAN_TASKS_PENDING` を出す）。
   - worktree に、どのステップにも含まれない変更があれば止まる（`LEFTOVER_CHANGES`）。
   - `docs/questions/<RQ_NAME>.md` の状態欄と `README.md` の一覧の状態の列を更新し（`references/steps.md`）、`docs(<RQ_NAME>): 状態を「<状態>」に更新` としてコミットする。
   - メインの作業ツリーに未コミットの変更がないことを確かめ、`main` にいることを確かめる（いなければ `NOT_ON_MAIN`）。
   - `git merge --no-ff -m "merge(<RQ_NAME>): <phase>"` でマージする。ブランチがすでにマージ済み（競合を手で解消した後など）なら、マージを飛ばして片付けだけを行う。
   - worktree の `data/large/`（コミットしない大きな生データ）にあるファイルを、メインの作業ツリーの同じ場所に写す（既存のファイルは上書きしない。出力は `KEPT_LARGE_DATA`）。分析を再実行できるようにするためである。
   - worktree とブランチを削除する。そのほかの無視対象のファイル（`.env` など）は一緒に消えるので、出力の `REMOVED_IGNORED` に挙がったものはユーザーに知らせる。
   - 出力の `RQ_STATUS` が、更新した後の状態である。クラウドセッションでは、続けてマージ先のブランチを push する（§8）。
2. マージが済んだら（`finish` が成功したら）、メインの作業ツリー（`main`）で引き継ぎ書を更新してコミットする。trailer は付けない。

   ```bash
   $RK handover --note "<RQ_NAME> の <phase> を完了（状態: <RQ_STATUS>）"
   git add docs/handover && git commit -m "docs(handover): 引き継ぎ書を更新"
   ```

   引き継ぎ書の中身と、手で書く節（今の目標、次にやること、判断待ち）の直し方は `researchkit-status` の「引き継ぎ書」の節に従う。この RQ の作業で踏んだ罠があれば、`PITFALLS.md` にも足す。
   - **手で書く節を必ず見直す**: `finish` は最後に `HANDOVER:` の行で、これを促す。`handover` が `WARN STALE_MANUAL`（手で書く節が RQ のマージより前から変わっていない）を出したら、コミットする前に「次にやること」「判断待ち」を今の状態に合わせて直し、もう一度 `$RK handover` を実行して警告が消えたことを確かめる。自動の節の「次の候補（自動）」と「手で書く節が挙げる RQ と今の状態」を材料にする。自動モードでも直す（直すのは引き継ぎ書の文だけで、判断は変えない。判断待ちを片付けたことにしない）。
3. マージで競合したときは、worktree とブランチが残る。競合の内容をユーザーに示し、解消の方針を確かめてから、メインの作業ツリーで解消してマージをコミットし、もう一度 `finish` を実行する。マージコミットのメッセージは `merge(<RQ_NAME>): <phase>` のままにする。並行して進めた RQ が同じ出典ファイルの `used_in` や `docs/glossary.md` を変えたときに競合しやすい。両方の追記を残す形で解消する。
