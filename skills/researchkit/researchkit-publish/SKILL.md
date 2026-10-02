---
name: "researchkit-publish"
description: "統合報告（reports/report.md）を、読み手に合わせた形式にするスキル。読み手は executive（意思決定者）・team（実務担当）・external（社外・公開）の 3 区分で、形式は Markdown・HTML の要約、スライド（pptx。speckit-presentation から移植した build_pptx.py で slides.md と design.yaml から作る）、docx を選ぶ。数値は findings.md と分析の出力にあるものだけを使い、numbers.py で突き合わせた後に、数値の参照の記号 {N:...} を取り除く（strip_refs.py）。新しい事実を足さない。公開そのものは人が判断する。999-research-report の Q9。単独でも使う。「スライドにして」「要約を作って」「経営向けにまとめて」「docx にして」「公開用にして」と言われたとき、または /researchkit-publish と打たれたときに使う。"
argument-hint: "[読み手: executive | team | external]（省略時は 999-research-report.md の読み手か質問）[形式: md,html,pptx,docx] [--auto]"
compatibility: "Requires Python 3.9+; uv (or python-pptx and PyYAML) for pptx; optional pandoc for html/docx; uses reports/report.md"
user-invocable: true
disable-model-invocation: false
---

# researchkit-publish スキル（999 の Q9: 読み手に合わせた形式）

統合報告を、読み手が使える形に直す。内容の正本は `reports/report.md` であり、このスキルは**削る・並べ替える・言い換える**だけを行う。調べ直したり、数値を作ったりしない。

内容（作業用の原稿 `draft.md` と `slides.md`）、見た目（`design.yaml`）、変換（`strip_refs.py`、`build_pptx.py`、pandoc）を分け、公開用のファイルはいつでも作り直せるようにする。パスは既定の配置で書いている。`.researchkit/config.yaml` の `paths` で読み替える。`$NUM` の意味は steering（`.kiro/steering/research.md`）の「エージェントの行動規範」のとおりである。

## 0. 大原則

- **新しい事実を作らない。** 数値・結論・確度は、`reports/report.md` にあるもの（その元の `findings.md` と分析の出力）だけを使う。足りないものがあっても、ここで調べたり計算したりしない。報告の不足は `researchkit-synthesize` で補うよう案内する。
- **確度を落とさない。** 読み手に合わせて短くしても、結論に付いた確度と、主な限界・判断を変える条件は残す。確度の言葉を「〜と見られる」などに言い換えない。
- **数値には出典を付ける。** 数値を出す箇所には、出典の名前（スライドは `> 出典: …`）を添える。
- **数値は突き合わせてから記号を取る。** 作業用の原稿では数値に `{N:...}` を残し、`$NUM --file` で突き合わせた後に、公開用のファイルから取り除く（steering「数値の参照」）。
- **1 枚・1 段落に 1 つの主張。** スライドの見出しは話題名（「市場規模」）ではなく主張（「市場は 1,234 億円で年 8% 伸びている」）にする。
- **構成は書き出す前に合意を取る**（通常モード）。
- **公開用のファイルを手で直さない。** pptx・docx・HTML は原稿から作り直すので、直接の修正は次の生成で消える。直したい点は原稿か `design.yaml` に反映する。
- **公開そのものはしない。** 社外への公開・送付の判断は `[人]` である（steering「人が行うタスク」）。

## 1. 引数と入出力

```text
$ARGUMENTS
```

- 第 1 引数は読み手（`executive`、`team`、`external`）。省略時は `docs/questions/999-research-report.md` の「読み手」から決め、決まらなければ質問する。複数の読み手の版を作ってよい。
- 第 2 引数は形式（`md`、`html`、`pptx`、`docx` を `,` 区切り）。省略時は `999-research-report.md` の「形式」に従う。

| 入力 | 用途 | ない場合 |
|---|---|---|
| `reports/report.md` | 内容の正本 | 止まって `researchkit-synthesize` を案内する |
| `docs/questions/999-research-report.md`、`studies/999-research-report/spec.md` | 読み手、形式、構成、言語 | 質問する |
| `docs/concept/seed.md`・`premises.md` | 読み手の決めたいこと、秘密情報・公開の範囲 | — |
| 憲章 | AI 利用の開示、引用の規則 | 既定（steering）で進める |
| `sources/` | 出典の書誌、利用規約の注意 | — |

