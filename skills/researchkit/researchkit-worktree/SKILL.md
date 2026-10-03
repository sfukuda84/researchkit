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

```bash
python3 <skills>/researchkit-worktree/scripts/worktree_helper.py <command> ...
```

以降、この呼び出しを `$HELPER` と書く。`$RK`（`researchkit-status` の `researchkit.py`）の意味は steering の「エージェントの行動規範」のとおりである。

- `<skills>` は、このスキルが置かれた skills ディレクトリ（`.claude/skills`、`.agents/skills`、`.kiro/skills` のいずれか）である。
- スクリプトは Python 3.9 以上の標準ライブラリだけで書かれており、macOS、Linux、Windows で動く。プロジェクトのルートからでも worktree の中からでも実行できる。`python3` がない環境では、`python` または `py -3` に読み替える。
- マージ先のブランチ（この文書の `main`）は、環境変数 `RESEARCHKIT_MAIN_BRANCH` があればその名前、なければ `main` である。クラウドセッションでの扱いは §8 に書く。

| コマンド | 用途 |
|---|---|
| `$HELPER ensure <RQ> --phase design\|execute\|all` | Q1 準備。worktree があれば再利用し、なければ `main` から作る |
| `$HELPER state <RQ> --phase design\|execute\|all` | 変更せずに進捗を表示する |
| `$HELPER checkpoint <RQ> <step> "<subject>"` | worktree の変更をすべてコミットし、ステップの完了を記録する |
| `$HELPER finish <RQ> --phase design\|execute\|all [--allow-unchecked] [--commit-leftovers] [--switch]` | Q13 片付け。RQ の状態を更新し、`main` に `--no-ff` でマージし、worktree とブランチを削除する。worktree の外で実行する |
| `$HELPER abort <RQ> [--yes]` | worktree とブランチを破棄する。`--yes` がなければ対象を表示するだけ |
| `$HELPER list` | 全 RQ の名前を着手順（`docs/questions/spec_order.md` の並び、その後に番号順。`999` は常に最後）で表示する |
| `$HELPER status` | 全 RQ の状態欄・設計・実行・worktree の状況と、残っている `[人]` のタスクの件数を表で表示する。`999` は、ほかが終わるまで「ほかの RQ の完了待ち」と出る |
| `$HELPER human-tasks [<RQ>]` | 残っている `[人]` のタスクを一覧する。worktree があればその `tasks.md`、なければ `main` のもの（メインの作業ツリーが `main` にいれば、コミット前の変更も含む）を読む |
| `$HELPER sync-status <RQ>` | `main` にマージ済みの RQ の状態欄を、`tasks.md` に合わせて `完了` か `人の作業待ち` にする。`main` で実行し、変更はコミットしない |
| `$HELPER next --phase design\|execute\|all [--skip <RQ,...>]` | 次に着手すべき RQ を表示する（途中の worktree を優先。`--skip` で除外。`999` はほかが終わるまで出さない）。なければ空行 |
| `$HELPER resolve <query>` | 番号（`1`、`003`）、スラッグ、完全名、ファイルパスから RQ の名前を決める |

`<RQ>` には、番号（`1`、`003`）、スラッグ（`market-size`）、完全名（`003-market-size`）、パス（`docs/questions/003-market-size.md`）のどれを渡してもよい。

`ensure` と `state` は次の形で結果を出力する。

```text
REPO_ROOT: /path/to/project
RQ_NAME: 003-market-size
BRANCH: rq/003-market-size
WORKTREE_DIR: /path/to/project/.worktrees/003-market-size
WORKTREE_STATE: created | reused | reattached | present | absent
PHASE: design
COMPLETED_STEPS: Q2 Q3
NEXT_STEP: Q4
```

終了コードは、0 が成功、1 がエラー、3 が前提条件を満たさないことを表す。3 のときは標準エラーに `PRECONDITION: <code>` と案内文が出る。

