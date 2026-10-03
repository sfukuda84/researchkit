# researchkit 設計書

AI と一緒に調査・分析を進めるためのスキルセット。[speckit](../speckit/README.md) の worktree による「単位ごとの工程」を土台に、[novelkit](../novelkit/README.md) の「全体の工程」（種 → 調査 → 方向性 → 壁打ち）、Web 検索の予算、正典を取り入れる。さらに、[gamekit](../gamekit/README.md) の「机上検証」「目標値と突き合わせるスクリプト」「多軸レビュー」を、調査向けに置き換える。

この文書は設計の考え方を残すものである（実装済み）。規則の正本は `.kiro/steering/research.md`、スキルとスクリプトの間の取り決めは `docs/dev/CONTRACT.md` にあり、食い違うときはそちらを正とする。

## 1. 方針

- **単位は問い（リサーチクエスチョン、RQ）**。speckit の「機能」、novelkit の「章」に当たる。RQ ごとに worktree（`.worktrees/<NNN-name>`、ブランチ `rq/<NNN-name>`）で進め、`main` にマージする。
- **対象は 4 種類の調査**: 市場・競合・技術のデスクリサーチ、学術・文献レビュー、データ分析、定性調査（インタビュー・アンケート）。手法は RQ ごとに選ぶ。1 つの調査で混ぜてよい。
- **骨格は 3 キットと同じ**: 規則の正本は `.kiro/steering/`、スキルの本体は `skills/researchkit/`、各エージェントからは相対シンボリックリンクで参照する。進捗はコミットの trailer で判定する。モードは `--auto`・`--oneshot`・`--adopt`、人の作業は `[人]` で表す。コマンドは `new-researchkit-project`（作成・`update`・取り込み）。スクリプトは Python 3.9 以上で、標準ライブラリだけを使う。
- **Spec Kit の標準スキルは同梱しない（推奨）**。`speckit-specify` などはソフトウェア向けの書式（ユーザーストーリー、契約、データモデル）が前提で、調査には合わない。そこで工程の型（specify → clarify ×2 → plan → tasks → analyze → implement → converge → review）だけを借り、researchkit 専用のスキルとして書く。`.specify/` も持たない。gamekit の worktree_helper.py と gklib.py は移植して流用する。

## 2. 大原則（steering に書くもの）

gamekit-research と novelkit-research の大原則を、調査の全工程に広げる。

1. **出典のない事実を書かない**。事実には出典 ID を付け、出典には URL か書誌情報と参照日を付ける。
2. **AI が挙げた文献・作品・統計は、1 件ずつ実在を確かめる**。論文は DOI か出版社・データベースのページで確かめる。確かめられなかったものは「未確認」の表に分け、根拠にしない。
3. **問いは意思決定から導く**。誰が何を決めるための調査かを R1 で決め、すべての RQ をそこにつなぐ。答えても決定が変わらない RQ は作らない。
4. **仮説と反証条件を先に書く**。分析の計画（何を見たら仮説を捨てるか）は、収集の前に `plan.md` に書く（事前登録に当たる）。収集の後に計画を変えたときは、変えたことと理由を記録する。
5. **主張には確度を付ける**。憲章で定めた段階（例: 確実／可能性が高い／示唆／不明）で表し、根拠の数と質から付ける。
6. **見つからなかったことも記録する**。検索式、データベース、期間、件数を検索ログに残す。ただし、見つからないことは存在しないことの証明ではない。
7. **反対の証拠を探す**。各 RQ で、仮説に反する証拠と代わりの説明を探す工程を省かない。
8. **数値は再計算できる形で持つ**。分析は `studies/<NNN-name>/analysis/` のスクリプトから再実行できるようにし、報告の数値は出力ファイルと突き合わせる（gamekit の `balance.py check` に当たる）。
9. **個人と権利を守る**。インタビューの同意、個人情報の匿名化、引用の範囲、有料データベースの利用規約を守る。判断に迷うものは `[人]` にする。
10. **成果物と結論を同期させる**。分析で前提や仮説が崩れたら、`findings.md` だけでなく、`hypotheses.md` と `issue-tree.md` にも戻して直す（novelkit の「逆流」）。

