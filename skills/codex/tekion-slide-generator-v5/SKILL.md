---
name: "tekion-slide-generator-v5"
description: "Markdown/テキストから日本語プレゼンスライド（16:9）を作り、PPTX/PDF として書き出す。Codex 内蔵の画像生成（gpt-image-2, $imagegen）をそのまま使うため OPENAI_API_KEY 不要・ChatGPT/Codex のサブスク枠で完結する。『スライドを作って』『プレゼン資料を作って』『この資料を提案書スライドに』のような依頼で使う。各スライドを画像として生成し、16:9 正規化・ロゴ・フッターを焼き込み、PPTX と PDF を出力する。デザイン提案書・営業資料・登壇ピッチに向く。"
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
mkdir -p "${WORK}/raw" "${WORK}/images"
```

### Phase 1: デザイン方針（簡潔に決める）

入力（Markdown/テキスト/依頼内容）を読み、以下を1〜2文で決める。スライド全体で一貫させる。
- カラーパレット（例: ネイビー基調＋ブルー/ティールのアクセント、白背景）
- トーン（営業資料＝図解と要点／登壇＝余白広め・ビジュアル主役）
- フォント感（太字見出し＋簡潔な本文）
- **言語: スライド上の全テキストは日本語**（固有名詞のみ英語可）

### Phase 2: スライド構成

各スライドについて `{ファイル名, プロンプト}` を決める。命名は `00_cover` / `01_xxx` … `99_cta`。
構成目安: 表紙 → 課題 → ソリューション → 詳細/比較 → まとめ → CTA。

プロンプトに必ず含める:
- レイアウト指示（全面ビジュアル／見出し＋3-5箇条／3ステップ図 等）
- 表示テキスト全文（タイトル・箇条書き・数値）
- 配色・アクセントの使い方
- **「16:9 横長、2K 相当の高精細、スライド上の全テキストは日本語」** を毎回明記

### Phase 3: 画像生成（既定 = 並列。サブスク枠で完結）

**既定は B（並列）。** 速くて大量にも強い。**1〜2枚のごく少数のときだけ A（in-loop）**に切り替える。
いずれも `OPENAI_API_KEY` は使わない＝**サブスク枠の gpt-image-2** で生成（API課金にならない）。

#### B. 並列（既定 / 子 codex exec を並列起動）

各スライドを**独立した子 codex exec** に投げ、サブスク枠の gpt-image-2 を並列で叩く
（**実測: 2K で並列20→20枚を約67秒**。逐次なら20分相当）。

1. Phase 2 の各スライドのプロンプトを **`${WORK}/prompts/<ファイル名>.txt`** に書き出す（`00_cover.txt` 等）。
2. 並列生成（warmup・認証コピー・**レート制限フォールバックは内部で自動**）:

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

#### A. in-loop（1〜2枚のときだけ / 内蔵 image_gen を1枚ずつ＝逐次）

1. 内蔵画像生成ツール（`$imagegen` / image_gen）で Phase 2 のプロンプトを **16:9・2K** で1枚生成。
2. 生成物（既定 `$CODEX_HOME/generated_images/...`）を **`${WORK}/raw/<ファイル名>.png` に move/copy**。
3. くり返す。子プロセスを起こさない分わずかに軽いが、枚数が増えると遅い。

### Phase 4: 仕上げ（16:9正規化・ロゴ・フッター）

内蔵生成は厳密な 16:9 やフッターを保証しないため、ここで確定的に仕上げる。

```bash
${PY} "${SKILL_DIR}/scripts/finalize_slides.py" \
  --input-dir "${WORK}/raw" \
  --output-dir "${WORK}/images" \
  --image-size 2K \
  --logo "${SKILL_DIR}/assets/logo.png"
```

ロゴ不要と言われたら `--logo` を省略する。

### Phase 5: PPTX/PDF 出力

```bash
${PY} "${SKILL_DIR}/scripts/export_to_pptx.py" \
  --input-dir "${WORK}/images" --output "${WORK}/deck.pptx" && \
${PY} "${SKILL_DIR}/scripts/export_to_pdf.py" \
  --input-dir "${WORK}/images" --output "${WORK}/deck.pdf"
```

完成物: `${WORK}/deck.pptx` と `${WORK}/deck.pdf`、各スライド画像は `${WORK}/images/`。

## 特定スライドの作り直し

気になるスライドだけ、プロンプトを調整して image_gen で再生成し `${WORK}/raw/<名前>.png` を上書き →
`finalize_slides.py` を再実行 → Phase 5 で出力し直す。バージョンを残したいなら `<名前>_v2.png` 等にする
（export は同名ベースの最新版を自動採用）。

## 注意

- `OPENAI_API_KEY` を環境に置かない（内蔵＝サブスク枠を維持するため。あると従量課金に切替わる）。
- 解像度は `--image-size` で 512px/1K/2K/4K（既定 2K、すべて 16:9）。
- 速度: 少枚数は A（in-loop）、大量は B（`generate_parallel.py` の子 codex exec 並列、最大20実証）。
- このスキルは ChatGPT/Codex 契約のみで完結（Claude も OpenAI API キーも不要）。
