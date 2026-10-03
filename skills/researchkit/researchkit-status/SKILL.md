---
name: "researchkit-status"
description: "researchkit の進捗確認・引き継ぎ書・環境の診断・Web 検索の予算・出典 ID のスキル。調査全体の工程（researchkit-bootstrap の R1〜R12）と RQ の工程（Q1〜Q13。researchkit-worktree）の進捗、出典台帳の件数（等級別）、残っている [人] のタスクを一覧し、次に実行すべきスキルを示す。引き継ぎ書（docs/handover/CURRENT_STATE.md の自動の節、sessions/、PITFALLS.md）を更新し、.researchkit/config.yaml・分析のコマンド・スキルのリンク・steering・検索の回数を数えるフックを診断する。Web 検索の残りで次の工程に入れるかを判定し（budget）、セッションの区切りを決める。出典 ID の払い出し（sources next）と出典の一覧（sources list）、設定の読み出し（config get）と初期化（init）もここで行う。「進捗を見せて」「次に何をすればいい」「引き継ぎ書を作って」「環境を確かめて」「検索の残りは」と言われたとき、または /researchkit-status と打たれたときに使う。"
argument-hint: "status | next | handover [--note <メモ>] | doctor | pitfall <内容> | budget [--step <STEP>] | sources next <NNN> | sources list [--grade A,B] [--rq <NNN>] [--unused] | init"
compatibility: "Requires git and Python 3.9+"
user-invocable: true
disable-model-invocation: false
---

# researchkit-status スキル（進捗・引き継ぎ書・診断・予算）

調査全体の工程と RQ の工程の進み具合をまとめて示し、セッションをまたいで作業を引き継ぐための文書を保つ。進捗の判定はコミットの trailer だけから行うので、エージェントやセッションを変えても同じ結果になる。Web 検索の回数を数え、工程の境目でセッションを区切る判断もここで行う。

パスは既定の配置で書いている。`.researchkit/config.yaml` の `paths` で読み替える。

## 1. ヘルパースクリプト

```bash
skills/researchkit/rk [--root <dir>] <command> ...
# 同じ: python3 <skills>/researchkit-status/scripts/researchkit.py [--root <dir>] <command> ...
```

以降、この呼び出しを `$RK` と書く（steering の「エージェントの行動規範」と同じ。`rk` は 1 語で呼べる入口で、zsh でも変数に入れて使える。Windows では `py -3 skills/researchkit/rk`）。`<skills>` は、このスキルが置かれた skills ディレクトリ（`.claude/skills`、`.agents/skills`、`.kiro/skills` のいずれか）である。`python3` がない環境では `python` または `py -3` に読み替える。`--root` を省くと、`.researchkit/config.yaml`（なければ `.git`）を上へ探してプロジェクトのルートにする。worktree の中では worktree がルートになる。

