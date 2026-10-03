---
name: "researchkit-worktree"
description: "researchkit-question・researchkit-execute・researchkit-all が共通で使う worktree 管理スキル。問い（RQ）ごとの Git worktree とブランチ（rq/<NNN-name>）の準備（既存があれば再利用）、ステップ完了ごとの進捗コミット、main への --no-ff マージと RQ の状態の更新と片付け、中止、進捗の確認、[人] のタスクの片付けを行う。RQ の工程の Q1 と Q13。3 スキル共通の実行規則（ステップ番号とチェックポイントの subject、再開、安全規則、対話、引数の解釈、自動モード --auto と止まる場面、セッションの区切り、クラウドセッション）もここに定める。「RQ の進捗を見せて」「worktree を破棄して」「人の作業が終わった」と言われたとき、または /researchkit-worktree と打たれたときにも使う。"
argument-hint: "status | next --phase design|execute|all | human-tasks [<RQ>] | sync-status <RQ> | abort <RQ>"
compatibility: "Requires git and Python 3.9+, researchkit project structure with .researchkit/config.yaml"
user-invocable: true
disable-model-invocation: false
---

# researchkit-worktree スキル（worktree 管理と共通実行規則）

`researchkit-question`（設計の工程）、`researchkit-execute`（実行の工程）、`researchkit-all`（通し）の 3 スキルが共通で使う。RQ の作業はすべて `.worktrees/<RQ_NAME>`（ブランチ `rq/<RQ_NAME>`）で行い、ステップが終わるたびにコミットして進捗を記録する。中断しても、どのスキルからでも、どのセッションからでも、続きのステップから再開できる。

Claude Code、Codex CLI、Antigravity、Kiro CLI、opencode のいずれでも同じ手順で動く。パスは既定の配置で書いている。`.researchkit/config.yaml` の `paths` で読み替える（`worktree_helper.py` は `paths.questions`、`paths.studies`、`paths.data` を読む）。

## 1. ヘルパースクリプト

`skills/researchkit/rk helper <command> ...`（以降 `$HELPER`。`python3 <skills>/researchkit-worktree/scripts/worktree_helper.py` と同じ）。プロジェクトのルートからでも worktree の中からでも動く。マージ先は環境変数 `RESEARCHKIT_MAIN_BRANCH`、なければ `main`。

- 主なコマンド: `ensure <RQ> --phase design|execute|all`（Q1）、`state`、`checkpoint <RQ> <step> "<subject>"`、`finish <RQ> --phase …`（Q13。worktree の外で）、`next --phase …`、`status`、`human-tasks [<RQ>]`、`sync-status <RQ>`、`abort <RQ> [--yes]`、`list`、`resolve`。`<RQ>` は番号・スラッグ・完全名・パスのどれでもよい。
- `ensure`・`state` の出力: `REPO_ROOT`、`RQ_NAME`、`BRANCH`、`WORKTREE_DIR`、`WORKTREE_STATE`（created / reused / reattached / present / absent）、`PHASE`、`COMPLETED_STEPS`、`NEXT_STEP`。再利用したときは `UNCOMMITTED_CHANGES` と `UNRECORDED_DATA` も出る（『再開』）。
- 終了コード 3 は前提条件を満たさない（標準エラーに `PRECONDITION: <code>`）。`ALREADY_DESIGNED`、`ALREADY_EXECUTED`、`EXECUTE_IN_PROGRESS`、`DESIGN_INCOMPLETE`、`DESIGN_MISSING`、`DEPENDENCY_PENDING`、`LEFTOVER_CHANGES`、`NOT_ON_MAIN`、`UNCHECKED_TASKS`。

コマンドの表、出力の例、前提条件のコードごとの対応、`HUMAN_TASKS_PENDING` の扱いは [references/helper.md](references/helper.md)。

## 2. ステップ番号