## 3. 工程

### 3.1 調査全体の工程（`researchkit-bootstrap`、R0〜R12）

| ステップ | スキル | 成果物 | 元 |
|---|---|---|---|
| R0 | （bootstrap） | Git、`.researchkit/config.yaml`、`docs/concept/core-question.md` | 3 キット共通 |
| R1 | `researchkit-seed` | `docs/concept/seed.md`（問いの種、読み手、決めたいこと、期限、答えの使い道） | novelkit-seed、gamekit-seed |
| R2 | `researchkit-scan` | `docs/scan/wide.md`（既存の調査・先行研究・用語・データの所在の地図） | novelkit-research-wide、gamekit-research |
| R3 | `researchkit-framing` | `docs/concept/framing.md`（問いの立て方の 3 案と選択。例: 仮説検証型／探索型／比較評価型） | novelkit-direction、speckit-architecture |
| R4 | `researchkit-sparring` | `docs/concept/premises.md`（RP1〜RP12）、`backlog.md` | novelkit-sparring、gamekit-sparring |
| R5 | `researchkit-hypothesis` | `docs/study/issue-tree.md`（イシューツリー）、`hypotheses.md`（仮説と反証条件） | gamekit-core |
| R6 | `researchkit-pilot` | `docs/study/pilot/`（小さな予備調査で、問いが答えられるか、データが手に入るかを確かめる） | gamekit-prototype |
| R7 | `researchkit-method` | `docs/method.md`（手法の 3 案比較と選択、データ源、分析環境）、`config.yaml` の `commands` | gamekit-architecture |
| R8 | `researchkit-constitution` | `.researchkit/memory/constitution.md`（出典の等級、確度の段階、引用、数値、倫理、AI 利用の開示） | speckit-constitution、novelkit-constitution |
| R9 | `researchkit-questions` | `docs/questions/`（`001-*.md` 以降、`README.md`、`spec_order.md`） | concept-2-feature、gamekit-features |
| R10 | `researchkit-foundation` | `docs/questions/000-research-foundation.md`（出典台帳・用語集・データの目録・分析環境・検索ログの形式） | speckit-common-feature |
| R11 | `researchkit-deliverable` | `docs/quality.md`（品質基準）、`docs/questions/999-research-report.md`（最終成果物の読み手・形式・構成） | speckit-nfr-feature |
| R12 | （bootstrap） | 全体の検証（`validate.py --require-reserved`、`check.py --all`、`researchkit.py doctor`） | 3 キット共通 |

- R4 の前提 RP1〜RP12 は、読み手、決めたいこと、範囲（地域・期間・対象）、期限、予算、使えるデータとアクセス、要求する確度、成果物の形式、倫理と個人情報、利害関係（スポンサーの意向など）、言語、既知の制約の 12 項目にする。
- R6 の予備調査は、検索数件とデータの所在の確認、1〜2 人への試しの質問などで、問いの立て方の誤りを早く見つけるために行う。小さな調査では飛ばせる（`researchkit-bootstrap --skip-pilot`、単独では `researchkit-pilot --skip <理由>`。飛ばしても理由を記録して R6 として記録する）。
- R12 の後は、novelkit と同じくセッションを区切る（§6）。

### 3.2 RQ の工程（`researchkit-question` → `researchkit-execute`、通しは `researchkit-all`）

