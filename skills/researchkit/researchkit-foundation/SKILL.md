---
name: "researchkit-foundation"
description: "調査の中身以外の共通の仕組み（出典台帳 sources/ の運用、用語集 docs/glossary.md、データの目録 data/manifest.md と生データの置き場所、分析環境のセットアップ、検索ログ search-log.md の形式、共通の出典 S000-）の要件を docs/questions/000-research-foundation.md に定義するスキル。docs/method.md、憲章、docs/scan/wide.md をもとに範囲をヒアリングで決め、000 の RQ の工程で何をするか（Q8 で整える、Q9 で分析環境の動作を確かめる、Q10 で残作業をまとめる。主張は作らない）を書く。spec_order.md の先頭への追加と各 RQ の依存の更新まで行う。用語集・目録・検索ログのテンプレートを持ち、000 の収集（researchkit-collect）と各 RQ の検索ログがそれを使う。researchkit-bootstrap の R10 から使われるほか、「共通基盤を定義して」「出典台帳や用語集の決まりをまとめて」「000 を作って」と言われたとき、または /researchkit-foundation と打たれたときに使う。"
argument-hint: "[--auto] [追加の希望（例: 用語集に英訳も載せたい、R の環境も用意したい）]"
compatibility: "Requires docs/questions/ (researchkit-questions output), docs/method.md and .researchkit/memory/constitution.md"
user-invocable: true
disable-model-invocation: false
---

# researchkit-foundation スキル（R10: 共通基盤 → 000-research-foundation）

調査の中身（問いへの答え）以外の、すべての RQ が使う仕組みの要件を、1 つの RQ の概要 `docs/questions/000-research-foundation.md` にまとめる。`000` は予約番号であり、すべての RQ より先に進める。speckit と gamekit の「共通基盤」（000）に当たる。

パスは `.researchkit/config.yaml` の `paths` で読み替える（以下は既定のパス）。

## 0. 大原則

- **調査の中身を持ち込まない。** ここに入れるのは、どの RQ でもほぼ同じ形で要る仕組みだけである。問いへの答え、仮説の検証、主張は、それぞれの RQ に残す。000 は主張を作らない（steering の「RQ の工程」）。
- **手法の選定はしない。** 手法と分析環境は `docs/method.md` に、出典の等級や引用の規則は憲章に従う。ここでは「何がそろっていればよいか」と「どう運用するか」を書く。
- **AI が確かめられる基盤にする。** 出典台帳の必須項目（`check.py`）、分析のスクリプトの実行（`commands.analysis`）、数値の突き合わせ（`numbers.py`）、データのハッシュは、後の RQ の検証の前提になる。000 で動くことを確かめる。
- **根拠のないものは入れない。** 根拠にしてよいのは、`docs/method.md`、憲章、`docs/scan/wide.md`（用語、データの所在）、`docs/questions/` の各 RQ の「想定する情報源」、ユーザーの回答である。
- **書き出す前に合意を取る。** 自動モード（`--auto`）では §6 の規則で決めて記録する。
- **記述の粒度は `researchkit-questions` と同じ**（広く浅く）。検索式、個々の用語の定義、具体的なデータの中身は書かない。それは 000 の `spec.md` 以降と、各 RQ で決める。
- ドキュメントは日本語で書く。

## 1. 引数と入出力

```text
$ARGUMENTS
```

| 入力 | 用途 |
|---|---|
| `docs/method.md` | 手法、データ源、分析環境、`commands`、大きなデータの扱い、定性調査の体制 |
| `.researchkit/memory/constitution.md` | 出典の等級、引用、数値、倫理と個人情報の条項 |
| `.researchkit/config.yaml` | `paths`、`commands`、`data.max_file_mb`、`sources` |
| `docs/scan/wide.md` | 用語の候補、データの所在、複数の RQ が使いそうな基本の資料 |
| `docs/questions/*.md`、`README.md`、`spec_order.md` | 各 RQ の手法、想定する情報源、依存 |
| `docs/concept/premises.md` | RP3（範囲）、RP6（使えるデータとアクセス）、RP9（倫理と個人情報）、RP11（言語） |

