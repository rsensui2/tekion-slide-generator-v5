# TEKION Slide Generator v5 — Claude Code 版（Codex 駆動）

**Markdown / テキスト → 高品質な日本語 16:9 スライド → PPTX / PDF** を Claude Code から自動生成するスキル。
画像生成は **Codex 内蔵 gpt-image-2（ChatGPT/Codex サブスク枠）** を既定に、必要なら OpenAI / Gemini の
API（従量課金）にも切替可能。

> リポジトリ全体の概要・Codex ネイティブ版は、リポ直下の [README.md](../../../README.md) を参照。
> 配布区分は社内 / 限定（非パブリック）。[NOTICE](../../../NOTICE) を参照。

---

## このスキルの位置づけ

| | 役割 |
|---|---|
| **オーケストレーター** | Claude Code（設計・JSON/プロンプト生成・レビュー往復） |
| **画像生成** | Codex（サブスク枠の gpt-image-2）を既定。`--provider openai/gemini` で API 課金にも切替可 |
| **強み** | Claude を UI に、設計→生成→特定スライド再生成のリレーが回せる。providers 抽象で 3 バックエンド切替 |

「ChatGPT 契約 1 本だけで完結させたい / 設定不要で配りたい」なら、**Codex ネイティブ版**
（`skills/codex/tekion-slide-generator-v5`）の方が向く。本版は **Claude Code を入口にしたい**とき。

---

## v5 の要点（v4 からの進化）

- **画像生成をサブスク枠へ**: 既定で Codex の gpt-image-2（同一モデル）を使い、OpenAI API 従量課金を回避。
  `OPENAI_API_KEY` は実行時に自動除去（残すと従量課金に切替わるため）。
- **真の並列**: 子 `codex exec` を並列起動。実測 **2K で並列 20 → 20 枚を約 67 秒**。既定 `--max-parallel 8`。
- **レート制限フォールバック**: 失敗時に並列度を段階的に下げ（8→4→2→1）バックオフ再試行。
- **認証セーフ**: 並列ワーカーは `auth.json` を**コピー**した隔離 CODEX_HOME で動作し、ファンアウト前に
  warmup でトークン更新。トークン競合による失効を防止（失効時は `codex login` を案内）。
- v4 までの機能は維持: **Visual / Balanced 2 スタイル**、16:9 2K ネイティブ、ロゴ色保全、
  PPTX/PDF 出力、providers 抽象（openai/gemini/codex）。

### v1 → v5 の歩み

| Ver | 時期 | テーマ |
|:---:|:---:|------|
| v1 | 2026-01 | Markdown → スライド → PPTX の基本パイプライン |
| v2 | 2026-02 | デザインガイドライン（ブランド対応） |
| v3-flash | 2026-03 | Gemini 3.1 Flash、Thinking/Grounding、16:9 2K |
| v4 | 2026-04 | マルチプロバイダ（OpenAI/Gemini）・Visual/Balanced |
| **v5** | 2026-06 | **Codex サブスク枠生成・子exec並列・レート/認証フォールバック** |

---

## クイックスタート

```bash
# 1. 取得してスキルとして配置
git clone https://github.com/rsensui2/tekion-slide-generator-v5.git
cp -R tekion-slide-generator-v5/skills/claude-code/tekion-slide-generator-v5 ~/.claude/skills/

# 2. 依存（Python）
pip install Pillow python-pptx requests Jinja2

# 3. Codex にログイン（サブスク枠で生成。OpenAI API キーは不要）
codex login

# 4. Claude Code で発動
# 「Codex でスライドを作って」
```

> API 課金版（OpenAI/Gemini）で動かしたい場合のみ、`~/.claude/.env.local` に
> `OPENAI_API_KEY` / `GEMINI_API_KEY` を置き、`--provider openai|gemini` を指定。
> 既定（codex）ではキー不要・サブスク枠。

---

## 主なオプション

| パラメータ | 既定 | 説明 |
|---|:---:|---|
| `--provider` | codex | `codex`（サブスク枠）/ `openai` / `gemini`（API課金） |
| `--max-parallel` | 8 | 並列数。2K で 20 まで実証（枠残量に注意） |
| `--image-size` | 2K | 512px / 1K / 2K / 4K（すべて 16:9） |
| `--logo` | assets/logo.png | 右下に色保全で合成 |
| `--style`（openai/gemini系） | balanced | `visual`（ピッチ）/ `balanced`（営業資料）|

---

## 自社ブランドに合わせる

1. **ロゴ差し替え**: `~/.claude/skills/tekion-slide-generator-v5/assets/logo.png` を置き換え
   （透過 PNG・横長・幅 1000px 以上推奨）。
2. **デザインガイドライン**: `design-setup` スキルで対話設定するか、
   `references/presets/example-preset.md` をコピーして編集 → `.active_preset` に登録。

詳細は [docs/branding.md](docs/branding.md)。

---

## 構成

```
scripts/
  generate_slides_parallel.py   # 並列オーケストレーション（--provider codex/openai/gemini）
  generate_slide_with_retry.py  # 単一スライド生成（provider 経由）
  codex_app_server_client.py    # Codex 駆動ブリッジ（warmup・隔離CODEX_HOME・exec/app-server）
  providers/                    # base / openai / gemini(内) / codex
  generate_prompts_from_json.py # Jinja2 でプロンプト生成
  finalize? / export_to_pptx.py / export_to_pdf.py
  regenerate_slide.py           # 特定スライド再生成（バージョニング）
templates/  references/  assets/
```

詳しい手順は [SKILL.md](SKILL.md)、アーキテクチャは [references/architecture.md](references/architecture.md)。

---

## 注意

- 画像生成はサブスク枠を**累積で**消費する（公式: 画像ターンは通常の 3-5 倍速く消費）。日次/週次の
  usage limit に達したら時間をおく / `--max-parallel` を下げる。
- `token_revoked`（認証失効）が出たら `codex login` で再ログイン。
- ライセンス / 再配布は [NOTICE](../../../NOTICE)（社内・限定配布）に従う。
