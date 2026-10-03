---
inclusion: always
---

# 調査・分析のルール（researchkit）

このプロジェクトは researchkit で調査・分析を進める。researchkit は、問い（リサーチクエスチョン、RQ）ごとに、仕様（何に答えるか）→ 計画（どう調べるか）→ 収集 → 分析 → 主張のまとめ → レビューを、Git worktree で進める。結論は根拠から導き、根拠は出典から導く。

## 基本原則

1. **出典のない事実を書かない**: 事実・数値・引用には出典 ID（`S<NNN>-<NNNN>`）を付ける。出典には、URL か書誌情報と、参照日と、等級を付ける（`sources/`）。
2. **AI が挙げた文献・作品・統計は、1 件ずつ実在を確かめる**: 論文は DOI か出版社・データベースのページで、統計は発表元のページで確かめる。確かめられなかったものは等級 `D`（未確認）にし、根拠に使わない。存在しない文献や、著者・年・数値の取り違えが起きやすい。
3. **問いは意思決定から導く**: 誰が何を決めるための調査かを `docs/concept/seed.md` で決め、すべての RQ をそこにつなぐ。答えても決定が変わらない RQ は作らない。
4. **仮説と反証条件を先に書く**: 分析の計画（何を見たら仮説を捨てるか）は、収集の前に `studies/<NNN-name>/plan.md` に書く。収集の後に計画を変えたときは、変えたことと理由を `plan.md` の「計画の変更」に記録する。
5. **主張には確度を付ける**: 確度は憲章で定めた段階（既定: `確実`／`可能性が高い`／`示唆`／`不明`）で表し、根拠の数と等級から付ける。確度の言葉を本文でぼかさない（「〜と思われる」で済ませない）。
6. **見つからなかったことも記録する**: 検索式、データベース、期間、件数を検索ログ（`studies/<NNN-name>/search-log.md`）に残す。見つからないことは、それ自体が結果である。ただし、存在しないことの証明ではない。
7. **反対の証拠を探す**: 各 RQ で、仮説に反する証拠と代わりの説明を探す工程（`researchkit-review` の Counter 軸）を省かない。
8. **数値は再計算できる形で持つ**: 分析は `studies/<NNN-name>/analysis/` のスクリプトから再実行できるようにする。報告の数値には出力ファイルへの参照（§「数値の参照」）を付け、`numbers.py` で突き合わせる。手で計算した数値は、計算式と入力を表に残す。
9. **個人と権利を守る**: インタビューとアンケートの同意、個人情報の匿名化、引用の範囲、有料データベースと統計の利用規約を守る。判断に迷うものは `[人]` のタスクにする。法的な判断はしない。
10. **成果物と結論を同期させる**: 分析で前提や仮説が崩れたら、`findings.md` だけを直さず、`docs/study/hypotheses.md`、`issue-tree.md`、`docs/questions/` にも戻して直す（逆流）。
11. **曖昧さは推測で埋めない**: 決まっていないことは `[NEEDS CLARIFICATION: ...]` として明示し、質問で解消する。自動モード（`--auto`、`--oneshot`）では、推奨案を明示して採用し、`auto-decisions.md` に記録することで確認に代える。
12. **憲章が最上位**: `.researchkit/memory/constitution.md`（憲章）と `docs/quality.md`（品質基準）をすべての判断の基準とする。

## 工程

### 調査全体の工程（`researchkit-bootstrap` が R1〜R12 を通しで行う）