| code | 意味 | 対応 |
|---|---|---|
| `ALREADY_DESIGNED` | 設計（`tasks.md`）はすでに `main` にマージ済み | `researchkit-execute` を案内する |
| `ALREADY_EXECUTED` | 実行まで `main` にマージ済み | その RQ は完了として扱う |
| `EXECUTE_IN_PROGRESS` | worktree がすでに実行の工程に入っている | `researchkit-execute` か `researchkit-all` での再開を案内する |
| `DESIGN_INCOMPLETE` | worktree の設計の工程が途中 | `researchkit-question` か `researchkit-all` での再開を案内する |
| `DESIGN_MISSING` | `spec.md`・`plan.md`・`tasks.md` がどこにもない | `researchkit-question` か `researchkit-all` を案内する |
| `DEPENDENCY_PENDING` | `999-research-report` を始めようとしたが、ほかの RQ（`000` を含む）に `完了` でも `人の作業待ち` でもないものがある | 残っている RQ を示し、先にそれらを進めるよう案内する |
| `LEFTOVER_CHANGES` | `finish` で、worktree にどのステップのコミットにも含まれていない変更がある | 変更の一覧をユーザーに示す。マージに含めてよければ `--commit-leftovers` を付けて再実行する。含めない変更は、ユーザーの了承を得て取り除く |
| `NOT_ON_MAIN` | `finish` で、メインの作業ツリーが `main` 以外のブランチにいる | 切り替えてよいかをユーザーに確認し、よければ `--switch` を付けて再実行する |
| `UNCHECKED_TASKS` | `finish`（execute / all）で、`tasks.md` に `[人]` 以外の未完了のタスクが残っている | 一覧をユーザーに示す。片付けるなら該当するステップ（収集なら Q8、分析なら Q9 など）の手順で片付ける。残したままマージしてよいと確認できたら `--allow-unchecked` を付けて `finish` を再実行する |

`finish`（execute / all）は、未完了のタスクが `[人]` のものだけなら止めずにマージし、標準出力に `HUMAN_TASKS_PENDING: <件数>` と残りのタスクを出す。この一覧はユーザーに示し、§3『人のタスクの片付け』を案内する。

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
- 再開の前に、`docs/handover/CURRENT_STATE.md` と `PITFALLS.md` を読み、止まった理由と判断待ちの事項を確かめる。止まった理由が解消していなければ、先にそれを片付ける。
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
3. マージで競合したときは、worktree とブランチが残る。競合の内容をユーザーに示し、解消の方針を確かめてから、メインの作業ツリーで解消してマージをコミットし、もう一度 `finish` を実行する。マージコミットのメッセージは `merge(<RQ_NAME>): <phase>` のままにする。並行して進めた RQ が同じ出典ファイルの `used_in` や `docs/glossary.md` を変えたときに競合しやすい。両方の追記を残す形で解消する。

### 人のタスクの片付け

`[人]` のタスクは、マージの後に `main` で片付けてよい。規則は steering の「人が行うタスク」に従う。

1. `$HELPER human-tasks <RQ_NAME>` で残りを示す。
2. ユーザーが完了を伝えたら、そのタスクの「完了の確かめ方」で確かめられる部分を確かめる（例: `data/manifest.md` に記載があり、ハッシュが一致する。入手した論文の書誌が出典ファイルと一致する）。確かめられたら、`main` の `RQ_DIR/tasks.md` を `- [x]` にする。確かめられないときは `- [ ]` のまま残し、何が足りないかを伝える。
3. 人が入手したもので、収集や分析をやり直す必要があるとき（有料レポートを入手した、インタビューを実施したなど）は、その RQ の続きの AI のタスクとして扱う。`researchkit-collect` と `researchkit-analysis` の手順で `main` の上で追加し、`researchkit-findings` で主張と確度を直す。変更が大きい（主張の確度が変わる、新しい主張が増える）ときは、`researchkit-review` で該当する軸を見直す。
4. `$HELPER sync-status <RQ_NAME>` で状態欄を合わせる。人のタスクがなくなれば `完了` になる。
5. `tasks.md`、概要ファイル、`docs/questions/README.md`、手順 3 の変更をまとめてコミットする（例: `docs(<RQ_NAME>): 人のタスクの完了を記録`）。クラウドセッションでは push する。

