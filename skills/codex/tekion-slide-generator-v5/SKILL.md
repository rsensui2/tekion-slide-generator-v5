---
name: "tekion-slide-generator-v5"
description: "TEKION Slide Generator v5（Codexネイティブ版） — Markdown/テキストから日本語プレゼンスライド（16:9）を作り PPTX/PDF まで書き出す。『スライドを作って』『プレゼン資料/提案書/企画書/ピッチデッキにして』『この資料をデッキ化』『登壇用の資料』のようにスライド作成を求められたら、ツール名を言わなくても使うこと。Codex 内蔵の画像生成（gpt-image-2 / $imagegen）をそのまま使うため OPENAI_API_KEY 不要・ChatGPT/Codex のサブスク枠だけで完結（必要なら --billing api で OpenAI API 従量課金も可）。TEKION ブランド（プリセット）適用・子 codex exec 並列生成・16:9 正規化・ロゴ/フッター焼き込み・PPTX/PDF 出力。デザイン提案書・営業資料・登壇ピッチ向け。"
---

# TEKION Slide Generator（Codexネイティブ版）

Markdown/テキスト → デザイン方針 → スライド画像生成（**Codex 内蔵 gpt-image-2＝サブスク枠**）→
16:9 仕上げ（ロゴ・フッター）→ PPTX/PDF。**OPENAI_API_KEY は不要**（あると従量課金に切替わるので使わない）。

このスキルは Codex 単体（ChatGPT/Codex 契約のみ）で完結する。外部の Claude Code も
OpenAI API キーも不要。画像生成は**内蔵 image_gen ツールを in-loop で直呼び**する。

## スキルの場所と定数

```bash
SKILL_DIR="$CODEX_HOME/skills/tekion-slide-generator"   # 既定 ~/.codex/skills/tekion-slide-generator
PY="python3"
```

## 前提

- Codex にログイン済み（サブスク枠）。`OPENAI_API_KEY` は**設定しない**。
- Python 3.10+ と Pillow / python-pptx が必要。未導入なら:
  ```bash
  python3 -c "import PIL, pptx" 2>/dev/null || pip3 install Pillow python-pptx -q
  ```

## ワークフロー

### Phase 0: 作業ディレクトリ

```bash
TS=$(date +%Y-%m-%d_%H%M)
WORK="${OUTPUT_DIR:-.}/slides_${TS}"      # OUTPUT_DIR 未指定ならカレント
mkdir -p "${WORK}/json" "${WORK}/prompts" "${WORK}/raw" "${WORK}/images"
```

### Phase 1: デザインガイドライン（ブランド適用｜重要）

**ブランド（配色・フォント・レイアウト）は自分で文章にせず、プリセットを通すこと。**
これを省くとブランドが効かず毎回バラバラの見た目になる。プリセットは `references/presets/*.md` に定義され、
`design_guidelines.md` として使う。既定の `example-preset.md` は
**TEKION ブランド（Primary オレンジ #EA5514・白背景・60-30-10 ルール・Pattern A〜K）**。

```bash
PRESET="${SKILL_DIR}/references/presets/example-preset.md"   # 既定 = TEKION
# 自社ブランドにするなら presets/ に自前 .md を作り、ここを差し替える
cp "${PRESET}" "${WORK}/design_guidelines.md"
```

### Phase 2: slides_plan.json（構成・テキストのみ）

各スライドを JSON で記述する。**配色・カラーコード・デザイン演出は書かない（プリセットが担当）。**
テキストとレイアウトの意図だけを書く。`source_file` は共通名（例 `"deck"`）、`slide_number` は連番。

```json
{
  "slides": [
    {"slide_number":1,"source_file":"deck","title":"タイトル","subtitle":"サブ","content":"講座タイトルスライド（表紙）。中央に大見出し＋サブ。テキストとレイアウトのみ記述（色は書かない）"},
    {"slide_number":2,"source_file":"deck","title":"見出し","content":"見出し＋3-5項目の箇条書き、または2-3ブロックの図解。表示テキストを全文記述"}
  ],
  "total_slides": 2
}
```

- 必須: `slide_number` / `source_file` / `title` / `content`。任意: `subtitle` / `key_message` / `_style`（`visual`/`balanced`）。
- 表紙は content に「講座タイトルスライド（表紙）」、中扉は「中扉スライド」と書くと専用レイアウトになる。
- 保存: `${WORK}/json/slides_plan.json`。検証: `${PY} "${SKILL_DIR}/scripts/validate_slides_json.py" --file "${WORK}/json/slides_plan.json"`。

### Phase 3: プロンプト生成（デザイン注入）

slides_plan.json ＋ design_guidelines.md を Jinja2 テンプレに通し、**ブランド配色・レイアウト・ロゴ指示が
注入された**プロンプトを作る。ここがブランド適用の要。

```bash
${PY} "${SKILL_DIR}/scripts/generate_prompts_from_json.py" \
  --session-dir "${WORK}" --json-file json/slides_plan.json --output-dir prompts \
  --design-guidelines "${WORK}/design_guidelines.md" --style balanced --image-size 2K
```

- `--style balanced`（営業資料・提案書）/ `visual`（登壇・ピッチ）。スライド毎は JSON の `_style` で上書き可。
- 出力: `${WORK}/prompts/<source_file>_NN.txt`（プリセットの配色等が各プロンプトに焼き込まれる）。