| ステップ | スキル | 成果物 |
|---|---|---|
| R0 | （bootstrap） | Git リポジトリ、`.researchkit/config.yaml`、`docs/concept/core-question.md` |
| R1 | `researchkit-seed` | `docs/concept/seed.md`（問いの種、読み手、決めたいこと、期限、答えの使い道） |
| R2 | `researchkit-scan` | `docs/scan/wide.md`（既存の調査・先行研究・用語・データの所在の地図） |
| R3 | `researchkit-framing` | `docs/concept/framing.md`（問いの立て方の 3 案と選択） |
| R4 | `researchkit-sparring` | `docs/concept/premises.md`（RP1〜RP12）、`docs/concept/backlog.md` |
| R5 | `researchkit-hypothesis` | `docs/study/issue-tree.md`（イシューツリー）、`docs/study/hypotheses.md`（仮説 H1〜 と反証条件） |
| R6 | `researchkit-pilot` | `docs/study/pilot/`（予備調査の計画と結果。問いが答えられるか、データが手に入るか） |
| R7 | `researchkit-method` | `docs/method.md`（手法の 3 案の比較と選択、データ源、分析環境）、`.researchkit/config.yaml` の `commands` |
| R8 | `researchkit-constitution` | `.researchkit/memory/constitution.md`（出典の等級、確度の段階、引用、数値、倫理、AI 利用の開示） |
| R9 | `researchkit-questions` | `docs/questions/`（`001-*.md` 以降、`README.md`、`spec_order.md`） |
| R10 | `researchkit-foundation` | `docs/questions/000-research-foundation.md`（出典台帳・用語集・データの目録・分析環境・検索ログの形式） |
| R11 | `researchkit-deliverable` | `docs/quality.md`（品質基準）、`docs/questions/999-research-report.md`（最終成果物の読み手・形式・構成） |
| R12 | （bootstrap） | 全体の検証（`validate.py` と `check.py` のエラーが 0 件） |

進捗はコミットの trailer `Researchkit-Bootstrap: R<n>` で記録する。R12 の後は、セッションを区切る（§「セッションの区切り」）。

### RQ の工程（`researchkit-question`・`researchkit-execute`・`researchkit-all`）

| ステップ | スキル | 成果物 |
|---|---|---|
| Q1 | `researchkit-worktree` | `.worktrees/<NNN-name>`（ブランチ `rq/<NNN-name>`） |
| Q2 | `researchkit-specify` | `studies/<NNN-name>/spec.md`（問い、つながる決定、答えの形、判定の基準、範囲外） |
| Q3〜Q4 | `researchkit-clarify` ×2 | `spec.md`（2 回目は調査特有の曖昧さ: 用語の定義、母集団、期間、地域、比較の対象、単位） |
| Q5 | `researchkit-plan` | `plan.md`（手法、検索式とデータベース、データ源、標本、分析の計画、反証条件、検索数の見積もり） |
| Q6 | `researchkit-tasks` | `tasks.md`（`[人]` を含む） |
| Q7-1〜Q7-2 | `researchkit-analyze` ×2 | spec・plan・tasks・憲章・仮説・品質基準の整合（1 回目は検出と修正、2 回目は確認） |
| Q8 | `researchkit-collect` | `sources/`（出典台帳）、`studies/<NNN-name>/evidence/`（抜き書き）、`data/`、`search-log.md` |
| Q9 | `researchkit-analysis` | `studies/<NNN-name>/analysis/`（スクリプト、`out/` の出力、抽出表、コーディング表） |
| Q10 | `researchkit-findings` | `findings.md`（主張 → 根拠 → 確度 → 反証）、逆流（`hypotheses.md` などの更新）、`tasks.md` の残作業 |
| Q11〜Q12 | `researchkit-review` ×2 | `studies/<NNN-name>/reviews/review-<n>.md`（5 軸。2 回目は 1 回目の修正の確認と別のレンズ）。Counter 軸で見つかった反対の証拠は、`researchkit-collect` の手順で出典に登録してから主張に反映する |
| Q13 | `researchkit-worktree` | `main` への `--no-ff` マージ、`docs/questions/` の状態の更新、引き継ぎ書 |

- `researchkit-question` は Q1〜Q7-2 と Q13（設計の工程。`--phase design`）、`researchkit-execute` は Q1、Q8〜Q13（実行の工程。`--phase execute`）、`researchkit-all` は Q1〜Q13（`--phase all`）を行う。
- 進捗はコミットの trailer `Researchkit-Step: <ステップ>` と `Researchkit-Question: <NNN-name>` で記録する。
- RQ の番号のうち、`000` は共通基盤（`000-research-foundation`）、`999` は統合報告（`999-research-report`）の予約番号である。調査の中身の RQ は `001` から振る。
- `000-research-foundation` では、Q8 で出典台帳・用語集・データの目録・分析環境を整え、Q9 で分析環境が動くことを確かめ、Q10 で残作業をまとめる。主張は作らない。
- `999-research-report` は、ほかのすべての RQ が `完了` か `人の作業待ち` になってから始める。Q8 は `researchkit-synthesize`（統合報告 `reports/report.md`）、Q9 は `researchkit-publish`（読み手に合わせた形式。不要なら、その旨を記録して空のチェックポイントにする）、Q10 は `researchkit-findings` の統合モード（報告の結論と各 RQ の `findings.md` の整合、逆流）である。

