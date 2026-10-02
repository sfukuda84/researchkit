# 問いの候補帳（backlog）

採らなかった案（問いの立て方の比較、壁打ち、仮説づくり、予備調査、RQ の途中で出た問い）と、`docs/questions/` にまだ RQ にしていない問いの候補を置く場所。`researchkit-sparring` が作り、`researchkit-framing`・`researchkit-hypothesis`・`researchkit-pilot`・`researchkit-questions`・`researchkit-findings`・`researchkit-synthesize` が足す。
`researchkit-questions --backlog <ID>` で、候補を `docs/questions/NNN-<slug>.md` として RQ にできる。

## 運用ルール

- 状態は **候補 / RQ化済み（docs/questions/NNN-slug.md） / 却下** のいずれか（`RQ化済み` は空白を入れずに書く。`validate.py` がリンク先を確かめる）
- 候補は消さない。RQ にしたり却下したりしたら状態欄を書き換える。却下したものを戻すときは、状態を「候補」に戻して理由を書き足す
- 候補は**問いの形**で書く（疑問文）。答えや数値の見込みは書かない
- 「RQ にするときに決めること」は、RQ にするときの質問の最初の論点になる
- 手で候補を足してよい。ID は既存の最大値の次から振る

## 一覧

| ID | 候補（問い） | 状態 | つながる決定 |
|---|---|---|---|
| BL-001 | <候補の問い> | 候補 | <D2 / —（決定を変えない）> |

## 候補

### BL-001 <候補の問い>

**状態**: 候補 | **つながる決定**: <D2 または —> | **関連する仮説**: <H1 または —> | **関連 RQ**: <NNN-slug, NNN-slug または —>

- **問いの概要**: <何を明らかにする問いか。1〜3 文>
- **出典**: <docs/concept/framing.md 案 B / docs/concept/premises.md Q<ID> / docs/study/issue-tree.md I2.3 / studies/<NNN-name>/findings.md / ユーザー追記（YYYY-MM-DD）>
- **RQ にしなかった理由**: <例: 答えても D1 の判断は変わらない / 予備調査でデータが手に入らないと分かった / 期限内に答えが出ない（RP4）/ 範囲外（RP3）>
- **RQ にするときに決めること**:
  - <論点>

### BL-002 <却下した候補の問い>

**状態**: 却下 | **つながる決定**: — | **関連する仮説**: — | **関連 RQ**: —

- **問いの概要**: <候補の内容>
- **出典**: <docs/concept/premises.md Q<ID>>
- **却下の理由**: <ユーザーの決定の要約と Q-ID>