| ステップ | スキル | 成果物 | speckit の対応 |
|---|---|---|---|
| Q1 | `researchkit-worktree` | `.worktrees/<NNN-name>` | S1 |
| Q2 | `researchkit-specify` | `studies/<NNN-name>/spec.md`（問い、つながる決定、答えの形、判定の基準、範囲外） | S2 |
| Q3〜Q4 | `researchkit-clarify` ×2 | `spec.md`（2 回目は調査特有の曖昧さ: 用語の定義、母集団、期間、地域、比較の対象、単位） | S3〜S4 |
| Q5 | `researchkit-plan` | `plan.md`（手法、情報源と検索式、データ、標本、分析の計画、仮説と反証条件、検索数の見積もり） | S5 |
| Q6 | `researchkit-tasks` | `tasks.md`（`[人]` を含む） | S6 |
| Q7-1〜Q7-2 | `researchkit-analyze` ×2 | spec・plan・憲章・仮説の整合 | S7 |
| Q8 | `researchkit-collect` | `sources/`（出典台帳）、`studies/<NNN-name>/evidence/`（抜き書き）、`data/raw/`、検索ログ | S8（前半） |
| Q9 | `researchkit-analysis` | `studies/<NNN-name>/analysis/`（スクリプト・出力）、抽出表、コーディング表 | S8（後半） |
| Q10 | `researchkit-findings` | `findings.md`（主張 → 根拠 ID → 確度 → 反証の有無）、逆流（`hypotheses.md` などの更新） | S9 converge |
| Q11〜Q12 | `researchkit-review` ×2 | `studies/<NNN-name>/reviews/review-<n>.md`（5 軸） | S10〜S11 |
| Q13 | `researchkit-worktree` | `main` への `--no-ff` マージ、`docs/questions/` の状態の更新、引き継ぎ書 | S12 |

- 仕様工程（Q1〜Q7）だけを行う `researchkit-question` と、実行工程（Q8〜Q13）を行う `researchkit-execute` に分ける。speckit-feature と speckit-coding の分け方と同じである。
- Q8 の前と Q11（反証の探索で検索する）の前に、`budget` で検索の残りを確かめる。

### 3.3 手法ごとの差（`researchkit-method/references/`）

Q8〜Q9 の中身は、`plan.md` で選んだ手法の参照文書に従う。

| 手法 | 参照文書 | Q8 収集 | Q9 分析 | 主な `[人]` |
|---|---|---|---|---|
| デスクリサーチ | `desk.md` | Web・公的統計・企業の開示資料・業界レポート | 主張と根拠の表、比較表、推計（フェルミ推定は前提を表で） | 有料レポートの購入 |
| 文献レビュー | `literature.md` | 検索式とデータベース（Google Scholar、CiNii、PubMed、Semantic Scholar など）、包含・除外の基準、PRISMA の流れ図の件数 | 抽出表、研究の質の評価、統合（ナラティブ／簡易メタ分析） | 有料論文の入手、専門家の確認 |
| データ分析 | `data.md` | データの取得と `data/raw/` の目録（出所、取得日、ライセンス、ハッシュ） | 再実行できるスクリプト（`commands.analysis`）、前処理の記録、図表 | 社内データの取得、アクセス権の申請 |
| 定性調査 | `qualitative.md` | インタビューガイド、アンケート票、同意書、対象者の選び方 | 文字起こしの匿名化、コーディング、KJ 法、テーマの抽出 | 実施、同意の取得、倫理審査 |

### 3.4 統合と公開

`999-research-report` は、全 RQ の完了後に同じ worktree の工程で進める。Q8 は `researchkit-synthesize`、Q9 は `researchkit-publish`（不要なら理由を記録して空のチェックポイント）、Q10 は `researchkit-findings` の統合モード（報告の結論と各 RQ の主張の整合、逆流）である。

- `researchkit-synthesize`: 全 RQ の `findings.md` を、結論を先に書く構成（ピラミッド構造）で統合し、`reports/report.md` を作る。エグゼクティブサマリー、確度つきの結論、限界、次の問いを含める。
- `researchkit-publish`（任意）: 読み手（`executive`／`team`／`external`）に合わせた形式を `reports/publish/<読み手>/` に作る。スライドは speckit-presentation の `build_pptx.py` を移植し、文書は Markdown・HTML か docx にする。公開用の文書からは `strip_refs.py` で `{N:...}` を取り除く。数値は `findings.md` と分析の出力にあるものだけを使う。

### 3.5 共通