### 手法

RQ の Q8・Q9 の中身は、`plan.md` で選んだ手法の参照文書（`researchkit-method/references/`）に従う。1 つの RQ で手法を組み合わせてよい。

| 手法 | 参照文書 | 主な `[人]` |
|---|---|---|
| デスクリサーチ（市場・競合・技術） | `desk.md` | 有料レポートの購入 |
| 文献レビュー | `literature.md` | 有料論文の入手、専門家の確認 |
| データ分析 | `data.md` | 社内データの取得、アクセス権の申請 |
| 定性調査（インタビュー・アンケート） | `qualitative.md` | 実施、同意の取得、倫理審査 |

### 共通

- `researchkit-status`: 進捗（調査全体の工程と RQ の工程）、引き継ぎ書（`docs/handover/`）、環境の診断、Web 検索の予算。
- `researchkit-review`: 5 軸のレビュー。RQ の工程の外で、任意の報告書や資料のレビューにも使う。
- `researchkit-check`: 機械検証（出典の参照、出典の必須項目、数値の突き合わせ）。

## 識別子

ID は振り直さない。取り下げたものも消さずに印を付ける。全量は scaffold の `docs/dev/CONTRACT.md` §5 にある。

| 記号 | 意味 | 定義する文書 |
|---|---|---|
| `D1`〜 | 決めたいこと（意思決定） | `docs/concept/seed.md` |
| `RP1`〜`RP12` | 前提 | `docs/concept/premises.md` |
| `I1`、`I1.2` | イシューツリーの節 | `docs/study/issue-tree.md` |
| `H1`〜 | 仮説（反証条件つき） | `docs/study/hypotheses.md` |
| `BL-001`〜 | 問いの候補 | `docs/concept/backlog.md` |
| `K-1-1`〜 | 憲章の条項 | `.researchkit/memory/constitution.md` |
| `QS-SR-001`〜 | 品質基準の項目 | `docs/quality.md` |
| `SQ1`〜、`AC1`〜 | RQ の小問、判定の基準 | `studies/<NNN-name>/spec.md` |
| `T001`〜 | タスク | `studies/<NNN-name>/tasks.md` |
| `S001-0001`〜 | 出典 | `sources/` |
| `C1`〜、`003-C2` | 主張、ほかの RQ の主張の参照 | `studies/<NNN-name>/findings.md` |
| `AZ1-B1`、`R1-S01` | 整合性の検証の所見、5 軸レビューの所見 | `studies/<NNN-name>/reviews/` |

## 出典台帳（`sources/`）

- 1 件 1 ファイル（`sources/<ID>.md`）。ID は `S<NNN>-<NNNN>` で、前半は最初にその出典を使った RQ の番号（共通の出典は `S000-`）、後半は RQ の中の連番である。worktree を並行で進めても衝突しない。
- フロントマターの項目: `id`、`type`（`web`／`paper`／`book`／`stat`／`report`／`dataset`／`interview`／`internal`）、`title`、`author`、`publisher`、`published`（発行日）、`url`、`doi`、`accessed`（参照日 `YYYY-MM-DD`）、`grade`（`A`／`B`／`C`／`D`）、`primary`（一次資料か `true`／`false`）、`verified_by`（実在を確かめた方法）、`used_in`（使った RQ の一覧）。
- 等級の既定（憲章で変えられる）: `A` 一次資料・査読つき論文・公的統計・企業の公式の開示、`B` 信頼できる二次資料（大手の報道、業界団体、調査会社の公開の要約）、`C` そのほかの二次資料（ブログ、まとめ、検索の要約）、`D` 未確認（実在を確かめられない、AI が挙げただけ）。`D` は根拠に使わない。
- 既存の出典を別の RQ で使うときは、新しく作らずに `used_in` に足す。
- インタビューの出典（`type: interview`）は、個人を特定できる情報を書かない。対象者は `P01` のような記号で表す。

## 主張の書式（`findings.md`）