| コマンド | 用途 |
|---|---|
| `$RK init [--config-only] [--title T]` | `.researchkit/config.yaml` がなければテンプレートから作り、`paths` のディレクトリのうち無いものを作る（空のディレクトリには `.gitkeep` を置く。`docs/method.md` や憲章のようにファイルを指すパスは作らない）。`docs/handover/PITFALLS.md` も作る。既存のファイルと値は変えない。`--config-only` は設定だけを作る（既存の調査で `paths` を合わせる前に使う） |
| `$RK config get <key.path>` | 設定の値を 1 行で出す（例: `commands.analysis`、`sources.min_grade`、`session.estimates.Q8`）。リストは `,` 区切り。値がなければ空行と終了コード 1 |
| `$RK bootstrap` | 調査全体の工程の完了済みのステップ（`COMPLETED_STEPS`）と次のステップ（`NEXT_STEP`。すべて済んでいれば `DONE`） |
| `$RK status` | 調査全体の工程、RQ の一覧（`worktree_helper.py status`）、出典台帳の件数（等級別）、このセッションの Web 検索の回数、引き継ぎ書の最終更新 |
| `$RK handover [--note <text>]` | 引き継ぎ書を更新する（§3）。コミットはしない |
| `$RK doctor` | 設定と環境を診断し、`OK` / `WARN` / `ERROR` の行と `SUMMARY` を出す（§4）。ERROR があれば終了コード 1 |
| `$RK pitfall <text>` | `PITFALLS.md` の先頭に、日付つきの見出しで 1 件足す（§3） |
| `$RK budget [--step <STEP> \| --need <N>] [--rq <RQ>]` | 次の工程に、このセッションの Web 検索の残りが足りるかを判定する（§5）。`--rq` で RQ の `plan.md` の見積もりと手法の既定を使う。STOP は終了コード 4 |
| `$RK hooks install` | `.claude/settings.json` に、Web 検索の回数を数えるフック（`count_search.py`）を登録する。既存の設定は残す。`.gitignore` に `.researchkit/usage/` を足す。`new-researchkit-project` が自動で行う |
| `$RK sources next <NNN> [--count <k>]` | RQ `<NNN>` の次の空き出典 ID を `k` 個出す（§6） |
| `$RK sources list [--grade A,B] [--rq <NNN>] [--unused]` | 出典の一覧（ID、等級、種類、題名、使った RQ）を表で出す（§6） |
| `$RK brief <RQ> [--width <n>] [--max-tasks <n>]` | RQ の要点を短く出す。spec の問い・小問・つながる決定と仮説・判定の基準、plan の仮説と反証条件・確度の付け方・検索数の見積もり・計画の変更、tasks の未完了のタスク、成果物の一覧。表の行は `--width`（既定 160）文字で切り詰める。全文を読む代わりに使い、要る節だけを読む |
| `$RK estat list <政府統計コード\|一覧の URL> [--grep <語>] [--limit <n>]` | e-Stat のファイルの一覧を短く出す（§8）。分類のページなら下の階層の名前・件数・公開日・URL、表のページなら statInfId・形式・表番号・題名・調査年月・公開日 |
| `$RK estat get <statInfId> --kind <0\|1\|2\|4> --out <保存先>` | e-Stat の表を取得する（§8）。中身の形式（xls、xlsx、csv、pdf、zip）に合う拡張子で保存し、SHA-256 と大きさを出す。中身が HTML（エラーのページ）なら保存せずに終了コード 1 |
| `$RK data add <file> --source <ID> --url <URL> --desc <内容> --rq <NNN> [--license <規約>] [--method <方法>] [--accessed <日付>]` | データの目録（`data/manifest.md` の「ファイル」の表）に 1 行足す（§8）。SHA-256・大きさ・置き場所（raw / large）はファイルから求める。同じファイルの行があれば止まる |

終了コードは、0 が成功、1 がエラー、3 が前提条件を満たさないこと、4 が `budget` の STOP（セッションを区切る）を表す。

RQ の工程の細かい操作（`next`、`human-tasks`、`sync-status`、`abort`）は [`researchkit-worktree`](../researchkit-worktree/SKILL.md) の `$HELPER` で行う。

## 2. 進捗の判定

| 工程 | 記録 | 判定 |
|---|---|---|
| 調査全体の工程（R1〜R12） | `researchkit-bootstrap` のコミットの trailer `Researchkit-Bootstrap: R<n>` | `$RK bootstrap` |
| RQ の工程（Q2〜Q12） | `checkpoint` のコミットの trailer `Researchkit-Step: <step>` と `Researchkit-Question: <RQ_NAME>` | `researchkit-worktree` の `$HELPER state` / `status` |
| RQ の状態 | `docs/questions/<RQ_NAME>.md` の `**状態**`（`未着手`／`設計済み`／`完了`／`人の作業待ち`）。Q13 の `finish` が更新する | `$HELPER status` |
| 出典 | `sources/` の出典ファイルのフロントマター（`grade`） | `$RK status`、`$RK sources list` |

- `$RK bootstrap` は R1〜R12 のすべての記録を見る。飛ばした工程（`--skip-pilot` の R6 など）も、`researchkit-bootstrap` が空のチェックポイントで記録する前提である。
- 既存の調査に取り込んだ（`--adopt`）ときは、調査全体の工程の記録がない。`researchkit-bootstrap` の取り込みの手順（成果物がそろっているステップを確かめて記録する）で埋める。

## 3. 引き継ぎ書

置き場は `paths.handover`（既定は `docs/handover/`）である。

