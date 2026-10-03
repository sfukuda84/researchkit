---
name: "researchkit-analysis"
description: "RQ の収集した根拠（evidence/、data/、sources/）を、plan.md で事前に決めた分析の計画どおりに分析するスキル。手法ごとに、主張と根拠の表・比較表・推計（デスクリサーチ）、抽出表と研究の質の評価と統合（文献レビュー）、再実行できるスクリプトと前処理の記録（データ分析。commands.analysis で実行し、数値を analysis/out/*.json に出す）、匿名化とコーディング表とテーマ（定性調査）を作る。計画との対応表を作り、計画を変えたときは plan.md の「計画の変更」に、変えたこと・理由・データを見る前か後かを記録する。反証条件の照合の材料もここで揃える。RQ の工程の Q9。「分析して」「抽出表を作って」「コーディングして」「スクリプトを回して」と言われたとき、または /researchkit-analysis と打たれたときに使う。"
argument-hint: "<RQ（例: 001, 001-market-size）> [--rerun] [--auto]"
compatibility: "Requires git and Python 3.9+; runs .researchkit/config.yaml commands.analysis (e.g. uv run --with pandas python {script}); uses studies/<NNN-name>/plan.md, evidence/, data/"
user-invocable: true
disable-model-invocation: false
---

# researchkit-analysis スキル（Q9: 分析）

集めた根拠を、**収集の前に決めた計画どおりに**分析し、Q10（`researchkit-findings`）が主張を書ける材料を揃える。分析の結果の数値は、手で写さずにスクリプトの出力（`analysis/out/*.json`）から参照できる形にする。

パスは既定の配置で書いている。`.researchkit/config.yaml` の `paths` で読み替える。ステップ番号、`$HELPER`、再開、自動モードの共通の規則は [`researchkit-worktree`](../researchkit-worktree/SKILL.md) に従う。`$NUM` の意味は steering（`.kiro/steering/research.md`）の「エージェントの行動規範」のとおりである。

## 0. 大原則

- **計画が先、結果が後。** `plan.md` の「分析の計画」と反証条件に沿って分析する。結果を見てから指標・区切り・除外の基準・比較の相手を変えるのは、都合のよい結果を選ぶこと（いわゆる p-hacking や HARKing）になりやすい。変えるときは §5 のとおり記録する。
- **数値は再計算できる形で持つ。** 計算はスクリプトに書き、`commands.analysis` で実行し、出力を JSON にする。手で計算した数値は、計算式と入力を表に残し、`{N:calc}` を付ける（steering「数値の参照」）。
- **スクリプトの標準出力は要約だけにする。** 表やデータフレームの全体を print しない。結果は `analysis/out/` に書き、標準出力には書いたファイルのパスと、確かめに要る数行（件数、主な値）だけを出す（steering「コマンドの出力を短くする」）。
- **根拠の鎖を切らない。** 表のどの行も、出典 ID と抜き書きの番号（`S001-0003` の `E2`）までたどれるようにする。出典のない値を表に入れない。
- **反対の証拠を同じ表に載せる。** 支持する根拠だけの表を作らない。
- **相関と因果を分ける。** 因果を言える設計（無作為化、自然実験など）でなければ、「関係がある」までにとどめ、代わりの説明（交絡、逆の因果、選択）を書く。
- **個人を守る。** 分析の出力・表・図に、個人を特定できる情報を出さない。小さな区分（数人しかいない属性の組み合わせ）も、特定につながるなら出さない。

## 1. 引数

```text
$ARGUMENTS
```

- RQ の指定は `001` か `001-market-size`。省略したら、今いる worktree のブランチから決める。
- `--rerun` は、スクリプトをすべて実行し直し、出力が変わらないことだけを確かめる（Q11・Q12 の Numbers 軸の後などに使う）。
- `--auto` は自動モード（§8）。

## 2. 入力と前提

| 入力 | 用途 |
|---|---|
| `studies/<NNN-name>/plan.md` | 分析の計画、反証条件、標本、手法 |
| `studies/<NNN-name>/spec.md` | 答えの形、判定の基準、範囲 |
| `studies/<NNN-name>/tasks.md` | 分析のタスク |
| `studies/<NNN-name>/evidence/`、`search-log.md`、`sources/` | 収集した根拠 |
| `data/raw/`、`data/manifest.md` | データ |
| `researchkit-method/references/<手法>.md` | 手法ごとの分析の手順 |
| `docs/study/hypotheses.md` | 仮説と反証条件 |
| `.researchkit/config.yaml` の `commands.analysis`・`commands.test` | スクリプトの実行 |
| 憲章、`docs/quality.md` | 再現性の水準、数値の規則 |

