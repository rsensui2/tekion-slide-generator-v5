# Changelog

本プロジェクトの主要な変更を記録します。日付は JST（Asia/Tokyo）。

## [v5.0.1] - 2026-06-05

### Fixed — warmup が Codex アプリの再認証を誘発する不具合（重要）

並列生成前の `warmup_auth()`（OAuth トークンの事前リフレッシュ）が、**実体の
`~/.codex/auth.json` に対して直接** `codex exec` を実行していた。Codex の
refresh_token は単回使用でサーバ側ローテーションされるため、warmup が走るたびに
実ファイルのトークンが回転し、**同じ `auth.json` を握っている Codex アプリ側の
トークンが失効 → 再ログインを要求される**事象が起きていた。

- **根本原因**: warmup が隔離ホームを使わず、実 `~/.codex/auth.json` を更新していた。
- **修正**:
  - `warmup_auth()` を**隔離ホーム（auth.json のコピー）**で実行するよう変更。
    実体の `~/.codex/auth.json` は v5 から一切書き換えない。
  - warmup でリフレッシュ済みの新鮮な auth を、環境変数
    `CODEX_SLIDES_WARM_AUTH` 経由で並列ワーカーへ伝播。
    （macOS の multiprocessing は spawn のため、モジュールグローバルでは
    子プロセスに渡らない。環境変数で確実に伝播させる。）
  - warm-auth 一時ファイルは認証情報のため `atexit` で確実に削除（`/tmp` に残さない）。
  - `token_revoked` / `refresh_token_reused` / `sign in again` を検知したら停止し、
    `codex login` での再ログインを促す。
- **検証**: `warmup_auth()` 実行の前後で `shasum -a 256 ~/.codex/auth.json` が
  **不変**であることを確認（実ファイルを書き換えない＝アプリ再認証を誘発しない）。

> このフィードバックを寄せてくれた v5 ユーザーに感謝します（warmup が実 auth.json を
> 更新してアプリ再認証が起きる、という的確な指摘）。修正の意図は同一で、spawn 環境でも
> 確実に伝播するよう実装は環境変数方式を採用しています。

#### 既知の補足
access_token が有効な通常ケースでは warmup はファイルを書き換えず完全に安全。
万一 access_token が失効していると、隔離コピー上でのリフレッシュでもサーバ側の
refresh_token はローテーションされ得る（共有トークンの仕様）。実ファイルは保護されるが、
この場合に限りアプリ側で再認証が必要になり得る点に留意。

## [v5.0.0] - 2026-06-04

### Added — 初回公開

- TEKION Slide Generator v5（Claude Code 版 / Codex ネイティブ版の2系統）。
- Codex 内蔵 gpt-image-2 を **ChatGPT/Codex サブスク枠**で利用（`OPENAI_API_KEY` 不要）。
  実行時に環境から `OPENAI_API_KEY` を除去し、気づかぬ従量課金を防止。
- `--billing subscription|api`（既定 subscription）で課金モードを明示切替。
- 子 `codex exec` の**並列画像生成**（隔離 CODEX_HOME・auth.json はコピー）。
  レート制限時は並列度を段階的に縮退（8→4→2→1）してバックオフ再試行。
- TEKION ブランド（プリセット `#EA5514`）→ `design_guidelines.md` → Jinja2 テンプレ注入の
  デザインパイプライン。16:9 正規化・ロゴ/フッター焼き込み・PPTX/PDF 出力。
- Source-available proprietary ライセンス（改変・再配布制限あり。`LICENSE` / `NOTICE` 参照）。

[v5.0.1]: https://github.com/rsensui2/tekion-slide-generator-v5/releases/tag/v5.0.1
[v5.0.0]: https://github.com/rsensui2/tekion-slide-generator-v5/releases/tag/v5.0.0