| ファイル | 書く人 | 中身 |
|---|---|---|
| `CURRENT_STATE.md` | 自動の節は `$RK handover`、ほかの節は人か AI | 今の目標、次にやること、判断待ち（手で書く）と、自動の節（更新日時とブランチ、調査全体の工程、出典台帳の件数、Web 検索の回数、次の候補〈次の RQ、残っている `[人]` のタスクの件数、見直しの優先度が「高」の判断の件数〉、手で書く節の点検〈古さの注意、手で書く節が挙げる RQ と今の状態〉、RQ の一覧、残っている `[人]` のタスク、見直しの優先度が「高」の自動判断、残っている `[NEEDS CLARIFICATION]`、前回の引き継ぎ以降のコミット） |
| `sessions/<YYYYMMDD-HHMM>.md` | `$RK handover` | そのときの自動の節の写しと、`--note` のメモ。消さずに積み上げる |
| `PITFALLS.md` | 人か AI（`$RK pitfall` でも足せる） | 踏んだ罠と避け方。新しいものを上に書く。`$RK handover` は変えない |

### 更新する場面

- 各 RQ の Q13（`finish`）の後。`researchkit-worktree` の『Q13 片付け』の手順で、`main` で更新してコミットする。
- `researchkit-bootstrap` の R12 の後（セッションを区切る前）。
- セッションを区切るとき（`budget` の STOP、コンテキストが長くなった、人に引き継ぐ、自動モードで止まった）。`--note` に、止めた理由と次の作業（再開のコマンド）を書く。
- ユーザーに「引き継ぎ書を作って」と言われたとき。

### 手順

1. `$RK handover --note "<メモ>"` を実行する。
2. `CURRENT_STATE.md` の手で書く節（今の目標、次にやること、判断待ち）を、今の状況に合わせて直す。次にやることは 1〜3 個に絞り、スキルと引数で書く。自動の節の「次の候補（自動）」（次の RQ、残っている `[人]` のタスク）と「手で書く節の点検」（手で書く節が挙げる RQ と今の状態）を材料にする。
   - `handover` は、手で書く節のハッシュと、その内容になった時点のコミットを、自動の節に印（`<!-- manual: hash=… since=… -->`）として残す。手で書く節が変わらないまま、その後に RQ のマージ（`merge(<RQ>): …`）があると、`WARN STALE_MANUAL` を出し、自動の節にも注意を書く。直してからもう一度 `$RK handover` を実行し、警告が消えたことを確かめてからコミットする。印は手で直さない。自動の節の印（`researchkit:auto:start`・`researchkit:auto:end` のコメント）の間は手で直さない（次の更新で消える）。
3. この作業で踏んだ罠があれば、`PITFALLS.md` の先頭に足す（日付、症状、原因、避け方、関係するファイルや RQ）。`$RK pitfall "<見出し>"` で見出しを足してから、本文を書き足してもよい。同じ罠がすでにあれば、足さずに既存の項目を直す。調査で起きやすい罠は、存在しない文献、古い統計、孫引き、単位や母数の取り違え、検索語の偏り、分析のスクリプトの再実行で結果が変わる、などである。
4. `git add <paths.handover>` と `git commit -m "docs(handover): 引き継ぎ書を更新"` でコミットする（trailer は付けない）。worktree の作業の途中ならコミットせずに残してよい（次の Q13 の更新で上書きされる）。クラウドセッションでは、コミットの後に push する。

### セッションの始め

新しいセッションで作業を始めるときは、まず `CURRENT_STATE.md` と `PITFALLS.md` を読み、`$RK status` で記録と食い違いがないかを確かめてから、「次にやること」を進める。

## 4. 診断（doctor）

`$RK doctor` は次を確かめる。

| 項目 | ERROR | WARN |
|---|---|---|
| Git | Git リポジトリではない | — |
| `.researchkit/config.yaml` | ない、解釈できない | — |
| `commands.analysis`・`commands.test` | — | `commands.analysis` が空。先頭のプログラムが PATH にない（`commands.test` は空でもよい） |
| `confidence.levels` | 空 | — |
| `sources.grades`・`sources.min_grade` | 等級が空、`min_grade` が等級の一覧にない | `min_grade` が最後の等級（未確認） |
| `.claude/skills`・`.agents/skills`・`.kiro/skills` | ない、リンクが切れている、`researchkit-status`・`researchkit-worktree` がない | — |
| steering の 2 ファイル（`language.md`、`research.md`） | ない | — |
| `CLAUDE.md`・`AGENTS.md`・`GEMINI.md` | — | ない、steering の 2 ファイルを参照していない |
| Web 検索のフック | — | `.claude/settings.json` に `count_search.py` がない |
| `.gitignore` | — | `.worktrees/` か `.researchkit/usage/` がない |

