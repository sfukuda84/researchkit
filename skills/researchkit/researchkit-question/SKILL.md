---
name: "researchkit-question"
description: "問い（RQ）の設計の工程を実行する統括スキル。Git worktree の準備（既存があれば再利用して続きから再開）、問いの仕様（researchkit-specify）、仕様の明確化 ×2（researchkit-clarify。2 回目は用語の操作的定義・母集団・期間・地域・比較の対象・単位・データの粒度など調査特有の曖昧さ）、調査計画（researchkit-plan。手法、検索式、標本、分析の計画、仮説ごとの反証条件）、タスク（researchkit-tasks。人の作業は [人]）、整合性の検証 ×2（researchkit-analyze）を行い、main へのマージと後片付けまでを実行する。RQ の工程の Q1〜Q7-2 と Q13（--phase design）。収集から先は researchkit-execute、通しは researchkit-all で行う。「この問いの調査を設計して」「RQ の計画を立てて」と言われたとき、または /researchkit-question と打たれたときに使う。"
argument-hint: "RQ の番号または範囲と、任意の --auto（例: 001, 002-005, all, all --auto, または省略して次の未着手）"
compatibility: "Requires git and Python 3.9+, researchkit project structure with .researchkit/config.yaml"
user-invocable: true
disable-model-invocation: false
---

# researchkit-question スキル（設計の工程: Q1 → Q2〜Q7-2 → Q13）

RQ ごとに、worktree の準備、問いの仕様、明確化 2 回、調査計画、タスク、整合性の検証 2 回を行い、仕様・計画・タスクを `main` にマージする。収集の前に「何に答えるか」と「何を見たら仮説を捨てるか」を固めることが、この工程の目的である（steering の基本原則 4）。

- 実行の工程（Q8〜Q12）は [`researchkit-execute`](../researchkit-execute/SKILL.md) が担当する。
- 設計から実行までを 1 つの worktree で通して行う場合は [`researchkit-all`](../researchkit-all/SKILL.md) を使う。`researchkit-all` は、このファイルの「§3 本体」だけを実行する。

**ステップ番号、ヘルパースクリプト（`$HELPER`）、再開、安全規則、対話、引数の解釈、自動モードは [`researchkit-worktree`](../researchkit-worktree/SKILL.md) に従う。** 作業を始める前に必ず読むこと。この文書では、その節を「`researchkit-worktree` の『ステップ番号』の節」のように見出しの名前で参照する。

パスは既定の配置で書いている。`.researchkit/config.yaml` の `paths` で読み替える。`$RK`、`$HELPER` の意味は steering の「エージェントの行動規範」のとおりである。

## 1. ユーザー入力・引数

```text
$ARGUMENTS
```

引数の解釈と複数の RQ の進め方は、`researchkit-worktree` の『引数の解釈と複数の RQ の進め方』の節に従う。自動検出では `--phase design` を使う。`--auto` があるときは、下の 💬 の質問も含めて、`researchkit-worktree` の『自動モード』の節で進める。

## 2. 実行の流れ（単独実行）

始める前に、調査全体の工程が終わっていることを確かめる。`$RK bootstrap` の `NEXT_STEP` が `DONE` でなければ、残っているステップを示し、先に `researchkit-bootstrap` を実行するよう案内する。既存の調査に取り込んだ（`--adopt`）などで工程の記録がないときは、`docs/questions/` と憲章があれば、ユーザーに確かめて進めてよい（自動モードでは、両方があれば進める）。

RQ に入る前（Q1 の前）に `$RK budget --step rq` を実行し、`VERDICT: STOP`（終了コード 4）なら、この RQ に入らずに止まる（steering の「セッションの区切り」、`researchkit-worktree` の『セッションの区切り』）。設計の工程だけでも、実行の工程に続けて入れるだけの残りがあることを確かめておく。Q5 で情報源やデータベースの所在を Web で確かめるときは、その前に `$RK budget --need <見積もり>` も実行し、STOP なら止まる。

対象の RQ ごとに、次を順に行う。

