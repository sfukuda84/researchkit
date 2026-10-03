---
name: "researchkit-collect"
description: "RQ の tasks.md の収集のタスクを実行し、根拠を集めるスキル。plan.md の手法（desk・literature・data・qualitative）の参照文書に従って検索・取得し、出典を sources/ に 1 件 1 ファイルで登録する（researchkit.py sources next で ID を取り、1 件ずつ実在を確かめ、等級を付ける）。原文の引用と位置を studies/<NNN-name>/evidence/ に抜き書きし、データは data/raw/ と data/manifest.md（出所・取得日・ライセンス・ハッシュ）に置き、検索式・件数・見つからなかったことを search-log.md に残す。反証条件に当たる証拠も探す。サブエージェントで並行に集めるときは出典 ID の範囲を分ける。[人] のタスク（インタビューの実施、有料資料の入手など）は実行せず、入手したものを確かめる側を担う。RQ の工程の Q8。「収集して」「資料を集めて」「出典を登録して」と言われたとき、または /researchkit-collect と打たれたときに使う。"
argument-hint: "<RQ（例: 001, 001-market-size）> [--tasks T003-T010] [--parallel <n>] [--auto]"
compatibility: "Requires git and Python 3.9+; WebSearch/WebFetch for desk and literature; uses studies/<NNN-name>/plan.md, tasks.md, .researchkit/config.yaml"
user-invocable: true
disable-model-invocation: false
---

# researchkit-collect スキル（Q8: 収集）

`plan.md` で決めた手順どおりに根拠を集め、**後から誰でもたどれる形**で残す。ここで集めるのは事実と原文であり、解釈と結論は Q9（`researchkit-analysis`）と Q10（`researchkit-findings`）で行う。

パスは既定の配置で書いている。`.researchkit/config.yaml` の `paths` で読み替える。ステップ番号、`$HELPER`、再開、自動モードの共通の規則は [`researchkit-worktree`](../researchkit-worktree/SKILL.md) に従う。`$RK`・`$CHECK` の意味は steering（`.kiro/steering/research.md`）の「エージェントの行動規範」のとおりである。

## 0. 大原則

- **出典のない事実を書かない。** 抜き書きと数値には、必ず出典 ID（`S<NNN>-<NNNN>`）を付ける。
- **AI が挙げた文献・統計・企業名は、1 件ずつ実在を確かめる**（§3.2）。存在しない論文、著者・年・数値の取り違え、架空の DOI が起きやすい。確かめられなかったものは等級 `D` で登録し、根拠に使わない。
- **原文を写す。** 抜き書きは原文のまま引用し、位置（ページ、節、表、時刻）を付ける。要約や言い換えは、引用と分けて書く。数値は、単位・母数・期間・定義と一緒に写す。
- **見つからなかったことも記録する。** 検索式、検索先、期間、件数を `search-log.md` に残す。見つからないことは結果の 1 つである。ただし、存在しないことの証明ではない。
- **反対の証拠も探す。** `plan.md` の「仮説と反証条件」と「反対の証拠の探し方」に沿って、反証条件に当たる証拠と代わりの説明を探す検索を、支持する証拠と同じ重さで行う（§6）。
- **検索の要約を鵜呑みにしない。** 検索結果の要約は、固有名詞と数値を取り違えることがある。要約だけで確かめた事実は、ページを開くか別の出典でもう一度確かめる。
- **計画を黙って変えない。** 検索式・データ源・標本を変えたら、`plan.md` の「計画の変更」に、変えたことと理由を書く（steering の原則 4）。
- **個人と権利を守る。** 個人情報を書かない。有料データベースと統計の利用規約、引用の範囲を守る。判断に迷うものは `[人]` のタスクにする。
- **既存の記録は消さない。** 再実行したときは、検索ログに行を足し、抜き書きに項目を足す。

## 1. 引数

```text
$ARGUMENTS
```

