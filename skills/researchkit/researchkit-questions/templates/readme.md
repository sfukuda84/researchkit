# RQ の一覧

**<調査の題名>（<誰が何を決めるための調査か、1 文>）のリサーチクエスチョン（RQ）**を 1 RQ 1 ファイルで置く場所。
`researchkit-question` / `researchkit-all` に渡す入力素材であり、問いの仕様と調査の計画は RQ の工程（`studies/<NNN-slug>/`）で詰める。

## 使い方

1. 着手する RQ のファイルを読む
2. `researchkit-question` / `researchkit-all` に番号を渡す（例: `/researchkit-all 001`）。このファイルが Q2（`researchkit-specify`）の入力になる
3. 状態は、`researchkit-worktree` が自動で更新する（設計の工程の後は `設計済み`、実行の工程の後は `完了`。`[人]` のタスクが残っていれば `人の作業待ち`）。人のタスクを片付けた後は `researchkit-worktree` の `sync-status` で `完了` にする。手で直すときは、ファイルの状態と下の一覧表の状態欄を同時に直す
4. **以降その RQ の正本は `studies/<NNN-slug>/`。** このファイルは追記せず、素材・履歴として残す（例外: `researchkit-findings` の逆流で、末尾の `## 上流からの変更` の節に追記する）

## 運用ルール

- **ここは進捗管理の場所ではない。** 進捗の正本は `studies/` の `tasks.md` と `findings.md`
- すべての RQ は `docs/concept/seed.md` の決定（D）につながる。答えても決定が変わらない RQ は作らない
- 区分は **中核**（決定に直接効く）と **補助**（中核の RQ の前提を埋める）。`000`（基盤。`researchkit-foundation`）と `999`（統合。`researchkit-deliverable`）は予約番号
- ファイル名は `NNN-<slug>.md`。`NNN` は想定順序で、`studies/NNN-<slug>` とブランチ `rq/NNN-<slug>` にそのまま対応する。**番号は振り直さない**。新しい RQ は既存の最大値の次から振る
- **区分・状態・依存・手法の欄は各ファイルのヘッダ行をそのまま写す**（依存は `001-market-size` のような完全名）。表記を変えると検証で不一致になる

## メタ文書（RQ ファイルではない）

| ファイル | 何が書いてあるか |
|---|---|
| [spec_order.md](./spec_order.md) | **着手順序の正本。** 段階分け、被参照数、依存グラフ |
| [../concept/seed.md](../concept/seed.md) | **決定（D）の正本。** 誰が何を決めるための調査か |
| [../study/issue-tree.md](../study/issue-tree.md) | **イシューツリーの正本。** 問いの分解 |
| [../study/hypotheses.md](../study/hypotheses.md) | **仮説（H）の正本。** 仮説と反証条件 |
| [../concept/backlog.md](../concept/backlog.md) | **RQ の候補の正本。** まだ RQ にしていない候補と却下した候補 |

## 一覧

**# は想定順序（採番）。着手順序は [spec_order.md](./spec_order.md) が正本。**

| # | 問い | 区分 | 状態 | 依存 | 手法 | 一言 |
|---|---|---|---|---|---|---|
| 1 | [<RQ の問い>](./001-<slug>.md) | 中核 | 未着手 | — | desk, data | <一言> |

**件数**: RQ ファイル **<N> 件**（中核 <a> / 補助 <b>。000 と 999 を含めた数）。

## 葉・仮説と RQ の対応

イシューツリー（[../study/issue-tree.md](../study/issue-tree.md)）の葉と仮説（[../study/hypotheses.md](../study/hypotheses.md)）を、どの RQ が受け持つか。**抜けと重なりの点検（MECE）の記録**であり、RQ にしなかった葉も理由とともに残す。

| 葉 | 仮説 | 優先度 | 扱い | 理由 |
|---|---|---|---|---|
| <I1.2> | <H1> | <高> | <RQ: 001-market-size> | — |
| <I1.1> | — | <低> | <既知（S000-0201）> | <scan/wide.md で答えが出ている> |
| <I3.2> | <H5> | <中> | <backlog: BL-003> | <答えても D1 の判断が変わらない> |

## 検証

```bash
python3 <validate.py のパス> docs/questions
```
