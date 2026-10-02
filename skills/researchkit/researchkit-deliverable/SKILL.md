---
name: "researchkit-deliverable"
description: "調査全体の品質基準と最終成果物を定義するスキル。すべての RQ が守る品質基準（出典の最低等級、主張ごとの最低の根拠の数、結論に要る確度、再現性の水準、レビューの合格条件、検索ログの必須項目、倫理）を docs/quality.md に、最終成果物（読み手、形式〈レポート／スライド／論文形式〉、構成、言語、分量、締切、公開の範囲）を統合報告の RQ docs/questions/999-research-report.md に書く。基準は憲章と docs/method.md で達成できる水準で、各 RQ の findings と統合報告に分けて決め、.researchkit/config.yaml の sources.min_grade と numbers.tolerance を合わせる。既存の 999-* があれば更新モードで使う。researchkit-bootstrap の R11 から使われるほか、「品質基準を決めて」「最終報告の形を決めて」「999 を作って」と言われたとき、または /researchkit-deliverable と打たれたときに使う。"
argument-hint: "[--auto] [追加の希望（例: 役員向けのスライド 10 枚、結論は可能性が高い以上で）]"
compatibility: "Requires docs/questions/, docs/method.md and .researchkit/memory/constitution.md"
user-invocable: true
disable-model-invocation: false
---

# researchkit-deliverable スキル（R11: 品質基準 → docs/quality.md ＋ 999-research-report）

調査の「どこまでできたら良しとするか」を、性質の違う 2 つに分けて書く。speckit と gamekit の非機能要件（`docs/nfr.md` と 999）に当たる。

| 出力 | 中身 | 使われ方 |
|---|---|---|
| `docs/quality.md` | **品質基準**。すべての RQ と統合報告が守る最低の水準（出典の等級、根拠の数、確度、再現性、レビューの合格条件、検索ログ） | 憲章から参照され、各 RQ の `plan.md`、`researchkit-analyze`、`researchkit-review`、`researchkit-check` が従う |
| `docs/questions/999-research-report.md` | **統合報告**。最終成果物の読み手、形式、構成、言語、分量、締切、公開の範囲 | 通常の RQ と同じく `researchkit-all` などで進める。Q8 が `researchkit-synthesize`、Q9 が `researchkit-publish`、Q10 が `researchkit-findings` の統合モード |

`999` は予約番号である。ほかの RQ は 999 に依存しない。999 は、ほかのすべての RQ（000 を含む）が `完了` か `人の作業待ち` になってから始める（`worktree_helper.py` が確かめる）。

パスは `.researchkit/config.yaml` の `paths` で読み替える（以下は既定のパス）。

## 0. 大原則

- **憲章と手法で達成できる基準にする。** 基準は、憲章の等級と確度の付け方、`docs/method.md` の手法と情報源で達成できる水準にする（例: 公開の情報だけのデスクリサーチで、すべての主張に等級 A を求めない）。手法を変えないと達成できない基準を求められたら、その旨と `researchkit-method` の見直しを提案する。
- **各 RQ と統合報告に分ける。** RQ の `findings.md` に求める水準と、読み手に渡す統合報告に求める水準を分けて書く（例: 統合報告の結論には「可能性が高い」以上を求めるが、RQ の中の「示唆」の主張は残してよい）。
- **測れる形で書く。** 「信頼できる」「十分に」ではなく、等級、件数、確度の段階、確かめ方（`check.py`、`numbers.py`、レビューの軸、`[人]`）を書く。
- **機械検証とそろえる。** `check.py` は `sources.min_grade` を、`numbers.py` は `numbers.tolerance` を読む。品質基準で決めた値を `config.yaml` にも書く。
- **書き出す前に合意を取る。** 自動モード（`--auto`）では §5 の規則で決めて記録する。
- ドキュメントは日本語で書く。

## 1. 引数と入出力

```text
$ARGUMENTS
```

