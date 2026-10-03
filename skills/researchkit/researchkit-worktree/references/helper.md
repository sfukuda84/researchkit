# researchkit-worktree: 詳細（helper.md）

[SKILL.md](../SKILL.md) の本文から移した詳細。本文の要点で足りないとき、ここを読む。見出しは本文と同じ番号を使う。

## 1. ヘルパースクリプト

```bash
skills/researchkit/rk helper <command> ...
# 同じ: python3 <skills>/researchkit-worktree/scripts/worktree_helper.py <command> ...
```

以降、この呼び出しを `$HELPER` と書く（steering の「エージェントの行動規範」と同じ。`rk` は 1 語で呼べる入口で、zsh でも変数に入れて使える）。`$RK`（`researchkit-status` の `researchkit.py`）の意味は steering の「エージェントの行動規範」のとおりである。

- `<skills>` は、このスキルが置かれた skills ディレクトリ（`.claude/skills`、`.agents/skills`、`.kiro/skills` のいずれか）である。
- スクリプトは Python 3.9 以上の標準ライブラリだけで書かれており、macOS、Linux、Windows で動く。プロジェクトのルートからでも worktree の中からでも実行できる。`python3` がない環境では、`python` または `py -3` に読み替える。
- マージ先のブランチ（この文書の `main`）は、環境変数 `RESEARCHKIT_MAIN_BRANCH` があればその名前、なければ `main` である。クラウドセッションでの扱いは §8 に書く。

| コマンド | 用途 |
|---|---|
| `$HELPER ensure <RQ> --phase design\|execute\|all` | Q1 準備。worktree があれば再利用し、なければ `main` から作る |
| `$HELPER state <RQ> --phase design\|execute\|all` | 変更せずに進捗を表示する |
| `$HELPER checkpoint <RQ> <step> ["<subject>"]` | worktree の変更をすべてコミットし、ステップの完了を記録する。subject を省くと、ステップごとの既定の形（`references/steps.md` の表）になる |
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
