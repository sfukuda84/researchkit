# レビュー <round> 回目: <NNN-name または対象の名前>

- **日付**: <YYYY-MM-DD>
- **対象**: <studies/<NNN-name>/findings.md と根拠（evidence/、analysis/、sources/ の N 件） / reports/report.md / パス>
- **審査の方法**: <サブエージェントによる独立審査（軸ごと。前提は templates/brief.md の定型） / 親による順次審査>。審査した状態: <コミット / 作業ツリー>。渡した不採用・人の確認への一覧: <2 回目のとき。R1-S04 など>
- **軸**: <Source, Logic, Counter, Bias, Numbers（, Ethics）>
- **機械検証**: check.py errors=<n> warnings=<n>（--online <あり / なし>） / numbers.py errors=<n> warnings=<n>
- **2 回目のとき**: 1 回目の記録 [review-1.md](./review-1.md)、修正の差分 `git diff <range>`

## 要約

| 軸 | CRITICAL | HIGH | MEDIUM | LOW | 採用 | 不採用 | 保留 | 人の確認へ |
|---|---|---|---|---|---|---|---|---|
| Source | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Logic | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Counter | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Bias | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Numbers | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Ethics | — | — | — | — | — | — | — | — |

## 指摘

### R<round>-<軸の頭文字><連番>: [<重大度>] <一言で。例: C2 の成長率が出力と一致しない>

- **軸**: <Numbers>
- **場所**: <studies/001-market-size/findings.md#L24（C2）>
- **根拠**: <例: findings.md は 8.0%、analysis/out/market.json の cagr は 0.072（7.2%）。numbers.py の ERROR と一致>
- **直し方**: <例: 2023 年の定義の変更を補正した系列で再計算し、C2 と答えを直す>
- **採否**: <採用（修正: <コミット>） / 不採用（理由） / 保留（ユーザーに確認） / 人の確認へ（T0xx）>

### R1-S01: [CRITICAL] <例: S001-0009 の DOI が解決せず、題名で探しても論文が見つからない>

- **軸**: Source
- **場所**: <sources/S001-0009.md、findings.md の C4>
- **根拠**: <https://doi.org/10.xxxx/... が 404。Google Scholar と CiNii Research で題名を検索して一致なし（2026-10-06）>
- **直し方**: <等級を D にして C4 の根拠から外す。C4 はほかの根拠がなければ「残った問い」に移す>
- **採否**: <採用>

## Counter の検索

| # | 対象（主張・仮説） | 検索先 | 検索式 | 結果 | 扱い |
|---|---|---|---|---|---|
| 1 | <C1> | <WebSearch> | <〇〇 市場 縮小 2025> | <該当なし（上位 10 件）> | — |
| 2 | <H1> | <Google Scholar> | <"..." decline> | <反する推計 1 件: URL> | <R1-C02。登録して C1 の反証・限界に追記> |

## 未確認・人の確認が要るもの

- <Source: ページを開けず、要約でしか確かめられなかった出典>
- <Ethics: 同意の範囲の確認が要るもの（tasks.md の T0xx に追記）>
- <法的な判断・専門家の確認が要るもの>

## 修正後の検証

- check.py: errors=<n> warnings=<n> / numbers.py: errors=<n> warnings=<n>
- 分析のスクリプトの再実行: <N 本。out/ の差分なし / 意図どおりの差分（C2 の再計算）>
