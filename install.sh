#!/bin/bash
# TEKION Slide Generator v5 インストーラ
# 使い方:
#   ./install.sh            両方（Codex 版・Claude Code 版）を導入
#   ./install.sh --codex    Codex 版のみ
#   ./install.sh --claude   Claude Code 版のみ
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DO_CODEX=false
DO_CLAUDE=false

case "${1:-}" in
  --codex)  DO_CODEX=true ;;
  --claude) DO_CLAUDE=true ;;
  ""|--all) DO_CODEX=true; DO_CLAUDE=true ;;
  *) echo "usage: ./install.sh [--codex|--claude|--all]"; exit 1 ;;
esac

echo "== TEKION Slide Generator v5 install =="

# --- 依存チェック（共通）---
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 が必要です。" >&2; exit 1
fi
if ! python3 -c "import PIL, pptx" >/dev/null 2>&1; then
  echo "📦 Python 依存をインストール: Pillow python-pptx"
  pip3 install Pillow python-pptx -q || python3 -m pip install Pillow python-pptx -q
fi

# --- Codex CLI / ログイン確認 ---
if ! command -v codex >/dev/null 2>&1; then
  echo "⚠️  codex CLI が見つかりません。画像生成には Codex CLI が必要です: https://developers.openai.com/codex" >&2
fi
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
if [ ! -f "${CODEX_HOME_DIR}/auth.json" ]; then
  echo "⚠️  Codex 未ログインの可能性。'codex login' で ChatGPT/Codex にサインインしてください（サブスク枠で生成）。" >&2
fi

install_one() {
  local src="$1" dst_dir="$2" name="tekion-slide-generator-v5"
  mkdir -p "${dst_dir}"
  rm -rf "${dst_dir}/${name}"
  cp -R "${src}" "${dst_dir}/${name}"
  find "${dst_dir}/${name}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  echo "✓ installed: ${dst_dir}/${name}"
}

if $DO_CODEX; then
  install_one "${REPO_DIR}/skills/codex/tekion-slide-generator-v5" "${CODEX_HOME_DIR}/skills"
fi
if $DO_CLAUDE; then
  install_one "${REPO_DIR}/skills/claude-code/tekion-slide-generator-v5" "${HOME}/.claude/skills"
fi

echo ""
echo "完了。OPENAI_API_KEY は unset 推奨（サブスク枠維持。スキルも自動除去します）。"
echo "Codex 版: 'codex' で「スライドを作って」 / Claude 版: Claude Code で「Codexでスライドを作って」"
