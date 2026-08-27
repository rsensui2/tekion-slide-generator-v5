# 受講生への配布用プロンプト

下のコードブロックを丸ごとコピーし、CodexまたはClaude Codeのチャットへ貼り付けてください。セットアップ、動作確認、最初の使い方までエージェントが案内します。

```text
「TEKION Slide Generator v5」を、この環境へセットアップしてください。

配布元:
https://github.com/rsensui2/tekion-slide-generator-v5

次の順に進めてください。

1. 自分がCodexとClaude Codeのどちらで動いているかを判定してください。
2. `git`、`python3`、`codex`の有無を確認してください。見つからないものがあれば、勝手に別のツールへ置き換えず、必要な準備を日本語で案内してください。
3. `mktemp -d`で作業用フォルダを作り、配布元を`git clone --depth 1`してください。
4. Codexで動いている場合は、取得したフォルダで`./install.sh --codex`を実行してください。Claude Codeで動いている場合は、`./install.sh --claude`を実行してください。
5. Codexをサブスクリプション枠で使う場合は、`codex login`の状態を確認してください。未ログインなら、認証情報を聞き出さず、利用者自身がブラウザでログインできるよう案内してください。
6. 次のファイルがあることを確認してください。
   - Codex: `~/.codex/skills/tekion-slide-generator-v5/SKILL.md`
   - Claude Code: `~/.claude/skills/tekion-slide-generator-v5/SKILL.md`
7. セットアップが終わったら、結果と確認できたファイルを報告してください。その後、新しいチャットを開き、次のように頼めば使えると案内してください。

   この原稿を、営業提案用のスライド5枚にしてください。PPTXとPDFで書き出してください。

画像生成は、原則としてCodex内蔵のgpt-image-2とChatGPT/Codexのサブスクリプション枠を使ってください。利用者が明示的に希望しない限り、OpenAI APIの従量課金へ切り替えたり、APIキーの入力を求めたりしないでください。
```

## 配布前の確認

- Codex版とClaude Code版の両方で、保存先に`SKILL.md`が作られる
- 新しいチャットで「スライドを作って」と頼むとv5が呼び出される
- APIキーを要求せず、サブスクリプション枠で進む
- 生成したPPTXとPDFを開ける
