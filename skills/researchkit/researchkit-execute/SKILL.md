---
name: "researchkit-execute"
description: "問い（RQ）の実行の工程を実行する統括スキル。Git worktree の準備（既存があれば再利用して続きから再開）、収集（researchkit-collect。出典台帳・抜き書き・データ・検索ログ）、分析（researchkit-analysis。再実行できるスクリプトと出力）、主張のまとめ（researchkit-findings。主張・根拠・確度・反証と逆流）、5 軸レビュー ×2（researchkit-review。Source・Logic・Counter・Bias・Numbers）と修正を行い、main へのマージ、引き継ぎ書の更新、後片付けまでを実行する。RQ の工程の Q1、Q8〜Q13（--phase execute）。Q8・Q11 の前に Web 検索の予算を確かめる。spec.md・plan.md・tasks.md が必要で、なければ researchkit-question を案内する。「この問いを調べて」「収集と分析を進めて」と言われたとき、または /researchkit-execute と打たれたときに使う。"
argument-hint: "RQ の番号または範囲と、任意の --auto（例: 001, 002-005, all, all --auto, または省略して次の未完了）"
compatibility: "Requires git and Python 3.9+, researchkit project structure with .researchkit/config.yaml"
user-invocable: true
disable-model-invocation: false
---

# researchkit-execute スキル（実行の工程: Q1 → Q8〜Q12 → Q13）

設計の工程（[`researchkit-question`](../researchkit-question/SKILL.md)）で作った `spec.md`、`plan.md`、`tasks.md` に基づき、収集、分析、主張のまとめ、2 回の 5 軸レビューと修正を行い、`main` にマージする。

- 設計から実行までを 1 つの worktree で通して行う場合は [`researchkit-all`](../researchkit-all/SKILL.md) を使う。`researchkit-all` は、このファイルの「§3 本体」だけを実行する。

**ステップ番号、ヘルパースクリプト（`$HELPER`）、再開、安全規則、対話、引数の解釈、自動モードは [`researchkit-worktree`](../researchkit-worktree/SKILL.md) に従う。** 作業を始める前に必ず読むこと。この文書では、その節を「`researchkit-worktree` の『ステップ番号』の節」のように見出しの名前で参照する。

パスは既定の配置で書いている。`.researchkit/config.yaml` の `paths` で読み替える。`$RK`、`$HELPER`、`$CHECK`、`$NUM` の意味は steering の「エージェントの行動規範」のとおりである。

## 1. ユーザー入力・引数

```text
$ARGUMENTS
```

引数の解釈と複数の RQ の進め方は、`researchkit-worktree` の『引数の解釈と複数の RQ の進め方』の節に従う。自動検出では `--phase execute` を使い、設計が `main` にマージ済みで、`tasks.md` に `[人]` 以外の未完了のタスク（`- [ ]`）が残っている RQ を対象にする。`--auto` があるときは、下の 💬 の質問も含めて、`researchkit-worktree` の『自動モード』の節で進める。

## 2. 実行の流れ（単独実行）

対象の RQ ごとに、次を順に行う。

1. **予算の確認**: `$RK budget --step rq --rq <RQ>` を実行する。`VERDICT: STOP`（終了コード 4）なら、この RQ に入らずに止まり、新しいセッションで同じ引数で実行するよう案内する（steering の「セッションの区切り」）。途中の RQ を再開するときは、残りのステップの分だけを見積もってよい（Q8 が残っていれば `--step Q8 --rq <RQ_NAME>`、Q11 から先だけなら `--step Q11 --rq <RQ_NAME>`）。
2. **Q1 準備**: `researchkit-worktree` の『Q1 準備』の節に従い、`$HELPER ensure <RQ> --phase execute` を実行する。
   - 設計の工程の途中の worktree がある場合は `DESIGN_INCOMPLETE`、設計がどこにもない場合は `DESIGN_MISSING` で止まる。そのときは何も作らずに、`researchkit-question` か `researchkit-all` を案内する。
   - すでに実行を終えている場合は `ALREADY_EXECUTED` で止まる。完了として扱う。
   - worktree がなく、設計が `main` にマージ済みの場合は、`main` から新しい worktree を作る。`researchkit-all` などで設計を終えた worktree が残っていれば、それを再利用する。