| 出力 | 内容 |
|---|---|
| `docs/questions/000-research-foundation.md` | 共通基盤の RQ の概要。様式は [templates/000-research-foundation.md](./templates/000-research-foundation.md)（CONTRACT の RQ の概要の書式。区分は `基盤`） |
| `docs/questions/README.md` | 一覧の先頭に 000 の行を足す（`researchkit-questions` の様式） |
| `docs/questions/spec_order.md` | 先頭に 000 の行を足す（`researchkit-questions` の様式） |
| 各 RQ のファイル（状態が「未着手」のもの） | `**依存**` に `000-research-foundation` を足す |

このスキルは `docs/glossary.md`、`data/manifest.md`、`search-log.md` を作らない。それらは 000 の Q8（`researchkit-collect`）で、次のテンプレートから作る。

| テンプレート | 作る場所 | 作る時期 |
|---|---|---|
| [templates/glossary.md](./templates/glossary.md) | `docs/glossary.md` | 000 の Q8 |
| [templates/manifest.md](./templates/manifest.md) | `data/manifest.md` | 000 の Q8 |
| [templates/search-log.md](./templates/search-log.md) | `studies/<NNN-name>/search-log.md` | 各 RQ の Q8 の最初（000 を含む） |

終わったら、`researchkit-bootstrap` の記録の形で R10 を記録する（`docs(bootstrap): R10 共通基盤を定義`、trailer `Researchkit-Bootstrap: R10`）。単独で実行したときも記録する。更新モードで 000 を直しただけのときは、`docs(questions): 000 を更新` の通常のコミットにする。

**`docs/questions/` にすでに `000-*` がある場合**は、新しく作らず、その名前のまま**更新モード**（§4）で使う。以下の `000-research-foundation` は、その名前に読み替える。`000-*` が複数あるときは、どれを共通基盤にするかをユーザーに確かめる（自動モードでは止まる）。

## 2. 手順

### ステップ 1: 候補の洗い出し

入力から候補を洗い出し、次の一覧で漏れがないかも確かめる。

| 区分 | 候補 |
|---|---|
| 出典台帳 | `sources/` の運用（1 件 1 ファイル、ID の採番 `$RK sources next`、フロントマターの必須項目、`used_in` の更新、並行で集めるときの ID の範囲の分け方、実在の確かめ方と `verified_by` の書き方）、共通の出典（`S000-`。複数の RQ が使う基本の統計・文献・定義の資料）の初期の登録 |
| 用語集 | `docs/glossary.md` の作成、初期の用語（`docs/scan/wide.md` と各 RQ の問いに出る用語）、表記の統一、英語の対訳（検索語に使う）、用語を足す手順（RQ の Q3〜Q4 で定義した用語を戻す） |
| データの目録 | `data/manifest.md` の作成、`data/raw/` と `data/large/` の置き場所、加工しない規則、SHA-256 のハッシュ、`data/large/` の保管場所（リポジトリの外）と入手の方法、`.gitignore` |
| 分析環境 | `docs/method.md` の分析環境の導入（`uv` か R、`pyproject.toml` と `uv.lock`、`renv.lock`）、`commands.analysis` と `commands.test` が動くこと、スクリプトと出力の置き方（`analysis/`、`out/*.json`、`fig/`）、乱数のシード |
| 検索ログ | `search-log.md` の形式（必須の項目、見つからなかった検索の書き方、文献レビューの PRISMA 2020 の件数、引用をたどった記録） |
| 証拠の置き方 | `studies/<NNN>/evidence/` の抜き書きの書き方（原文、出典 ID、頁・表、取得日） |
| 定性調査（ある場合） | 同意書とインタビューガイドのひな形の置き場所、対象者の記号（`P01`）の振り方、対応表と録音をリポジトリの外に置く場所（`[人]`） |
| 検証 | `$RK doctor`、`$CHECK --all`、`$NUM --all` がエラーなく通ること、Web 検索のフック（`$RK hooks install`）が入っていること |

