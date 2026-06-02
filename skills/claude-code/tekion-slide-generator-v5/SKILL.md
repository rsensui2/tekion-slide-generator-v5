---
name: tekion-slide-generator-v5
description: "TEKION Slide Generator v5（Claude Code版） — Markdown/テキストから日本語プレゼンスライド（16:9）を生成し PPTX/PDF まで書き出す。ユーザーが『スライドを作って』『プレゼン資料/提案書/企画書/ピッチデッキにして』『この資料をデッキ化』『登壇用の資料』のようにスライド作成を求めたら、ツール名を明示しなくても使うこと。画像生成は Codex 内蔵 gpt-image-2 を使い、ChatGPT/Codex のサブスク枠なら API 従量課金なしで作れる（Codex 未導入や API 課金がよければ provider を openai/gemini に切替）。Visual/Balanced 2スタイル、TEKION ブランド/ロゴ適用、子 codex exec 並列生成、16:9・フッター焼き込み対応。Claude Code を入口に設計→生成→特定スライド再生成のリレーをしたいときに最適。"
---

# TEKION Slide Generator v5 — Claude Code版（Codex駆動）

TEKION Slide Generator の **Codex 駆動版**。画像生成のバックエンドを
**OpenAI API（従量課金）から Codex 内蔵 gpt-image-2（サブスク枠）** に差し替えた版。
モデルは同じ gpt-image-2 なので品質は同等、課金だけが ChatGPT/Codex サブスクに乗る。

**コスト原則**: Codex 起動時に `OPENAI_API_KEY` を環境から除去する（残っていると公式仕様で
API 従量課金に切り替わる）。本スキルのブリッジが各実行で自動除去するが、シェル側でも極力 unset。

## 実行モード

```yaml
mode: auto  # Pre-flight〜Phase 5を承認なしで連続実行
pause_only_on: [route_ambiguous, codex_not_logged_in]
chain_commands: true  # bashは && で連結
```

## 定数

```bash
SKILL_DIR="<path-to-this-skill>"
PYTHON="python3"
```

## 前提条件

- Python 3.10+（Pillow / python-pptx / requests / Jinja2）
- **Codex CLI** がインストール済み・ログイン済み（`~/.codex/auth.json` 存在）。ChatGPT/Codex のサブスクで認証。
  - 確認: `codex --version` / `codex exec "hello"` が通ること
- 画像生成は Codex 内蔵 gpt-image-2（サブスク枠）。**API キーは不要**。
- バックエンド既定は `codex exec`（確実・並列向き）。常駐 App Server を使う場合は
  `export CODEX_SLIDES_BACKEND=app-server`（experimental）。

初回セットアップ:
```bash
bash ${SKILL_DIR}/scripts/setup.sh
```

## 言語ルール

```yaml
display_language: "ターゲット聴衆に合わせる（素材の言語ではない）"
target_fields: [title, subtitle, key_message, content]
english_allowed: "固有名詞のみ (Cursor, MCP等)"
content_suffix: "※スライド上の全テキストは{lang}で表示すること。"
```

## スタイル選択

Phase 3 のプロンプト生成で `--style` フラグを指定、またはスライド毎に JSON で `_style` を付与することで、
スライドの雰囲気（文字量・ビジュアル比率・余白）を切り替えられます。

| 判断基準 | スタイル | テンプレート |
|----------|:---:|---|
| 「登壇」「ピッチ」「Keynote風」「ビジュアル重視」「写真主役」 | **visual** | `prompt_template_visual.j2` |
| 「営業資料」「提案書」「バランス」「図解と文字の両立」（デフォルト） | **balanced** | `prompt_template_balanced.j2` |

### visual スタイル（ピッチデッキ風）
- Apple Keynote / TED Talk の余白美学、Less is more
- タイトル15文字 + キーメッセージ1文（最大2行）
- 画面の**60-80%**を1つの大胆なビジュアル（全面写真・巨大数字・大きなシンボル）
- 複数カード・網羅リストは禁止、大胆な余白
- **用途**: 登壇・ピッチ・表紙・中扉・感情に訴える1枚