### 中止

`$HELPER abort <RQ_NAME>` で削除の対象を表示し、ユーザーの明示的な同意を得てから `--yes` を付けて実行する。ユーザーの指示なしに中止してはならない。中止すると、worktree の中の出典、データ、分析の出力も失われる。残したいものがあれば、先にユーザーと扱いを決める。

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
| RQ に入る前（Q1 の前） | `$RK budget --step rq` | 3 スキルすべて |
| 途中の RQ を再開する前 | 残りのステップの分（Q8 が残っていれば `--step Q8`、Q11 から先だけなら `--step Q11`、設計の工程だけなら `--step rq`） | 3 スキルすべて |
| Q8（収集）の前 | `$RK budget --step Q8` | researchkit-execute、researchkit-all |
| Q11（5 軸レビュー 1 回目。Counter 軸で検索する）の前 | `$RK budget --step Q11` | researchkit-execute、researchkit-all |
| そのほか、検索の多い作業を単独で始める前 | `$RK budget --need <見積もり>` | 必要に応じて |

| 結果 | すること |
|---|---|
| `VERDICT: OK` | 続ける |
| `VERDICT: STOP`（終了コード 4） | その工程に入らずに止まる。**自動モードでも止まる。** それまでのチェックポイントは記録済みなので、新しいセッションで同じスキルを同じ引数で実行すれば、続きから再開する。これは失敗ではなく区切りである。worktree はそのまま残し、`$RK handover --note "<止めた理由と再開のコマンド>"` で引き継ぎ書を更新する（worktree の中で止めたときは、引き継ぎ書はコミットせずに残してよい） |
| `VERDICT: UNMETERED` | 回数を数えられない環境である。1 セッションで `session.rqs_unmetered`（既定 1）件の RQ の Q13 を終えたら、次の RQ に入らずに止まる |

- 調査全体の工程（R12）を終えたのと同じセッションでは、RQ の工程を始めない。新しいセッションで始めるよう案内する。
- 見積もりの外れで工程の途中で上限に当たったときは、そのステップを完了にせず（`checkpoint` を記録せず）、検索ログに未検索の範囲を書いて止まる。再開したセッションで、そのステップの残りから続ける。

## 6. 引数の解釈と複数の RQ の進め方

| 指定 | 例 | 動作 |
|---|---|---|
| 単一 | `1`、`003`、`003-market-size`、`market-size` | `$HELPER resolve` で 1 件に決める |
| 範囲 | `002-005`、`002..005` | `$HELPER list` の結果から、番号が範囲内のものを着手順に選ぶ |
| 全件 | `all` | `$HELPER next --phase <phase>` を、空になるまで繰り返す |
| なし | （空） | `$HELPER next --phase <phase>` の 1 件。空なら対象なしと報告する |
| 自動モード | `--auto`、`002-005 --auto`、`--auto all` | 上のいずれかと組み合わせる。質問せずに推奨案を採用して進める（§7） |