3. **本体**: 下の §3 の Q8〜Q12 のうち、`NEXT_STEP` 以降を順に実行する。
4. **Q13 片付け**: `researchkit-worktree` の『Q13 片付け』の節に従い、`$HELPER finish <RQ_NAME> --phase execute` を実行し、引き継ぎ書を更新する。状態は `完了`、`[人]` のタスクが残れば `人の作業待ち` になる。
5. 次の RQ があれば 1 に戻る。回数を数えられない環境（`budget` が `VERDICT: UNMETERED`）では、このセッションで `session.rqs_unmetered`（既定 1）件の RQ を終えたところで止まる。

## 3. 本体（Q8〜Q12）

作業場所は `WORKTREE_DIR`、RQ のディレクトリは `studies/<RQ_NAME>`（以下 `RQ_DIR`）である。各ステップの最後に、`researchkit-worktree` の『ステップ番号』の節の subject で `checkpoint` を記録する。

| ステップ | 内容 | スキル | 成果物 |
|---|---|---|---|
| Q8 | 収集 | [`researchkit-collect`](../researchkit-collect/SKILL.md) | `sources/`、`RQ_DIR/evidence/`、`data/`、`RQ_DIR/search-log.md` |
| Q9 | 分析 | [`researchkit-analysis`](../researchkit-analysis/SKILL.md) | `RQ_DIR/analysis/`（スクリプト、`out/`、抽出表、コーディング表） |
| Q10 | 主張のまとめ | [`researchkit-findings`](../researchkit-findings/SKILL.md) | `RQ_DIR/findings.md`、逆流の更新 |
| Q11 | 5 軸レビュー 1 回目と修正 | [`researchkit-review`](../researchkit-review/SKILL.md) | `RQ_DIR/reviews/review-1.md` |
| Q12 | 5 軸レビュー 2 回目と修正 | `researchkit-review` | `RQ_DIR/reviews/review-2.md` |

### 入力情報

まず `$RK brief <RQ_NAME>` で RQ の要点を読み、下の文書は要る節だけを読む（全文を読まない。steering の「RQ の要点を短く読む」）。

- `RQ_DIR/spec.md`（問い、答えの形、判定の基準、範囲、用語）、`plan.md`（手法、検索式、標本、分析の計画、反証条件、計画の変更）、`tasks.md`
- 手法の参照文書 `researchkit-method/references/`（`plan.md` で選んだ手法の分。`desk.md`、`literature.md`、`data.md`、`qualitative.md`）
- 憲章 `.researchkit/memory/constitution.md`、品質基準 `docs/quality.md`、用語集 `docs/glossary.md`、データの目録 `data/manifest.md`
- 仮説 `docs/study/hypotheses.md`、イシューツリー `docs/study/issue-tree.md`
- 依存する RQ の `findings.md`、既存の出典 `sources/`

### Q8: 収集

1. **始める前に** `$RK budget --step Q8 --rq <RQ_NAME>` を実行する。STOP なら Q8 に入らずに止まる（Q7-2 までのチェックポイントは記録済み）。
2. `researchkit-collect` の手順で、`tasks.md` の収集のフェーズのタスクを実行する。要点は次のとおりである。
   - 出典 ID は `$RK sources next <NNN> --count <k>` で取る。既存の出典は新しく作らず、`used_in` に足す。サブエージェントで並行に集めるときは、ID の範囲を分ける（steering の「サブエージェントに任せるとき」）。
   - AI が挙げた文献・統計は 1 件ずつ実在を確かめる。確かめられないものは等級 `D` にし、根拠に使わない。
   - 検索式、データベース、期間、件数を `search-log.md` に残す。見つからなかったことも書く。
   - 仮説に反する証拠を探す検索も、`plan.md` のとおりに行う。
   - `[人]` のタスク（有料資料の入手、インタビューの実施、同意の取得など）は実行しない。手順を示して保留にし、依存しない後続のタスクを続ける。
3. `$CHECK --rq <NNN>` を実行し、出典ファイルの ERROR を 0 件にする（主張はまだないので、主張の参照に関する指摘は Q10 で見る）。
4. `checkpoint <RQ_NAME> Q8` を記録する。

> 💬 有料の情報源を使うか、検索の範囲を `plan.md` から変えるかなど、判断が必要な場合は推奨案を添えて質問する。計画を変えたときは、`plan.md` の「計画の変更」に、変えたことと理由を書く。

