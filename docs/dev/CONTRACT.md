# 実装の取り決め（スキルとスクリプトの間の契約）

scaffold の開発用の文書である（新規プロジェクトには持ち込まない）。スキルを書く人とスクリプトを書く人が、この取り決めに合わせる。規則の正本は `.kiro/steering/research.md`、設計は `DESIGN.md`。

## 1. 共通

- 書き方は 3 キット（`../speckit`、`../novelkit`、`../gamekit`）に合わせる。日本語、常体、短い文。SKILL.md のフロントマターは gamekit と同じ項目（`name`、`description`、`argument-hint`、`compatibility`、`user-invocable: true`、`disable-model-invocation: false`）。`description` には、何をするか、どの工程か、発動の言い回し（「〜と言われたとき、または /researchkit-xxx と打たれたときに使う」）を書く。
- パスは既定の配置で書き、冒頭で「パスは `.researchkit/config.yaml` の `paths` で読み替える」と断る。
- `$RK`、`$HELPER`、`$CHECK`、`$NUM` の意味は steering の「エージェントの行動規範」の最後の項目のとおり。
- スキルの置き場は `skills/researchkit/<スキル名>/`（`SKILL.md`、`templates/`、`scripts/`、`references/`）。
- スクリプトは Python 3.9 以上、標準ライブラリのみ。YAML は gamekit の `gklib.py` と同じく、必要な範囲を自前で読む。Windows でも動く（パスは `pathlib`、改行は `\n` で書く、`encoding="utf-8"` を明示）。

## 2. `researchkit.py`（`researchkit-status/scripts/`）

`python3 researchkit.py [--root <dir>] <command>`。`--root` を省くと `.researchkit/config.yaml`（なければ `.git`）を上へ探す。

| コマンド | 出力・動作 |
|---|---|
| `init [--config-only] [--title T]` | `.researchkit/config.yaml` がなければテンプレートから作り、`paths` のディレクトリのうち無いものを作る（`.gitkeep` を置く）。既存は変えない |
| `config get <key.path>` | 値を 1 行で出す。なければ空行と終了コード 1。リストは `,` 区切り |
| `bootstrap` | `COMPLETED_STEPS: R1 R2 ...` と `NEXT_STEP: R<n>`（すべて済めば `DONE`）。trailer `Researchkit-Bootstrap: R<n>` から判定 |
| `status` | 調査全体の工程、RQ の一覧（`worktree_helper.py status` の出力を取り込む）、引き継ぎ書の最終更新、出典の件数（等級別） |
| `handover [--note <text>]` | 引き継ぎ書を更新する（gamekit と同じ。`CURRENT_STATE.md` の自動の節、`sessions/`）。コミットしない |
| `doctor` | 設定、リンク、steering、`commands.analysis` の有無、フックの有無を診断。`OK`/`WARN`/`ERROR` と `SUMMARY`。ERROR で終了コード 1 |
| `pitfall <text>` | `PITFALLS.md` の先頭に日付つきで足す |
| `budget [--step <STEP> \| --need <N>]` | novelkit と同じ。`USED`、`LIMIT`、`NEED`、`REMAINING`、`VERDICT: OK\|STOP\|UNMETERED`。STOP は終了コード 4。`STEP` は `session.estimates` のキー（`R2`、`R6`、`Q8`、`Q11`、`rq`） |
| `hooks install` | `.claude/settings.json` に、Web 検索の回数を数えるフック（`count_search.py`）を登録する。既存の設定は保つ |
| `sources next <NNN> [--count <k>]` | RQ `<NNN>` の次の空き出典 ID を `k` 個出す（既定 1）。`sources/` の作業ツリーと `main` の両方を見て、使われている最大の連番の次から出す |
| `sources list [--grade A,B] [--rq <NNN>] [--unused]` | 出典の一覧（ID、等級、種類、題名、使った RQ） |