| 入力 | 用途 |
|---|---|
| `.researchkit/memory/constitution.md` | 出典の等級、確度の付け方、引用、数値、倫理、AI の開示 |
| `docs/method.md` | 手法、情報源の見込みの等級、分析環境（再現性の水準に効く） |
| `.researchkit/config.yaml` | `sources.min_grade`、`numbers.tolerance`、`confidence.levels`、`commands` |
| `docs/concept/seed.md`、`premises.md` | 読み手と決めたいこと（D1〜）、RP1（読み手）、RP4（期限）、RP7（要求する確度）、RP8（成果物の形式）、RP9（倫理と個人情報）、RP10（利害関係）、RP11（言語） |
| `docs/questions/*.md`、`README.md`、`spec_order.md` | RQ の一覧、手法、`[人]` の見込み |
| `docs/questions/000-*.md` | 共通基盤の範囲（検索ログの形式、分析環境） |

| 出力 | 様式 |
|---|---|
| `docs/quality.md` | [templates/quality.md](./templates/quality.md) |
| `docs/questions/999-research-report.md` | [templates/999-research-report.md](./templates/999-research-report.md)（CONTRACT の RQ の概要の書式。区分は `統合`） |
| `docs/questions/README.md`、`spec_order.md` | 999 の行を最後に足す（`researchkit-questions` の様式） |
| `.researchkit/config.yaml` | `sources.min_grade`、`numbers.tolerance` |
| `.researchkit/memory/constitution.md` | `docs/quality.md` を参照する条項がなければ、`researchkit-constitution` の改訂の手順で足す |

終わったら、`researchkit-bootstrap` の記録の形で R11 を記録する（`docs(bootstrap): R11 品質基準と最終成果物を定義`、trailer `Researchkit-Bootstrap: R11`）。単独で実行したときも記録する。更新モードで直しただけのときは、`docs(quality): <変更の要約>` の通常のコミットにする。

`docs/quality.md` か `999-*` がすでにある場合は、**更新モード**として §4 に従う。**`docs/questions/` にすでに `999-*` がある場合**は、新しく作らず、その名前のまま使う。以下の `999-research-report` は、その名前に読み替える。`999-*` が複数あるときは、どれを統合報告にするかをユーザーに確かめる（自動モードでは止まる）。

## 2. 手順

### ステップ 1: 読み込み

入力を読み、次を整理する。

- 手法と情報源の制約（公開の情報だけか、査読つきの文献がどれだけ期待できるか、データの分析をスクリプトで再実行できるか）
- 読み手と決定（誰が、何を、いつ決めるか。求める確度）
- 成果物の希望（RP8）、言語（RP11）、期限（RP4）
- 倫理と利害関係（RP9、RP10）

### ステップ 2: ヒアリング

次の区分ごとに、決まっていないものを AskUserQuestion で聞く。1 ラウンド最大 4 問、推奨案を先頭に置く。推奨案は、憲章と手法で達成できる値にする。

| 区分 | ID の接頭辞 | 決めること（例） |
|---|---|---|
| 出典 | `QS-SR` | 主張の根拠に使える最低の等級（`sources.min_grade`）、結論に使う主張に等級 A を求めるか、参照日の鮮度 |
| 主張と確度 | `QS-CL` | 主張ごとの最低の根拠の数、結論（統合報告の要約）に要る確度、届かないときの扱い、反証・限界の欄 |
| 再現性 | `QS-RP` | 再現性の水準（下の表）、数値の参照の範囲、許容差（`numbers.tolerance`） |
| レビュー | `QS-RV` | レビューの軸（5 軸、Ethics を足すか）、合格条件、専門家の確認（`[人]`）の要否 |
| 検索ログ | `QS-SL` | 必須の項目、見つからなかった検索、反対の証拠を探した検索、文献レビューの PRISMA 2020 の件数 |
| 倫理 | `QS-ET` | 同意と匿名化の記録、利用規約の確認、AI の利用の開示（憲章の条項の確かめ方） |
| 最終成果物 | （999） | 読み手、形式（レポート／スライド／論文形式／1 枚の要約）、構成、言語、分量、締切、公開の範囲と配布の方法 |