- `--auto` は位置を問わない。RQ の指定を解釈する前に取り除き、`$HELPER` には渡さない。
- 一覧にない新しい RQ は、`004-short-name` の形の完全名で指定する。ただし、RQ は `researchkit-questions` で `docs/questions/` に足してから進めることを勧める（概要ファイルがないと、状態の更新と `validate.py` の検証ができない）。
- 複数の RQ は 1 件ずつ直列に進める。前の RQ の Q13（マージ）が終わってから、次の RQ の Q1 に進む。後の RQ は、前の RQ の成果（出典、`findings.md`、逆流の更新）を含む最新の `main` から分岐する。
- 各 RQ の Q1 の前に §5 の予算を確かめる。STOP なら、残りの RQ に進まずに止まる。
- `999-research-report` は、ほかのすべての RQ が `完了` か `人の作業待ち` になるまで `next` の候補にならず、`ensure` は `DEPENDENCY_PENDING` で止まる。範囲や `all` の最後に来たときに進める。
- 範囲指定の途中で `ALREADY_DESIGNED` や `ALREADY_EXECUTED` になった RQ は、飛ばしたことを記録して次に進む。それ以外の理由で止まったときは、飛ばして続けるか中断するかをユーザーに確かめる（自動モードでは確かめずに飛ばす。§7『止まったときの扱い』）。
- `all` で飛ばした RQ は、以降の `next` に `--skip <飛ばしたもの,...>` を付けて除く（付けないと、途中の worktree が残っている RQ がまた選ばれる）。

## 7. 自動モード

引数に `--auto` があるときは、ユーザーに質問せず、エージェント自身が示す推奨案を採用して進める。範囲指定や `all` と組み合わせて、無人で続けて流す使い方を想定する。`researchkit-bootstrap --oneshot` の後に続けて RQ を進めるときも、このモードで扱う。

「曖昧さは推測で埋めない」（steering の基本原則 11）に反しないよう、自動で決めたことはすべて推奨案として明示し、後から見直せる形で記録する（下の『記録』）。§4 の安全規則と、出典の規則（実在を確かめていない出典を根拠にしない、数値を推測で埋めない）は、自動モードでも変わらない。

### 推奨案を自動で採用する場面

| 場面 | 自動モードでの動作 |
|---|---|
| Q1 の再開の確認（`reused` / `reattached`） | `NEXT_STEP` から再開する |
| Q2〜Q4 の問いの範囲・答えの形・判定の基準・用語の定義の質問 | 推奨案を回答として採用する。1 つに絞れない論点は、範囲が狭く、後から広げやすい選択肢を採る |
| Q5 の手法の組み合わせ、検索式とデータベース、標本、反証条件 | `docs/method.md` で選んだ手法の範囲の中で推奨案を採る。反証条件は、収集の前に書く（基本原則 4） |
| Q6 の `[人]` の切り分け | steering の「人が行うタスク」の対象に当たるものは `[人]` にし、人と AI が混ざる作業は 2 つに分ける |
| Q7 の修正方針（「修正案を当てますか」など） | 「はい」とみなし、推奨の修正を当てる |
| Q8 で実在を確かめられない出典 | 等級 `D` にして根拠に使わない。ほかの出典を探す。見つからなければ「見つからなかった」ことを検索ログに書く |
| Q8 で有料・要申請の資料が要る | `[人]` のタスクに足し、手に入る資料で進める。その資料がないと答えられない判定の基準は、確度を下げるか「残った問い」にする |
| Q9 で収集の後に計画を変える必要がある | 変えたことと理由を `plan.md` の「計画の変更」に書いて進める（基本原則 4）。見直しの優先度は「高」にする |
| Q10 の確度の付け方、逆流（`hypotheses.md`、`issue-tree.md`、`docs/questions/` の更新） | 憲章の確度の段階と根拠の数・等級から付ける。逆流は行い、仮説の棄却・採択と上流の文書の変更は見直しの優先度を「高」にする |
| Q11〜Q12 の指摘の直し方 | 推奨の修正を当てる。Counter 軸の追加の検索で反対の証拠が見つかったら、主張の確度を下げるか、反証・限界の欄に書く |
| `LEFTOVER_CHANGES` | worktree の変更はこの RQ の作業で生じたものなので、`--commit-leftovers` を付けて `finish` を再実行する。含めた変更の一覧を完了報告に挙げる |
| `UNCHECKED_TASKS` | 未完了のタスクを該当するステップの手順で片付け、`finish` を再実行する（`--allow-unchecked` は自動で付けない） |
| `[人]` のタスク | 実行せず、`[x]` にもしない。保留にし、依存しない後続のタスクを続ける。保留にしたタスクを完了報告に挙げる |
| `HUMAN_TASKS_PENDING` | マージは済んでいる。残りの `[人]` のタスクを完了報告に挙げる（自動で完了にしない） |