主張は表で書く。`check.py` と `numbers.py` がこの書式を読む。

```markdown
| ID | 主張 | 根拠 | 確度 | 反証・限界 |
|---|---|---|---|---|
| C1 | 国内の〇〇市場は 2025 年に 1,234 億円{N:analysis/out/market.json#size_2025}である | S001-0003, S001-0007 | 可能性が高い | 推計の方法が異なる S001-0011 では 980 億円 |
```

- 主張の ID は RQ の中で `C1` から振る。統合報告では `<NNN>-C<n>`（例: `003-C2`）で各 RQ の主張を参照する。
- 根拠の欄には出典 ID か、ほかの主張の ID を書く。根拠のない主張は書かない（確度 `不明` の問いとして「残った問い」に書く）。

## 数値の参照

分析の出力から得た数値は、直後に `{N:<path>#<key>}` を付ける。`<path>` は JSON のファイルを指す。`studies/` の下の文書（各 RQ の `findings.md`、`999-research-report` の `findings.md` を含む）では、その RQ のディレクトリからの相対パス（999 からほかの RQ の出力を指すときは `../001-market-size/analysis/out/market.json`）で書く。`reports/` の下の文書では、リポジトリのルートからの相対パス（`studies/001-market-size/analysis/out/market.json`）で書く。`<key>` はドット区切りのキーである。`numbers.py` が、直前の数値と JSON の値を突き合わせる（許容差は `config.yaml` の `numbers.tolerance`）。手で計算した数値は `{N:calc}` を付け、計算式と入力を同じ文書の「計算」の節に表で書く。公開用の文書（`researchkit-publish`）では、参照の記号を取り除く。

結果を見た後に足した分析（探索的な分析。レビューの指摘に答えて足したものを含む）の出力は、JSON の `exploratory` の下に置き（`{N:analysis/out/x.json#exploratory.<key>}`）、別の主張にして確度を「示唆」までにする。事前に決めた主張の確度と仮説の判定には使わない。主張の欄でこのキーを使う主張の確度が高いと、`check.py` が `EXPLORATORY_CONFIDENCE` で止める。

## レビューの 5 軸（`researchkit-review`）

| 軸 | 見ること |
|---|---|
| Source | 出典が実在し、たどれるか。一次資料か。日付は新しいか。等級は品質基準を満たすか。孫引きをしていないか。引用が原文と一致するか |
| Logic | 主張と根拠の間に飛躍がないか。相関と因果の混同、過度の一般化がないか。`spec.md` の「答えの形」に答えているか |
| Counter | 反対の証拠と代わりの説明を探したか（Web で追加の検索をする）。反証条件に当たる結果を無視していないか |
| Bias | 確証バイアス、選択バイアス、生存者バイアス、標本の偏り、スポンサーの利害、検索語の偏りがないか |
| Numbers | 数値を出力ファイルと突き合わせて検算する。単位、母数、期間、為替や物価の扱い。分析のスクリプトを再実行して同じ結果になるか |

定性調査とデータ分析を含む RQ では、Ethics（同意、匿名化、ライセンス、利用規約）を 6 軸目として足す。レビューの記録は `studies/<NNN-name>/reviews/` に置く。工程の外のレビューは `docs/reviews/<YYYYMMDD>-<対象>.md` に置く。

## 人が行うタスク（`[人]`）

`tasks.md` のタスクは AI が実行するものを基本とし、AI が実行できない、または実行すべきでないタスクにだけ `[人]` を付ける。

- 書式: `- [ ] T001 [P] [SQ1] [人] 〇〇社の決算説明会の資料を入手し、data/raw/ に置く（完了の確かめ方: data/manifest.md に記載があり、ハッシュが一致する）`。`[P]`（並行可）、`[SQn]`（対象の小問）の後、本文の前に印を置く。
- `[人]` の対象: インタビューとアンケートの実施、同意の取得、倫理審査、有料の論文・レポート・データベースの入手、社内データの取得とアクセス権の申請、専門家への確認、報告の公開の判断、秘密情報の入力。
- 人と AI が混ざる作業は、2 つのタスクに分ける。人が入手したものを AI が確かめる場合は、確かめる側を AI のタスクにする。
- `[人]` のタスクには、末尾に「（完了の確かめ方: …）」を書く。
- AI は `[人]` のタスクを実行せず、自動モードでも `- [x]` にしない。ユーザーが完了を伝え、確かめられる部分を AI が確かめてから `- [x]` にする。
- `researchkit-analyze`・`researchkit-findings`・`researchkit-review` は、未完了の `[人]` のタスクを漏れや不整合として扱わない。
- `[人]` のタスクだけが残った RQ は、Q13 で `main` にマージしてよい。状態は `人の作業待ち` になる。残りは `main` で片付け、`researchkit-worktree` の `sync-status` で状態を `完了` にする。
- AI は、秘密情報の値を読んだり出力したりしない。