再現性の水準は、次の 3 段階から選ぶ。

| 水準 | 内容 | 向いている調査 |
|---|---|---|
| L1 記録 | 報告の数値に、出典 ID か `{N:...}` が付いている。手で計算した数値は計算式と入力が表にある | デスクリサーチ中心、期限が短い |
| L2 再実行 | L1 に加え、分析の数値を、生データからスクリプトで再生成でき、許容差の範囲で同じ値になる | データ分析を含む（既定） |
| L3 固定 | L2 に加え、依存の版を固定し（`uv.lock`、`renv.lock`）、生データのハッシュが目録と一致し、別の環境（別の人の端末や CI）で再実行して同じ値になる | 外部に公開する、後から検証される |

- 憲章の確度の付け方と重なる項目（「確実」に要る根拠の数など）は、憲章を正とし、`docs/quality.md` には最低の水準（「結論に使う主張は、可能性が高い以上」など）だけを書く。
- 000 と重なる項目（検索ログの形式、分析環境）は、000 を仕組みとし、`docs/quality.md` には基準（必須の項目、再現性の水準）だけを書く。

### ステップ 3: 品質基準と統合報告への仕分け

- **品質基準（`docs/quality.md`）**: 各 RQ と統合報告が守る基準。例: 「主張の根拠は等級 C 以上」「結論に使う主張は可能性が高い以上」「分析の数値は L2」
- **統合報告（`999-research-report.md`）**: 1 回作れば調査全体に効く成果物。例:
  - 読み手と、読み手が決めること（D1〜）
  - 形式と構成（エグゼクティブサマリー、背景と決定、方法、結果、結論と確度、限界、次の問い、付録）
  - 言語、分量、締切、公開の範囲と配布の方法（公開の判断は `[人]`）
  - AI の利用と利害関係の開示（憲章の 6・7）

### ステップ 4: 書き出し案の提示と合意

次をまとめて示し、承認を得る。

1. `docs/quality.md` の基準の一覧（ID、区分、各 RQ の値、統合報告の値、確かめ方）
2. `config.yaml` に書く値（`sources.min_grade`、`numbers.tolerance`）
3. `999-research-report.md` の要点（読み手、形式、構成、言語、分量、締切、公開の範囲）と、そのうち `[人]` になる作業
4. 今の憲章と手法では達成できない基準（あれば）と、その対応

### ステップ 5: 書き出し

- `docs/quality.md` を [templates/quality.md](./templates/quality.md) に沿って書く。対象外の区分（定性調査がないときの同意の記録など）は「対象外」と書いて残す。
- `config.yaml` の `sources.min_grade` と `numbers.tolerance` を、決めた値に直す。
- `999-research-report.md` を [templates/999-research-report.md](./templates/999-research-report.md) に沿って書く。ヘッダは `**状態**: 未着手 | **区分**: 統合 | **想定順序**: 999 | **依存**: 000-research-foundation | **手法**: <ほかの RQ で使う手法>` とする（000 がなければ依存は `—`）。ほかのすべての RQ の完了は `worktree_helper.py` が前提として確かめるので、`**依存**` に列挙しない。
- `README.md` の一覧と `spec_order.md` の最後に 999 の行を足す。
- 憲章に `docs/quality.md` を参照する条項がなければ、`researchkit-constitution` の改訂の手順で足す（例: 「すべての RQ は docs/quality.md の品質基準を満たす。researchkit-analyze と researchkit-review で確かめる」）。`researchkit-constitution` のテンプレートから作った憲章には、この条項（K-8-1）がすでにある。自動モードでは憲章を改訂せず、足す提案を `docs/auto-decisions.md` に記録する。

### ステップ 6: 検証

```bash
python3 <skills>/researchkit-questions/scripts/validate.py docs/questions
$CHECK --all
```