WARN は、工程の途中では正常なこともある（例: R7 の前は `commands.analysis` が空）。ERROR は直す。直し方の目安:

- リンクが切れている、スキルがない: scaffold の `new-researchkit-project <プロジェクト> --adopt` を実行し直す（既存のファイルは上書きしない）。
- `commands.analysis` が空: `researchkit-method` の更新モードで埋める。`uv` や `Rscript` が PATH にないなら、インストールの手順を示すか、絶対パスで書く。
- フックがない: `$RK hooks install` を実行し、Claude Code を起動し直す。
- `.gitignore` に `.worktrees/` がない: 足してコミットする（ないと `ensure` が止まる）。

## 5. セッションの区切りと予算

Web 検索には、1 セッションあたりの回数に上限がある（Claude Code で観測した値は 200 件。公式の記載はない）。サブエージェントの検索も、同じセッションの上限を使う。調査は 3 キットの中で最も検索が多いので、次の規則でセッションを区切る。**区切りは工程の境目に置き、工程の途中で上限に当たって未完了が残らないようにする。** 規則の正本は steering の「セッションの区切り」である。

### 回数の数え方

- プロジェクトを作るとき（`new-researchkit-project`）に、`$RK hooks install` が `.claude/settings.json` にフックを登録する。フック（`count_search.py`）は、`SessionStart` で今のセッションの記録を 0 件で作り、`PostToolUse`（`WebSearch`・`WebFetch`）で回数を 1 つ増やす。記録は `.researchkit/usage/<session_id>.json` と `.researchkit/usage/current`（コミットしない）に書く。
- worktree の中で動いたツールの回数も、メインの作業ツリーの `.researchkit/usage/` に記録する。`$RK budget` は worktree の中から実行しても、メインの作業ツリーの記録を読む。
- 上限と比べるのは `WebSearch` の回数である。`WebFetch` は表示だけで、上限には数えない。
- 同じプロジェクトで 2 つのセッションを同時に開くと、後から開いた方が「今のセッション」になる。同時に開かない。

### `budget` の出力

```text
STEP: Q11
RQ: 003-production-volume（plan.md: studies/003-production-volume/plan.md、手法: data, desk）
NEED: 40（Q11 25 + Q12 15）
SOURCE: plan.md / estimates_by_method（data, desk）
LIMIT: 200（reserve 10）
SESSION: 3f2a...
USED: WebSearch 92 / WebFetch 40
REMAINING: 98
VERDICT: OK
```

- `NEED` の決め方（`SOURCE` に出る）: `--need <N>` があればそれ。なければ、`--rq <RQ>` のときは RQ の `plan.md` の「検索数の見積もり」の表の値（WebSearch の値、幅なら上限）、表にそのステップがなければ `session.estimates_by_method` の値（RQ の概要の `**手法**` のうち最大）、最後に `session.estimates` の値を使う。RQ の工程（Q8、Q11、`rq`）では `--rq` を付ける。`plan.md` は、プロジェクトのルート、メインの作業ツリー、その RQ の worktree の順に探す。
- `--step Q11` は、5 軸レビューの 2 回分（Q11 と Q12）の合計を見る（Q12 も Counter 軸で検索する）。`NEED` の後ろに内訳が出る。
- `STEP` は `R2`、`R6`、`Q8`、`Q11`、`Q12`、`rq`（1 件の RQ の Q2〜Q13 の合計）のいずれか（`session.estimates` のキー）。ないキーを渡すとエラーになる。`R2`・`R6` は `--rq` を付けても `session.estimates` を使う。
- `REMAINING` は `web_search_limit − reserve − USED` である。`NEED` が `REMAINING` を超えれば `VERDICT: STOP`（終了コード 4）になる。
- フックの記録がないときは、`USED` と `REMAINING` が `-` になり、`VERDICT: UNMETERED`（終了コード 0）になる。Claude Code 以外のエージェント、フックを登録する前、登録した後に Claude Code を起動し直していないときである。
- Claude Code では、今のセッションの ID（環境変数 `CLAUDE_CODE_SESSION_ID`）と記録のセッションを照らす。記録が別のセッションのもの（プロジェクトの外で Claude Code を起動した、フックが読まれていない）なら、前のセッションの回数を使わずに `VERDICT: UNMETERED` にし、`RECORDED_SESSION` に記録のセッションと更新日時を出す。この場合は、プロジェクトのルートで Claude Code を起動し直すまで、使った回数を手で数えて引き継ぎ書に書く。

