#!/usr/bin/env python3
"""ネイティブ版の高速生成: 子 codex exec を並列起動して raw 画像を作る。

Codex 内蔵の image_gen は in-loop では逐次（1ターン1アセット）のため、大量枚数は遅い。
本スクリプトは各スライドを **独立した子 codex exec** に投げ、サブスク枠の gpt-image-2 を
並列で叩く（親が Codex でも Claude でも同じ機構）。生成は raw 画像（16:9正規化・ロゴ・
フッターは未適用）として保存し、後段の finalize_slides.py で仕上げる。

認証の安全策（重要）:
- ファンアウト前に warmup でアクセストークンを更新（複数子プロセスの同時トークン更新＝
  refresh token 競合による失効を防ぐ）。
- 各子プロセスは auth.json を **コピー** した独立 CODEX_HOME で動く（実 auth.json を壊さない）。
- これらは codex_app_server_client.py 側で実装済み。

使い方:
    python3 generate_parallel.py --prompts-dir prompts --output-dir raw \
        --max-parallel 8 --image-size 2K
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed


# レート制限/枠超過のサイン（一時的＝デグレードして再試行する）
RATE_SIGNS = (
    "429", "rate limit", "rate_limit", "too many requests", "usage limit",
    "quota", "resource_exhausted", "overloaded", "try again",
)
# 認証失効のサイン（恒久的＝再ログインが必要、即停止）
AUTH_SIGNS = ("token_revoked", "refresh_token", "sign in again", "401")


def _classify(error: str) -> str:
    """エラー文字列を 'auth' / 'rate' / 'other' に分類する。"""
    e = (error or "").lower()
    if any(s in e for s in AUTH_SIGNS):
        return "auth"
    if any(s in e for s in RATE_SIGNS):
        return "rate"
    return "other"


def _gen_one(task):
    prompt_file, out_path, image_size, max_retries, billing = task
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from codex_app_server_client import generate_image

    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read()
        res = generate_image(
            prompt=prompt,
            output_path=out_path,
            image_size=image_size,
            aspect="16:9",
            backend="exec",
            billing=billing,
            max_retries=max_retries,
        )
        if res.ok and res.image_bytes:
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(res.image_bytes)
            return (True, out_path, None)
        return (False, out_path, res.error)
    except Exception as e:
        return (False, out_path, f"{type(e).__name__}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="子codex exec並列でraw画像を生成（ネイティブ版高速モード）")
    ap.add_argument("--prompts-dir", required=True, help="プロンプト *.txt ディレクトリ")
    ap.add_argument("--output-dir", required=True, help="raw 画像の出力先")
    ap.add_argument("--max-parallel", type=int, default=8, help="並列数（既定8、最大20まで実証済み）")
    ap.add_argument("--max-retries", type=int, default=2)
    ap.add_argument("--max-rounds", type=int, default=5,
                    help="レート制限フォールバックの最大ラウンド数（並列度を段階的に下げて再試行）")
    ap.add_argument("--billing", default="subscription", choices=["subscription", "api"],
                    help="subscription=サブスク枠(既定・OPENAI_API_KEY除去) / api=OpenAI API従量課金(キー使用)")
    ap.add_argument("--image-size", default="2K", choices=["512px", "1K", "2K", "4K"])
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    prompt_files = sorted(glob.glob(os.path.join(args.prompts_dir, "*.txt")))
    if not prompt_files:
        print(f"❌ プロンプトが見つかりません: {args.prompts_dir}/*.txt", file=sys.stderr)
        return 1

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if args.billing == "api":
        # API 従量課金モード: OPENAI_API_KEY を使う。OAuth トークン更新は不要なので warmup しない。
        if not os.environ.get("OPENAI_API_KEY"):
            print("⚠️  --billing api だが OPENAI_API_KEY が未設定。Codex はサブスク枠に切替わります。",
                  file=sys.stderr)
        else:
            print("💳 課金モード: OpenAI API（従量課金）。OPENAI_API_KEY を使用します。", file=sys.stderr)
    else:
        # サブスク枠: 並列前にトークンを更新（refresh token 競合による失効を防ぐ）
        from codex_app_server_client import warmup_auth
        print("🔑 課金モード: サブスク枠。認証ウォームアップ中（並列前にトークン更新）...", file=sys.stderr)
        if not warmup_auth():
            print("❌ Codex 認証が無効です。`codex login` で再ログインしてください。", file=sys.stderr)
            return 2
        print("✓ 認証OK。並列生成を開始します。", file=sys.stderr)

    tasks = []
    for pf in prompt_files:
        base = os.path.splitext(os.path.basename(pf))[0]
        tasks.append((pf, os.path.join(args.output_dir, f"{base}.png"),
                      args.image_size, args.max_retries, args.billing))

    total = len(tasks)
    done_ok = set()

    # フォールバック: レート制限に当たったら並列度を段階的に下げて再試行する梯子。
    # 認証失効を検知したら即停止（再ログインが必要）。
    concurrency = max(1, args.max_parallel)
    remaining = list(tasks)
    round_no = 0
    while remaining:
        round_no += 1
        label = f"ラウンド{round_no}（並列{concurrency}, 残り{len(remaining)}枚）"
        print(f"▶ {label} ...", file=sys.stderr)
        failures = []
        rate_hit = False
        auth_hit = False
        with ProcessPoolExecutor(max_workers=concurrency) as ex:
            futs = {ex.submit(_gen_one, t): t for t in remaining}
            for fut in as_completed(futs):
                t = futs[fut]
                success, out_path, err = fut.result()
                if success:
                    done_ok.add(out_path)
                    print(f"✓ [{len(done_ok)}/{total}] {os.path.basename(out_path)}")
                else:
                    kind = _classify(err)
                    failures.append(t)
                    print(f"✗ {os.path.basename(out_path)} [{kind}] - {err}")
                    if kind == "auth":
                        auth_hit = True
                    elif kind == "rate":
                        rate_hit = True

        if auth_hit:
            print("\n❌ 認証が失効しました（token_revoked）。`codex login` で再ログインしてから再実行してください。",
                  file=sys.stderr)
            return 2

        remaining = failures
        if not remaining:
            break

        # 安全弁: ラウンド上限（並列1でレート制限が続く場合の無限ループ防止）
        if round_no >= args.max_rounds:
            print(f"⚠ 最大ラウンド数 {args.max_rounds} に到達。残り {len(remaining)} 枚は中断します。",
                  file=sys.stderr)
            break
        # 非レート要因で並列1でも失敗が続く → 自動回復見込みなし
        if concurrency <= 1 and not rate_hit:
            break

        # まだ失敗が残る → 並列度を下げ、レート制限ならバックオフして再試行
        new_conc = max(1, concurrency // 2)
        backoff = 20 if rate_hit else 5
        reason = "レート制限を検知" if rate_hit else "失敗を検知"
        print(f"⤵ {reason}。並列 {concurrency}→{new_conc} に下げ {backoff}s 待機後に再試行。",
              file=sys.stderr)
        concurrency = new_conc
        time.sleep(backoff)

    ok = len(done_ok)
    print(f"\n完了: {ok}/{total} 枚")
    if remaining:
        print("最終的に失敗したスライド（時間をおいて再実行 or `codex login` を検討）:", file=sys.stderr)
        for pf, out_path, _, _ in remaining:
            print(f"  - {os.path.basename(out_path)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