### balanced スタイル（営業資料・提案書風／デフォルト）
- Pitch.com / MorningBrew / Figma Slides の洗練
- 見出し + 3-5項目の簡潔な箇条書き / 2-3ブロックの図解
- テキスト40-60% / ビジュアル40-60%のバランス
- 情報網羅は求めず、要点を絞る
- **用途**: 営業資料・提案書・プラン比較・実績紹介（今回のVibeCoder Bootcamp資料相当）

### スライド毎のオーバーライド（`_style`）

`slides_plan.json` で個別指定可能:

```json
{
  "source_file": "00_cover",
  "_style": "visual",    ← 表紙だけ visual にする
  "title": "...",
  "content": "..."
}
```

`_style` が未指定なら `--style` のデフォルトを継承。

### ユースケース別レコメンド

| 用途 | 推奨 | 備考 |
|------|:---:|------|
| 登壇用ピッチ資料 | visual | 表紙・章扉・キーメッセージを visual で |
| 営業資料・提案書 | balanced | 今回の VibeCoder Bootcamp 相当 |
| 表紙＋本編の混在 | `--style balanced` + 表紙だけ `_style: visual` | 最も良く使うパターン |

## スライド構成（slides_plan.json）の作り方

Codex版は **Claude（このエージェント）が slides_plan.json を単一パスで直接作成**する
（Claudeサブエージェントの並列fan-outは使わない）。入力Markdown/テキストを読み、Phase 2 の
スキーマに沿って各スライドの content を丁寧に書く。少数（〜15枚）でも大量（20枚以上）でも
同じ手順。生成（Phase 4）の並列化は Codex 経由の画像生成側で行う。

## Provider（画像生成バックエンド）

**このスキルは常に Codex（サブスク枠の gpt-image-2）で生成する** = `--provider codex`。
APIキー不要。`generate_slides_parallel.py --provider codex` が既定の入り口。

| バックエンド | 指定 | 用途 |
|----------|:---:|---|
| `codex exec`（既定） | （指定不要） | 確実・並列向き。各実行を独立 CODEX_HOME に隔離し競合を防ぐ |
| `codex app-server`（experimental） | `export CODEX_SLIDES_BACKEND=app-server` | 常駐サーバ/対話履歴引き継ぎが要るとき |

### 並列数の目安（Codex サブスク枠・実測反映）

実測（認証修正後）:
- **2K で並列8 → 8枚を56秒**で全成功。
- **2K で並列20 → 20枚を68秒**で全成功・throttle なし。1K の並列20（78秒）と同様、**真の並列が効き総時間はほぼ横ばい**。
- サブスク枠のレート天井は **2K でも 20 以上**（少なくとも 20 までは当たらない）。

- **既定 `--max-parallel 8`**（日常運用の安全寄りの既定。速度・枠消費・ローカル負荷のバランス）。
- **急ぎの大量生成は `--max-parallel 20` を使ってよい**（2K でも実証済み・67秒/20枚）。
- ただしサブスク枠は画像ターンの消費が速い（公式: 通常の3-5倍）。**累積**で日次/週次 usage limit に達し得るため、常時20で回すより必要時のみ高並列が安全。
- 1枚あたり約55〜70秒。並列を上げても1枚あたり時間（律速＝エージェントターン）は縮まらない。

### 並列と認証（重要・既知の落とし穴）

並列ワーカーは各自の隔離 CODEX_HOME に **auth.json をコピー**して動く（symlink で共有しない）。
理由: 共有すると、アクセストークン期限切れ時に複数プロセスが同じ refresh token で同時更新し、
使い捨て refresh token を奪い合って**トークンが失効**する（`refresh_token_reused` / `token_revoked`）。
対策として `generate_slides_parallel.py` は **ファンアウト前に warmup でトークンを更新**してから並列化する。
それでも `token_revoked` が出たら **`codex login` で再ログイン**すること（サーバ側失効はファイル復元では直らない）。

