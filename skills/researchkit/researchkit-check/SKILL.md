---
name: "researchkit-check"
description: "調査の成果物を機械で検証するスキル。同梱の check.py で、主張の表（findings.md、統合報告 reports/report.md、任意の文書）の根拠の欄の出典 ID・主張 ID が実在するか、根拠が最低等級（sources.min_grade）を満たすか、確度が憲章の段階（confidence.levels）にあるか、出典台帳（sources/）の必須項目・ID・DOI の書式・参照日・使われていない出典・used_in の食い違いを検査し、--online で URL と DOI の到達性も確かめる。numbers.py で、本文の数値と分析の出力（JSON）を {N:<path>#<key>} の参照で突き合わせる。ERROR が 0 件になるまで直す。RQ の工程の Q8・Q10〜Q12、調査全体の工程の R12、統合報告の検証から使われる。「出典をチェックして」「数値を突き合わせて」「根拠の参照を検証して」「報告書を機械でチェックして」と言われたとき、または /researchkit-check と打たれたときに使う。"
argument-hint: "[--rq <NNN> | --all | --file <path>] [--online] [--strict] [--numbers-only | --sources-only]"
compatibility: "Requires Python 3.9+. Uses .researchkit/config.yaml, sources/, studies/<NNN-name>/findings.md, reports/report.md"
user-invocable: true
disable-model-invocation: false
---

# researchkit-check スキル（機械検証: 出典の参照と数値の突き合わせ）

読んで判断する前に、機械で判定できる食い違いを取り除く。**ERROR は直す。WARN は内容を確かめ、意図どおりなら報告に書く。**

このスキルが確かめるのは「書いたものどうしが対応しているか」までである。出典の中身が主張を本当に支えるか、引用が原文と一致するか、反対の証拠を探したかは、`researchkit-review` の 5 軸（Source・Logic・Counter・Bias・Numbers）で人の目と同じように読んで確かめる。

パスは既定の配置で書いている。`.researchkit/config.yaml` の `paths` で読み替える。`$CHECK`、`$NUM` の意味は steering（`.kiro/steering/research.md`）の「エージェントの行動規範」のとおりである。

## 1. 引数

```text
$ARGUMENTS
```

| 指定 | 対象 |
|---|---|
| なし、または `--all` | すべての RQ の `findings.md`、`reports/report.md`（あれば）、すべての出典 |
| `--rq <NNN>` | `studies/<NNN>-*/findings.md` と、その RQ の出典（`S<NNN>-*` と、`used_in` か参照にその RQ を含むもの） |
| `--file <path>` | 任意の文書（統合報告、公開前の資料、`analysis/` のメモなど）と、そこで参照した出典 |
| `--online` | URL と DOI の到達性も確かめる（`check.py` だけ） |
| `--strict` | WARN があっても終了コード 1 にする（`check.py` だけ） |
| `--numbers-only` / `--sources-only` | `numbers.py` だけ / `check.py` だけを実行する（このスキルの指定。スクリプトには渡さない） |

worktree の中で呼ばれたときは、worktree のディレクトリで実行する（`.researchkit/config.yaml` を上へ探してルートを決める）。

## 2. 実行

```bash
$CHECK [--rq <NNN> | --all] [--file <path>] [--online] [--strict]
$NUM   [--rq <NNN> | --all] [--file <path>]
```

`$CHECK` は `python3 <skills>/researchkit-check/scripts/check.py`、`$NUM` は `python3 <skills>/researchkit-check/scripts/numbers.py` である。どちらも 1 行 1 件 `ERROR|WARN <file>:<line> <code> <説明>` と、最後に `SUMMARY: errors=<n> warnings=<n>` を出す（`numbers.py` は `checked=<突き合わせた数> calc=<{N:calc} の数>` も続ける）。ERROR があれば終了コード 1。

### 2.1 `check.py`（出典の参照と出典台帳）

主張の表は steering の「主張の書式」の表（`| ID | 主張 | 根拠 | 確度 | 反証・限界 |`）である。見出しに `ID`・`主張`・`根拠`・`確度` の列を持つ表だけを読む。

