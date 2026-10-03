# researchkit-worktree: 詳細（cloud.md）

[SKILL.md](../SKILL.md) の本文から移した詳細。本文の要点で足りないとき、ここを読む。見出しは本文と同じ番号を使う。

## 8. クラウドセッション

環境変数 `CLAUDE_CODE_REMOTE` が `true`（Claude Code のクラウドセッション）のときだけ当てはまる。規則は steering の「Claude Code のクラウドセッション」に従う。

- **マージ先**: `RESEARCHKIT_MAIN_BRANCH` がなければ、`$HELPER` はメインの作業ツリーの今のブランチ（セッションの作業ブランチ）をマージ先にする。この文書の `main` は、その作業ブランチに読み替える。メインの作業ツリーが `rq/*` のブランチや detached HEAD にいるときは判定できないので、`main` に戻る。
- **push**: `finish` はマージの後に、マージ先のブランチを origin に push する。出力は `PUSHED`、`PUSH_SKIPPED`（origin がない）、`PUSH_FAILED` のいずれかである。`PUSH_FAILED` のときもマージは済んでいるので、その内容をユーザーに伝える。引き継ぎ書のコミットや、人のタスクの片付けのコミットなど、作業ブランチへのコミットの後も、そのたびに push する。`main` へは PR で取り込む。
- **中断と再開**: `rq/*` のブランチは push できず、VM が回収されると消える。1 つの RQ は 1 つのセッションで `finish` まで進める。予算で止まりそうな RQ（文献レビューなど検索の多いもの）は、セッションの初めに着手する。
- **質問**: `--auto` で進めることを勧める。
- **Web 調査**: WebFetch が失敗したら、WebSearch の結果で進める。ページを開けなかった出典は、その旨を `verified_by` に書き、等級を 1 段下げる。数値を推測で埋めない。

## 9. 手動での利用

ユーザーからこのスキルを直接呼ばれたときは、引数に応じて次を行う。

- `status`（または引数なし）: `$HELPER status` の結果を表示し、途中の worktree があれば、再開に使うスキル（Q2〜Q7-2 は `researchkit-question`、Q8〜Q12 は `researchkit-execute`、どちらでも `researchkit-all`）を案内する。人の作業が残っている RQ があれば、`human-tasks` での確認を案内する。
- `human-tasks [<RQ>]`: 結果を表示する。ユーザーが完了を伝えたら、§3『人のタスクの片付け』の手順に従う。
- `sync-status <RQ>`: §3『人のタスクの片付け』の手順に従う。
- `next --phase <phase>`: 結果を表示する。
- `abort <RQ>`: §3『中止』の手順に従う。