---

## Pre-flight

1. Codex CLI とログインを確認:

```bash
command -v codex >/dev/null && [ -f ~/.codex/auth.json ] && echo "codex OK" || echo "STOP: codex 未導入/未ログイン"
```

2. 未ログインなら **STOP**（`codex` を一度起動してログイン）。
3. 依存チェック:

```bash
python3 -c "import PIL, pptx, requests, jinja2; print('OK')" 2>/dev/null || bash ${SKILL_DIR}/scripts/setup.sh
```

4. サブスク枠維持のため `OPENAI_API_KEY` は極力 unset（ブリッジが各実行でも自動除去する）。

## Phase 0: セッション準備

```bash
TIMESTAMP=$(date +%Y-%m-%d_%H%M) && OUTPUT_DIR="[指定された出力先]" && SESSION_DIR="${OUTPUT_DIR}/slides_output/${TIMESTAMP}" && mkdir -p ${SESSION_DIR}/{json,prompts,images}
```

## Phase 1: デザインガイドライン作成

テンプレート: `${SKILL_DIR}/references/design_guidelines_template.md`

**プリセット使用時:**

`design-setup` スキルでブランドを設定済みなら `references/presets/.active_preset` にプリセット名が記録されている。それを優先し、無ければ `example-preset.md` にフォールバックする。

```bash
ACTIVE_PRESET_FILE="${SKILL_DIR}/references/presets/.active_preset"
if [ -f "${ACTIVE_PRESET_FILE}" ]; then
  PRESET_NAME=$(cat "${ACTIVE_PRESET_FILE}")
  PRESET_PATH="${SKILL_DIR}/references/presets/${PRESET_NAME}"
  [ -f "${PRESET_PATH}" ] || PRESET_PATH="${SKILL_DIR}/references/presets/example-preset.md"
else
  PRESET_PATH="${SKILL_DIR}/references/presets/example-preset.md"
fi
cp "${PRESET_PATH}" "${SESSION_DIR}/design_guidelines.md"
echo "Using preset: $(basename "${PRESET_PATH}")"
```

**カスタム作成時** — テンプレート参照し以下を決定:
1. カラーパレット（テーマに合った色）
2. 写真スタイル（ターゲット層の年代・性別・シーン）
3. トーン（1-2文で方向性）
4. フォントサイズ（ターゲットに応じて調整）

```bash
cat > ${SESSION_DIR}/design_guidelines.md << 'EOF'
[カスタマイズした内容]
EOF
```

## Phase 2: slides_plan.json 作成（最重要）

Codex版は **Claude が単一パスで直接作成**する（サブエージェント並列fan-outは廃止）。
入力を読み、各スライドの content を丁寧に書く。

**content に含める項目:**
- `<!-- Pattern X: 説明 -->` — レイアウトヒント
- 表示テキスト全文（タイトル、箇条書き、数値データ）
- 背景写真指示（被写体、構図、雰囲気）
- 図解・アイコン・グラフの内容
- カラー使い分け（アクセント色の配置）
- 言語強制: `※スライド上の全テキストは{lang}で表示すること。`

**構成目安:** 表紙(G) → 課題提起(C/D) → ソリューション(B/C) → 市場(J) → ビジネスモデル(E) → 差別化(H/A) → ロードマップ(I) → まとめ(D) → CTA(G)

> 注: グラウンディング（`_grounding`）は Codex バックエンドでは非対応のため無視される。
> 大量枚数でも Claude が直接 JSON を書く（チャンク分割・サブエージェント統合は不要）。

### JSONスキーマ