### ステップ 2: 範囲のヒアリング

AskUserQuestion で、決まっていないものを聞く。1 ラウンド最大 4 問、推奨案を先頭に置く。

- 用語集の初期の範囲（`wide.md` の主要な用語だけ / 各 RQ の問いの用語まで）と、英語の対訳を載せるか
- 共通の出典（`S000-`）として先に登録するもの（例: 複数の RQ が使う公的統計、定義の資料）
- `data/large/` の保管場所（共有ドライブ、クラウドのストレージ）と、入手の方法
- 分析環境の導入を AI が行うか、`[人]` が行うか（`uv` や R がまだ入っていない場合）

- 各 RQ の「想定する情報源」から必要と判断できるものは、根拠（RQ の番号）を添えて推奨する。
- 出典台帳の運用、検索ログの形式、分析環境の動作の確認は、必ず 000 に入れる（§0）。
- 後でよいもの（例: 引用文献の管理ツールとの連携）は `docs/concept/backlog.md` に足す。

### ステップ 3: 大きさの確認

000 は、1 つの RQ の工程（Q2〜Q13）を 1 回で通せる大きさにする。共通の出典の登録が多い（目安として 20 件を超える）場合や、大きなデータの入手に時間がかかる場合は、その部分を通常の番号の RQ（既存の最大値の次から。区分は `補助`）に分け、`000-research-foundation` に依存させる。分け方を示し、合意を取る。

### ステップ 4: 書き出し案の提示と合意

次をまとめて示し、承認を得る。

1. 000 の主な要求（区分ごと）と、Q8・Q9・Q10 で行うこと
2. スコープ外にするもの（各 RQ に残すもの、後で入れるもの）
3. `[人]` になる作業の見込み（分析環境の導入、`data/large/` の保管場所の用意、同意書のひな形の確認など）
4. 依存に `000-research-foundation` を足す RQ の一覧
5. 分けた RQ がある場合は、その一覧

### ステップ 5: 書き出し

- `000-research-foundation.md` を [templates/000-research-foundation.md](./templates/000-research-foundation.md) に沿って書く。ヘッダは `**状態**: 未着手 | **区分**: 基盤 | **想定順序**: 0 | **依存**: — | **手法**: <docs/method.md で採用した手法>` とする。`**手法**` には、000 が環境を整える手法（`docs/method.md` で採用したもの）をすべて書く。
- `## つながる決定` と `## つながる仮説` には「—（共通基盤。すべての RQ を支える）」と書く（`validate.py` は 000 を決定とのつながりの検査から外す）。
- `README.md`、`spec_order.md`、各 RQ の依存を、§1 の表どおりに更新する。状態が `設計済み` 以降の RQ は変更せず、影響があれば報告する。

### ステップ 6: 検証

```bash
python3 <skills>/researchkit-questions/scripts/validate.py docs/questions
```

`<skills>` は、このスキルが置かれた skills ディレクトリである。エラーが 0 件になるまで直す。000 に依存していない RQ の警告は、意図どおりなら理由を報告に書く。

### ステップ 7: 報告と記録

- 000 に入れた仕組みと、スコープ外にしたもの
- 000 の Q8・Q9・Q10 で行うことと、`[人]` の作業の見込み
- 更新したファイルと、依存を足した RQ
- 検証の結果
- 次の手順の案内（R11 `researchkit-deliverable`。`researchkit-bootstrap` の中で実行している場合は、その手順に戻る）

最後に §1 の形で R10 を記録する。

## 3. 000 の RQ の工程で行うこと

000 は、通常の RQ と同じく `researchkit-question` と `researchkit-execute`（または `researchkit-all`）で進める。中身は次のとおりである（steering の「RQ の工程」）。000 の概要ファイルの「工程ごとの作業」にも書く。