1. **Q1 準備**: `researchkit-worktree` の『Q1 準備』の節に従い、`$HELPER ensure <RQ> --phase design` を実行する。
   - `999-research-report` は、ほかのすべての RQ（`000` を含む）が `完了` か `人の作業待ち` になるまで始められない（`PRECONDITION: DEPENDENCY_PENDING`）。そのときは残っている RQ を示して止まる。
   - 設計がすでに `main` にマージ済みなら `ALREADY_DESIGNED` で止まる。`researchkit-execute` を案内する。
2. **本体**: 下の §3 の Q2〜Q7-2 のうち、`NEXT_STEP` 以降を順に実行する。
3. **Q13 片付け**: `researchkit-worktree` の『Q13 片付け』の節に従い、`$HELPER finish <RQ_NAME> --phase design` を実行する。`docs/questions/<RQ_NAME>.md` の状態は `設計済み` になる。
4. 次の RQ があれば 1 に戻る。

## 3. 本体（Q2〜Q7-2）

作業場所は `WORKTREE_DIR`、RQ のディレクトリは `studies/<RQ_NAME>`（以下 `RQ_DIR`）である。各ステップの最後に、`researchkit-worktree` の『ステップ番号』の節の subject で `checkpoint` を記録する。指摘や変更がなくても記録する。

| ステップ | 内容 | スキル | 成果物 |
|---|---|---|---|
| Q2 | 問いの仕様 | [`researchkit-specify`](../researchkit-specify/SKILL.md) | `RQ_DIR/spec.md` |
| Q3 | 明確化 1 回目（一般の曖昧さ） | [`researchkit-clarify`](../researchkit-clarify/SKILL.md) `--round 1` | `spec.md` の `## Clarifications` |
| Q4 | 明確化 2 回目（調査特有の曖昧さ） | `researchkit-clarify --round 2` | 同上 |
| Q5 | 調査計画 | [`researchkit-plan`](../researchkit-plan/SKILL.md) | `RQ_DIR/plan.md` |
| Q6 | タスク | [`researchkit-tasks`](../researchkit-tasks/SKILL.md) | `RQ_DIR/tasks.md` |
| Q7-1 | 整合性の検証 1 回目（検出と修正） | [`researchkit-analyze`](../researchkit-analyze/SKILL.md) `--round 1` | `RQ_DIR/reviews/analyze-1.md` |
| Q7-2 | 整合性の検証 2 回目（確認） | `researchkit-analyze --round 2` | `RQ_DIR/reviews/analyze-2.md` |

### 入力情報

各ステップで、存在するものを参照する。

- RQ の概要 `docs/questions/<RQ_NAME>.md`（問い、つながる決定と仮説、答えの形、範囲、想定する情報源、人の作業の見込み、`**手法**`、`**依存**`）
- 問いの種 `docs/concept/seed.md`（読み手、決めたいこと `D1`〜、期限）、前提 `docs/concept/premises.md`（`RP1`〜`RP12`）
- イシューツリー `docs/study/issue-tree.md`、仮説 `docs/study/hypotheses.md`（`H1`〜 と反証条件）、予備調査 `docs/study/pilot/`
- 地図 `docs/scan/wide.md`、手法 `docs/method.md`、手法の参照文書 `researchkit-method/references/`
- 憲章 `.researchkit/memory/constitution.md`、品質基準 `docs/quality.md`、用語集 `docs/glossary.md`
- 依存する RQ の `studies/<NNN-name>/findings.md`（`main` にマージ済みのもの）
- 引数やプロンプトで与えられた追加指示

RQ の概要がなく、追加指示もない場合は、何を問うかをユーザーに質問してから Q2 に進む。新しい問いは、先に `researchkit-questions` で RQ を足すよう勧める。

### Q2: 問いの仕様

`researchkit-specify` の手順で `RQ_DIR/spec.md` を作る。問い、つながる決定と仮説、答えの形、判定の基準、範囲と範囲外、用語を書き、決まっていないことは `[NEEDS CLARIFICATION: ...]` にする。手法や検索式（HOW）は書かない（Q5 に回す）。

> 💬 問いの範囲や、つながる決定の読み方に疑問がある場合は、ユーザーに質問して確かめる。

### Q3〜Q4: 仕様の明確化 2 回