終了コード: 0 成功、1 エラー、3 前提条件を満たさない、4 budget の STOP。

## 3. `worktree_helper.py`（`researchkit-worktree/scripts/`）

gamekit の `worktree_helper.py` を移植する。違いだけを書く。

- 単位は RQ。ディレクトリは `docs/questions/`（RQ の概要）と `studies/<NNN-name>/`（成果物）。ブランチは `rq/<NNN-name>`、worktree は `.worktrees/<NNN-name>`。
- マージ先: 環境変数 `RESEARCHKIT_MAIN_BRANCH`、なければ `main`（クラウドセッションの扱いは gamekit と同じ）。
- trailer: `Researchkit-Step: <step>`、`Researchkit-Question: <NNN-name>`。
- フェーズ: `--phase design|execute|all`。
  - design: Q2 Q3 Q4 Q5 Q6 Q7-1 Q7-2
  - execute: Q8 Q9 Q10 Q11 Q12
  - all: 両方
- 完了の判定: design の完了は Q7-2 のチェックポイントがあること（`main` にマージ済みなら `studies/<NNN>/tasks.md` があること）。execute の完了は Q12 のチェックポイント、または `main` の `studies/<NNN>/findings.md` があり、`tasks.md` の `[人]` 以外がすべて `- [x]` であること。
- 状態欄: `docs/questions/<NNN-name>.md` の `**状態**: <値> |`。値は `未着手`／`設計済み`／`完了`／`人の作業待ち`。`finish` が、design の後は `設計済み`、execute・all の後は `完了` か `人の作業待ち` にする。`docs/questions/README.md` の一覧の状態列も合わせる（gamekit と同じ）。
- `999-research-report` の前提: `ensure 999-...` は、ほかのすべての RQ（`000` を含む）の状態が `完了` か `人の作業待ち` でなければ、`PRECONDITION: DEPENDENCY_PENDING` で終了コード 3。`next` は、ほかが終わるまで 999 を候補にしない。
- 前提条件のコード: `ALREADY_DESIGNED`、`ALREADY_EXECUTED`、`EXECUTE_IN_PROGRESS`、`DESIGN_INCOMPLETE`、`DESIGN_MISSING`、`LEFTOVER_CHANGES`、`NOT_ON_MAIN`、`UNCHECKED_TASKS`、`DEPENDENCY_PENDING`。
- コマンド: `ensure`、`state`、`checkpoint`、`finish`、`abort`、`list`、`status`、`human-tasks`、`sync-status`、`next`、`resolve`（gamekit と同じ意味）。`ensure` と `state` の出力の項目名は `RQ_NAME`（gamekit の `FEATURE_NAME`）以外は gamekit と同じ。
- 着手順は `docs/questions/spec_order.md` の並び、その後に番号順。

### チェックポイントの subject

| ステップ | subject |
|---|---|
| Q2 | `docs(<RQ>): 問いの仕様を作成` |
| Q3 | `docs(<RQ>): 仕様を明確化（1 回目）` |
| Q4 | `docs(<RQ>): 仕様を明確化（2 回目）` |
| Q5 | `docs(<RQ>): 調査計画を作成` |
| Q6 | `docs(<RQ>): タスクを作成` |
| Q7-1 | `docs(<RQ>): 整合性を検証（1 回目）` |
| Q7-2 | `docs(<RQ>): 整合性を検証（2 回目）` |
| Q8 | `research(<RQ>): 収集` |
| Q9 | `research(<RQ>): 分析` |
| Q10 | `research(<RQ>): 主張をまとめる` |
| Q11 | `review(<RQ>): 5 軸レビュー（1 回目）` |
| Q12 | `review(<RQ>): 5 軸レビュー（2 回目）` |

### 調査全体の工程のコミット

`git commit --allow-empty -m "<subject>" -m "Researchkit-Bootstrap: R<n>"`。subject は `docs(bootstrap): R<n> <内容>`（例: `docs(bootstrap): R1 問いの種を作成`）。