### Q9: 分析

1. `researchkit-analysis` の手順で、`tasks.md` の分析のフェーズのタスクを実行する。分析は `RQ_DIR/analysis/` のスクリプトにし、`commands.analysis` で再実行できるようにする。出力は `analysis/out/` に JSON で置き、報告に使う数値をキーで引けるようにする。
2. `plan.md` の分析の計画と反証条件のとおりに分析する。計画から外れた分析をしたときは、「計画の変更」に書き、探索的な分析として区別する。
3. `checkpoint <RQ_NAME> Q9` を記録する。

> 💬 分析の方法の分岐（外れ値の扱い、コードの統合など）に判断が必要な場合は、推奨案を添えて質問する。

### Q10: 主張のまとめ

1. `researchkit-findings` の手順で、`RQ_DIR/findings.md` を作る。主張は steering の「主張の書式」の表で書き、数値には `{N:<path>#<key>}` を付ける。`spec.md` の答えの形と判定の基準に答え、判定できなかった問いは「残った問い」に書く。
2. 仮説ごとに、反証条件に当たったかを書く。前提や仮説が崩れたら、`docs/study/hypotheses.md`、`issue-tree.md`、`docs/questions/` にも戻して直す（逆流）。
3. `$CHECK --rq <NNN>` と `$NUM --rq <NNN>` のエラーを 0 件にする。
4. `tasks.md` の残作業を確かめ、AI のタスクがすべて `- [x]` になっていることを確かめる。
5. `checkpoint <RQ_NAME> Q10` を記録する。`SPLIT_SESSION` が出たら（`session.split_after`）、Q11 に入らずに引き継ぎ書を更新して止まり、新しいセッションで同じスキルを同じ引数で実行して再開する（`researchkit-all` の §2 の手順 4 と同じ）。ほかのステップの後で出たときも同じ。

### Q11: 5 軸レビュー 1 回目と修正

1. **始める前に** `$RK budget --step Q11 --rq <RQ_NAME>` を実行する。STOP なら Q11 に入らずに止まる（Q10 までのチェックポイントは記録済み）。
2. `researchkit-review --round 1` の手順で、`findings.md` と根拠（`evidence/`、`analysis/`、`sources/`）を、Source・Logic・Counter・Bias・Numbers の 5 軸でレビューする。定性調査かデータ分析を含む RQ では Ethics を足す。記録は `RQ_DIR/reviews/review-1.md` に書く。可能なら、軸ごとに文脈を持たないサブエージェントで独立に審査し、親が指摘の裏を取ってから採否を決める。
3. CRITICAL・HIGH・MEDIUM の指摘を直す。主張を直したら、`$CHECK --rq <NNN>` と `$NUM --rq <NNN>` が通ることを確かめ、逆流が要るものは Q10 と同じく上流の文書も直す。
4. `checkpoint <RQ_NAME> Q11` を記録する。

> 💬 指摘への対応方針（主張を弱めるか、追加で調べるか）に判断が必要な場合は、推奨案を添えて質問する。

### Q12: 5 軸レビュー 2 回目と修正

1. Q11 の修正が、別の主張や数値を壊していないか、新しい飛躍がないかを確かめるため、1 回目と違うレンズで `researchkit-review --round 2` を実行し、記録を `RQ_DIR/reviews/review-2.md` に書く。
2. 残っている指摘を直し、`$CHECK --rq <NNN>` と `$NUM --rq <NNN>` のエラーを 0 件にする。修正がなくても次へ進む。
3. `checkpoint <RQ_NAME> Q12` を記録する。

### 000 と 999 の扱い

`000-research-foundation` は主張を作らない基盤づくり（Q8 で基盤を整え、Q9 で分析環境を確かめ、Q10 で残作業をまとめる）。`999-research-report` は Q8 が `researchkit-synthesize`、Q9 が `researchkit-publish`、Q10 が `researchkit-findings` の統合モード。読み替えの表と数値の参照の書き方は [references/special.md](references/special.md)。

## 4. 完了報告

完了報告の項目（マージコミット、収集・分析・主張の要約、レビューの指摘、`$CHECK`・`$NUM`、残っている `[人]`、飛ばした RQ、自動の判断、次の案内）は [references/special.md](references/special.md)。