```json
{
  "slides": [
    {
      "slide_number": 0,
      "source_file": "00_cover",
      "title": "タイトル",
      "subtitle": "サブタイトル",
      "content": "<!-- Pattern G --> ...",
      "key_message": "核心メッセージ1文",
      "_grounding": false
    }
  ],
  "total_slides": 12
}
```

**フィールド:**
- 必須: `slide_number`(数値), `source_file`(文字列), `title`, `subtitle`, `content`
- オプション: `key_message`(文字列), `_grounding`(真偽値)
- 禁止: `slide_type`, `layout`, `visual_description`（デザイン判断はGeminiが行う）

**命名規則:** 表紙 `"00_cover"` / 本編 `"01_xxx"`〜`"97_xxx"` / まとめ `"98_summary"` / CTA `"99_cta"`

### バリデーション

```bash
cat > ${SESSION_DIR}/json/slides_plan.json << 'JSONEOF'
{作成したJSON}
JSONEOF
${PYTHON} ${SKILL_DIR}/scripts/validate_slides_json.py --file ${SESSION_DIR}/json/slides_plan.json
```

## Phase 3: プロンプト生成 + グラウンディングマップ

`.active_style` ファイル（`design-setup` が書き出す）があればその値を `--style` に渡す。無ければ `balanced`。

```bash
ACTIVE_STYLE_FILE="${SKILL_DIR}/references/presets/.active_style"
if [ -f "${ACTIVE_STYLE_FILE}" ]; then
  STYLE=$(cat "${ACTIVE_STYLE_FILE}")
  [ -z "${STYLE}" ] && STYLE=balanced
else
  STYLE=balanced
fi

${PYTHON} ${SKILL_DIR}/scripts/generate_prompts_from_json.py \
  --session-dir ${SESSION_DIR} \
  --json-file json/slides_plan.json \
  --output-dir prompts \
  --design-guidelines ${SESSION_DIR}/design_guidelines.md \
  --style "${STYLE}" \
  --image-size 2K
```

**スタイル切替**:
- `--style balanced` (デフォルト) — 営業資料・提案書風
- `--style visual` — ピッチデッキ風（文字極少、ビジュアル主役）
- JSON で個別指定 — 各スライドに `"_style": "visual"` を書けば、そのスライドだけ Visual に

JSONでの混在例:
```json
{"source_file": "00_cover", "_style": "visual", "title": "...", "content": "..."},
{"source_file": "01_body", "title": "...", "content": "..."}
```
→ 表紙だけ Visual、本編は `--style` のデフォルト（balanced）を継承。

## Phase 3.5: プロンプト検証（任意）

```bash
${PYTHON} ${SKILL_DIR}/scripts/render_test.py \
  --session-dir ${SESSION_DIR} \
  --design-guidelines ${SESSION_DIR}/design_guidelines.md
```

## Phase 3.7: リファレンス画像マップ作成（任意）

特定のスライドに参照画像（キャラクター・ロゴ・写真等）をGeminiに渡したい場合、リファレンス画像マップを作成する。

```bash
cat > ${SESSION_DIR}/reference_image_map.json << 'JSONEOF'
{
  "Ryoko": "/path/to/ryoko_avatar.jpeg",
  "5-1.1_オープニング_07": "/path/to/specific_image.png"
}
JSONEOF
```

**マッチングルール:**
- キーがスライドのベース名に**部分一致**すれば適用される
- 例: `"Ryoko"` → `5-3.6_総合ケーススタディ_Ryoko_01.png` にマッチ
- 完全一致キーが優先される

ユーザーが画像を添付した場合、`${SESSION_DIR}/images/` にコピーしてマップに登録する。

## Phase 4: スライド画像生成（Codex / サブスク枠）

```bash
# サブスク枠維持: OPENAI_API_KEY が環境にあっても、この実行では使わせない
unset OPENAI_API_KEY 2>/dev/null
${PYTHON} ${SKILL_DIR}/scripts/generate_slides_parallel.py \
  --provider codex \
  --prompts-dir ${SESSION_DIR}/prompts \
  --output-dir ${SESSION_DIR}/images \
  --max-parallel 8 --max-retries 2 \
  --image-size 2K \
  --logo ${SKILL_DIR}/assets/logo.png
```