### 実行する場所

| 場所 | コマンド | 実行するスキル |
|---|---|---|
| R2（広域の調査）の前 | `$RK budget --step R2` | researchkit-bootstrap |
| R6（予備調査）の前 | `$RK budget --step R6` | researchkit-bootstrap |
| RQ に入る前（Q1 の前） | `$RK budget --step rq --rq <RQ>` | researchkit-question、researchkit-execute、researchkit-all |
| Q8（収集）の前 | `$RK budget --step Q8 --rq <RQ_NAME>` | researchkit-execute、researchkit-all |
| Q11（5 軸レビュー 1 回目）の前 | `$RK budget --step Q11 --rq <RQ_NAME>` | researchkit-execute、researchkit-all |
| そのほか、検索の多い作業を単独で始める前 | `$RK budget --need <見積もり>` | 必要に応じて |

### 結果ごとの動き

| 結果 | すること |
|---|---|
| `VERDICT: OK` | 続ける |
| `VERDICT: STOP` | その工程に入らずに止まる。それまでのステップのチェックポイントは記録済みなので、新しいセッションで同じスキルを同じ引数で実行すれば、続きから再開する。完了報告に、止まった理由（`USED`・`REMAINING`・`NEED`）と再開のコマンドを書き、`$RK handover --note` で引き継ぎ書を更新する。**自動モードでも止まる。** これは失敗ではなく区切りである |
| `VERDICT: UNMETERED` | 下の「必ず区切る場所」だけに従う |

### 必ず区切る場所（どの環境でも）

| 場所 | すること |
|---|---|
| 調査全体の工程の後（R12 の後） | `session.stop_after_bootstrap` が true（既定）なら、RQ の工程に進まずに止まる。完了報告で「新しいセッションで `researchkit-all` を実行する」と案内する。自動モードでも止まる |
| RQ と RQ の間（Q13 の後） | 回数を数えられない環境（UNMETERED）では、`session.rqs_unmetered`（既定 1）件の RQ を終えたら止まる |

### 見積もりの見直し

- 見積もりは `.researchkit/config.yaml` の `session.estimates` で変える。文献レビューの RQ（検索式を多くのデータベースで回す）は、`rq` と `Q8` を多めにする。
- 実績が見積もりと大きく違ったら、見積もりを直す。実績は、工程の前後の `budget` の `USED` の差で分かる。
- 見積もりが外れて工程の途中で上限に当たったときは、そのステップを完了にせず（`checkpoint` を記録せず）、検索ログに未検索の範囲を書いて止まる。

## 6. 出典 ID と一覧

出典 ID は `S<NNN>-<NNNN>`（前半は最初にその出典を使った RQ の番号、共通の出典は `S000-`）である（steering の「出典台帳」）。

### `sources next`

- `$RK sources next 003` は `S003-0004` のように 1 件、`--count 20` なら 20 件を 1 行ずつ出す。`<NNN>` には `3`、`003`、`003-market-size` のどれを渡してもよい。
- 作業ツリーの `sources/` と、`main`（`RESEARCHKIT_MAIN_BRANCH`）の `sources/` の両方を見て、使われている最大の連番の次から出す。worktree の中で実行しても、`main` にマージ済みの出典と重ならない。
- 払い出しは予約ではない。払い出した ID のファイルを作る前に、もう一度払い出すと同じ ID が出る。サブエージェントに並行して集めさせるときは、親がまとめて払い出してから範囲を分けて渡す（例: `--count 100` の前半と後半）。
- 別の RQ の worktree はそれぞれの RQ の番号を使うので、並行して進めても衝突しない。同じ RQ を 2 か所で同時に進めない。