| 出力 | 役割 |
|---|---|
| `reports/publish/README.md` | 作った版の一覧（読み手、形式、元にした `report.md` の日付、作らなかった理由） |
| `reports/publish/design.yaml` | スライドのデザインスペック。読み手の版で共通。なければ [templates/design.yaml](./templates/design.yaml) から作る |
| `reports/publish/<読み手>/draft.md` | 文書の作業用の原稿（`{N:...}` と主張の参照つき）。様式: [templates/summary.md](./templates/summary.md) |
| `reports/publish/<読み手>/summary.md`、`summary.html`、`report.docx` | 公開用の文書（記号を取り除いたもの） |
| `reports/publish/<読み手>/slides.md` | スライドの原稿と発表者ノート。書き方は §5、見本は [templates/slides.md](./templates/slides.md) |
| `reports/publish/<読み手>/slides.pptx` | スライド（`build_pptx.py` が作る） |
| `reports/publish/<読み手>/images/` | スライドに貼る図（分析の出力の `analysis/out/fig/` から写す） |

既存の原稿があるときは、更新モード（§6）で進める。

## 2. 読み手ごとの構成

| 項目 | executive（意思決定者） | team（実務担当） | external（社外・公開） |
|---|---|---|---|
| 結論と確度 | ◎ 最初の 1 枚・1 段落 | ◎ | ◎ |
| 決めたいことごとの答え | ◎ 表で | ○ | △ 公開してよい範囲 |
| 理由（キーライン） | ○ 3 つ程度 | ◎ 根拠の主張まで | ○ |
| 数値の強調 | ○ 決定に効くものだけ | ○ | ○ 公開してよいものだけ |
| 限界と判断を変える条件 | ◎ | ◎ | ◎ |
| 方法（RQ、手法、出典の数） | △ 1 枚 | ◎ | ◎ 再現できる程度に |
| 次の問い・次の一歩 | ◎ お願いしたいこと | ◎ 次のタスク | △ |
| 主張の参照（`001-C1`） | 発表者ノートだけ | 本文に残す | 取り除く |
| 出典の一覧 | △ 主なもの | ◎ | ◎ URL・DOI つき |
| 目安の量 | スライド 5〜10 枚、要約 1〜2 ページ | スライド 10〜20 枚、要約 3〜5 ページ | 要約 2〜5 ページ |

◎ は厚く、○ は短く、△ は必要なら入れる。どの読み手でも、結論を先に置く（ピラミッド構造の頂点から書く）。

**external の追加の点検**: 秘密情報・社内データ・未公開の数値を含めない。個人を特定できる情報を含めない（インタビューの発言は、公開の同意の範囲でだけ使う）。有料レポートや有料データベースの数値・図表は、利用規約が公開を許す範囲でだけ使う。憲章の AI 利用の開示を入れる。迷うものは `[人]` の確認に回す。

## 3. 手順

### ステップ 1: 読み手と目的の確認

AskUserQuestion などで、次を確かめる（引数や `999-research-report.md` で決まっているものは聞かない）。

- 読み手と、この資料で得たいこと（例: D1 の判断、実務の計画、社外への説明）
- 形式（md・html・pptx・docx）
- 発表で使うか、配布して読んでもらうか（配布なら発表者ノートと要約を厚くする）
- 発表の時間（スライドは 1 枚 1〜2 分が目安）

**作らないとき**: `999-research-report.md` で公開用の形式が要らないと決まっているときは、`reports/publish/README.md` に「作らない（理由）」と書いて終える。呼び出し元が空のチェックポイントを記録する。

### ステップ 2: 構成案の提示と合意

§2 の構成から、版ごとの一覧を示し、承認を得る。

| # | 形式 | レイアウト・節 | 見出し（主張） | 元にした `report.md` の節 |
|---|---|---|---|---|
| 1 | pptx | title | <題名> | — |
| 2 | pptx | message | <結論の 1 文> | エグゼクティブサマリー |

修正があれば直して再提示する。合意するまで書き出さない。

### ステップ 3: 原稿を書く

- **文書**: [templates/summary.md](./templates/summary.md) の様式で `reports/publish/<読み手>/draft.md` を書く。`report.md` の文と数値を写し、数値の `{N:...}` と主張の参照（`（001-C1）`）を残す。
- **スライド**: §5 の規約で `reports/publish/<読み手>/slides.md` を書く。数値の強調・表・グラフの値の直後に `{N:...}` を残す（`build_pptx.py` が取り除く）。主張の参照は発表者ノートに書く。図は `analysis/out/fig/` から `images/` に写す。
- 丸めるときは「約」を付ける。`report.md` にない計算（合計、比率、換算）はしない。

