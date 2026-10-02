# researchkit

AI と一緒に調査・分析を進めるためのスキルセット。[my-speckit-scaffold](../speckit/README.md)（仕様駆動開発）の worktree による「単位ごとの工程」を土台に、[novelkit](../novelkit/README.md) の「全体の工程」（種 → 調査 → 方向性 → 壁打ち）と Web 検索の予算、[gamekit](../gamekit/README.md) の「机上検証」「目標値と突き合わせるスクリプト」「多軸レビュー」を、調査向けに置き換えたものである。設計の経緯は [DESIGN.md](DESIGN.md) にある。

- 調べたいことの 1 文から、問いの種、既存の調査の地図、問いの立て方、壁打ち、イシューツリーと仮説、予備調査、手法の選定、問い（RQ）の切り出しまでを `researchkit-bootstrap` で通しで進める（R1〜R12）。
- RQ ごとの仕様から収集・分析・主張のまとめ・レビューまでは、speckit と同じ worktree の工程を調査向けにした `researchkit-all` で進める（Q1〜Q13）。
- 対象は 4 種類の調査である: 市場・競合・技術のデスクリサーチ、文献レビュー、データ分析、定性調査（インタビュー・アンケート）。手法は RQ ごとに選び、1 つの調査で混ぜてよい。
- 事実には出典 ID を付け、出典は 1 件 1 ファイルの台帳（`sources/`）で等級とともに管理する。報告の数値は分析の出力（JSON）への参照を付け、`numbers.py` で突き合わせる。
- Claude Code、Codex CLI、Antigravity、Kiro CLI、opencode で同じスキルと規則を使う（規則の正本は `.kiro/steering/`、スキルの本体は `skills/researchkit/`）。
- ステップが終わるたびにコミットし、trailer（`Researchkit-Bootstrap`、`Researchkit-Step`、`Researchkit-Question`）から進捗を判定する。中断しても続きから再開できる。
- スクリプトは Python（標準ライブラリのみ、3.9 以上）で、macOS、Linux、Windows で動く。分析のコードは、プロジェクトごとに依存を持ってよい（既定は Python と uv）。

## 工程

```text
調査全体の工程（researchkit-bootstrap）
 R1 問いの種（読み手と決めたいこと） → R2 既存の調査・先行研究・データの所在の地図
 → R3 問いの立て方の 3 案 → R4 壁打ち（前提 RP1〜RP12）
 → R5 イシューツリーと仮説（反証条件つき） → R6 予備調査（問いが答えられるか、データが手に入るか）
 → R7 手法と分析環境 → R8 憲章 → R9 RQ の切り出し
 → R10 共通基盤（000） → R11 品質基準と最終成果物（999） → R12 検証

RQ の工程（researchkit-question → researchkit-execute、通しは researchkit-all）
 Q1 worktree → Q2 specify → Q3・Q4 clarify ×2 → Q5 plan（事前に分析の計画と反証条件）
 → Q6 tasks → Q7 analyze ×2 → Q8 収集 → Q9 分析 → Q10 主張のまとめと逆流
 → Q11・Q12 5 軸レビュー ×2 → Q13 マージと引き継ぎ書
```