ステップは 3 スキルで共通の通し番号（Q1 準備、Q2 仕様、Q3〜Q4 明確化、Q5 計画、Q6 タスク、Q7-1〜Q7-2 整合性の検証、Q8 収集、Q9 分析、Q10 主張のまとめ、Q11〜Q12 5 軸レビュー、Q13 片付け）。`design` は Q2〜Q7-2、`execute` は Q8〜Q12、`all` は Q2〜Q12 で、どれも Q1 で始まり Q13 で終わる。`999-research-report` は Q8 が `researchkit-synthesize`、Q9 が `researchkit-publish`、Q10 が `researchkit-findings` の統合モード、`000-research-foundation` は主張を作らない（番号と subject は変えない）。

- ステップが終わったら `$HELPER checkpoint <RQ_NAME> <step>` で記録する。subject は省くと既定の形（例: `research(<RQ_NAME>): 収集`）になる。変更がなくても空コミットで記録する（飛ばさない）。
- 進捗は trailer `Researchkit-Step`・`Researchkit-Question` と `merge(<RQ_NAME>): <phase>` のマージコミットから判定する。RQ の状態欄は `finish` が更新する（手で書き換えない）。

ステップごとの担当スキルと subject の表、進捗の判定と状態欄の規則の全文は [references/steps.md](references/steps.md)。

## 3. 共通手順

### Q1 準備

1. 調査全体の工程が終わっていることを確かめる（`$RK bootstrap` の `NEXT_STEP` が `DONE`）。終わっていなければ、残っているステップを示し、先に `researchkit-bootstrap` を案内する。既存の調査に取り込んだ（`--adopt`）などで工程の記録がないときは、`docs/questions/` と憲章があれば、ユーザーに確かめて進めてよい。
2. Web 検索の予算を確かめる（§5）。
3. `$HELPER ensure <RQ> --phase <phase>` を実行する。`<phase>` は、`researchkit-question` が `design`、`researchkit-execute` が `execute`、`researchkit-all` が `all` である。
4. 終了コードが 3 のときは、§1 の表に従って案内し、その RQ の作業を止める。
5. 出力から `RQ_NAME`、`REPO_ROOT`、`WORKTREE_DIR`、`NEXT_STEP` を控える。以降、`studies/<RQ_NAME>` を `RQ_DIR` と書く。
6. `WORKTREE_STATE` が `reused` か `reattached` のときは、下の『再開』に従う。
7. `NEXT_STEP` が担当範囲の最後より後（`Q13`）なら、本体のステップを飛ばして Q13 に進む。

### 再開

- 途中で止まった RQ は、同じスキル（または担当範囲を含む別の統括スキル）をもう一度実行すれば、`ensure` が既存の worktree を再利用し（`reused`）、ブランチだけが残っていれば worktree を作り直して（`reattached`）、`NEXT_STEP` から続ける。セッションをまたいでも、エージェントを変えても同じである。
- 再開のときは、`COMPLETED_STEPS` と `NEXT_STEP` をユーザーに示し、`NEXT_STEP` から再開してよいかを確かめる（自動モードでは確かめずに再開する）。ユーザーが別のステップからのやり直しを指示したら、そのステップから進める。完了済みの記録は残したまま、成果物を更新し、そのステップの `checkpoint` を記録し直す。
- 再開の前に、`docs/handover/CURRENT_STATE.md` と `PITFALLS.md` を読み、止まった理由と判断待ちの事項を確かめる。止まった理由が解消していなければ、先にそれを片付ける。引き継ぎ書は「今の目標」「次にやること」と、この RQ の判断待ちだけを読めばよい（ほかの RQ の判断待ちや測定の表は読み飛ばす）。
- **再開の直後に読む量を絞る**: 区切り（`SPLIT_SESSION`、予算の STOP）の後の新しいセッションは、文脈が小さいうちに始まる。ここで読んだものは、以降のすべての呼び出しで読み直される。SKILL.md は、この文書と、残っている工程の統括スキル（実行の工程なら `researchkit-execute`）とそのステップのスキルの本文だけを読む。RQ の文書は `$RK brief <RQ_NAME> --step <NEXT_STEP>` で読み、`spec.md`・`plan.md`・`tasks.md` を全文で読まない。
- `ensure` は、再利用した worktree にどのステップのコミットにも入っていない変更があると `UNCOMMITTED_CHANGES: <件数>` を出し、そのうち目録（`data/manifest.md`）にない `data/raw/` のファイルを `UNRECORDED_DATA: <件数>` と一覧で出す。前のセッションが収集（Q8）の途中で切れた跡である。続きのステップに入る前に、ファイルごとに出どころ（URL、statInfId）を確かめ、取り直して SHA-256 が一致したものを `$RK data add` で目録に載せる（`researchkit-status` の §8）。出どころが分からないファイルは根拠に使わず、ユーザーに確かめてから取り除く（自動モードでは取り除かずに残し、完了報告に挙げる）。
- 設計の途中の worktree を `researchkit-execute` で再開しようとすると `DESIGN_INCOMPLETE`、実行に入った worktree を `researchkit-question` で再開しようとすると `EXECUTE_IN_PROGRESS` で止まる。`researchkit-all` は、どちらの途中からでも再開できる。