- `researchkit-status`: 進捗、引き継ぎ書（`docs/handover/`）、環境の診断、Web 検索の予算（novelkit の `budget` を移植）。
- `researchkit-review`: 5 軸のレビュー（§4）。工程の外でも、任意の報告書や資料のレビューに使う。
- `researchkit-check`: 機械検証（§5）。

## 4. レビューの 5 軸（`researchkit-review`）

gamekit-review と同じく、軸ごとに文脈を持たないサブエージェントで独立に審査し、親が裏を取る。

| 軸 | 見ること |
|---|---|
| Source | 出典が実在し、たどれるか。一次資料か。日付は新しいか。出典の等級は憲章の最低水準を満たすか。孫引きをしていないか。 |
| Logic | 主張と根拠の間に飛躍がないか。相関と因果を混同していないか。一般化しすぎていないか。spec の「答えの形」に答えているか。 |
| Counter | 反対の証拠と代わりの説明を探したか（Web で追加の検索をする）。反証条件に当たる結果を無視していないか。 |
| Bias | 確証バイアス、選択バイアス、生存者バイアス、標本の偏り、スポンサーの利害、検索語の偏りがないか。 |
| Numbers | 数値を出力ファイルと突き合わせて検算する。単位、母数、期間、為替や物価の扱いを確かめる。分析のスクリプトを再実行して同じ結果になるかも確かめる。 |

定性調査とデータ分析では、Ethics（同意、匿名化、ライセンス）を 6 軸目として足す（`--axis` で選ぶ）。

## 5. スクリプト

| スクリプト | 場所 | 内容 | 移植元 |
|---|---|---|---|
| `researchkit.py`、`rklib.py` | `researchkit-status/scripts/` | `init`、`config get`、`bootstrap`、`status`、`handover`、`doctor`、`pitfall`、`budget`、`hooks install`、`sources next`、`sources list`、`estat list`・`estat get`（`estat.py`）、`data add` | gamekit.py、novelkit.py |
| `count_search.py` | 同上 | Web 検索の回数を数えるフック | novelkit |
| `worktree_helper.py` | `researchkit-worktree/scripts/` | worktree、ステップ判定、`status`、`next`、`human-tasks`、`sync-status`、`abort` | gamekit |
| `validate.py` | `researchkit-questions/scripts/` | RQ 一式の検証（番号、決定とのつながり、spec_order、仮説との対応） | gamekit-features |
| `check.py` | `researchkit-check/scripts/` | 主張ごとの出典 ID の有無、出典の必須項目（URL か書誌、参照日、等級）、使われていない出典、DOI の書式、`--online` で URL と DOI の到達性、データの目録と `data/raw/` の照合（目録にない・ない・SHA-256 の違い） | novelkit-check |
| `numbers.py` | `researchkit-check/scripts/` | `findings.md`・報告書の数値と、分析の出力（JSON）の突き合わせ | gamekit balance.py |
| `build_pptx.py` | `researchkit-publish/scripts/` | スライドの生成（python-pptx、`uv run`） | speckit-presentation |
| `strip_refs.py` | `researchkit-publish/scripts/` | 公開用の文書から `{N:...}`（と主張の参照）を取り除く | — |

## 6. セッションの区切りと予算

調査は 3 キットの中で最も検索が多いので、novelkit の仕組みをそのまま入れる。

- **必ず区切る**: 全体の工程（R12）の後。
- **回数を数えて区切る**: R2、R6、Q8、Q11 の前と、RQ に入る前に `budget --step <STEP>` を実行する。STOP なら工程の境目で止まる（自動モードでも止まる）。
- **数えられない環境**: 1 セッションで 1 RQ を進めたら止まる。
- 見積もりは `config.yaml` の `session.estimates` に書く。文献レビューの RQ は多めにする。

## 7. ディレクトリ構成

### scaffold