## モード

| | 通常モード（既定） | 自動モード（`--auto`） |
|---|---|---|
| 質問 | 推奨案を添えて質問し、合意を得てから進める | 質問せず推奨案を採用し、`auto-decisions.md` に記録する |
| 止まる場面 | — | マージの競合、中止、憲章・品質基準・`docs/method.md` の変更が要るとき、`[人]` のタスクが終わらないと先に進めないとき、同じ原因の失敗が 3 回続いたとき、Web 検索の予算が足りないとき |

`researchkit-bootstrap` には、最初に一度だけ質問して以降を自動で進める `--oneshot` と、既存の調査の資料から足りない成果物だけを作る `--adopt` もある。自動で決めたことは、調査全体の工程の分は `docs/auto-decisions.md`、RQ の工程の分は `studies/<NNN-name>/auto-decisions.md` に書く。

## セッションの区切り

Web 検索には 1 セッションあたりの回数の上限がある（Claude Code で観測した値は 200 件）。調査は検索が多いので、セッションを工程の境目で区切る。

- **必ず区切る**: 調査全体の工程（R12）の後。新しいセッションで `researchkit-all` を始める。
- **設定で区切る**: `session.split_after`（既定は空。例: `[Q10]`）に入っているステップのチェックポイントの後。`checkpoint` が `SPLIT_SESSION` を出したら、引き継ぎ書を更新して止まり、新しいセッションで同じスキルを同じ引数で実行して再開する。親の文脈は工程の後半ほど重くなる（003 の実測で Q8 の 1 回あたり約 19 万トークンが Q12 では約 51 万）ので、Q10 の後で区切ると Q11・Q12 を軽い文脈で進められる。
- **回数を数えて区切る**: プロジェクトを作るときに `.claude/settings.json` にフックが入り、セッションごとの Web 検索の回数を `.researchkit/usage/` に記録する。次の場所で `$RK budget --step <STEP>` を実行する: R2・R6 の前、RQ に入る前（`--step rq --rq <RQ>`）、Q8・Q11 の前（`--rq <RQ>` を付ける。Q11 は Q12 の分も含めて見る）。見積もりは、RQ の `plan.md` の「検索数の見積もり」、なければ手法ごとの既定（`session.estimates_by_method`）、なければ `session.estimates` を使う。`VERDICT: STOP`（終了コード 4）なら、その工程に入らずに止まる。自動モードでも止まる。これは失敗ではなく区切りであり、新しいセッションで同じスキルを同じ引数で実行すれば続きから再開する。
- **数えられない環境**（`VERDICT: UNMETERED`）では、1 セッションで `session.rqs_unmetered`（既定 1）件の RQ を終えたら止まる。記録が別のセッションのもの（プロジェクトの外で Claude Code を起動したなど）のときも `UNMETERED` になる。Claude Code はプロジェクトのルートで起動する。
- 見積もりは `.researchkit/config.yaml` の `session.estimates` で変える。

## サブエージェントに任せるとき

調査（R2、Q8）やレビューの軸（Q11、Q12）のように、工程の一部をサブエージェントに任せる場合は、次のように分担する。

| 担当 | すること |
|---|---|
| サブエージェント | そのスキルの SKILL.md とテンプレートを読み、手順どおりに成果物を書く。**指定されたファイル以外は編集しない。** 最終回答で、要点と、自動モードで記録すべき判断と、手順どおりに進めにくかった点を返す |
| 親（呼び出した側） | 出典 ID の採番の調整、`auto-decisions.md` への記録、成果物の確認、チェックポイントのコミット |