### ステップ 4: 数値の突き合わせ

```bash
$NUM --file reports/publish/<読み手>/draft.md
$NUM --file reports/publish/<読み手>/slides.md
```

ERROR を 0 件にする。`{N:calc}` は、`report.md` の「計算」の節にある数値だけに使う。原稿の数値がすべて `report.md` にあることも確かめる（`report.md` にない数値は消す）。

### ステップ 5: 公開用のファイルを作る

`<skills>` は、このスキルが置かれた skills ディレクトリである。

**Markdown**（記号を取り除く。executive と external は `--claims` で主張の参照も取り除く）:

```bash
python3 <skills>/researchkit-publish/scripts/strip_refs.py reports/publish/<読み手>/draft.md -o reports/publish/<読み手>/summary.md [--claims]
python3 <skills>/researchkit-publish/scripts/strip_refs.py reports/publish/<読み手>/summary.md --check
```

**HTML**: pandoc があれば `pandoc reports/publish/<読み手>/summary.md -s -o reports/publish/<読み手>/summary.html --metadata title="<題名>"`。なければ、`summary.md` の中身をそのまま 1 つの HTML ファイル（CSS を中に書き、外部の読み込みを持たない）に移す。文を足したり変えたりしない。

**docx**: pandoc があれば `pandoc reports/publish/<読み手>/summary.md -o reports/publish/<読み手>/report.docx`（社の雛形があれば `--reference-doc <雛形.docx>`）。なければ、エージェントの docx を作る手段を使う。どちらもなければ、作れなかったことを報告し、`summary.md` を渡す。

**pptx**:

```bash
uv run <skills>/researchkit-publish/scripts/build_pptx.py reports/publish/<読み手>/slides.md --check
uv run <skills>/researchkit-publish/scripts/build_pptx.py reports/publish/<読み手>/slides.md
```

`reports/publish/<読み手>/slides.pptx` ができる。uv がない環境では `pip install python-pptx PyYAML` のうえで `python3`（または `python`、`py -3`）で実行する。`--check` のエラーは必ず直す。上限を超えた警告は、文を短くする、スライドを分ける、レイアウトを変えるなどして直す。直さない場合は理由を報告に書く。

最後に、公開用のファイルに `{N:` が残っていないことを確かめる（HTML と docx は、元の `summary.md` を `strip_refs.py --check` で確かめていれば足りる）。見た目を確かめられる環境（PowerPoint、Word、日本語フォントの入った LibreOffice で PDF に変換できる環境、ブラウザ）なら、文字のあふれや重なりを確かめ、原稿か `design.yaml` を直して作り直す。

### ステップ 6: デザインスペック（スライドのとき）

`reports/publish/design.yaml` がなければ、[templates/design.yaml](./templates/design.yaml) から作る。次を質問する（自動モードではテンプレートのまま）。

- 会社やブランドの雛形の .pptx があるか（あれば `template` に指定する）
- ブランドの色、フォント（既定は Meiryo）
- フッターの文言（例: 「社外秘」「ドラフト」）

### ステップ 7: 一覧の更新

`reports/publish/README.md` に、版ごとの読み手、形式、ファイル、元にした `report.md` の日付、公開の判断の状態（`[人]` 待ち・済み）を書く。external の版を作ったら、`studies/999-research-report/tasks.md` に公開の判断の `[人]` のタスクがあるかを確かめ、なければ足す（完了の確かめ方: 公開の可否と範囲が README に記録されている）。

## 4. 単独の利用

RQ の工程の外で、読み手の版を足す・作り直すときにも使う。`reports/report.md` が新しくなっていたら、原稿を更新モード（§6）で直す。

- `999-research-report` の worktree の中で単独で実行したとき（Q9 の途中）は、最後に `$HELPER checkpoint 999-research-report Q9 "<『ステップ番号』の節の subject>"` を記録する（`researchkit-worktree`）。
- 999 を `main` にマージした後に、`main` で版を足す・作り直すときは、RQ の工程ではないので、通常のコミット（`docs(publish): <読み手> の版を作成`）にする。