### 各ステップの作業場所

- 以降の作業は、すべて `WORKTREE_DIR` の中で行う。コマンドは `cd "$WORKTREE_DIR"` してから実行し、ファイルは `WORKTREE_DIR` の下のパスで読み書きする。メインの作業ツリーのファイルは編集しない（`finish` が未コミットの変更で止まる）。
- RQ の成果物は `RQ_DIR`（`spec.md`、`plan.md`、`tasks.md`、`search-log.md`、`evidence/`、`analysis/`、`findings.md`、`reviews/`、`auto-decisions.md`）に置く。出典は `sources/`、データは `data/`、逆流で直す上流の文書は `docs/` の下にある。どれも worktree の中のものを編集する。
- 1 つのステップが終わったら、そのステップのチェックポイントを必ず記録する。

  ```bash
  $HELPER checkpoint <RQ_NAME> <step>   # subject は省くと §2 の既定の形
  ```

- 長いステップ（特に Q8 の収集と Q9 の分析）の途中では、trailer なしの通常のコミットを作ってよい（例: 出典 10 件ごと、分析のスクリプト 1 本ごと）。完了の記録は、ステップの最後の `checkpoint` だけで行う。

### Q13 片付け

1. **worktree の外に出てから**（`cd "$REPO_ROOT"`）、`$HELPER finish <RQ_NAME> --phase <phase>` を実行する。状態欄の更新、`main` への `--no-ff` マージ、worktree とブランチの削除をスクリプトが行う。止まったときのコード（`UNCHECKED_TASKS`、`LEFTOVER_CHANGES`、`NOT_ON_MAIN`）と出力（`RQ_STATUS`、`HUMAN_TASKS_PENDING`、`REMOVED_IGNORED`）の扱いは下の詳細を読む。
2. 成功したら、`main` で `$RK handover --note "<RQ_NAME> の <phase> を完了（状態: <RQ_STATUS>）"` を実行し、`git add docs/handover && git commit -m "docs(handover): 引き継ぎ書を更新"` でコミットする。`WARN STALE_MANUAL` が出たら、手で書く節（次にやること、判断待ち）を今の状態に直してから、もう一度 `handover` を実行してコミットする（自動モードでも直す）。
3. マージで競合したら、内容をユーザーに示し、方針を確かめてから解消して、もう一度 `finish` を実行する。

スクリプトが行うことの全文、引き継ぎ書の直し方、競合の解消の仕方は [references/finish.md](references/finish.md)。

### 人のタスクの片付け

`[人]` のタスクはマージの後に `main` で片付けてよい。`$HELPER human-tasks <RQ>` で示し、ユーザーが完了を伝えたら「完了の確かめ方」で確かめられる部分を確かめてから `- [x]` にし、`$HELPER sync-status <RQ>` で状態欄を合わせてコミットする。人が入手したもので収集や分析をやり直すときの扱いを含む手順は [references/human-tasks.md](references/human-tasks.md)。