- **モデル**: サブエージェントには `.researchkit/config.yaml` の `subagents.model`（既定 `sonnet`）を指定する（Claude Code の Agent の `model`）。呼び出しのたびに会話の全体を読み直すので、下請けを最上位のモデルで動かすと利用量が大きく膨らむ。判断の要る作業（主張と確度の確定、仮説の判定、指摘の裏取りと修正、統合）は親が行う。モデルを選べないエージェントでは、この項目は読み飛ばす。
- **同時に動かす数**: 同時に動かすサブエージェントは `subagents.max_parallel`（既定 3）までにする。系統や軸がそれより多いときは、組に分けて、前の組が終わってから次の組を出す。少ない系統で足りるなら、上限まで増やさない。
- 並行で出典を集めるときは、サブエージェントごとに出典 ID の範囲を分ける（例: `S003-0001`〜`0099` と `S003-0100`〜`0199`）。
- サブエージェントの報告の中の事実（件数、文献名、数値）は、成果物のファイルと出典で確かめてから使う。

## エージェントの行動規範

- ユーザーが新しい問いを調べるよう頼み、対応する `studies/` の RQ がないときは、規模に応じて案内する。決定に関わる問いは `researchkit-questions` で RQ を足してから `researchkit-all` で進める。事実の確認程度の小さな問いは、その場で調べて出典を付けて答えてよい。
- 各スキルは前の工程の成果物を前提にする。前提の成果物がなければ、欠けている工程を案内する。
- 1 つの工程が終わったら結果を要約し、次に実行すべきスキルを示す。
- **コマンドの出力を短くする**: 統計の取得、ファイルのダウンロード、集計・分析のスクリプトの出力は、会話に溜まって以降のすべての呼び出しを重くする。結果はファイル（`data/raw/`、`analysis/out/`、`/tmp` の作業用ファイルなど）に書き、会話には件数・パス・要約・確かめに要る数行だけを返す。目安は 1 回あたり `output.max_lines`（既定 40）行まで。表やファイルの中身を確かめるときは、`head`、`wc -l`、列名の一覧、必要な行の抜き出しで見る。`curl` は `-sS -o <ファイル>` で保存し、本文を画面に出さない。サブエージェントにも同じ規則を渡し、最終回答は要点だけにさせる。
- スクリプトは Python（3.9 以上、標準ライブラリのみ）で書かれており、`python3 <スクリプト>` の形で呼ぶ。`python3` がない環境では `python` または `py -3` に読み替える。分析のコードは、`.researchkit/config.yaml` の `commands.analysis` を正とし、依存を持ってよい（既定は `uv run --with pandas python {script}` など。`researchkit-method` が決める）。
- 以降、`$RK` は `skills/researchkit/rk`、`$HELPER` は `skills/researchkit/rk helper`、`$CHECK` は `skills/researchkit/rk check`、`$NUM` は `skills/researchkit/rk num` を表す（パスはプロジェクトのルートからの相対。worktree の中でも同じ形で、その worktree のスクリプトを使う）。`rk` は researchkit-status・researchkit-worktree・researchkit-check の各スクリプトに渡す入口で、1 語なのでシェルの変数に入れても zsh で動く（`RK="python3 …/researchkit.py"` のように空白を含む値を変数に入れて `$RK budget` と展開すると、zsh では語に分かれずに失敗する。`rk` を使えばこの罠を踏まない）。Windows では `py -3 skills/researchkit/rk …` と書く。各スクリプトを直接 `python3 skills/researchkit/<スキル>/scripts/<名前>.py` で呼んでもよい（変数に入れない）。
- **RQ の要点を短く読む**: 実行の工程（Q8〜Q12）で RQ の spec・plan・tasks を読むときは、全文を読まずに、まず `$RK brief <RQ>` で要点（問い、小問、つながる決定と仮説、判定の基準、仮説と反証条件、確度の付け方、検索数の見積もり、計画の変更、未完了のタスク、成果物）を見る。全文が要る場面（確度を付ける、計画を直す）は、該当の節だけを読む。読んだ文書は以降のすべての呼び出しで読み直されるので、最初に読む量がそのまま利用量に効く。
- **公的統計の取得**: e-Stat の表は、一覧の HTML を自分で読まずに `$RK estat list <政府統計コード|一覧の URL> [--grep <語>]` で分類と表（statInfId・題名・公開日・形式）を見て、`$RK estat get <statInfId> --kind <0|1|2> --out data/raw/<名前>` で取得する（中身の形式に合う拡張子で保存し、SHA-256 を出す）。取得したら、その場で `$RK data add <file> --source <出典 ID> --url <URL> --desc <内容> --rq <NNN>` で目録に載せる。目録に載っていないファイルは `$CHECK` が `UNLISTED_DATA` で止める。