- `--api-key` は不要（Codex のログイン認証＝サブスク枠を使う）。
- 既定 `--max-parallel 8`。急ぎのバーストは `--max-parallel 20` まで実証済み（枠残量に注意）。
- 各スライドは独立 CODEX_HOME で生成するため、並列でも画像が混ざらない。
- 16:9 正規化・ロゴ右下合成・フッター中央下焼き込みは provider 内で自動適用。
- 常駐 App Server を使う場合: 実行前に `export CODEX_SLIDES_BACKEND=app-server`（experimental）。

**注意事項:**
- **`--logo` は常に付与する** — ユーザーが「ロゴ不要」と言った場合のみ省略。
- `--thinking-level` / `--grounding-map` / `--quality` は Codex では無視される。
- 解像度マップ: `1K=1792x1008`, `2K=2752x1536`, `4K=3840x2160`（すべて16:9）。

| パラメータ | デフォルト | 選択肢 |
|-----------|:---------:|--------|
| `--provider` | （codex 固定で指定） | codex |
| `--image-size` | 2K | 512px, 1K, 2K, 4K |
| `--max-parallel` | 8 | 実測で20までthrottle無し。累積枠に注意 |
| `--per-slide-timeout` | 600（codex） | 秒。重い枚数で延ばす |
| `--logo` | `${SKILL_DIR}/assets/logo.png` | 常に付与 |

## Phase 4.5: Claude↔Codex リレー（レビュー→特定スライド再生成・任意）

Claude が生成結果をレビューし、気になるスライドだけ Codex（サブスク枠）で作り直す。
`regenerate_slide.py` は Gemini 専用のため、Codex版では **該当プロンプトだけを再実行**する:

```bash
# 例: 02_solution_02 を作り直す（プロンプトを微調整したうえで上書き再生成）
unset OPENAI_API_KEY 2>/dev/null
${PYTHON} ${SKILL_DIR}/scripts/codex_app_server_client.py \
  --prompt "$(cat ${SESSION_DIR}/prompts/02_solution_02.txt)" \
  --output ${SESSION_DIR}/images/02_solution_02.png \
  --image-size 2K --aspect 16:9 --backend auto --max-retries 2
```

> 注: このブリッジ直叩きは 16:9 正規化・ロゴ・フッターを含まない素の生成。仕上げ込みで
> 作り直すなら、対象プロンプトのみを一時ディレクトリに置き Phase 4 を `--max-parallel 1` で再実行する。
> バージョニング（`_01.png`→`_01_v2.png`）が要るときも後者を使う（Phase 5は最新を自動選択）。

## Phase 5: PPTX/PDF生成

```bash
${PYTHON} ${SKILL_DIR}/scripts/export_to_pptx.py \
  --input-dir ${SESSION_DIR}/images --output ${OUTPUT_DIR}/${OUTPUT_NAME}.pptx && \
${PYTHON} ${SKILL_DIR}/scripts/export_to_pdf.py \
  --input-dir ${SESSION_DIR}/images --output ${OUTPUT_DIR}/${OUTPUT_NAME}.pdf
```

---

## 参照ドキュメント

| ファイル | 内容 |
|----------|------|
| [references/architecture.md](references/architecture.md) | アーキテクチャ図 + API仕様 |
| [references/troubleshooting.md](references/troubleshooting.md) | トラブルシューティング |
| [references/quality-checklist.md](references/quality-checklist.md) | 品質チェックリスト |
| [references/design_guidelines_template.md](references/design_guidelines_template.md) | デザインガイドラインテンプレート |
| [references/presets/](references/presets/) | プリセット集 |
| [templates/prompt_template.j2](templates/prompt_template.j2) | Jinja2テンプレート |