- 収集（Q8）の成果物がなければ、`researchkit-collect` を案内する。
- `999-research-report` の Q9 は、このスキルではなく `researchkit-publish` である。
- `000-research-foundation` のときは §7 に従う。

## 3. 計画との対応

最初に、`plan.md` の「分析の計画」の行（判定の基準 `AC1`〜 ごとの分析と出力）を 1 つずつ書き出し、`analysis/analysis.md` の「計画との対応」の表に並べる（様式: [templates/analysis.md](./templates/analysis.md)）。「先に決めておく分岐」（外れ値の扱いなど）も行にする。

| 列 | 書くこと |
|---|---|
| 計画の項目 | 判定の基準（`AC1`）と、`plan.md` の分析の要約 |
| 実施 | 実施 / 一部 / 未実施 / 変更 |
| 成果 | 表の節、スクリプト、出力ファイルとキー（`plan.md` に書いたキーと同じ名前にする） |
| 備考 | 一部・未実施の理由（例: データが `[人]` のタスク待ち）、変更なら §5 の記録への参照 |

分析が終わったら、この表に空欄がないことを確かめる。未実施の項目は、Q10 で「残った問い」か残作業になる。

## 4. 手法ごとの分析

中身は `plan.md` で選んだ手法の参照文書（`researchkit-method/references/<手法>.md`）に従う。1 つの RQ で手法を組み合わせたときは、手法ごとに節を分ける。ここには、このスキルで必ず作るものを書く。表が長くなるときは、`analysis/` の下に別のファイル（`extraction.md`、`coding.md` など）に分け、`analysis.md` から相対リンクを張る。

### 4.1 デスクリサーチ（`desk`）

主張と根拠の表（支持と反する根拠を並べる）、比較表（分からないセルは「不明（search-log.md #n で探した）」）、推計（前提ごとに値・出典・幅、計算はスクリプト）。詳細は [references/methods.md](references/methods.md)。

### 4.2 文献レビュー（`literature`）

抽出表、研究の質の評価（設計に合う道具）、統合（似ていればメタ分析、そうでなければナラティブ。票を数えない）、出版バイアス。詳細は [references/methods.md](references/methods.md)。

### 4.3 データ分析（`data`）

- **スクリプト**: `studies/<NNN-name>/analysis/<名前>.py`（R なら `.R`）に書き、`commands.analysis` の `{script}` をスクリプトのパスに置き換えて、プロジェクトのルートで実行する。入力は `data/raw/`（または `data/large/`）から読み、元のファイルを書き換えない。
- **出力**: 数値は `studies/<NNN-name>/analysis/out/<名前>.json` に書く。キーは英数字と `_` にし、入れ子はドット区切りで参照する（`{N:analysis/out/market.json#size.2025}`）。値は数値にする。割合は 0〜1 で持つ（`numbers.py` が 100 倍して `%` と比べる。`docs/method.md` の出力の規約）。単位はキー名か、同じ JSON の `units` に書く。図は `analysis/out/fig/` に置く。
- **探索的な分析の出力**: `plan.md` で事前に決めていない分析（結果を見た後に足した感度・指標・除外の組み合わせ。レビューの指摘に答えて足したものを含む）の出力は、JSON の `exploratory` の下に置き（例: `{"exploratory": {"coef_chain": {...}}}`）、`analysis.md` の「探索的な分析」の表に、日付・きっかけ（計画の変更の行、レビューの指摘 ID）・分析・出力のキー・結果・向き（支持／反証／中立）を書く。事前に決めた分析のキーと混ぜない（`check.py` がキーの名前で確認的か探索的かを見分ける）。
- **出力の `_meta`**: JSON に `_meta` を置き、スクリプトの名前、入力のファイルと SHA-256、乱数のシードを書く。実行の日時は書かない（同じ入力なら同じ出力になるようにする）。
- **前処理の記録**: 手順ごとに、行数（前・後）、除いたものと理由、欠損の扱い、変数の作り方を `analysis.md` の表に書く。除外の基準は `plan.md` のとおりにする。
- **結果の書き方**: p 値だけでなく、効果の大きさと幅（信頼区間など）を出す。多くの比較をしたときは、その数と補正の有無を書く。
- **再現の確認**: 全部のスクリプトをもう一度実行し、`out/` の JSON が変わらないことを確かめる（`git diff --stat -- studies/<NNN-name>/analysis/out/` が空）。乱数を使うときは、シードを固定する。`commands.test` があれば、分析のコードのテストも実行する。
- **`commands.analysis` が空**: スクリプトが要る分析なら止まり、`researchkit-method`（分析環境を決める）を案内する。自動モードでも止まる（`docs/method.md` の変更に当たる）。スクリプトの要らない分析（表だけのデスクリサーチなど）なら、`{N:calc}` と計算の表で進めてよい。

