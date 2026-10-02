# new-researchkit-project

[researchkit](https://github.com/sfukuda84/researchkit) の調査のプロジェクトを作り、AI エージェントで立ち上げ（`researchkit-bootstrap`）を始めるコマンド。既存の調査への取り込みと、作成済みのプロジェクトの更新もできる。macOS、Linux、Windows で動く（Python 3.9 以上、依存なし）。

## 導入と更新

```bash
uv tool install "git+https://github.com/sfukuda84/researchkit#subdirectory=tool"
uv tool upgrade new-researchkit-project
```

## プロジェクトを作る・取り込む

```bash
new-researchkit-project <ディレクトリ> [--title <仮題>] [-m "調べたい問い"] [--auto | --oneshot] [--agent <エージェント>] [--adopt] [--no-launch]
```

| オプション | 内容 |
|---|---|
| `--title` | 調査の仮題（`.researchkit/config.yaml` の `title`） |
| `-m`, `--message` | 調べたい問い。`docs/concept/core-question.md` に保存する。省略すると対話で入力を受ける。空なら起動せずに手順だけを表示する |
| `--auto` / `--oneshot` | 立ち上げを質問なしで進める / 最初に一度だけ質問して進める |
| `--agent` | 立ち上げに使うエージェント（`claude`（既定）/ `codex` / `agy` / `kiro` / `opencode`） |
| `--adopt` | 既存の調査に取り込む（既存のファイルは上書きしない。エージェントは起動しない。続きは `/researchkit-bootstrap --adopt`） |
| `--no-launch` | エージェントを起動せず、手順だけを表示する |
| `--ref` / `--repo` | 取得する scaffold のブランチまたはタグ / リポジトリ（環境変数 `RESEARCHKIT_SCAFFOLD_REF` / `RESEARCHKIT_SCAFFOLD_REPO`） |
| `--scaffold` | GitHub から取得せず、手元の scaffold を使う |
| `--link` | スキルを scaffold へのシンボリックリンクにする（`--scaffold` を使うときだけ） |

作るときは、`researchkit.py init`（`.researchkit/config.yaml` と既定のディレクトリ）と `researchkit.py hooks install`（Web 検索の回数を数えるフック。`.claude/settings.json`）も実行する。シンボリックリンクを作れない環境（Windows で開発者モードがオフなど）では、スキルの実体をコピーして警告する。作ったプロジェクトには、使った scaffold の版を `.researchkit/scaffold.json` に記録する。

## 作成済みのプロジェクトを更新する

```bash
new-researchkit-project update [プロジェクトのディレクトリ] [--dry-run] [--ref <ブランチまたはタグ>] [--repo <リポジトリ>] [--scaffold <ディレクトリ>]
```

scaffold の持ち物（スキル、steering、CLAUDE.md などの規則ファイル）だけを取り込み、1 つのコミットにする（`main` で、未コミットの変更がないときだけ動く。既定のブランチが別なら環境変数 `RESEARCHKIT_MAIN_BRANCH`）。

- scaffold の全履歴のどれかの版と一致するファイルは、新しい版で上書きする。scaffold から消えたファイルは削除する。
- どの版とも一致しないファイルは手で直したものとみなして上書きせず、新しい版を `.scaffold-new/` に置く。比べるときは `git diff --no-index <ファイル> .scaffold-new/<ファイル>`。
- 取り込み（`--adopt`）で残した同名のスキルや、追跡していない既存のファイルには触らない。
- スキルを scaffold へのリンクで置いたプロジェクトは、スキルを更新しない（すでに最新）。
- 調査の成果物（設定、憲章、`docs/`、`sources/`、`studies/` など）は対象外。

## テスト

```bash
cd tool && python3 -m unittest discover -s tests
```
