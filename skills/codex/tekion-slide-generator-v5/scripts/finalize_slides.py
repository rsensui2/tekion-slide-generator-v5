#!/usr/bin/env python3
"""スライド画像の仕上げ（16:9正規化 → ロゴ合成 → フッター焼き込み）一括処理。

Codex の内蔵 image_gen が生成した raw 画像は、16:9 が厳密でなかったり、ロゴ・
フッターを含まない。本スクリプトは入力ディレクトリの全画像に対し、

  1. 16:9 ターゲット解像度へ正規化（テキスト欠けを避けるためクロップせずパッド）
  2. ロゴを右下に合成（任意）
  3. フッターウォーターマークを中央下に焼き込み

を適用し、出力ディレクトリへ PNG 保存する。Claude版 providers/codex.py と同じ仕上げ。

使い方:
    python3 finalize_slides.py --input-dir raw --output-dir images \
        --image-size 2K --logo ../assets/logo.png
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from io import BytesIO


# 共通サイズラベル → 16:9 ターゲット解像度（Claude版と統一）
SIZE_MAP = {
    "512px": "1280x720",
    "1K":    "1792x1008",
    "2K":    "2752x1536",
    "4K":    "3840x2160",
}


def target_dims(size_label: str) -> tuple[int, int]:
    spec = SIZE_MAP.get(size_label, "2752x1536")
    w, h = spec.lower().split("x")
    return int(w), int(h)


def normalize_to_16_9(img, target_w: int, target_h: int):
    """16:9 ターゲットへ正規化。概ね16:9ならリサイズ、大きくずれたらレターボックス。"""
    from PIL import Image, ImageOps

    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    target_ratio = target_w / target_h
    src_ratio = img.width / img.height
    if abs(src_ratio - target_ratio) / target_ratio <= 0.02:
        return img.resize((target_w, target_h), Image.LANCZOS)
    bg = (255, 255, 255) if img.mode == "RGB" else (255, 255, 255, 255)
    return ImageOps.pad(img, (target_w, target_h), method=Image.LANCZOS, color=bg)


def composite_logo(img, logo_path: str):
    """右下にロゴを合成（幅の約9%、余白付き）。"""
    from PIL import Image

    if not logo_path or not os.path.exists(logo_path):
        return img
    base = img.convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")
    target_w = max(1, int(base.width * 0.09))
    ratio = target_w / logo.width
    target_h = max(1, int(logo.height * ratio))
    logo = logo.resize((target_w, target_h), Image.LANCZOS)
    margin = int(base.width * 0.025)
    base.alpha_composite(logo, (base.width - target_w - margin, base.height - target_h - margin))
    return base


def finalize_one(in_path: str, out_path: str, target_w: int, target_h: int, logo_path: str) -> None:
    from PIL import Image

    img = Image.open(in_path)
    img.load()
    img = normalize_to_16_9(img, target_w, target_h)
    if logo_path and os.path.exists(logo_path):
        img = composite_logo(img, logo_path)

    # フッター焼き込み（footer_utils を再利用）
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from footer_utils import apply_footer_to_bytes

    buf = BytesIO()
    img.save(buf, format="PNG")
    final_bytes = apply_footer_to_bytes(buf.getvalue(), output_format="PNG")
    with open(out_path, "wb") as f:
        f.write(final_bytes)


def main() -> int:
    ap = argparse.ArgumentParser(description="スライド画像の仕上げ（16:9/ロゴ/フッター）")
    ap.add_argument("--input-dir", required=True, help="raw 画像ディレクトリ（*.png）")
    ap.add_argument("--output-dir", required=True, help="仕上げ出力ディレクトリ")
    ap.add_argument("--image-size", default="2K", choices=list(SIZE_MAP.keys()))
    ap.add_argument("--logo", default=None, help="ロゴ画像パス（任意）")
    ap.add_argument("--pattern", default="*.png", help="入力パターン（既定 *.png）")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    target_w, target_h = target_dims(args.image_size)

    files = sorted(glob.glob(os.path.join(args.input_dir, args.pattern)))
    if not files:
        print(f"❌ 入力画像が見つかりません: {args.input_dir}/{args.pattern}", file=sys.stderr)
        return 1

    ok = 0
    for in_path in files:
        out_path = os.path.join(args.output_dir, os.path.basename(in_path))
        try:
            finalize_one(in_path, out_path, target_w, target_h, args.logo)
            ok += 1
            print(f"✅ 仕上げ: {os.path.basename(out_path)} ({target_w}x{target_h})")
        except Exception as e:
            print(f"❌ 失敗: {os.path.basename(in_path)} - {type(e).__name__}: {e}", file=sys.stderr)

    print(f"\n完了: {ok}/{len(files)} 枚")
    return 0 if ok == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())