### 4.4 定性調査（`qualitative`）

匿名化を先に行い、コーディング表、テーマ（反例も並べる）、数はコーディング表から数える。詳細は [references/methods.md](references/methods.md)。

### 4.5 反証条件の照合の材料

`plan.md` の「仮説と反証条件」の行ごとに、見る指標・データの値と、それが「支持の条件」「反証条件」「どちらでもない」のどれに当たるかを、根拠（表の行、出力のキー、出典 ID）と一緒に `analysis.md` の「反証条件の照合」の表に書く。**判定（支持・棄却・保留）は Q10 で行う。** ここでは、どの条件に当たる結果が出たかを事実として書く。`plan.md` の「反対の証拠の探し方」にある代わりの説明を確かめられたかも書く。

## 5. 計画の変更

収集の後に分析の計画を変えたときは、`plan.md` の「計画の変更」の節に足す（steering の原則 4）。既存の記述は消さない。

```markdown
| 日付 | ステップ | 変えたこと（前 → 後） | 理由 | 結果を見た後か | 影響する判定の基準 |
|---|---|---|---|---|---|
| 2026-10-05 | Q9 | 外れ値の基準 ±3SD → IQR の 1.5 倍 | 分布が大きく歪んでいた | はい | AC2（H2 の判定。両方の基準の結果を出す） |
```

- **結果を見た後の変更**は、元の計画どおりの結果も出し、両方を `analysis.md` に並べる。Q10 では、元の計画の結果を主とし、変更後の結果は補足にする。
- **結果を見た後に足した分析**（感度、別の指標など）は探索的な分析である。出力を `exploratory` の下に置き（§4.3）、Q10 では別の主張（確度は示唆まで）にする。事前に決めた分析の誤りを直すだけなら「修正」で、主の値を直してよい（`researchkit-review` の §4.4）。
- 問い・範囲・反証条件そのものを変える必要があるときは、ここでは変えずに止まり、`researchkit-clarify` か `researchkit-plan` に戻るよう案内する。自動モードでも止まる。

## 6. 仕上げ

1. 分析のタスクを `- [x]` にする（`[人]` を除く）。
2. スクリプトがあれば、全部をもう一度実行し、出力が変わらないことを確かめる（§4.3）。
3. `analysis.md` などに `{N:...}` を書いたら、`$NUM --file studies/<NNN-name>/analysis/analysis.md` で突き合わせ、ERROR を 0 件にする。
4. 「計画との対応」に空欄がないことを確かめる。
5. `out/` と表に個人を特定できる情報がないことを確かめる。

## 7. `000-research-foundation` のとき

分析環境が動くことを確かめる（小さなスクリプトを `commands.analysis` で 2 回実行して同じ出力）。主張は作らない。手順は [references/special.md](references/special.md)。

## 8. 自動モード（`--auto`）

細部は推奨案を採る。計画の変更が要るなら推奨案を採って §5 で記録し、元の計画の結果も出す。問い・範囲・反証条件の変更が要るとき、`commands.analysis` が空でスクリプトが要るとき、同じ原因で 3 回失敗したときは止まる。表は [references/special.md](references/special.md)。

## 9. 出力

出力は `analysis.md`（様式: [templates/analysis.md](./templates/analysis.md)）、手法ごとの表、スクリプトと `out/*.json`・`out/fig/`、`plan.md` の計画の変更、`tasks.md` の分析のタスクの `- [x]`。次は `researchkit-findings`（Q10）。詳細は [references/special.md](references/special.md)。

## 10. 完了報告

完了報告の項目は [references/special.md](references/special.md)。
