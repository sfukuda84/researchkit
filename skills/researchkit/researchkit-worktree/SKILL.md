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
  $HELPER checkpoint <RQ_NAME> <step> "<§2 の subject>"
  ```

- 長いステップ（特に Q8 の収集と Q9 の分析）の途中では、trailer なしの通常のコミットを作ってよい（例: 出典 10 件ごと、分析のスクリプト 1 本ごと）。完了の記録は、ステップの最後の `checkpoint` だけで行う。

### Q13 片付け

1. **worktree の外に出てから**、`$HELPER finish <RQ_NAME> --phase <phase>` を実行する（`cd "$REPO_ROOT"`）。worktree の中で実行すると、スクリプトは止まる。スクリプトは次を行う。
   - 担当範囲の最終ステップ（design は Q7-2、execute と all は Q12）が完了し、`RQ_DIR` に `spec.md`・`plan.md`・`tasks.md` があることを確かめる。
   - execute と all では、`tasks.md` に `[人]` 以外の未完了のタスクがないことを確かめる（あれば `UNCHECKED_TASKS` で止まる。`[人]` だけなら続けて、最後に `HUMAN_TASKS_PENDING` を出す）。
   - worktree に、どのステップにも含まれない変更があれば止まる（`LEFTOVER_CHANGES`）。
   - `docs/questions/<RQ_NAME>.md` の状態欄と `README.md` の一覧の状態の列を更新し（§2）、`docs(<RQ_NAME>): 状態を「<状態>」に更新` としてコミットする。
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

### 人のタスクの片付け

`[人]` のタスクはマージの後に `main` で片付けてよい。`$HELPER human-tasks <RQ>` で示し、ユーザーが完了を伝えたら「完了の確かめ方」で確かめられる部分を確かめてから `- [x]` にし、`$HELPER sync-status <RQ>` で状態欄を合わせてコミットする。人が入手したもので収集や分析をやり直すときの扱いを含む手順は [references/human-tasks.md](references/human-tasks.md)。

### 中止

`$HELPER abort <RQ>` で対象を示し、ユーザーの明示的な同意を得てから `--yes` で実行する。ユーザーの指示なしに中止しない（worktree の中の出典・データ・分析の出力も失われる）。詳細は [references/human-tasks.md](references/human-tasks.md)。

## 4. 共通規則

- **対話**: 問いの範囲、答えの形、手法の選択、反証条件、確度の付け方、レビューの指摘の直し方など、ユーザーの判断が必要な事項は、推奨案（`**Recommended:**`）と理由を添えて質問し、合意を得てから進める。質問は `AskUserQuestion`（ほかのエージェントでは同じ働きのツール。なければ選択肢と推奨案を文章で示して回答を待つ）で行う。引数に `--auto` があるときは、質問せずに §7 の自動モードで進める（各スキル本文の 💬 の質問も含む）。
- **安全規則**:
  - `rm -rf`、`git reset --hard`、`git clean -f`、`git push --force` などの破壊的なコマンドは使わない。worktree とブランチの操作は `$HELPER` だけで行う。
  - 出典、生データ（`data/raw/`、`data/large/`）、インタビューの記録を、ユーザーの了承なしに消さない。生データは加工せず、加工したものは `RQ_DIR/analysis/` に置く。
  - `[人]` のタスクは実行せず、自動モードでも `- [x]` にしない（§3『人のタスクの片付け』）。
  - 秘密情報（API キー、社内データの認証情報、個人情報）の値を読んだり、出力したり、コミットしたりしない。
  - 有料のデータベースや統計の利用規約、引用の範囲を守る。判断に迷うものは `[人]` にする。法的な判断はしない。
- **言語**: 応答と成果物は、プロジェクトの言語ルール（`.kiro/steering/language.md`）に従う。最終成果物（`reports/`）の言語は `docs/questions/999-research-report.md` に従う。
- **分析のコマンド**: 分析のスクリプトを実行するコマンドは、`.researchkit/config.yaml` の `commands.analysis`（`$RK config get commands.analysis` で読む。`{script}` をスクリプトのパスに置き換える）を正とする。テストは `commands.test`。空なら `docs/method.md` の分析環境から判断する。判断できなければユーザーに確かめる。
- **出典 ID**: 新しい出典の ID は `$RK sources next <NNN> --count <k>` で払い出す（`<NNN>` はこの RQ の番号）。サブエージェントに並行して集めさせるときは、範囲を分けて渡す（steering の「サブエージェントに任せるとき」）。既存の出典を使うときは、新しく作らずに `used_in` に足す。
- **サブエージェント**: 収集（Q8）やレビューの軸（Q11、Q12）をサブエージェントに任せるときは、steering の「サブエージェントに任せるとき」の分担に従う。チェックポイントのコミットと `auto-decisions.md` への記録は親が行う。
- **並行**: 1 つの統括スキルの中では、RQ を 1 件ずつ直列に進める（§6）。別のセッションで別の RQ を並行して進めてもよいが、同じ RQ を 2 つのセッションで同時に進めない。

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