- RQ の指定は `001` か `001-market-size`。省略したら、今いる worktree のブランチ（`rq/<NNN-name>`）から決める。
- `--tasks <範囲>` で実行するタスクを絞る（既定は、収集のタスクのうち未完了のものすべて）。
- `--parallel <n>` で同時に動かすサブエージェントの数を決める（§7。既定は、検索の系統の数と `subagents.max_parallel` の小さい方）。
- `--auto` は自動モード（§10）。

## 2. 入力と前提

| 入力 | 用途 | ない場合 |
|---|---|---|
| `studies/<NNN-name>/tasks.md` | 実行するタスク | 止まって `researchkit-question` を案内する |
| `studies/<NNN-name>/plan.md` | 手法、情報源と検索式、データ、標本、仮説と反証条件、検索数の見積もり | 同上 |
| `studies/<NNN-name>/spec.md` | 問い、答えの形、範囲（地域・期間・対象）、範囲外 | 同上 |
| `researchkit-method/references/<手法>.md` | 手法ごとの収集の手順（`plan.md` の手法に対応するもの） | 手法の節がなければ止まる |
| `.researchkit/memory/constitution.md`、`docs/quality.md` | 出典の等級、最低等級、引用・倫理の規則 | 既定（steering）で進め、完了報告に書く |
| `docs/questions/000-research-foundation.md` | 出典台帳・検索ログ・データの目録の形式 | steering と下の既定で進める |
| `docs/study/hypotheses.md` | 仮説と反証条件 | `plan.md` の反証条件だけで進める |
| `sources/` | 既存の出典（重複を避け、`used_in` に足す） | — |

- `999-research-report` の Q8 は、このスキルではなく `researchkit-synthesize` である。999 が指定されたら案内して止まる。
- `000-research-foundation` のときは §9 に従う。

### 始める前に（検索の予算）

`$RK budget --step Q8 --rq <RQ_NAME>` を実行する（呼び出し元の `researchkit-execute`・`researchkit-all` が直前に確かめていれば省いてよい）。`VERDICT: STOP`（終了コード 4）なら、始めずに止まる。自動モードでも止まる。これは失敗ではなく区切りであり、新しいセッションで同じ引数で実行すれば続きから再開する（steering の「セッションの区切り」）。タスクを絞って一部だけを集めるときは `$RK budget --need <見積もり>` でよい。

## 3. 出典の登録（`sources/`）

### 3.1 ID の取得と再利用

1. 新しい出典を登録する前に、既存の出典を探す。`$RK sources list` の一覧と、URL・DOI・題名での検索（`grep -rl "<DOI か URL の一部>" sources/`）で重複を確かめる。
2. 既存の出典を使うときは、新しく作らずに、その出典の `used_in` にこの RQ を足す（steering「出典台帳」）。
3. 新しい出典の ID は、`plan.md` の「出典 ID」の節に範囲があれば（`tasks.md` の準備のタスクで取ったもの）、その範囲から順に使う。範囲がない、または足りなくなったら `$RK sources next <NNN>`（まとめて取るときは `--count <k>`）で取る。自分で連番を数えない。`main` と並行の worktree の番号を見て空きを出すのはスクリプトの役目である。

### 3.2 実在の確認

出典の種類ごとに実在を確かめ、確かめた方法と日付を `verified_by` に書く（論文は DOI を解決して題名・著者・年・誌名を照合、統計は発表元か e-Stat の表、web はページを開く）。確かめられなかったものは等級 `D` で登録して根拠に使わない（`verified_by` に `未確認: <試したこと>`）。ページを開けず検索の要約で確かめたものは等級を 1 段下げる。孫引きをしない。種類ごとの確かめ方の表は [references/sources.md](references/sources.md)。

### 3.3 等級

等級は憲章に従う（既定: `A` 一次資料・査読つき論文・公的統計・公式の開示、`B` 信頼できる二次資料、`C` そのほかの二次資料、`D` 未確認で根拠に使わない）。`primary`（一次資料か）は等級と別に付ける。詳細は [references/sources.md](references/sources.md)。

### 3.4 ファイルの形