### 中止

`$HELPER abort <RQ>` で対象を示し、ユーザーの明示的な同意を得てから `--yes` で実行する。ユーザーの指示なしに中止しない（worktree の中の出典・データ・分析の出力も失われる）。詳細は [references/human-tasks.md](references/human-tasks.md)。

## 4. 共通規則

- **対話**: ユーザーの判断が要る事項は、推奨案（`**Recommended:**`）と理由を添えて質問する。`--auto` では質問せずに §7 で進める。
- **安全規則**: 破壊的なコマンド（`rm -rf`、`git reset --hard`、`git clean -f`、`git push --force`）を使わず、worktree とブランチの操作は `$HELPER` だけで行う。出典・生データ・インタビューの記録を了承なしに消さない（生データは加工しない）。`[人]` のタスクは実行せず、`- [x]` にしない。秘密情報の値を読まない・出さない・コミットしない。利用規約と引用の範囲を守り、法的な判断はしない。
- **分析のコマンド**は `commands.analysis`（`$RK config get commands.analysis`）を正とする。**出典 ID** は `$RK sources next <NNN> --count <k>` で払い出す。**サブエージェント**は steering の「サブエージェントに任せるとき」に従い、チェックポイントと `auto-decisions.md` は親が書く。RQ は 1 件ずつ直列に進め、同じ RQ を 2 つのセッションで同時に進めない。

各規則の全文は [references/rules.md](references/rules.md)。

## 5. セッションの区切り

Web 検索には 1 セッションあたりの回数の上限がある。規則は steering の「セッションの区切り」、コマンドの詳細は `researchkit-status` の「セッションの区切りと予算」の節に従う。3 スキルでは次の場所で `$RK budget` を実行する。

| 場所 | コマンド | 実行するスキル |
|---|---|---|
| RQ に入る前（Q1 の前） | `$RK budget --step rq --rq <RQ>` | 3 スキルすべて |
| 途中の RQ を再開する前 | 残りのステップの分（Q8 が残っていれば `--step Q8 --rq <RQ_NAME>`、Q11 から先だけなら `--step Q11 --rq <RQ_NAME>`、設計の工程だけなら `--step rq`） | 3 スキルすべて |
| Q8（収集）の前 | `$RK budget --step Q8 --rq <RQ_NAME>` | researchkit-execute、researchkit-all |
| Q11（5 軸レビュー 1 回目。Counter 軸で検索する）の前 | `$RK budget --step Q11 --rq <RQ_NAME>` | researchkit-execute、researchkit-all |
| そのほか、検索の多い作業を単独で始める前 | `$RK budget --need <見積もり>` | 必要に応じて |
| `session.split_after` に入っているステップの `checkpoint` の後 | `checkpoint` の出力の `SPLIT_SESSION` を見る | researchkit-execute、researchkit-all |

| 結果 | すること |
|---|---|
| `VERDICT: OK` | 続ける |
| `VERDICT: STOP`（終了コード 4） | その工程に入らずに止まる。**自動モードでも止まる。** それまでのチェックポイントは記録済みなので、新しいセッションで同じスキルを同じ引数で実行すれば、続きから再開する。これは失敗ではなく区切りである。worktree はそのまま残し、`$RK handover --note "<止めた理由と再開のコマンド>"` で引き継ぎ書を更新する（worktree の中で止めたときは、引き継ぎ書はコミットせずに残してよい） |
| `VERDICT: UNMETERED` | 回数を数えられない環境である。1 セッションで `session.rqs_unmetered`（既定 1）件の RQ の Q13 を終えたら、次の RQ に入らずに止まる |

