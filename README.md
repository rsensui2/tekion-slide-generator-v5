# TEKION Slide Generator v5

Markdown / テキストから **日本語プレゼンスライド（16:9）** を生成し、**PPTX / PDF** まで書き出すスキル。
画像生成は OpenAI **gpt-image-2** を使い、**ChatGPT / Codex のサブスクリプション枠**で動く
（API 従量課金なし）。営業資料・提案書・登壇ピッチ向け。

> **公開（ソース公開）だが OSS ではない。** 未改変での利用は誰でも可（商用含む）、
> **改変・再配布は事前許可制で禁止**。詳細は [LICENSE](./LICENSE) / [NOTICE](./NOTICE)。

---

## 2 つの版（同梱）

| | 版 | ホスト | 必要な契約 | 向く用途 |
|---|---|---|---|---|
| **Codex 版** | `skills/codex/tekion-slide-generator-v5` | Codex CLI | **ChatGPT/Codex のみ** | サブスク1本で完結・ゼロコンフィグ・並列既定 |
| **Claude Code 版** | `skills/claude-code/tekion-slide-generator-v5` | Claude Code | Claude ＋ ChatGPT/Codex | Claude で設計・レビュー往復、providers(openai/gemini/codex)切替 |

どちらも **画像生成エンジンは共通**（子 `codex exec` を並列起動し、サブスク枠の gpt-image-2 を叩く）。
SKILL.md 形式は Claude / Codex でほぼ共通のため、同じスクリプトを両ホストで流用している。

**迷ったら Codex 版**（契約が ChatGPT 1 本で済む）。

---

## 必要環境

共通:
- **Codex CLI** インストール済み・ログイン済み（`~/.codex/auth.json`）。画像生成はサブスク枠で行う。
- **Python 3.10+** ＋ `Pillow` / `python-pptx`（`pip install Pillow python-pptx`）。

Claude Code 版のみ:
- **Claude Code**（オーケストレーターとして使用）。

> 画像生成に **OpenAI API キーは不要**。むしろ `OPENAI_API_KEY` を環境に残すと従量課金へ切り替わるため、
> スキルは実行時に自動で除去する（サブスク枠を維持）。

---

## インストール

```bash
# 両方入れる（既定）
./install.sh

# どちらかだけ
./install.sh --codex     # ~/.codex/skills/ に Codex 版
./install.sh --claude    # ~/.claude/skills/ に Claude Code 版
```

手動で入れる場合は、対応するスキルフォルダを各ホストの skills ディレクトリへコピーするだけ:
- Codex: `cp -R skills/codex/tekion-slide-generator-v5 ~/.codex/skills/`
- Claude: `cp -R skills/claude-code/tekion-slide-generator-v5 ~/.claude/skills/`

---

## 使い方（クイックスタート）

- **Codex 版**: `codex` で「スライドを作って。内容は …」と頼む（または `codex exec`）。
  既定で並列生成 → 16:9 正規化・ロゴ・フッター → PPTX/PDF 出力まで自動。
- **Claude Code 版**: Claude Code で「Codex でスライドを作って」。Phase0-3 を Claude が設計し、
  Phase4 を Codex（サブスク枠）で並列生成、レビュー→特定スライド再生成のリレーが可能。

出力: `deck.pptx` / `deck.pdf` ＋ 各スライド画像（`images/`）。

---

## レート制限・認証の扱い（重要）

- 画像生成はサブスク枠を**累積で**消費する（公式: 画像ターンは通常の 3-5 倍速く消費）。日次/週次の
  usage limit に達し得る。
- **自動フォールバック**: 失敗を検知すると並列度を段階的に下げ（8→4→2→1）バックオフ再試行する。
- **認証失効**（`token_revoked` / `refresh_token_reused`）を検知したら停止し、`codex login` での再ログインを促す。
- 並列ワーカーは各自の隔離 `CODEX_HOME` に **auth.json をコピー**して動作（実 auth.json を壊さない）。
  ファンアウト前に warmup でトークンを更新するため、並列実行でもトークン競合が起きない。

### 実測（参考）
- 2K・並列 20 → 20 枚を約 67 秒（スロットリングなし）。
- 並列を上げても 1 枚あたり時間（律速＝エージェントターン）は縮まらない。既定は `--max-parallel 8`。

---

## ライセンス / 配布

[LICENSE](./LICENSE)（ソース公開のプロプライエタリ）に従う。要点:
- **できる**: 未改変のまま閲覧・複製・実行（商用含む）。生成物は利用者に帰属。
- **できない（要・TEKION 事前書面許可）**: 改変・派生物作成、再配布・公開・販売、
  著作権/帰属表示や焼き込みフッター・同梱ロゴの削除。

> 注: OSI 定義の「オープンソース」ではない（改変の自由を制限するため）。
> GitHub 公開リポは規約上 fork/閲覧が可能だが、改変・再配布の権利は本ライセンスの範囲に限られる。
> 正式運用前に TEKION 法務でのレビューを推奨。