`sources/<ID>.md`。フロントマターは steering の項目どおりで、様式は `researchkit-check` の `templates/source.md`。`url`・`doi`・書誌（`author` と `publisher`）のどれかは必ず埋める。例は [references/sources.md](references/sources.md)。

## 4. 抜き書き（`studies/<NNN-name>/evidence/`）

様式は [templates/evidence.md](./templates/evidence.md)。1 つの出典に 1 ファイル（`evidence/<出典 ID>.md`）を作り、項目を `E1`、`E2` と足す。

- **引用**: 原文のまま書く。省略は「（中略）」、補いは〔 〕で示す。外国語は原文を引用し、自分の訳を添える（言語ルールの「引用」）。
- **位置**: ページ、節、表・図の番号、段落、URL のアンカー、録音の時刻のどれかを必ず書く。レビューの Source 軸が、この位置で原文と照合する。
- **数値**: 単位、母数、期間、時点、定義を一緒に写す。表の数値は、表の題と行・列の名前も写す。
- **向き**: 仮説（`H1` など）に対して、支持・反対・中立のどれかを書く。反対の証拠も同じ形で残す。
- **解釈は分ける**: 「メモ」の欄に書き、引用の中に混ぜない。
- **引用の量は必要な範囲にとどめる。** 長い本文を丸ごと写さない。有料資料の本文は、利用規約が許す範囲だけを写す。

## 5. 手法ごとの収集

中身は `plan.md` で選んだ手法の参照文書（`researchkit-method/references/<手法>.md`）に従う。ここには、このスキルで必ず行うことだけを書く。

| 手法 | 必ず行うこと |
|---|---|
| デスクリサーチ（`desk`） | 公的統計・企業の開示資料（EDINET など）・業界団体の資料を、報道や要約より先に当たる。同じ数値が複数の資料にあれば、元の発表に遡る。推計に使う前提の値も、1 つずつ出典を付ける |
| 文献レビュー（`literature`） | `plan.md` の検索式をデータベースごとにそのまま実行し、件数を記録する。重複の除去、題名と要旨でのふるい分け、本文での適格性の判断を、包含・除外の基準で行い、除外の理由を記録する。PRISMA 2020（Page ほか, 2021）の流れ図の件数（特定、重複除去、ふるい分け、本文の評価、採用）を `search-log.md` にまとめる |
| データ分析（`data`） | データを `data/raw/` に加工せずに置き、`data/manifest.md` に出所（出典 ID）、取得日、ライセンス・利用規約、大きさ、SHA-256 を書く。`data.max_file_mb`（既定 5MB）を超えるファイルは `data/large/` に置き（コミットしない）、目録とハッシュだけを残す。取得の手順（URL、API の条件、絞り込み）も目録に書く。e-Stat の表は `$RK estat list` と `$RK estat get` で探して取り、**取得したらその場で** `$RK data add` で目録に 1 行足す（`researchkit-status` の §8）。まとめて後で書くと、セッションが途中で切れたときに出どころの分からないファイルが残る |
| 定性調査（`qualitative`） | インタビューガイド、アンケート票、同意書、対象者の選び方の案を作るのは AI のタスクである。実施と同意の取得は `[人]`。入手した記録は、個人を特定できる情報を除いてから（対象者は `P01` のような記号）`evidence/` と `sources/`（`type: interview`）に入れる。対応表（記号と本人）はリポジトリに入れない |

ハッシュは次で取る（OS を問わない）。

```bash
python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" data/raw/<file>
```

## 6. 検索ログ（`studies/<NNN-name>/search-log.md`）

すべての検索を 1 回 1 行で書く（採用がない検索も。件数は検索先が示す数）。反証の検索にはメモに「反証の検索（H<n>）」と書く。「見つからなかったこと」の節に、探したが見つからなかったものと調べた範囲を書く。計画から変えた検索は「計画との違い」と `plan.md` の「計画の変更」の両方に書く。文献レビューの記録（引用をたどった記録、PRISMA 2020 の件数）を含む詳細は [references/search-log.md](references/search-log.md)。

## 7. サブエージェントでの並行収集