| 区分 | スキル | 工程 | 元 |
|---|---|---|---|
| 統括 | `researchkit-bootstrap` | R0〜R12（`--auto`、`--oneshot`、`--adopt`、`--skip-pilot`） | gamekit-bootstrap、novelkit-bootstrap |
| 統括 | `researchkit-question` | Q1〜Q7-2、Q13 | speckit-feature |
| 統括 | `researchkit-execute` | Q1、Q8〜Q13 | speckit-coding |
| 統括 | `researchkit-all` | Q1〜Q13 | speckit-all |
| 共通 | `researchkit-worktree` | Q1、Q13、ステップ番号、自動モード | gamekit-worktree |
| 共通 | `researchkit-status` | 進捗、引き継ぎ書、環境の診断、Web 検索の予算 | gamekit-status、novelkit-status |
| 共通 | `researchkit-check` | 出典の参照と数値の機械検証 | novelkit-check、gamekit-balance |
| 共通 | `researchkit-review` | Q11、Q12、単独 | gamekit-review |
| 企画 | `researchkit-seed` | R1 | novelkit-seed、gamekit-seed |
| 企画 | `researchkit-scan` | R2 | novelkit-research-wide、gamekit-research |
| 企画 | `researchkit-framing` | R3 | novelkit-direction、speckit-architecture |
| 企画 | `researchkit-sparring` | R4 | novelkit-sparring、gamekit-sparring |
| 設計 | `researchkit-hypothesis` | R5 | gamekit-core |
| 設計 | `researchkit-pilot` | R6 | gamekit-prototype |
| 設計 | `researchkit-method` | R7 | gamekit-architecture |
| 設計 | `researchkit-constitution` | R8 | speckit-constitution、novelkit-constitution |
| 設計 | `researchkit-questions` | R9 | speckit-concept-2-feature、gamekit-features |
| 設計 | `researchkit-foundation` | R10 | speckit-common-feature |
| 設計 | `researchkit-deliverable` | R11 | speckit-nfr-feature |
| RQ | `researchkit-specify` | Q2 | speckit-specify |
| RQ | `researchkit-clarify` | Q3、Q4 | speckit-clarify |
| RQ | `researchkit-plan` | Q5 | speckit-plan |
| RQ | `researchkit-tasks` | Q6 | speckit-tasks |
| RQ | `researchkit-analyze` | Q7-1、Q7-2 | speckit-analyze |
| RQ | `researchkit-collect` | Q8 | speckit-implement（前半） |
| RQ | `researchkit-analysis` | Q9 | speckit-implement（後半） |
| RQ | `researchkit-findings` | Q10 | speckit-converge |
| 統合 | `researchkit-synthesize` | 999 の Q8 | — |
| 統合 | `researchkit-publish` | 999 の Q9（任意） | speckit-presentation |

Spec Kit の標準スキル（`speckit-specify` など）は同梱しない。ソフトウェア向けの書式（ユーザーストーリー、契約、データモデル）が前提で、調査には合わないためである。工程の型（specify → clarify ×2 → plan → tasks → analyze → 実行 → converge → review）だけを借り、researchkit 専用のスキルとして書いている。`.specify/` も持たない。

RQ の番号のうち、`000-research-foundation` は共通基盤（出典台帳・用語集・データの目録・分析環境・検索ログの形式）、`999-research-report` は統合報告である。999 は、ほかのすべての RQ が `完了` か `人の作業待ち` になってから始め、Q8 で `researchkit-synthesize`（結論を先に書く統合報告 `reports/report.md`）、Q9 で `researchkit-publish`（読み手に合わせた形式）を使う。

### 手法

RQ の Q8（収集）と Q9（分析）の中身は、`plan.md` で選んだ手法の参照文書（`researchkit-method/references/`）に従う。

| 手法 | 参照文書 | Q8 収集 | Q9 分析 | 主な `[人]` |
|---|---|---|---|---|
| デスクリサーチ | `desk.md` | Web・公的統計・企業の開示資料・業界レポート | 主張と根拠の表、比較表、推計（フェルミ推定は前提を表で） | 有料レポートの購入 |
| 文献レビュー | `literature.md` | 検索式とデータベース、包含・除外の基準、PRISMA の流れ図の件数 | 抽出表、研究の質の評価、統合（ナラティブ／簡易メタ分析） | 有料論文の入手、専門家の確認 |
| データ分析 | `data.md` | データの取得と `data/manifest.md` の目録（出所、取得日、ライセンス、ハッシュ） | 再実行できるスクリプト（`commands.analysis`）、前処理の記録、図表 | 社内データの取得、アクセス権の申請 |
| 定性調査 | `qualitative.md` | インタビューガイド、アンケート票、同意書、対象者の選び方 | 文字起こしの匿名化、コーディング、KJ 法、テーマの抽出 | 実施、同意の取得、倫理審査 |

### レビューの 5 軸