### Phase 4: 画像生成（既定 = 並列。サブスク枠で完結）

**既定は B（並列）。** Phase 3 で出来たプロンプトを子 codex exec で並列生成する。
**1〜2枚のごく少数のときだけ A（in-loop）**でもよい。
いずれも `OPENAI_API_KEY` は使わない＝**サブスク枠の gpt-image-2** で生成（API課金にならない）。

#### B. 並列（既定 / 子 codex exec を並列起動）

各スライドを**独立した子 codex exec** に投げ、サブスク枠の gpt-image-2 を並列で叩く
（**実測: 2K で並列20→20枚を約67秒**。逐次なら20分相当）。

Phase 3 で生成したプロンプト（`${WORK}/prompts/`）を並列生成（warmup・認証コピー・**レート制限フォールバックは内部で自動**）:

```bash
${PY} "${SKILL_DIR}/scripts/generate_parallel.py" \
  --prompts-dir "${WORK}/prompts" \
  --output-dir "${WORK}/raw" \
  --max-parallel 8 --image-size 2K
```

- 既定 `--max-parallel 8`。急ぎは `--max-parallel 20` まで実証済み（枠残量に注意）。
- 子 codex exec は各自の隔離 CODEX_HOME（auth.json は**コピー**）で動き、生成画像も混ざらない。
- **レート制限フォールバック（自動）**: 失敗が出ると並列度を段階的に下げ（8→4→2→1）バックオフ再試行。
  `token_revoked`（認証失効）を検知したら停止し **`codex login` 再ログイン**を促す。
- サブスク枠の画像ターンは消費が速い（公式: 通常の3-5倍）。**累積**で日次/週次 usage limit に達し得る。

##### 課金モード（`--billing`）

| モード | 指定 | 挙動 |
|---|---|---|
| **subscription（既定）** | （指定不要）/ `--billing subscription` | ChatGPT/Codex サブスク枠で生成。実行時に `OPENAI_API_KEY` を**除去**（気づかず従量課金される事故を防ぐ安全策）。 |
| **api** | `--billing api` | **OpenAI API 従量課金**で生成。`OPENAI_API_KEY` を使う（枠を消費したくない/usage limit回避に）。 |

- 環境変数 `CODEX_SLIDES_BILLING=api` でも切替可。
- 実行時にどちらのモードかをログに明示（`[サブスク枠]` / `[API従量課金]`）。黙って剥がさない。
- `--billing api` でも `OPENAI_API_KEY` 未設定なら自動的にサブスク枠にフォールバック（警告を表示）。
- api モードは usage limit を消費しないため warmup（OAuthトークン更新）はスキップする。

#### A. in-loop（1〜2枚のときだけ / 内蔵 image_gen を1枚ずつ＝逐次）

1. 内蔵画像生成ツール（`$imagegen` / image_gen）で Phase 3 のプロンプト（`${WORK}/prompts/<名前>.txt`）を **16:9・2K** で1枚生成。
2. 生成物（既定 `$CODEX_HOME/generated_images/...`）を **`${WORK}/raw/<名前>.png` に move/copy**。
3. くり返す。子プロセスを起こさない分わずかに軽いが、枚数が増えると遅い。

### Phase 5: 仕上げ（16:9正規化・ロゴ・フッター）

内蔵生成は厳密な 16:9 やフッターを保証しないため、ここで確定的に仕上げる。

```bash
${PY} "${SKILL_DIR}/scripts/finalize_slides.py" \
  --input-dir "${WORK}/raw" \
  --output-dir "${WORK}/images" \
  --image-size 2K \
  --logo "${SKILL_DIR}/assets/logo.png"
```

ロゴ不要と言われたら `--logo` を省略する。
（Phase 3 のテンプレにもロゴ指示は入るが、ロゴは実画像を確実に焼くためここでローカル合成する。）

### Phase 6: PPTX/PDF 出力

```bash
${PY} "${SKILL_DIR}/scripts/export_to_pptx.py" \
  --input-dir "${WORK}/images" --output "${WORK}/deck.pptx" && \
${PY} "${SKILL_DIR}/scripts/export_to_pdf.py" \
  --input-dir "${WORK}/images" --output "${WORK}/deck.pdf"
```

完成物: `${WORK}/deck.pptx` と `${WORK}/deck.pdf`、各スライド画像は `${WORK}/images/`。

## 特定スライドの作り直し

気になるスライドだけ slides_plan.json の content を直し、Phase 3（そのスライドのみ）→ Phase 4 →
Phase 5 を回して `${WORK}/raw/<名前>.png` を更新 → Phase 6 で出力し直す。バージョンを残したいなら
`<名前>_v2.png` 等にする（export は同名ベースの最新版を自動採用）。

## 注意

- **ブランドは必ず Phase 1→3 を通す**（プリセット→テンプレ注入）。生プロンプト直書きはブランドが効かない。
- `OPENAI_API_KEY` を環境に置かない（既定サブスク枠を維持するため。`--billing api` 指定時のみ使う）。
- 解像度は `--image-size` で 512px/1K/2K/4K（既定 2K、すべて 16:9）。
- 速度: 少枚数は A（in-loop）、大量は B（`generate_parallel.py` の子 codex exec 並列、最大20実証）。
- このスキルは ChatGPT/Codex 契約のみで完結（Claude も OpenAI API キーも不要。`--billing api` 時のみ OpenAI キー）。