検索の系統が 2 つ以上あれば、**文献だけでなく、デスク（政策・法令・企業の資料）、統計の取得、反対の証拠の検索も**サブエージェント（`subagents.model`、同時に `subagents.max_parallel` まで）に任せる。親は自分で収集せず、系統の割り振り、ID の範囲、まとめ、抜き取りの確認だけを行う（親の文脈は呼び出しのたびに伸び、以降のすべての呼び出しで読み直される。005 の実測で、親が自分で約 100 回の収集をして Q8 の親の利用量が 1.5 倍になった）。親が出典 ID の範囲を分けて渡し、`tasks.md`・`search-log.md`・`data/manifest.md`・既存の出典ファイルは親だけが書く。サブエージェントの報告の件数・文献名・数値は、成果物のファイルと出典で確かめてから使う。渡すもの・書かせないもの・まとめ方の手順は [references/parallel.md](references/parallel.md)。

## 8. タスクの実行と `[人]`

- `tasks.md` の収集のタスクを、依存の順に実行する。`[P]` のタスクは並行にしてよい。終わったタスクは `- [x]` にする。
- **`[人]` のタスクは実行しない。** 自動モードでも `- [x]` にしない。代わりに、人が動けるように準備する（入手先の URL、必要な手続き、置き場所、完了の確かめ方）。
- ユーザーが `[人]` のタスクの完了を伝えたら、確かめられる部分を確かめてから `- [x]` にする（目録のハッシュの一致、匿名化の済み具合、同意の記録の有無）。
- `[人]` のタスクを待つ間は、依存しない後続のタスクを続ける。
- **答えの形に要る根拠の大半が `[人]` のタスクに依存し**、それなしでは Q9 に進めないとき（例: 根拠がインタビューだけの RQ）は、準備を終えたところで止まる。自動モードでも止まる（steering「モード」）。

## 9. `000-research-foundation` のとき

主張は作らない。共通の出典（`S000-*`）、用語集、データの目録、分析環境の用意、検索ログの形式の見本を整える。詳細は [references/special.md](references/special.md)。

## 10. 自動モード（`--auto`）

`plan.md` の範囲の中の検索式の言い換えは行って記録する。検索式・データ源の変更は推奨案を採って `plan.md` の「計画の変更」と `auto-decisions.md` に記録する。等級に迷う出典は低い方にする。有料資料は入手せず `[人]` のタスクを提案する。予算の STOP、根拠の大半が `[人]` 待ち、`docs/method.md` や憲章の変更が要る、同じ取得の失敗が 3 回、のときは止まる。表は [references/special.md](references/special.md)。

## 11. 仕上げ

1. `tasks.md` の収集のタスクの状態を確かめる（`[人]` 以外がすべて `- [x]`）。
2. `$CHECK --rq <NNN>` を実行し、出典ファイルの ERROR（必須項目の欠け、`id` とファイル名の不一致）を 0 件にする。この時点では `findings.md` がないので、「使われていない出典」の WARN は残ってよい。
3. `data/manifest.md` のハッシュと、`data/raw/` のファイルが一致することを確かめる。`$CHECK --rq <NNN>` が照合し、目録にないファイル（`UNLISTED_DATA`）、目録にあるのにないファイル（`MISSING_DATA`）、ハッシュの違うファイル（`HASH_MISMATCH`）を ERROR にする。
4. 個人を特定できる情報、秘密情報、`data/large/` のファイルがコミットの対象に入っていないことを確かめる（`git status`）。

## 12. 出力

出力の一覧（`sources/`、`evidence/`、`search-log.md`、`data/`、`tasks.md`、`plan.md` の計画の変更）と、次の工程（`researchkit-analysis`、Q8 のチェックポイントは呼び出し元が記録）は [references/special.md](references/special.md)。

## 13. 完了報告

完了報告の項目（実行したタスクと残った `[人]`、出典の件数〈等級別〉、等級 `D`、検索の件数と見つからなかったこと、データと目録、計画の変更と自動の判断、`$CHECK` の結果、次の案内）は [references/special.md](references/special.md)。