| 軸 | 見ること |
|---|---|
| Source | 出典が実在し、たどれるか。一次資料か。日付は新しいか。等級は品質基準を満たすか。孫引きをしていないか |
| Logic | 主張と根拠の間に飛躍がないか。相関と因果の混同、過度の一般化がないか |
| Counter | 反対の証拠と代わりの説明を探したか（Web で追加の検索をする） |
| Bias | 確証バイアス、選択バイアス、生存者バイアス、標本の偏り、スポンサーの利害、検索語の偏り |
| Numbers | 数値を出力ファイルと突き合わせて検算する。分析のスクリプトを再実行して同じ結果になるか |

定性調査とデータ分析を含む RQ では、Ethics（同意、匿名化、ライセンス、利用規約）を 6 軸目として足す。軸ごとに文脈を持たないサブエージェントで独立に審査し、親が裏を取る。

## 3 キットとの違い

| 観点 | speckit | novelkit | gamekit | researchkit |
|---|---|---|---|---|
| 単位 | 機能 | 章 | 機能 | 問い（RQ） |
| 全体の工程 | コアコンセプト → 機能の仕分け | 種 → 調査 → 方向性 → 壁打ち → プロット → 設定 | 種 → 調査 → 方向性 → 壁打ち → 柱とコアループ → 机上検証 → システム設計 | 種 → 地図 → 問いの立て方 → 壁打ち → イシューツリーと仮説 → 予備調査 → 手法 |
| 単位の工程 | specify → plan → tasks → implement | アウトライン → 矛盾検出 → 執筆 → 4 軸レビュー | speckit ＋ 調整仕様、バランス検証 | specify → plan（反証条件） → tasks → 収集 → 分析 → 主張 |
| 根拠の管理 | — | 正典（設定資料） | 目標値（`targets.md`） | 出典台帳（`sources/`、等級 A〜D）と主張の表 |
| 機械検証 | テスト | `check.py`（整合・文章） | `balance.py`（目標値） | `check.py`（出典）、`numbers.py`（数値） |
| レビュー | Standards・Spec の 2 軸 | 物語・整合・類似性・文章の 4 軸 | ＋ Balance・Feel・Originality の 5 軸 | Source・Logic・Counter・Bias・Numbers の 5 軸（＋ Ethics） |
| Web 検索の予算 | — | `budget` | — | `budget`（novelkit から移植） |
| 人のタスク（`[人]`） | 契約、管理画面の操作など | 作者が書く話 | ＋ プレイ確認、ストアの公開 | インタビューの実施、同意、倫理審査、有料資料の入手、社内データの取得 |
| Spec Kit の標準スキル | 同梱 | 同梱しない | 同梱 | 同梱しない（工程の型だけを借りる） |

## モード

| | 通常モード（既定） | 自動モード（`--auto`） |
|---|---|---|
| 質問 | 推奨案を添えて質問し、合意を得てから進める | 質問せず推奨案を採用し、`auto-decisions.md` に記録する |
| 止まる場面 | — | マージの競合、中止、憲章・品質基準・`docs/method.md` の変更が要るとき、`[人]` のタスクが終わらないと先に進めないとき、同じ原因の失敗が 3 回続いたとき、Web 検索の予算が足りないとき |
| `[人]` のタスク | 人が行い、完了を伝える | 同じ（自動で完了にしない） |

`researchkit-bootstrap` には、最初に一度だけ質問して以降を自動で進める `--oneshot` と、既存の調査の資料から足りない成果物だけを作る `--adopt` もある。小さな調査では `--skip-pilot` で予備調査（R6）を省ける。

## セッションの区切り

Web 検索には 1 セッションあたりの回数の上限がある（Claude Code で観測した値は 200 件）。調査は 4 キットの中で最も検索が多いので、novelkit の仕組みをそのまま入れ、セッションを工程の境目で区切る。