| コード | 水準 | 意味と直し方 |
|---|---|---|
| `NO_EVIDENCE` | ERROR | 根拠の欄が空。出典 ID か主張 ID を書く。根拠がなければ、主張にせず確度 `不明` の問いとして「残った問い」に回す |
| `UNKNOWN_SOURCE` | ERROR | 出典台帳にない出典 ID（根拠の欄、本文のどちらでも）。ID の打ち間違いを直すか、`researchkit-collect` の手順で登録する。**存在しない出典を作って埋めない** |
| `UNKNOWN_CLAIM` | ERROR | 根拠の主張 ID（同じ文書の `C<n>`、統合報告の `<NNN>-C<n>`）がない。統合報告では、RQ の `studies/<NNN>-*/findings.md` の ID を確かめる |
| `SELF_CLAIM`、`DUP_CLAIM` | ERROR | 主張が自分を根拠にしている。主張の ID が重複している |
| `LOW_GRADE` | ERROR | 根拠が、最低等級（`sources.min_grade`。品質基準で決める）未満の出典だけ。等級の高い出典を足すか、確度を下げて主張を弱めるか、主張をやめる |
| `BAD_CONFIDENCE` | ERROR | 確度が `confidence.levels`（憲章の段階）にない |
| `SOURCE_NO_FRONTMATTER`、`SOURCE_MISSING_FIELD` | ERROR | 出典のフロントマターがない、必須の項目（`id`、`type`、`title`、`accessed`、`grade`、`url`・`doi`・書誌〈`author` と `publisher`〉のどれか）がない |
| `SOURCE_ID_MISMATCH`、`SOURCE_ID_FORMAT`、`SOURCE_BAD_GRADE` | ERROR | `id` とファイル名が違う、`id` が `S<NNN>-<NNNN>` でない、等級が `sources.grades` にない |
| `UNUSED_SOURCE` | WARN | どの RQ（`studies/<NNN>-*/` の文書）からも統合報告（`reports/`）からも参照されていない |
| `USED_IN_MISMATCH` | WARN | `used_in` と実際に参照している RQ が食い違う（統合報告からの参照は `999` として数える）。`used_in` を直す |
| `BAD_DOI`、`BAD_DATE`、`SOURCE_BAD_TYPE` | WARN | DOI が `10.<登録者>/<番号>` の形でない、参照日が `YYYY-MM-DD` でないか未来、`type` が steering の値にない |
| `STALE_ACCESS` | WARN | 参照日が 1 年以上前。ページが変わっていないか確かめ、確かめたら参照日を更新する |
| `GRADE_D` | WARN | 等級 `D`（未確認）の出典がある。根拠に使っていないことを確かめる |
| `UNREACHABLE` | WARN | `--online` で URL か DOI に到達できない。ページの移転なら URL を直し、消えたならアーカイブの URL を足すか等級を見直す |
| `NO_CLAIM_TABLE` | WARN | `findings.md` に主張の表がない（`000` を除く） |

- 新しい出典ファイルは [templates/source.md](./templates/source.md) の形で書く（steering の「出典台帳」の項目どおり）。ID は `$RK sources next <NNN>` で取る。
- `--online` は時間がかかり、サイトによっては機械からの接続を断る（403 など）。WARN が出たら、ブラウザで開けるかを確かめてから扱いを決める。`sources.check_online: true` なら、`--online` を付けなくても確かめる。

### 2.2 `numbers.py`（数値の突き合わせ）

steering の「数値の参照」のとおり、分析の出力から得た数値の直後に `{N:<path>#<key>}` を付ける。

- `<path>` は、RQ の中の文書（`studies/<NNN>-*/` の下）では RQ のディレクトリから、それ以外（統合報告など）ではリポジトリのルートからの相対パスである。`<key>` はドット区切り（配列は添字。例: `by_year.1.n`）。
- 突き合わせるのは、参照の直前の同じ行にある最後の数値である。数値と参照の間には、単位（`億円`、`件`、`人`）だけを置ける。
- 数値の書式は `1,234`、`12.3%`、`1.2万`、`3億`、`-0.5` を読む（全角の数字も読む）。`万`・`億`・`兆`・`千` の付いた数値は、JSON の値が単位込み（`123400000000`）でも、その単位で数えた値（`1234`）でも一致とみなす。`%` は、JSON の値が 0〜1 なら 100 倍して比べる。
- 一致の判定は、相対の差が `numbers.tolerance`（既定 0.5%）以内か、JSON の値を表示の桁数で丸めると表示の数値になることである。
- `{N:calc}` は手で計算した数値の印で、突き合わせない。同じ文書の「計算」の節に、計算式と入力の表を書く（節がなければ `NO_CALC_SECTION` の WARN）。