## 4. RQ の概要ファイル（`docs/questions/<NNN-name>.md`）

```markdown
# <RQ の問い（日本語の疑問文）>

**状態**: 未着手 | **区分**: 中核 | **想定順序**: <N> | **依存**: <NNN-slug, ... または —> | **手法**: <desk, literature, data, qualitative のうち使うもの>

## 問い
## つながる決定
## つながる仮説
## 答えの形
## 範囲
## 想定する情報源
## 人の作業の見込み
```

- `**区分**` は `基盤`（000）、`中核`、`補助`、`統合`（999）。
- `**依存**` は、先に答えが要る RQ。`validate.py` が循環と存在しない参照を検出する。
- `**手法**` の値は `desk`、`literature`、`data`、`qualitative`（`,` 区切り）。
- `## つながる決定` には `docs/concept/seed.md` の決定（`D1` など）を、`## つながる仮説` には `docs/study/hypotheses.md` の仮説（`H1` など）を書く。`validate.py` は、どの決定にもつながらない RQ をエラーにする（000 と 999 を除く）。

## 5. 識別子

| 記号 | 意味 | 定義する文書 |
|---|---|---|
| `D1`〜 | 調査で決めたいこと（意思決定） | `docs/concept/seed.md` |
| `RP1`〜`RP12` | 前提 | `docs/concept/premises.md` |
| `I1`、`I1.2` | イシューツリーの節 | `docs/study/issue-tree.md` |
| `H1`〜 | 仮説（反証条件つき） | `docs/study/hypotheses.md` |
| `C1`〜 | 主張（RQ の中） | `studies/<NNN>/findings.md` |
| `<NNN>-C<n>` | 他の RQ の主張の参照 | 統合報告 |
| `S<NNN>-<NNNN>` | 出典 | `sources/` |
| `T001`〜 | タスク | `studies/<NNN>/tasks.md` |
| `{N:<path>#<key>}` | 数値の参照 | steering の「数値の参照」 |

## 6. `check.py` と `numbers.py`（`researchkit-check/scripts/`）

- `check.py [--root R] [--rq <NNN>|--all] [--file <path>] [--online] [--strict]`: 出典の参照の検証。
  - ERROR: 主張の根拠の欄に、存在しない出典 ID・主張 ID がある。根拠の欄が空。根拠が `min_grade` 未満の等級の出典だけ。出典ファイルの必須項目（`id`、`type`、`title`、`accessed`、`grade`、`url` か `doi` か書誌（`author`＋`publisher`）のどれか）が欠けている。`id` とファイル名が一致しない。確度の値が `confidence.levels` にない。
  - WARN: 使われていない出典。`used_in` と実際の参照の食い違い。DOI の書式の誤り。参照日が 1 年以上前。`grade: D` の出典がある。
  - `--online`: URL（HEAD、だめなら GET）と DOI（`https://doi.org/<doi>`）の到達性。失敗は WARN。
  - 出力: 1 行 1 件 `ERROR|WARN <file>:<line> <code> <説明>` と、最後に `SUMMARY: errors=<n> warnings=<n>`。エラーがあれば終了コード 1。
- `numbers.py [--root R] [--rq <NNN>|--all] [--file <path>]`: `{N:<path>#<key>}` の直前の数値と JSON の値を突き合わせる。数値の書式（`1,234`、`12.3%`、`1.2万`、`3億`、`-0.5`）を解釈する。`%` の扱いは、JSON の値が 0〜1 なら 100 倍して比べる。`{N:calc}` は対象外（件数を数えて出すだけ）。出力は `check.py` と同じ形式。

## 7. テスト

`tool/tests/` に `unittest` で書く（gamekit の `tool/tests/` を参照）。一時ディレクトリに Git リポジトリを作って、スクリプトを `subprocess` で呼ぶ。実行は `cd tool && python3 -m unittest discover -s tests`。
