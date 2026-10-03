# researchkit-findings: 詳細（special.md）

[SKILL.md](../SKILL.md) の本文から移した詳細。本文の要点で足りないとき、ここを読む。見出しは本文と同じ番号を使う。

## 9. 統合モード（`999-research-report`）

Q8（`researchkit-synthesize`）が書いた `reports/report.md` の結論と、各 RQ の `findings.md` の整合を確かめ、`studies/999-research-report/findings.md` を書く。

1. **結論の表**: 報告書の結論の表（`C1`〜）を、主張の書式のまま `findings.md` に写す。根拠の欄は `<NNN>-C<n>`（各 RQ の主張）である。これが統合の主張の正本になる。数値の参照は、この RQ のディレクトリからの相対パスに直す（報告書の `{N:studies/001-market-size/analysis/out/market.json#size_2025}` は `{N:../001-market-size/analysis/out/market.json#size_2025}` にする。`numbers.py` は studies/ の下の文書を RQ のディレクトリから解決する）。
2. **整合の表**: 結論ごとに、次を確かめて表にする（様式の「整合の表」）。
   - 参照した `<NNN>-C<n>` が存在し、その主張の中身と結論の文が合っている（言い過ぎていない、範囲を広げていない）
   - 結論の確度が、§4 の上限（欠けると結論が成り立たない主張の最も低い確度）を超えていない
   - 数値が、元の主張と同じ値で、同じ出力ファイルを参照している（報告書では `{N:studies/<NNN-name>/analysis/out/...}`、`findings.md` では `{N:../<NNN-name>/analysis/out/...}`）
   - 元の主張の反証・限界が、報告書の限界に引き継がれている
   - 報告書に、どの主張にもつながらない事実の文がない（新しい事実を足していない）
3. **RQ どうしの食い違い**: 主張が互いに食い違う組を挙げ、報告書が扱っているか（どちらを採るか、限界に書くか）を確かめる。
4. **直す**: ずれは報告書の側を直す。各 RQ の `findings.md` は、このモードでは書き換えない。元の主張に誤りを見つけたら、報告書でその主張を使わないか限界に書き、完了報告でユーザーに伝える（その RQ の見直しは、その RQ の工程で行う）。
5. **逆流**: 仮説の最終の判定を `hypotheses.md` に、答えた節を `issue-tree.md` に、次の問いを `docs/concept/backlog.md` に反映する。
6. **公開用の形式**（Q9 の `researchkit-publish` の出力）があれば、そこに報告書と findings にない数値・事実がないかも確かめる。
7. **検証**: `$CHECK --rq 999`、`$CHECK --file reports/report.md`、`$NUM --rq 999`、`$NUM --file reports/report.md` の ERROR を 0 件にする。

## 10. `000-research-foundation` のとき

主張は作らない（steering「RQ の工程」）。`findings.md` には、基盤の状態（出典台帳の件数、用語集の項目数、データの目録、分析環境の確認の結果）と、残作業と残った問いだけを書く。§8 の収束は行う。

## 11. 自動モード（`--auto`）

| 場面 | 自動モードでの動作 |
|---|---|
| 確度の判断に迷う主張 | 低い方の段階を採り、理由を「確度の理由」に書く |
| 仮説の判定に迷う | `保留` にする |
| 逆流（仮説・イシューツリー・未着手の RQ・用語集・ネタ帳） | 行い、`studies/<NNN-name>/auto-decisions.md` に記録する |
| 決定・前提が崩れた | 書き換えずに、見直しの優先度「高」で記録して進む |
| 収束のタスク | 足して実行する。予算の STOP、`[人]` 待ち、同じ原因の失敗が 3 回続いたときは止まる |