### `sources list`

- 出力は `| ID | 等級 | 種類 | 題名 | 使った RQ |` の表と、最後の `TOTAL: <件数>` である。
- `--grade A,B` は等級で絞る。`--rq 003` は、ID が `S003-` で始まるものと、`used_in` に `003` の RQ があるものに絞る。`--unused` は、`studies/` と `reports/` の Markdown のどこからも ID が参照されていないものに絞る。組み合わせてよい。
- 出典の必須項目の検証と、使われていない出典の警告は `researchkit-check`（`$CHECK`）が行う。`sources list` は一覧を見るためのものである。

## 8. 公的統計の取得とデータの目録

e-Stat（政府統計の総合窓口）の表は、一覧の HTML を自分で読まずに、次の順で取る。一覧の HTML の読み解きは呼び出しの回数を大きく増やす（003 の Q8 では親の呼び出しの多くがこれに使われた）。

1. `$RK estat list <政府統計コード>`（例: `00500300` 食料需給表）で統計の分類を見る。出力の URL を次の `estat list` に渡し、表の一覧（`TABLES:`）まで下りる。`--grep 国内生産量` のように語で絞る。
2. `$RK estat get <statInfId> --kind <0|1|2> --out data/raw/<名前>.<拡張子>` で取得する。`fileKind` は 0 が Excel、1 が CSV、2 が PDF（一覧の形式の欄）。拡張子が中身と違えば、中身に合う拡張子で保存する（`WARNING` と `PATH` を見る）。
3. その場で `$RK data add <PATH> --source <出典 ID> --url <URL> --desc <表の名前・範囲・単位> --rq <NNN>` を実行し、目録に載せる。ライセンスの既定は e-Stat の利用規約で、ほかの提供元は `--license` で書く。取得の方法の既定は curl のコマンド（`--method` で変える）。
4. 出典台帳（`sources/`）への登録と、抜き書き（`evidence/`）は `researchkit-collect` の手順で行う。

目録に載っていない data/raw/ のファイル、目録にあるのにないファイル、SHA-256 の違うファイルは、`$CHECK --rq <NNN>`（と `--all`）が `UNLISTED_DATA`・`MISSING_DATA`・`HASH_MISMATCH` の ERROR で止める。

## 7. 手動での利用

ユーザーからこのスキルを直接呼ばれたときは、引数に応じて次を行う。

- `status`（または引数なし）: `$RK status` の結果を示し、次に実行すべきスキルを案内する。
  - 調査全体の工程が `DONE` でなければ `researchkit-bootstrap`（`NEXT_STEP` から再開）。R12 を終えたのと同じセッションなら、新しいセッションで始めるよう案内する。
  - 途中の worktree があれば、そのステップを担当するスキル（Q2〜Q7-2 は `researchkit-question`、Q8〜Q12 は `researchkit-execute`、どちらでも `researchkit-all`）。
  - なければ `$HELPER next --phase all` の結果で `researchkit-all <番号>`。空で、`999-research-report` が `完了` なら、`reports/report.md` のレビュー（`researchkit-review`）か公開（`researchkit-publish`）を案内する。
  - 残っている `[人]` のタスクと、等級 `D` の出典があれば、それも挙げる。
- `next`: 上の案内だけを示す。
- `handover [--note <メモ>]`: §3 の手順に従い、次にやることを 1〜3 個に絞って添える。
- `doctor`: 結果を示し、ERROR と、今の工程で直すべき WARN の直し方を案内する。
- `pitfall <内容>`: §3 の書き方で `PITFALLS.md` の先頭に 1 件足す（`$RK pitfall` で見出しを足し、症状・原因・避け方・関係を書き足す。コミットはユーザーに確かめてから）。
- `budget [--step <STEP>]`: 結果を示す。STOP なら区切りであることと再開の方法を、UNMETERED なら 1 セッションで進める RQ の数を伝える。
- `sources next <NNN> [--count <k>]` / `sources list [...]`: 結果を示す。
- `init [...]`: `$RK init` を実行し、作ったものを示す。
- `estat list|get ...` / `data add ...`: 結果の要点を示す（§8）。

応答と成果物は、プロジェクトの言語ルール（`.kiro/steering/language.md`）に従う。