`<skills>` は、このスキルが置かれた skills ディレクトリである。エラーが 0 件になるまで直す（`min_grade` を上げたことで既存の出典にエラーが出たら、報告する）。

### ステップ 7: 報告と記録

- `docs/quality.md` の基準の件数（区分ごと）と、主な値（最低の等級、結論に要る確度、再現性の水準、レビューの合格条件）
- `config.yaml` に書いた値
- `999-research-report.md` の要点と、`[人]` の作業
- 今の憲章と手法では達成できない基準（あれば）と、その対応
- 次の手順の案内（R12 の全体の検証。`researchkit-bootstrap` の中で実行している場合は、その手順に戻る）

最後に §1 の形で R11 を記録する。

## 3. 記述の規則

- `docs/quality.md` の各基準には、ID、各 RQ の値、統合報告の値、確かめ方を書く。確かめ方が人の判断だけのものは「（[人]）」と書く。
- 999 には、成果物の「何が要るか」を書き、作り方（`build_pptx.py` などの道具、文章の書き方）は `researchkit-synthesize` と `researchkit-publish` に従う。
- 特定の RQ にだけ効く基準（ある RQ だけ等級 A を求めるなど）は、その RQ の `spec.md` の「判定の基準」で決める。`docs/quality.md` には全体の既定値を書く。

## 4. 更新モード

- `docs/quality.md` を変えるときは、差分と影響（すでに `完了` の RQ が新しい基準を満たすか、`config.yaml` のどの値が変わるか）を示し、合意した変更だけを反映する。「変更履歴」に日付、内容、理由を足す。基準を厳しくしたときは、`$CHECK --all` で新しいエラーが出る RQ を挙げる。
- `999-*` が `設計済み` 以降なら、書き換えない。読み手や形式の変更は、999 の `spec.md` を `researchkit-clarify` で直すよう案内する。

## 5. 自動モード（`--auto`）

| 論点 | 自動モードでの動作 |
|---|---|
| 出典 | `min_grade` は `C`（既定のまま）。結論に使う主張は、等級 A か B の根拠を 1 件以上含む |
| 主張と確度 | 主張ごとに根拠 1 件以上。統合報告の結論は「可能性が高い」以上。届かない結論は、確度を明示して「残った問い」に回す |
| 再現性 | データ分析を含むなら L2、含まないなら L1。`numbers.tolerance` は既定のまま |
| レビュー | 5 軸（定性調査かデータ分析を含むなら Ethics を足す）。2 回目のレビューで CRITICAL と HIGH の未解決が 0 件、`check.py` と `numbers.py` のエラーが 0 件 |
| 最終成果物 | 読み手と形式は premises（RP1、RP8）から採る。根拠がなければ、Markdown のレポート（エグゼクティブサマリーつき）、言語は RP11、分量は本文 10 ページ相当まで、締切は RP4 |
| 公開の範囲 | 決めない。公開の判断を `[人]` の作業にする |
| `999-*` が複数ある | 止まる |

自動で決めたことは `docs/auto-decisions.md` に記録する（`researchkit-bootstrap` の書き方）。結論に要る確度、再現性の水準、読み手と形式は、見直しの優先度を「高」にする。

## 6. 禁止事項

- 憲章と手法で達成できない基準を、注記なしに書くこと
- 測れない形（「信頼できる」「十分に」）で基準を書くこと
- 憲章の確度の付け方より緩い基準を書くこと（憲章が上位である）
- `config.yaml` の `sources.min_grade` と `numbers.tolerance` を、品質基準と食い違ったままにすること
- 公開の判断を AI が行うこと
- ユーザーの合意なしに書き出す、または上書きすること（自動モードを除く）
- 状態が `設計済み` 以降の RQ のファイルを書き換えること（例外: `researchkit-findings` の逆流で、ファイルの末尾の `## 上流からの変更` の節に追記することだけは許す）、既存の `999-*` を消す・名前を変えること
