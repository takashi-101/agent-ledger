# AIエージェント台帳

道具 9 件（MCPサーバー 8、スキル 1）。権限区分：実行 2、外部送信 4、書き込み 2、読み取り 1。
指摘：高 3、中 12、低 0、情報 1。

## 指摘
| 重さ | ID | 指摘 | 対象 | 内容 | 理由と対応 | 根拠 |
|---|---|---|---|---|---|---|
| 高 | L01 | 秘密情報の直書き | chat-bot | CHAT_API_TOKEN に値が直接書かれている | 鍵やトークンが設定ファイルに書かれている。環境変数や入力欄からの参照に替える | OWASP ASI03／セキュリティ確保 |
| 高 | L03 | 広すぎるフォルダ | filesystem | 引数 C:\Users\taro | ドライブ全体や利用者のフォルダ全体を渡している。業務に要るフォルダだけにする | OWASP ASI02／安全性 |
| 高 | L07 | 取得したスクリプトの実行 | report-maker | 取得して実行する記述がある | スキルの中で、ネットから取得したスクリプトをそのまま実行している | OWASP ASI04, ASI05／セキュリティ確保 |
| 中 | L02 | 版の固定なし | browser | example/browser-mcp:latest | 起動のたびに最新版を取りに行く。承認した版と違うものが動きうる | OWASP ASI04／セキュリティ確保 |
| 中 | L02 | 版の固定なし | filesystem | @modelcontextprotocol/server-filesystem | 起動のたびに最新版を取りに行く。承認した版と違うものが動きうる | OWASP ASI04／セキュリティ確保 |
| 中 | L04 | 暗号化されていない接続 | intranet-search | http://search.intra.example.local/mcp | 手元以外のサーバーに http で接続している | -／セキュリティ確保 |
| 中 | L05 | コマンド実行の権限 | ops-shell | ops-shell | 任意のコマンドを実行できる道具。隔離した環境か、人の承認を挟む | OWASP ASI05／安全性 |
| 中 | L05 | コマンド実行の権限 | report-maker | report-maker | 任意のコマンドを実行できる道具。隔離した環境か、人の承認を挟む | OWASP ASI05／安全性 |
| 中 | L06 | 管理者・停止手順の未記入 | browser | browser | 誰が管理し、どう止めるかが台帳に無い | OWASP ASI10／アカウンタビリティ |
| 中 | L06 | 管理者・停止手順の未記入 | chat-bot | chat-bot | 誰が管理し、どう止めるかが台帳に無い | OWASP ASI10／アカウンタビリティ |
| 中 | L06 | 管理者・停止手順の未記入 | filesystem | filesystem | 誰が管理し、どう止めるかが台帳に無い | OWASP ASI10／アカウンタビリティ |
| 中 | L06 | 管理者・停止手順の未記入 | intranet-search | intranet-search | 誰が管理し、どう止めるかが台帳に無い | OWASP ASI10／アカウンタビリティ |
| 中 | L06 | 管理者・停止手順の未記入 | ops-shell | ops-shell | 誰が管理し、どう止めるかが台帳に無い | OWASP ASI10／アカウンタビリティ |
| 中 | L06 | 管理者・停止手順の未記入 | report-maker | report-maker | 誰が管理し、どう止めるかが台帳に無い | OWASP ASI10／アカウンタビリティ |
| 中 | L06 | 管理者・停止手順の未記入 | tickets | tickets | 誰が管理し、どう止めるかが台帳に無い | OWASP ASI10／アカウンタビリティ |
| 情報 | L08 | 認証の設定が見当たらない | intranet-search | http://search.intra.example.local/mcp | リモート接続に認証ヘッダーが無い（OAuthで認証する場合は問題ない） | OWASP ASI03／セキュリティ確保 |

## 台帳
| 種類 | 名前 | 権限区分（推定） | 接続 | 起動するもの | 版の固定 | 管理者 | 停止手順 |
|---|---|---|---|---|---|---|---|
| MCPサーバー | tickets | 外部送信 | リモート | https://tickets.example.com/mcp | あり | （未記入） | （未記入） |
| MCPサーバー | intranet-search | 外部送信 | リモート | http://search.intra.example.local/mcp | あり | （未記入） | （未記入） |
| MCPサーバー | filesystem | 書き込み | 手元で起動 | @modelcontextprotocol/server-filesystem | なし | （未記入） | （未記入） |
| MCPサーバー | notes-readonly | 読み取り（確認済み） | 手元で起動 | python C:/work/readonly-mcp/server.py | あり | 総務課 情報担当 | 設定から notes-readonly を削除し、Claude Desktop を再起動 |
| MCPサーバー | chat-bot | 外部送信 | 手元で起動 | example-chat-mcp@1.4.2 | あり | （未記入） | （未記入） |
| スキル | report-maker | 実行 | 手元 |  |  | （未記入） | （未記入） |
| MCPサーバー | db | 書き込み | 手元で起動 | mcp-server-sqlite==0.6.2 | あり | 業務システム係 | .mcp.json から db を削除 |
| MCPサーバー | ops-shell | 実行 | 手元で起動 | bash ./scripts/ops.sh | あり | （未記入） | （未記入） |
| MCPサーバー | browser | 外部送信 | 手元で起動 | example/browser-mcp:latest | なし | （未記入） | （未記入） |