## 5. slides.md の規約

`speckit-presentation` と同じ書式である（`build_pptx.py` は同じ解析をする）。

- 先頭の front matter に、`title`、`audience`（`executive`／`team`／`external`）、`purpose`、`duration`、`date`、`author`、`source`（`../../report.md`）、`design`（`../design.yaml`）を書く。
- スライドは `---` だけの行で区切る。レイアウトは `<!-- layout: <名前> -->` で指定する（省略時は `bullets`）。
- 見出しは `# `、発表者ノートは `<!-- notes … -->`、出典は `> 出典: …`（スライドの下に小さく入る）。本文中の `**…**` は太字になる。
- 数値の後の `{N:...}` は、`build_pptx.py` がスライドに出さずに取り除く。主張の参照（`001-C1`）は発表者ノートに書く。

| レイアウト | 書き方 | 調査の報告での用途 |
|---|---|---|
| `title` | `#` 題名、続く段落が副題 | 表紙 |
| `section` | `#` 章の名前 | 章の扉 |
| `message` | `#` に 1 文、続く段落が補足 | 結論と確度、お願いしたいこと |
| `bullets` | `- ` の箇条書き（2 階層まで） | キーライン、限界、判断を変える条件 |
| `two-column` | `## ` の小見出しを 2 つ、それぞれの下に箇条書き | 選択肢の比較、条件ごとの答え |
| `table` | Markdown の表 | 決めたいことごとの答え、比較表 |
| `stats` | `- **数値** 説明` を最大 4 つ | 決定に効く数値の強調 |
| `chart` | Markdown の表と `<!-- chart: column\|bar\|line\|pie -->` | 推移、構成比（値は分析の出力から） |
| `image` | `![説明](images/…)` | 分析の図 |

1 枚に収める量の上限は `design.yaml` の `limits` にある。`--check` が、超えた箇所を警告する。

## 6. 更新モード

原稿がすでにある場合は、次のように進める。

1. `reports/report.md` の変更（`git log -p -- reports/report.md`）と、見直しのきっかけを確かめる。
2. 影響を受ける節・スライドと、変える内容を示し、合意を取る（自動モードでは、`report.md` の変更をそのまま反映する）。
3. 原稿を直し、ステップ 4・5 で突き合わせて作り直す。
4. ほかの読み手の版がある場合は、同じ数値を使っている箇所も直す。

## 7. 自動モード（`--auto`）

| 場面 | 自動モードでの動作 |
|---|---|
| 読み手・形式 | `999-research-report.md` のとおりにする。決まっていなければ executive の md と pptx にし、`studies/999-research-report/auto-decisions.md` に記録する |
| 構成案 | §2 の表のとおりに作り、記録する |
| `design.yaml` | テンプレートのままにする |
| external の公開の点検で迷うもの | 含めない。記録し、`[人]` の確認に回す |
| pandoc も docx を作る手段もない | docx を作らず、記録して進む |

## 8. 出力

- `reports/publish/README.md`
- `reports/publish/design.yaml`（スライドを作ったとき）
- `reports/publish/<読み手>/` の原稿（`draft.md`、`slides.md`）と公開用のファイル（`summary.md`、`summary.html`、`report.docx`、`slides.pptx`、`images/`）

999 の工程では、次は `researchkit-findings` の統合モード（999 の Q10）である。チェックポイントは呼び出し元（`researchkit-execute`・`researchkit-all`）が記録する。

## 9. 完了報告

- 作成・更新したファイル（読み手と形式ごと）
- 構成の要約（スライドの枚数、要約の量）
- `$NUM` の結果と、`strip_refs.py --check`・`build_pptx.py --check` の結果（直さなかった警告があれば、その理由）
- external の点検で外したもの、`[人]` の確認に回したもの
- 公開の判断の `[人]` のタスク
- `report.md` が足りずに省いた項目と、補うためのスキル（`researchkit-synthesize`）
- 次の案内: `researchkit-findings 999`（統合モード）

## 10. 禁止事項

- `report.md`（とその元の `findings.md`・分析の出力）にない数値・結論・事実を書くこと
- 出典のない数値を書くこと
- 確度を上げる、または限界を消すこと
- ユーザーの合意なしに原稿や `design.yaml` を書き出す、または上書きすること（通常モード）
- pptx・docx・HTML を直接編集して直すこと
- 公開・送付そのものを行うこと