| ステップ | 行うこと | 確かめ方 |
|---|---|---|
| Q2〜Q7 | 共通基盤の仕様（何がそろえば完了か）と、作業の計画とタスク | — |
| Q8（収集） | `docs/glossary.md`、`data/manifest.md` をテンプレートから作る。初期の用語を載せる。共通の出典を `S000-` で登録し、実在を確かめる。`data/` の置き場所と `.gitignore` を整える。分析環境を導入する（`pyproject.toml` と `uv.lock`、または `renv.lock`）。000 自身の `search-log.md` を作る | `$CHECK --all` のエラーが 0 件 |
| Q9（分析） | 分析環境が動くことを確かめる。`studies/000-research-foundation/analysis/` に小さな確認用のスクリプト（ライブラリを読み込み、既知の値を `out/smoke.json` に出す）を置き、`commands.analysis` で実行する。`commands.test` があれば実行する | スクリプトが成功し、`out/smoke.json` の値が期待どおり。`$RK doctor` に ERROR がない |
| Q10（まとめ） | 主張は作らない。`findings.md` には、そろえたもの、確かめた結果、残作業（`[人]` を含む）を書く。各 RQ への申し送り（用語集と目録の使い方、ID の範囲の分け方）を書く | `tasks.md` の `[人]` 以外がすべて `- [x]` |
| Q11〜Q12（レビュー） | Source 軸（共通の出典の実在と等級）、Numbers 軸（確認用のスクリプトの再実行）を中心に見る。主張がないので、Logic・Counter 軸は形式の確認にとどめる | レビューの記録 |

## 4. 更新モード

`000-*` がすでにある場合は、次のように進める。

- 状態が「未着手」なら、§2 ステップ 1 の一覧で足りないものを洗い出し、追加・変更の差分案を示して、承認されたものだけ反映する。
- 状態が `設計済み` 以降なら、000 は書き換えない。足りないものは、通常の番号の新しい RQ（区分 `補助`）として提案する。
- 用語集、目録、検索ログの形式を変えたいときは、テンプレートではなく、各ファイル（`docs/glossary.md` など）の冒頭の説明を直す。すでに書かれた検索ログは書き換えない。

## 5. 既存の調査

既存の調査に、すでに出典の一覧、用語集、データのフォルダ、分析のスクリプトがある場合は、000 の「範囲」に、それぞれの場所と、researchkit の形式（1 件 1 ファイルの出典、目録とハッシュ、`out/*.json`）との差を書く。移し替えは 000 の Q8 で行い、元のファイルは動かさない・消さない。

## 6. 自動モード（`--auto`）

| 論点 | 自動モードでの動作 |
|---|---|
| 範囲のヒアリング | 出典台帳の運用、用語集（`wide.md` の主要な用語）、データの目録、分析環境、検索ログの形式を入れる。英語の対訳は、文献レビューを含むときだけ載せる。共通の出典は、2 つ以上の RQ の「想定する情報源」に出るものだけにする |
| 分析環境の導入 | `uv` や R がなければ、導入を `[人]` のタスクにする |
| `data/large/` の保管場所 | 決めずに `[人]` のタスクにする（大きなデータがない場合は「対象外」） |
| 分け方、書き出しの合意 | 推奨案のまま進める |
| `000-*` が複数ある | 止まる |

自動で決めたことは `docs/auto-decisions.md` に記録する（`researchkit-bootstrap` の書き方）。

## 7. 禁止事項

- 調査の中身（問いへの答え、仮説の検証、主張）を 000 に入れること
- 手法や分析環境の選定を 000 に書くこと（`docs/method.md` に従う）
- ユーザーの合意なしに書き出す、または上書きすること（自動モードを除く）
- 状態が `設計済み` 以降の RQ のファイルを書き換えること
- 既存の RQ の番号を振り直すこと、既存の `000-*` を消す・名前を変えること
- このスキルで `docs/glossary.md`、`data/manifest.md`、出典を作ること（000 の Q8 で行う）