- 調査全体の工程（R12）を終えたのと同じセッションでは、RQ の工程を始めない。新しいセッションで始めるよう案内する。
- 見積もりの外れで工程の途中で上限に当たったときは、そのステップを完了にせず（`checkpoint` を記録せず）、検索ログに未検索の範囲を書いて止まる。再開したセッションで、そのステップの残りから続ける。

## 6. 引数の解釈と複数の RQ の進め方

RQ の指定は、単一（`003`、`market-size` など。`$HELPER resolve`）、範囲（`002-005`。着手順に）、`all`（`$HELPER next --phase <phase>` を空になるまで）、なし（`next` の 1 件）のどれかで、`--auto` は位置を問わず組み合わせる（`$HELPER` には渡さない）。複数の RQ は 1 件ずつ直列に進め、各 RQ の Q1 の前に §5 の予算を確かめる。`999-research-report` は最後に進む。`ALREADY_DESIGNED`・`ALREADY_EXECUTED` は飛ばして次へ、`all` で飛ばした RQ は `next --skip` で除く。表と規則の全文は [references/arguments.md](references/arguments.md)。

## 7. 自動モード

引数に `--auto` があるときは質問せず、推奨案を採用して進め、すべてを `RQ_DIR/auto-decisions.md` に記録する（ステップ、論点、選択肢、採用した案、理由、根拠の種類、見直しの優先度、反映したファイル）。安全規則と出典の規則は変わらない。

**自動モードでも止まる場面**: マージの競合、中止、`NOT_ON_MAIN`、`DEPENDENCY_PENDING`（範囲指定では飛ばす）、憲章・品質基準・`docs/method.md` の変更が要るとき、`[人]` のタスクが終わらないと先に進めないとき、同じ原因の失敗が 3 回続いたとき、Web 検索の予算の STOP、分析のコマンドが決められないとき、Q2 で何を問うか決められないとき、法的な判断が要るとき、`UNCHECKED_TASKS` が片付けても残るとき。止まったときは下の『止まったときの扱い』に従う。

**見直しの優先度を「高」にするもの**: 問いの範囲・答えの形・判定の基準、手法の選択、収集の後の計画の変更、結果を見た後に足した探索的な分析、仮説の棄却・採択、逆流で上流の文書を変えたもの、確度 `確実` の主張、根拠が推測だけのもの。

場面ごとの自動の動き（`LEFTOVER_CHANGES` は `--commit-leftovers`、`UNCHECKED_TASKS` は片付けて再実行、など）、止まったときの扱い、明確化の記録の書き方は [references/auto-mode.md](references/auto-mode.md)。

### 止まったときの扱い

1. worktree とブランチはそのまま残し、止まった理由、止まったステップ、ユーザーに判断してほしい事項（選択肢と推奨案）を `RQ_DIR/auto-decisions.md` と完了報告に書く。`$RK handover --note "<止めた理由と次の作業>"` で引き継ぎ書も更新する。
2. 単一の RQ の指定なら、完了報告を出して終了する。
3. 範囲指定や `all` なら、その RQ を飛ばして次に進む（`all` では `next` の `--skip` に加える）。後の RQ の概要ファイルの `**依存**` に、飛ばした RQ が含まれる場合は、その RQ も飛ばす。予算の STOP のときは、飛ばさずに全体を止める。
4. 止まった RQ は、ユーザーが判断した後に、同じスキルをもう一度実行すれば（`--auto` の有無を問わない）続きのステップから再開できる。

## 8. クラウドセッション

環境変数 `CLAUDE_CODE_REMOTE` が `true` のときだけ当てはまる（マージ先は作業ブランチ、`finish` の後に push、1 つの RQ は 1 つのセッションで `finish` まで、`--auto` を勧める、WebFetch の失敗時の扱い）。詳細は [references/cloud.md](references/cloud.md)。

## 9. 手動での利用

ユーザーにこのスキルを直接呼ばれたとき（`status`、`human-tasks`、`sync-status`、`next`、`abort`）の動きは [references/cloud.md](references/cloud.md)。