```text
.
├── README.md、DESIGN.md、LICENSE
├── docs/dev/CONTRACT.md                # スキルとスクリプトの間の取り決め（新規プロジェクトには持ち込まない）
├── CLAUDE.md / AGENTS.md / GEMINI.md / opencode.json
├── .kiro/steering/
│   ├── language.md
│   └── research.md                     # researchkit の工程とルール
├── .claude/skills/ .agents/skills/ .kiro/skills/   # → skills/researchkit/*
├── skills/researchkit/                 # 29 本
├── scripts/new_project.py、new-researchkit-project
└── tool/                               # new-researchkit-project（作成・取り込み・update）とテスト
```

### 調査プロジェクト

```text
.researchkit/config.yaml          # パス、コマンド（analysis, test）、予算、確度の段階
.researchkit/memory/constitution.md
docs/
├── concept/                      # core-question.md、seed.md、framing.md、premises.md、backlog.md
├── scan/                         # wide.md
├── study/                        # issue-tree.md、hypotheses.md、pilot/
├── method.md、quality.md
├── questions/                    # 000-research-foundation.md、001-*.md、999-research-report.md、spec_order.md
├── glossary.md                   # 用語集（正典）
├── auto-decisions.md、adopt-plan.md
├── reviews/                      # 工程の外のレビュー
└── handover/
sources/                          # 出典台帳（1 件 1 ファイル、フロントマター）
data/raw/、data/manifest.md       # 生データと目録（大きいファイルは Git に入れない）
studies/<NNN-name>/               # spec.md、plan.md、tasks.md、search-log.md、evidence/、analysis/、findings.md、reviews/
reports/                          # report.md、publish/（読み手ごとの形式）
```

## 8. 決めておきたい点

| 論点 | 推奨 | 理由 |
|---|---|---|
| 出典 ID の振り方 | `S<NNN>-<連番>`（RQ の番号を前に付ける） | worktree を並行で進めると、通しの連番は衝突する。共通の出典は `S000-*` にする |
| 生データの扱い | 小さいもの（既定 5MB 未満）は Git に入れ、大きいものは目録とハッシュだけを入れる | 再現性とリポジトリの重さの両立。しきい値は `config.yaml` で変える |
| 分析の言語 | スクリプトは Python と uv（pandas などを `uv run --with` で入れる）を既定にし、R も `commands.analysis` で使えるようにする | kit のスクリプトは標準ライブラリだけにし、分析のコードは依存を持ってよい |
| trailer | `Researchkit-Bootstrap`、`Researchkit-Step`、`Researchkit-Question` | speckit の trailer と混ざらないようにする。speckit のプロジェクトに取り込む予定はないので、共通にしない |
| 壁打ちの相手 | `~/.myai/sparring` に調査向けのエージェント（市場アナリスト、学術研究者、データサイエンティスト、UX リサーチャー）と `sparring-research` を足す | novelkit と gamekit が sparring を参照している形に合わせる |
| 000 と 999 | 000 は調査の共通基盤、999 は統合報告 | speckit の「共通基盤」と「最後に全体を支えるもの」という予約番号の意味を保つ |
| 品質基準（quality.md） | 出典の最低等級、確度の要求、再現性の水準、レビューの合格条件 | speckit の nfr.md に当たる。全 RQ が守る |

## 9. 作る順番

| 段階 | 内容 | 確かめ方 |
|---|---|---|
| P1 骨格 | steering、リンク、config のテンプレート、`researchkit.py`、`worktree_helper.py`（gamekit から移植） | `tool/tests` の単体テスト |
| P2 全体の工程 | R1〜R12 のスキル 12 本とテンプレート、`validate.py` | 小さな題材で bootstrap を通す |
| P3 RQ の工程 | Q2〜Q13 のスキル、手法の参照文書 4 本、`check.py`、`numbers.py` | 手法ごとに 1 つずつ、RQ を通す |
| P4 統合と公開 | synthesize、publish、`build_pptx.py` | 999 を通して報告書とスライドを作る |
| P5 配布 | `tool/`（作成・`--adopt`・`update`）、README、CI | 3 キットと同じテスト一式 |
| P6 実地の試し | 本物の調査 1 件を `--oneshot` で通し、PITFALLS に詰まった点を記録する | 振り返りを設計に戻す |
