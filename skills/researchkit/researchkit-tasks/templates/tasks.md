# <RQ の問い> — タスク

- RQ: `<NNN-name>`（仕様: `spec.md`、計画: `plan.md`）
- 作成日: <YYYY-MM-DD>

書式: `- [ ] T001 [P] [SQn] [人] 本文（対象のファイル）（完了の確かめ方: …）`。`[P]` は並行可、`[SQn]` は対象の小問（収集と分析のフェーズだけ）、`[人]` は人が行うタスク。AI は `[人]` のタスクを実行せず、`- [x]` にもしない。

## Phase 1: 準備

目的: <収集を始める前に要るものをそろえる>。終える条件: <出典 ID の範囲と作業用のファイルがあり、収集の前に要る [人] のタスクに着手している>

- [ ] T001 出典 ID の範囲を取り、plan.md の「出典 ID」に書く（researchkit.py sources next <NNN> --count <k>）（完了の確かめ方: plan.md に範囲がある）
- [ ] T002 [P] studies/<NNN-name>/search-log.md を作り、plan.md の情報源ごとの欄を用意する（完了の確かめ方: 情報源の数だけ欄がある）
- [ ] T003 [P] [人] <例: 有料レポート〈名前〉を購入するかを判断し、購入したら data/large/ に置く>（完了の確かめ方: <data/manifest.md に記載があり、ハッシュが一致する。購入しない場合は plan.md の「計画の変更」に記録がある>）

## Phase 2: 収集（Q8）

目的: <plan.md の情報源から根拠を集め、出典台帳と検索ログに記録する>。終える条件: <plan.md のすべての情報源で検索を終え、判定の基準の「探すのを止める条件」を満たす>

- [ ] T004 [P] [SQ1] <例: 情報源 1（e-Stat）の該当の表を取得し、data/raw/ に置いて data/manifest.md に記載する>（完了の確かめ方: <manifest に出所・取得日・ライセンス・ハッシュがある>）
- [ ] T005 [P] [SQ1] <例: 情報源 2 の検索式で Web 検索し、候補の出典の実在を 1 件ずつ確かめて sources/ に記録し、該当の箇所を evidence/ に抜き書きする>（完了の確かめ方: <search-log.md に検索式・日付・件数があり、check.py --rq <NNN> の ERROR が 0 件>）
- [ ] T006 [SQ1] T003 で入手したレポートの該当の数値を抜き書きし、evidence/ と sources/ に記録する（完了の確かめ方: <出典ファイルに grade と accessed がある>）
- [ ] T007 [P] [SQ1] 反対の証拠を探す: <plan.md の「反対の証拠の探し方」の検索式>で検索し、結果を evidence/ と search-log.md に記録する（見つからなかった場合も書く）（完了の確かめ方: <search-log.md に検索式と件数がある>）

## Phase 3: 分析（Q9）

目的: <plan.md の分析の計画どおりに、判定の基準に答える数値と表を出す>。終える条件: <commands.analysis で全スクリプトが再実行でき、analysis/out/ に plan.md のキーがそろう>

- [ ] T008 [SQ1] <例: analysis/market.py に 2 通りの推計を書き、analysis/out/market.json に size_2025_a と size_2025_b を出力する>（完了の確かめ方: <commands.analysis で再実行して同じ値が出る>）
- [ ] T009 [P] [SQ2] <例: 比較表を analysis/out/compare.json と analysis/compare.md に作る>（完了の確かめ方: <5 社 × 3 軸がすべて埋まり、各セルに出典 ID がある>）
- [ ] T010 [SQ1] 仮説 <H1> の反証条件の判定に使う指標を算出する（完了の確かめ方: <analysis/out/ に plan.md の「仮説と反証条件」の指標がある>）

## Phase 4: まとめ（Q10）

目的: <判定の基準ごとに答えを主張の表にし、上流の文書に逆流させる>。終える条件: <findings.md があり、check.py と numbers.py のエラーが 0 件>

- [ ] T011 studies/<NNN-name>/findings.md に、判定の基準（AC1〜）ごとの主張を steering の「主張の書式」で書く（完了の確かめ方: すべての AC に主張か「残った問い」がある）
- [ ] T012 仮説ごとに、反証条件に当たったかを findings.md に書き、崩れた仮説や前提を docs/study/hypotheses.md・issue-tree.md・docs/questions/ に戻して直す（完了の確かめ方: findings.md の判定と hypotheses.md の状態が一致する）
- [ ] T013 check.py --rq <NNN> と numbers.py --rq <NNN> を実行し、エラーを 0 件にする（完了の確かめ方: 両方の SUMMARY が errors=0）

## 依存

- T003（[人]）→ T006
- T004、T005 → T008
- T008、T009、T010 → T011 → T012 → T013

## 並行の例

- 準備: T002 と T003 は並行できる
- 収集: T004、T005、T007 は並行できる（サブエージェントに任せるなら、出典 ID の範囲を分ける）

## 人のタスク

| ID | 内容 | 必要になる時点 | 待つ間に進められるタスク |
|---|---|---|---|
| T003 | <有料レポートの購入の判断と入手> | <T006 の前> | <T004、T005、T007、T009> |