`researchkit-clarify` の手順で、1 回目は一般の曖昧さ（問いの範囲、決定とのつながり、答えの形、判定の基準、範囲外）、2 回目は調査特有の曖昧さ（用語の操作的定義、母集団、期間、地域、比較の対象、単位、データの粒度）を、推奨案を添えて質問する（各回最大 5 問）。回答は `spec.md` の `## Clarifications` に記録し、本文に反映する。

### Q5: 調査計画

`researchkit-plan` の手順で `RQ_DIR/plan.md` を作る。手法（`docs/method.md` の範囲で選ぶ）、情報源と検索式、標本、分析の計画、仮説ごとの反証条件、検索数の見積もり、倫理を、**収集の前に**書く。

> 💬 手法の組み合わせ、標本の大きさ、有料の情報源を使うかなど、判断が必要な場合は推奨案を添えて質問する。`docs/method.md` から外れる手法が要るときは、`researchkit-method` の改訂を案内する（自動モードでは止まる）。

### Q6: タスク

`researchkit-tasks` の手順で `RQ_DIR/tasks.md` を作る。準備・収集・分析・まとめのフェーズに分け、AI が実行できない作業にだけ `[人]` を付け、すべてのタスクに完了の確かめ方を書く。

### Q7-1〜Q7-2: 整合性の検証 2 回

`researchkit-analyze` の手順で、`spec.md`・`plan.md`・`tasks.md` を、憲章・品質基準・仮説・RQ の概要と照合する。1 回目は検出と修正、2 回目は確認である。2 回目の終わりに、CRITICAL・HIGH・MEDIUM が 0 件、判定の基準と反証条件に対応するタスクのカバレッジが 100% であることを確かめる。

> 💬 修正の方針にトレードオフがある場合は、ユーザーに質問する。憲章・品質基準・`docs/method.md` の改訂が要る場合は、直さずに報告する（自動モードでは止まる）。

### 000 と 999 の扱い

予約番号の RQ は、同じステップを次のように読み替えて進める（steering の「RQ の工程」の注記）。各ステップのスキルに、読み替えの詳しい手順がある。

| RQ | 設計の工程での扱い |
|---|---|
| `000-research-foundation` | **主張を作らない基盤づくり**である。spec の「問い」は「この調査の共通基盤（出典台帳・用語集・データの目録・分析環境・検索ログの形式）は整っているか」とし、答えの形は基盤の完成条件の一覧にする。つながる決定と仮説は書かない（`—`）。plan に反証条件は書かず、各基盤の整え方と動作の確かめ方を書く。Q4 の調査特有の曖昧さは、用語集の範囲とデータの目録の粒度に絞る |
| `999-research-report` | **統合報告**である。spec の「問い」は「すべての RQ の答えを合わせると、決定 `D1`〜 に何が言えるか」とし、`docs/questions/999-research-report.md` の読み手・形式・構成を答えの形にする。plan には、統合の構成（結論を先に書くピラミッド構造）、取り込む RQ と主張、公開の形式を書く。tasks の収集・分析のフェーズは、Q8 の `researchkit-synthesize`、Q9 の `researchkit-publish`、Q10 の `researchkit-findings`（統合モード）の作業に置き換える |

## 4. 完了報告

各 RQ の完了時と、指定範囲の全体の完了時に、次を報告する。

- 完了した RQ の名前と番号、マージコミット
- 問いの要約（問い、つながる決定、答えの形、判定の基準）
- clarify 2 回で確定した重要な決定事項（用語の定義、母集団、期間、範囲外など）
- 計画の要約（手法、主な情報源とデータベース、標本、仮説ごとの反証条件、検索数の見積もり）
- タスクの件数（フェーズ別）と、`[人]` のタスクの件数と内容
- analyze 2 回の検証結果（直した所見、残した LOW）
- 飛ばした、または中断した RQ とその理由
- `--auto` のとき: 自動で採用した判断の要約（`RQ_DIR/auto-decisions.md`。見直しを勧める判断を先に）と、止まった RQ についてユーザーに判断してほしい事項
- 次の案内: 収集から先は `researchkit-execute <RQ_NAME>`。`[人]` のタスクのうち収集の前に要るもの（有料資料の入手、同意書の準備、アクセス権の申請など）は、早めに着手するよう勧める。設計が未着手の RQ は `$HELPER next --phase design` の結果