## コマンドの呼び出し方

| エージェント | スキルの場所 | 呼び出し例 |
|---|---|---|
| Claude Code | `.claude/skills/` | `/researchkit-all 001` |
| Codex CLI | `.agents/skills/` | `$researchkit-all 001` |
| Antigravity (agy) | `.agents/skills/` | `/researchkit-all 001` |
| Kiro CLI | `.kiro/skills/` | スキル `researchkit-all` を指定して依頼する |
| opencode | `.claude/skills/` と `.agents/skills/` | 「`researchkit-all` スキルで…」と依頼する |

各エージェントのスキルディレクトリにあるのは、`skills/researchkit/` への相対シンボリックリンクである。編集は `skills/researchkit/` 側で行う。スキルの本文にある `AskUserQuestion`（選択肢付きの質問）、`WebSearch` / `WebFetch`（Web 検索とページの取得）、Agent（サブエージェント）は Claude Code のツール名である。ほかのエージェントでは同じ働きのツールを使う。質問のツールがなければ、選択肢と推奨案を文章で示して回答を待つ。Web を調べられない環境では、推測で埋めずに、調査が必要な項目と理由を伝える。

## Claude Code のクラウドセッション

環境変数 `CLAUDE_CODE_REMOTE` が `true` のときだけ当てはまる。

- **マージ先**: `RESEARCHKIT_MAIN_BRANCH` がなければ、セッションの作業ブランチをマージ先にする。スキルの本文の `main` は、その作業ブランチに読み替える。`worktree_helper.py` がこれを自動で判定し、`finish` の後に作業ブランチを push する。`main` へは PR で取り込む。
- **push**: 作業ブランチにコミットしたら、そのたびに push する。
- **中断と再開**: `rq/*` のブランチは push できないので、1 つの RQ は 1 つのセッションで `finish` まで進める。
- **質問**: `--auto` か `--oneshot` で進めることを勧める。
- **Web 調査**: WebFetch が失敗したら、WebSearch の結果で進める。ページを開けなかった出典は、その旨を `verified_by` に書き、等級を 1 段下げる。数値を推測で埋めない。

## ディレクトリ構成

```text
.researchkit/
├── config.yaml              # パス、コマンド、Web 検索の予算、確度の段階、数値の許容差
├── memory/constitution.md   # 憲章（最上位の規範）
└── usage/                   # Web 検索の回数の記録（コミットしない）
docs/
├── auto-decisions.md        # 自動モードで決めたこと（調査全体の工程）
├── adopt-plan.md            # 既存の調査への取り込みの計画（researchkit-bootstrap --adopt）
├── concept/                 # core-question.md（入力）、seed.md、framing.md、premises.md、backlog.md
├── scan/                    # wide.md
├── study/                   # issue-tree.md、hypotheses.md、pilot/
├── method.md                # 手法と分析環境
├── quality.md               # 品質基準
├── questions/               # 000-research-foundation.md、001-*.md、999-research-report.md、README.md、spec_order.md
├── glossary.md              # 用語集
├── reviews/                 # 工程の外のレビュー
└── handover/                # CURRENT_STATE.md、PITFALLS.md、sessions/
sources/                     # 出典台帳（1 件 1 ファイル）
data/
├── manifest.md              # データの目録（出所、取得日、ライセンス、ハッシュ）
├── raw/                     # 小さな生データ（加工しない）
└── large/                   # 大きな生データ（コミットしない。目録だけを残す）
studies/<NNN-name>/          # spec.md、plan.md、tasks.md、search-log.md、evidence/、analysis/、findings.md、reviews/、auto-decisions.md
reports/                     # report.md（統合報告）、publish/（読み手ごとの形式）
```

パスは `.researchkit/config.yaml` の `paths` で既存の配置に合わせられる。スキルは、上の既定のパスを `paths` に読み替えて使う。