### 自動モードでも止まる場面

次の場面は、推奨案を選んでも取り返しがつかないか、推測で進めると危険なので、自動では進めない。

- `finish` でのマージの競合（自動で解消しない）
- 中止（`abort`）。ユーザーの明示的な同意が要る
- `NOT_ON_MAIN`（メインの作業ツリーのブランチを自動で切り替えない）
- `DEPENDENCY_PENDING`（範囲指定や `all` では飛ばす）
- 憲章（`.researchkit/memory/constitution.md`）、品質基準（`docs/quality.md`）、`docs/method.md` の変更が要るとき（これらの改訂は自動で行わない）
- `[人]` のタスクが終わらないと先に進めないとき（例: 主な情報源が有料で、入手しないと問いに答えられない。インタビューの実施が要る。倫理審査や同意の取得が要る）
- 同じ原因の失敗（分析のスクリプトの失敗、`check.py` や `numbers.py` の ERROR など）が、3 回直しても解消しないとき
- Web 検索の予算が足りないとき（§5 の `VERDICT: STOP`）。これは失敗ではなく区切りである
- 分析のコマンドが §4 の情報源から判断できないとき
- Q2 で、RQ の概要ファイルも追加の指示もなく、何を問うかが決められないとき
- 個人情報、利用規約、引用の範囲について、法的な判断が要るとき
- `UNCHECKED_TASKS` で、未完了のタスクを片付けても残るとき

### 止まったときの扱い

1. worktree とブランチはそのまま残し、止まった理由、止まったステップ、ユーザーに判断してほしい事項（選択肢と推奨案）を `RQ_DIR/auto-decisions.md` と完了報告に書く。`$RK handover --note "<止めた理由と次の作業>"` で引き継ぎ書も更新する。
2. 単一の RQ の指定なら、完了報告を出して終了する。
3. 範囲指定や `all` なら、その RQ を飛ばして次に進む（`all` では `next` の `--skip` に加える）。後の RQ の概要ファイルの `**依存**` に、飛ばした RQ が含まれる場合は、その RQ も飛ばす。予算の STOP のときは、飛ばさずに全体を止める。
4. 止まった RQ は、ユーザーが判断した後に、同じスキルをもう一度実行すれば（`--auto` の有無を問わない）続きのステップから再開できる。

### 記録

- **明確化（Q3、Q4）**: 見出しを `### Session YYYY-MM-DD (Round 1, auto)` のようにし、自動で採用した回答の行末に `(auto)` を付ける。
- **自動判断の一覧**: 自動で採用したすべての判断を `RQ_DIR/auto-decisions.md` に追記する。1 件ごとに、ステップ、論点、選択肢、採用した案、理由、根拠の種類（ユーザーの入力 / 調査 / 推測）、見直しの優先度（高 / 中 / 低）、反映したファイルを書く。明確化の回答もここに併記する。
- **見直しの優先度を「高」にするもの**: 問いの範囲・答えの形・判定の基準の決定、手法の選択、収集の後の計画の変更、仮説の棄却・採択、逆流で上流の文書（`hypotheses.md`、`issue-tree.md`、`docs/questions/`）を変えたもの、確度 `確実` を付けた主張、根拠が推測だけのもの。`$RK handover` が「高」のものを引き継ぎ書に集める。
- **完了報告**: 各スキルの完了報告に、`auto-decisions.md` の要約（見直しを勧める判断を先に）と、止まった RQ とその理由、ユーザーに判断してほしい事項を加える。見直すときは、該当するステップのスキル（`researchkit-clarify`、`researchkit-plan` など）を案内する。

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
