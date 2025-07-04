# BOCCO emo MCP Server インストールガイド

## 概要
Claude DesktopからBOCCO emoロボットを直接制御するためのMCP (Model Context Protocol) サーバーのインストール手順です。

## 前提条件
- Windows 10/11
- Python 3.8以上
- Claude Desktop アプリ
- BOCCO emo ロボット
- BOCCO emo Platform API のリフレッシュトークン

## 1. 環境準備

### Python の確認
```powershell
# Python バージョン確認（3.8以上が必要）
python --version

# pip の確認
pip --version
```

### プロジェクトフォルダの作成
```powershell
# 作業フォルダの作成
New-Item -ItemType Directory -Path "C:\bocco-mcp" -Force
Set-Location "C:\bocco-mcp"
```

## 2. 仮想環境の作成

```powershell
# 仮想環境作成
python -m venv bocco-mcp-env

# 仮想環境の有効化
.\bocco-mcp-env\Scripts\Activate.ps1

# 実行ポリシーエラーが出る場合
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 3. 必要なパッケージのインストール

```powershell
# pip のアップグレード
python -m pip install --upgrade pip

# 必要なパッケージをインストール
pip install mcp aiohttp

# インストール確認
pip list | findstr mcp
```

## 4. BOCCO emo MCP サーバーファイルの作成

### bocco_mcp_server.py の作成

```powershell
# UTF-8エンコーディングでファイルを作成
$serverCode = @'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOCCO emo MCP Server - 最終版
Claude から BOCCO emo ロボットを制御するためのMCPサーバー
"""

import asyncio
import json
import logging
import aiohttp
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# [完全なサーバーコードはアーティファクトに含まれています]
'@

# UTF-8で保存（重要：エンコーディング問題を回避）
[System.IO.File]::WriteAllText("C:\bocco-mcp\bocco_mcp_server.py", $serverCode, [System.Text.Encoding]::UTF8)
```

**注意**: 完全なサーバーコードは上記の「BOCCO emo MCP Server 最終版」アーティファクトを使用してください。

## 5. Claude Desktop の設定

### 設定ファイルの場所
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### 設定ファイルの作成
```powershell
# BOCCO emo MCP Server の設定
$config = @"
{
  "mcpServers": {
    "bocco-emo": {
      "command": "C:\\bocco-mcp\\bocco-mcp-env\\Scripts\\python.exe",
      "args": ["C:\\bocco-mcp\\bocco_mcp_server.py"],
      "env": {
        "BOCCO_REFRESH_TOKEN": "YOUR_REFRESH_TOKEN_HERE"
      }
    }
  }
}
"@

# Shift JIS エンコーディングで保存（Claude Desktop要件）
$config | Out-File "$env:APPDATA\Claude\claude_desktop_config.json" -Encoding Default

# 設定確認
Get-Content "$env:APPDATA\Claude\claude_desktop_config.json"
```

### リフレッシュトークンの設定
`YOUR_REFRESH_TOKEN_HERE` を実際のBOCCO emo Platform API リフレッシュトークンに置き換えてください。

## 6. 動作確認

### Claude Desktop の再起動
```powershell
# Claude Desktop を完全終了
Get-Process Claude* | Stop-Process -Force -ErrorAction SilentlyContinue

# 3秒待機
Start-Sleep 3

# Claude Desktop を手動で起動
```

### 基本機能のテスト
Claude Desktop で以下のメッセージを送信してテストしてください：

1. **メッセージ送信**:
   ```
   "エモちゃんに「こんにちは」と言って"
   ```

2. **モーション実行**:
   ```
   "エモちゃんに頭を振らせて"
   ```

3. **部屋一覧確認**:
   ```
   "エモちゃんの部屋一覧を見せて"
   ```

## 7. 利用可能な機能

### メッセージ送信
- 基本: `"エモちゃんに「メッセージ」と言って"`
- 部屋指定: `"リビングの部屋に「おはよう」と言って"`

### モーション制御
- 頭振り: `"エモちゃんに頭を振らせて"`
- うなずき: `"エモちゃんにうなずかせて"`

### 部屋管理
- 部屋一覧: `"エモちゃんの部屋一覧を見せて"`
- 部屋情報: `"エモちゃんの接続状況を確認して"`

### カスタムモーション
JSON形式でカスタムモーションを定義して実行可能

## 8. トラブルシューティング

### よくある問題と解決方法

#### 1. "Server disconnected" エラー
**原因**: Claude Desktop設定またはPythonファイルのエンコーディング問題
**解決方法**:
- Claude Desktop設定ファイルがShift JISエンコーディングで保存されているか確認
- Pythonファイルが UTF-8 + エンコーディング宣言 で保存されているか確認

#### 2. "SyntaxError: Non-UTF-8 code" エラー
**原因**: Pythonファイルのエンコーディング問題
**解決方法**:
```powershell
# ファイルをUTF-8で再保存
[System.IO.File]::WriteAllText("C:\bocco-mcp\bocco_mcp_server.py", $serverCode, [System.Text.Encoding]::UTF8)
```

#### 3. "ModuleNotFoundError: No module named 'mcp'" エラー
**原因**: 仮想環境が正しく設定されていない
**解決方法**:
```powershell
# 仮想環境の再作成
Remove-Item "bocco-mcp-env" -Recurse -Force
python -m venv bocco-mcp-env
.\bocco-mcp-env\Scripts\Activate.ps1
pip install mcp aiohttp
```

#### 4. アクセストークンエラー
**原因**: リフレッシュトークンが無効または期限切れ
**解決方法**:
- BOCCO emo Platform API で新しいリフレッシュトークンを取得
- 設定ファイルの `BOCCO_REFRESH_TOKEN` を更新

### ログの確認
```powershell
# MCPサーバーを手動実行してエラーログを確認
Set-Location "C:\bocco-mcp"
.\bocco-mcp-env\Scripts\Activate.ps1
python bocco_mcp_server.py
```

## 9. セキュリティ注意事項

- リフレッシュトークンは秘密情報として厳重に管理してください
- 設定ファイルを他人と共有しないでください
- 定期的にトークンを更新することを推奨します

## 10. 更新・メンテナンス

### パッケージの更新
```powershell
.\bocco-mcp-env\Scripts\Activate.ps1
pip install --upgrade mcp aiohttp
```

### サーバーコードの更新
新しいバージョンのサーバーコードが利用可能になった場合、UTF-8エンコーディングで上書き保存してください。

## サポート

問題が発生した場合は、以下を確認してください：
1. Python のバージョン（3.8以上）
2. 仮想環境の正しい設定
3. ファイルのエンコーディング（Python: UTF-8, 設定: Shift JIS）
4. Claude Desktop の完全再起動
5. リフレッシュトークンの有効性

---

**🎉 これで Claude Desktop から直接 BOCCO emo ロボットを制御できるようになりました！**

普通に話しかけるだけで、エモちゃんがメッセージを話したり、頭を振ったり、LEDが光ったりします。まさに未来的なロボット制御システムの完成です！