- **必ず区切る**: 調査全体の工程（R12）の後。新しいセッションで `researchkit-all` を始める。
- **回数を数えて区切る**: プロジェクトを作るときに `.claude/settings.json` にフックが入り、セッションごとの Web 検索の回数を `.researchkit/usage/` に記録する。R2・R6 の前、RQ に入る前、Q8・Q11 の前に `researchkit.py budget --step <STEP>` で残りを確かめ、`VERDICT: STOP` なら工程の境目で止まる（自動モードでも止まる）。新しいセッションで同じスキルを同じ引数で実行すれば、続きから再開する。
- **数えられない環境**（Claude Code 以外）では、1 セッションで `session.rqs_unmetered`（既定 1）件の RQ を終えたら止まる。
- 上限と見積もりは `.researchkit/config.yaml` の `session` で変える。文献レビューの RQ は多めに見積もる。既存の調査には `python3 skills/researchkit/researchkit-status/scripts/researchkit.py hooks install` でフックを入れる。

## コマンドの導入と更新

[speckit](https://github.com/sfukuda84/my-speckit-scaffold) の `new-speckit-project` と同じく、uv のツールとして入れる。

```bash
uv tool install "git+https://github.com/sfukuda84/researchkit#subdirectory=tool"   # 導入（初回だけ）
uv tool upgrade new-researchkit-project                                          # コマンドの更新
new-researchkit-project update [プロジェクトのディレクトリ]                          # 作成済みのプロジェクトに scaffold の新しい版を取り込む
```

- `new-researchkit-project` は、実行のたびに scaffold を GitHub から取得してプロジェクトを作る（`--ref` でブランチやタグ、`--repo` でリポジトリを指定できる）。
- `update` は、scaffold の持ち物（スキル、ルールなど）だけを取り込み、1 つのコミットにする。scaffold のどの版とも中身が一致しないファイルは手で直したものとみなして上書きせず、新しい版を `.scaffold-new/` に置く。取り込みで残した同名のスキルにも触らない。`--dry-run` で、何が変わるかだけを見られる。
- スキルを scaffold へのリンクで置いたプロジェクト（`--link`）は、スキルがすでに最新なので、`update` はリンクの外（ルールなど）だけを更新する。
- 手元の scaffold（このリポジトリの clone）から使うときは、`scripts/new-researchkit-project` を直接実行するか、`--scaffold <ディレクトリ>` を付ける。`--link` は手元の scaffold を使うときだけ使える。
- オプションの一覧は [tool/README.md](tool/README.md) にある。

## 使い方

### 新しい調査

```bash
new-researchkit-project ~/research/market-entry --title "〇〇市場の参入判断" -m "国内の〇〇市場に、来年度に参入すべきか"
```

- プロジェクトを作り、問いを `docs/concept/core-question.md` に保存して、Claude Code で `/researchkit-bootstrap` を始める。`-m` を省くと対話で問いを聞く。`--auto`・`--oneshot` を付けると、そのモードで始める。`--agent codex`（`agy`、`kiro`、`opencode`）で別のエージェントを起動する。
- 作るときに `researchkit.py init`（`.researchkit/config.yaml` と既定のディレクトリ）と `researchkit.py hooks install`（Web 検索の回数を数えるフック）を実行する。
- スキルはプロジェクトの `skills/researchkit/` にコピーされる。手元の scaffold を使い `--link` を付けると、scaffold へのシンボリックリンクになる（scaffold の更新がすぐ反映される）。シンボリックリンクを作れない環境（Windows で開発者モードがオフなど）では、実体をコピーして警告する。
- 立ち上げ（R12）が終わったらセッションを区切り、新しいセッションの `/researchkit-all` で `000-research-foundation` から 1 件ずつ進める。`/researchkit-all all --auto` で全 RQ を無人で進めることもできる（`[人]` のタスクと、Web 検索の予算による区切りでは止まる）。

### 既存の調査に取り込む

```bash
new-researchkit-project ~/research/existing --adopt
```

- 既存のファイルは上書きしない。`.gitignore` は、足りない行だけを末尾に足す。追加したファイルを確かめてからコミットする。
- `.claude/skills/` などに同名のスキルがあれば残し、`CONFLICT` として表示する。researchkit 版に揃えるなら、既存のものを消してから、表示されたコマンド（取り込みの再実行か、手元の scaffold の `python3 scripts/new_project.py --relink <プロジェクト>`）で張り直す。
- 既存の `CLAUDE.md` などは上書きしないので、表示された行（`@.kiro/steering/research.md` など）を足す。
- `.researchkit/config.yaml` の `paths` を既存の配置に合わせる。ファイルは動かさない。合わせた後に `researchkit.py init` を実行すると、足りないディレクトリだけを作る。`researchkit.py doctor` で確かめる。
- `/researchkit-bootstrap --adopt` で、既存の資料（企画書、調査報告、文献リスト、データ、インタビューのメモ）から足りない成果物だけを作る。R1〜R12 ごとの扱いを `docs/adopt-plan.md` に書いて合意してから進める。元のファイルは動かさない。

### 進捗の確認と引き継ぎ

```bash
RK=skills/researchkit/researchkit-status/scripts/researchkit.py
python3 $RK status               # 調査全体の工程と RQ の工程の進捗、出典の件数（等級別）
python3 $RK handover             # 引き継ぎ書（docs/handover/）
python3 $RK doctor               # 設定、リンク、フックの診断
python3 $RK budget --step Q8     # Web 検索の残り（VERDICT: OK / STOP / UNMETERED）
python3 $RK sources list --unused   # 使われていない出典
```

または `/researchkit-status` を実行する。

### 出典と数値の確認

```bash
CHECK=skills/researchkit/researchkit-check/scripts/check.py
NUM=skills/researchkit/researchkit-check/scripts/numbers.py
python3 $CHECK --all             # 主張の根拠の出典 ID、出典の必須項目、等級、使われていない出典
python3 $CHECK --rq 003 --online # RQ 003 だけ。URL と DOI に到達できるかも確かめる
python3 $NUM --all               # findings.md・報告書の数値と、分析の出力（JSON）の突き合わせ
python3 $NUM --file reports/report.md
```

- `check.py` と `numbers.py` は、1 行 1 件 `ERROR|WARN <ファイル>:<行> <コード> <説明>` と、最後に `SUMMARY: errors=<n> warnings=<n>` を出す。エラーがあれば終了コード 1。
- 主張は `findings.md` の表（ID・主張・根拠・確度・反証と限界）で書き、根拠の欄に出典 ID（`S<NNN>-<NNNN>`）を書く。分析の出力から得た数値には `{N:analysis/out/<ファイル>.json#<キー>}` を付ける。手で計算した数値は `{N:calc}` を付け、計算式と入力を表に残す。
- または `/researchkit-check` を実行する。

## ディレクトリ構成（scaffold）

```text
.
├── README.md、DESIGN.md、LICENSE
├── CLAUDE.md / AGENTS.md / GEMINI.md / opencode.json   # .kiro/steering を読むよう指示するだけ
├── .kiro/steering/                     # エージェント共通ルールの正本
│   ├── language.md                     #   応答と成果物は日本語
│   └── research.md                     #   researchkit の工程とルール
├── .claude/skills/ .agents/skills/ .kiro/skills/   # → skills/researchkit/* へのシンボリックリンク
├── skills/researchkit/                 # researchkit のスキル（29 本）
│   ├── researchkit-status/scripts/     #   researchkit.py（進捗・引き継ぎ書・診断・予算・出典 ID）、rklib.py、count_search.py
│   ├── researchkit-worktree/scripts/   #   worktree_helper.py（gamekit 版の移植）
│   ├── researchkit-questions/scripts/  #   validate.py（RQ 一式の検証）
│   ├── researchkit-check/scripts/      #   check.py（出典）、numbers.py（数値）
│   ├── researchkit-method/references/  #   desk.md、literature.md、data.md、qualitative.md
│   └── researchkit-publish/scripts/    #   build_pptx.py（スライド。python-pptx を uv run で使う）
├── docs/dev/CONTRACT.md                # スキルとスクリプトの間の取り決め（scaffold の開発用）
├── scripts/
│   ├── new_project.py                  # プロジェクトを作る・既存の調査に取り込む・リンクを張り直す（--relink）
│   └── new-researchkit-project         # 手元の scaffold から使うときの入口（本体は tool/）
├── tool/                               # uv で入れるコマンド new-researchkit-project（作成・取り込み・update）とテスト
└── .github/workflows/scaffold-tests.yml   # tool/tests を Ubuntu・macOS・Windows × Python 3.9・3.12 で実行
```

プロジェクトには、`tool/`、`.github/`、`scripts/`、`DESIGN.md`、`docs/dev/`、`LICENSE`、この README は持ち込まない。

## プロジェクトのディレクトリ構成

```text
.researchkit/config.yaml          # パス、コマンド（analysis、test）、Web 検索の予算、確度の段階、出典の等級、数値の許容差
.researchkit/memory/constitution.md   # 憲章（出典の等級、確度の段階、引用、数値、倫理、AI 利用の開示）
.researchkit/scaffold.json        # 取り込んだ scaffold の版（update が使う）
.researchkit/usage/               # Web 検索の回数の記録（コミットしない）
docs/concept/                     # core-question.md、seed.md、framing.md、premises.md、backlog.md
docs/scan/                        # wide.md
docs/study/                       # issue-tree.md、hypotheses.md、pilot/
docs/method.md、docs/quality.md、docs/glossary.md
docs/questions/                   # 000-research-foundation.md、001-*.md、999-research-report.md、README.md、spec_order.md
docs/auto-decisions.md、docs/adopt-plan.md
docs/reviews/                     # 工程の外のレビュー
docs/handover/                    # CURRENT_STATE.md、PITFALLS.md、sessions/
sources/                          # 出典台帳（S<NNN>-<NNNN>.md。1 件 1 ファイル）
data/                             # manifest.md、raw/（小さな生データ）、large/（コミットしない）
studies/<NNN-name>/               # spec.md、plan.md、tasks.md、search-log.md、evidence/、analysis/、findings.md、reviews/
reports/                          # report.md（統合報告）、publish/（読み手ごとの形式）
```

## 取り入れた手法

| 工程 | 手法 |
|---|---|
| 種（R1） | 問いを意思決定から導く（誰が何を決めるための調査か）、読み手と答えの使い道を先に決める |
| 地図（R2） | 一次資料と二次資料の区別、KJ 法（川喜田二郎）による事実のまとめ |
| 仮説（R5） | イシューツリーと MECE（漏れなく重なりなく）、仮説思考（仮の答えを先に置いて検証する）、反証可能性（カール・ポパー）に基づく反証条件 |
| 予備調査（R6） | パイロット調査（本調査の前に、問いとデータの入手可能性を小さく確かめる） |
| 計画（Q5） | 事前登録（分析の計画と反証条件を収集の前に書き、変更は理由とともに記録する） |
| 文献レビュー | PRISMA 2020（Page ほか、2021）の流れ図の件数、検索式と包含・除外の基準、抽出表、ナラティブ統合と簡易メタ分析 |
| デスクリサーチ | 公的統計と企業の開示資料を一次資料として優先する、フェルミ推定（前提を表で示す） |
| データ分析 | 再実行できる分析（スクリプトと出力の分離、データの目録とハッシュ） |
| 定性調査 | 半構造化インタビュー、同意と匿名化、コーディング、KJ 法、テーマの抽出 |
| 主張（Q10） | 主張・根拠・確度・反証の表、見つからなかったことの記録 |
| レビュー（Q11・Q12） | バイアスの点検（確証バイアス、選択バイアス、生存者バイアスなど）、反対の証拠と代わりの説明の探索、数値の検算と再実行 |
| 統合（999） | ピラミッド構造（バーバラ・ミント）による、結論を先に書く報告 |

## まだないもの

- 本物の調査での通しの試し（DESIGN.md §9 の P6。詰まった点は PITFALLS に記録して設計に戻す）
- 調査向けの壁打ちの相手（`~/.myai/sparring` の市場アナリスト、学術研究者、データサイエンティスト、UX リサーチャーと `sparring-research`）
- 有料データベースや社内データへの自動の接続（いまは `[人]` のタスクで扱う）
- 引用文献の書式（APA など）への自動の整形