| コード | 水準 | 意味と直し方 |
|---|---|---|
| `MISMATCH` | ERROR | 文書の数値と JSON の値が合わない。**文書を出力に合わせて直す**。出力が誤っているなら、分析のスクリプトを直して再実行する（出力の JSON を手で書き換えない） |
| `MISSING_FILE`、`BAD_JSON` | ERROR | 出力のファイルがない・読めない。`commands.analysis` で分析のスクリプトを再実行する |
| `MISSING_KEY`、`NOT_NUMBER` | ERROR | キーがない、値が数値でない。キーの綴りか、出力の形を直す |
| `NO_NUMBER`、`BAD_REF` | ERROR | 参照の直前に数値がない、参照の書式が違う |
| `NO_CALC_SECTION` | WARN | `{N:calc}` があるのに「計算」の節がない |

## 3. 手順

1. 場面に合わせて範囲を決める。

   | 場面 | 実行するもの |
   |---|---|
   | Q8（収集の後） | `$CHECK --rq <NNN>`。出典ファイルの ERROR を 0 件にする。主張はまだないので `UNUSED_SOURCE` は残ってよい |
   | Q9（分析の途中） | `$NUM --file studies/<NNN>-<slug>/analysis/<文書>.md` |
   | Q10〜Q12（主張のまとめとレビュー） | `$CHECK --rq <NNN>` と `$NUM --rq <NNN>` |
   | 999 の Q8・Q10（統合報告） | `$CHECK --file reports/report.md` と `$NUM --file reports/report.md` |
   | R12（調査全体の検証） | `$CHECK --all`（`validate.py` と合わせて。`researchkit-bootstrap` §4） |
   | 公開の前 | `$CHECK --all --online` |

2. 実行し、ERROR を 1 件ずつ直す。
   - 直す側を間違えない。出典 ID の誤りは文書を、出典ファイルの欠けは出典ファイルを、数値の不一致は文書（出力が誤りなら分析のスクリプト）を直す。
   - **ERROR を消すために事実を作らない。** 出典がない主張は、出典を探すか、主張をやめるか、確度 `不明` の残った問いにする。数値を出力に合わせられないなら、その数値を書かない。
   - 主張を弱めたり消したりしたら、統合報告や `hypotheses.md` がその主張に頼っていないかを確かめる（steering の原則 10「逆流」）。
3. もう一度実行し、ERROR が 0 件になるまで繰り返す。同じ原因で 3 回直しても 0 件にならなければ、止まって報告する（自動モードでも止まる）。
4. WARN を種類ごとにまとめ、直すもの・意図どおりのものに分ける。
   - **通常モード**: 分け方を示して確かめる。
   - **自動モード**: 直すもの（`used_in`、DOI の書式、参照日）は直す。意図どおりとしたもの（R2・R6 で登録したまだ使っていない `S000-*` の出典など）は、理由を `auto-decisions.md` に書く（RQ の工程では `studies/<NNN>-<slug>/auto-decisions.md`、それ以外は `docs/auto-decisions.md`）。

## 4. 完了報告

- 実行したコマンドと、ERROR・WARN の件数（`numbers.py` は突き合わせた件数と `{N:calc}` の件数も）
- 直したもの、意図どおりとした WARN とその理由
- 主張を弱めた・消したものと、逆流で直した文書
- 次の案内: 呼び出し元の工程に戻る。単独で実行したときは、主張の中身の検証に `researchkit-review` を案内する

## 5. 禁止事項

- ERROR を消すために、出典ファイル・出典 ID・数値・分析の出力を作ったり書き換えたりすること
- 等級 `D` の出典の等級を、確かめずに上げること
- 確度の段階（`confidence.levels`）や最低等級（`sources.min_grade`）、許容差（`numbers.tolerance`）を、エラーを消すために変えること（変えるのは憲章と品質基準の変更として `researchkit-constitution`・`researchkit-deliverable` で行う）
