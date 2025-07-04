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

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bocco-mcp")

class BoccoEmoAPI:
    """BOCCO emo API クライアント"""

    def __init__(self, refresh_token: str):
        self.refresh_token = refresh_token
        self.base_url = "https://platform-api.bocco.me"
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.rooms: List[Dict[str, Any]] = []
        self.default_room_id: Optional[str] = None
        logger.info("BOCCO emo API クライアント初期化")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def initialize(self):
        """初期化：アクセストークン取得と部屋情報取得"""
        logger.info("BOCCO emo API 初期化開始...")

        if not await self.get_access_token():
            raise Exception("アクセストークンの取得に失敗しました")

        await self.fetch_rooms()
        logger.info(f"初期化完了: {len(self.rooms)}個の部屋を発見")

    async def get_access_token(self) -> bool:
        """リフレッシュトークンからアクセストークンを取得"""
        try:
            data = {"refresh_token": self.refresh_token}
            async with self.session.post(
                f"{self.base_url}/oauth/token/refresh",
                json=data,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()

                if response.status == 200 and "access_token" in result:
                    self.access_token = result["access_token"]
                    expires_in = result.get("expires_in", 3600)
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    logger.info(f"アクセストークン取得成功 (有効期限: {expires_in}秒)")
                    return True
                else:
                    logger.error(f"トークン取得失敗: {result}")
                    return False
        except Exception as e:
            logger.error(f"トークン取得エラー: {e}")
            return False

    async def ensure_valid_token(self) -> bool:
        """トークンの有効性を確認し、必要に応じて更新"""
        if (not self.access_token or
            not self.token_expires_at or
            datetime.now() > self.token_expires_at - timedelta(minutes=5)):
            logger.info("アクセストークンを更新中...")
            return await self.get_access_token()
        return True

    async def fetch_rooms(self) -> bool:
        """部屋一覧を取得してデフォルト部屋を設定"""
        if not await self.ensure_valid_token():
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            async with self.session.get(
                f"{self.base_url}/v1/rooms",
                headers=headers
            ) as response:
                if response.status == 200:
                    rooms_data = await response.json()

                    # レスポンス形式の処理
                    if isinstance(rooms_data, dict) and "rooms" in rooms_data:
                        self.rooms = rooms_data["rooms"]
                    elif isinstance(rooms_data, list):
                        self.rooms = rooms_data
                    else:
                        logger.error(f"予期しない部屋データ形式: {type(rooms_data)}")
                        return False

                    # デフォルト部屋を設定
                    if self.rooms:
                        # 「エモちゃんの部屋」を探す
                        for room in self.rooms:
                            if isinstance(room, dict):
                                room_name = room.get("name", "")
                                if "エモ" in room_name or "emo" in room_name.lower():
                                    self.default_room_id = room["uuid"]
                                    logger.info(f"デフォルト部屋設定: {room_name} ({room['uuid']})")
                                    return True

                        # 見つからなければ最初の部屋を使用
                        if isinstance(self.rooms[0], dict):
                            self.default_room_id = self.rooms[0]["uuid"]
                            logger.info(f"デフォルト部屋設定（最初の部屋）: {self.rooms[0].get('name')} ({self.default_room_id})")

                    return True
                else:
                    logger.error(f"部屋一覧取得失敗: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"部屋一覧取得エラー: {e}")
            return False

    async def send_message(self, text: str, room_id: Optional[str] = None) -> Dict[str, Any]:
        """テキストメッセージを送信"""
        if not await self.ensure_valid_token():
            raise Exception("アクセストークンの取得に失敗しました")

        target_room = room_id or self.default_room_id
        if not target_room:
            raise Exception("送信先の部屋が指定されていません")

        data = {
            "text": text,
            "unique_id": str(int(datetime.now().timestamp() * 1000))
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        async with self.session.post(
            f"{self.base_url}/v1/rooms/{target_room}/messages/text",
            json=data,
            headers=headers
        ) as response:
            result = await response.json()
            return {"status": response.status, "data": result, "room_id": target_room}

    async def send_motion(self, motion_data: Dict[str, Any], room_id: Optional[str] = None) -> Dict[str, Any]:
        """モーションデータを送信"""
        if not await self.ensure_valid_token():
            raise Exception("アクセストークンの取得に失敗しました")

        target_room = room_id or self.default_room_id
        if not target_room:
            raise Exception("送信先の部屋が指定されていません")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        async with self.session.post(
            f"{self.base_url}/v1/rooms/{target_room}/motions",
            json=motion_data,
            headers=headers
        ) as response:
            result = await response.json()
            return {"status": response.status, "data": result, "room_id": target_room}

    async def get_rooms_info(self) -> Dict[str, Any]:
        """部屋一覧情報を取得"""
        if not self.rooms:
            await self.fetch_rooms()

        return {
            "status": 200,
            "data": {
                "rooms": self.rooms,
                "default_room_id": self.default_room_id,
                "room_count": len(self.rooms)
            }
        }

# 定義済みモーション
PREDEFINED_MOTIONS = {
    "head_shake": {
        "sound": {"delay_ms": 0, "name": ""},
        "head": [
            {"duration": 500, "p0": [None, None], "p1": [None, None], "p2": [45, 20], "p3": [45, 20], "ease": [0, 0, 0.745, 0.3100625610351563]},
            {"duration": 500, "p0": [None, None], "p1": [45, 20], "p2": [-45, 20], "p3": [-45, 20], "ease": [0, 0, 1, 1]},
            {"duration": 500, "p0": [None, None], "p1": [-45, 20], "p2": [-45, -20], "p3": [-45, -20], "ease": [0, 0, 1, 1]},
            {"duration": 825, "p0": [None, None], "p1": [-45, -20], "p2": [0, 0], "p3": [0, 0], "ease": [0, 0, 1, 1]}
        ],
        "antenna": [{"duration": 2325, "start": {"amp": 0.8, "freq": 20, "pos": None}, "end": {"amp": 1, "freq": 0, "pos": None}}],
        "led_cheek_l": [
            {"duration": 1625, "start": [246, 0, 0, 1], "end": [6, 0, 255, 1], "ease": [0, 0, 1, 1]},
            {"duration": 700, "start": [None, None, None, None], "end": [None, None, None, None], "ease": [0, 0, 0, 0]}
        ],
        "led_cheek_r": [
            {"duration": 1625, "start": [0, 40, 246, 1], "end": [255, 38, 0, 1], "ease": [0, 0, 0.705, 0.5703125]},
            {"duration": 700, "start": [None, None, None, None], "end": [None, None, None, None], "ease": [0, 0, 0, 0]}
        ],
        "led_rec": [],
        "led_play": [],
        "led_func": []
    },
    "simple_nod": {
        "sound": {"delay_ms": 0, "name": ""},
        "head": [
            {"duration": 500, "p2": [0, -30], "p3": [0, -30]},
            {"duration": 500, "p1": [0, -30], "p2": [0, 0], "p3": [0, 0]}
        ],
        "antenna": [],
        "led_cheek_l": [],
        "led_cheek_r": [],
        "led_rec": [],
        "led_play": [],
        "led_func": []
    }
}

# 環境変数からリフレッシュトークンを取得
REFRESH_TOKEN = os.getenv("BOCCO_REFRESH_TOKEN")
if not REFRESH_TOKEN:
    logger.error("環境変数 BOCCO_REFRESH_TOKEN が設定されていません")
    raise ValueError("BOCCO_REFRESH_TOKEN environment variable is required")

# MCPサーバーの初期化
server = Server("bocco-emo")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツールのリストを返す"""
    return [
        Tool(
            name="bocco_send_message",
            description="BOCCO emoにテキストメッセージを送信します",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "送信するメッセージ"
                    },
                    "room_name": {
                        "type": "string",
                        "description": "送信先の部屋名（省略可、デフォルト部屋を使用）"
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="bocco_send_motion",
            description="BOCCO emoにモーションを送信します",
            inputSchema={
                "type": "object",
                "properties": {
                    "motion_name": {
                        "type": "string",
                        "enum": ["head_shake", "simple_nod"],
                        "description": "実行するモーション名"
                    },
                    "room_name": {
                        "type": "string",
                        "description": "送信先の部屋名（省略可、デフォルト部屋を使用）"
                    }
                },
                "required": ["motion_name"]
            }
        ),
        Tool(
            name="bocco_custom_motion",
            description="カスタムモーションJSONを送信します",
            inputSchema={
                "type": "object",
                "properties": {
                    "motion_json": {
                        "type": "object",
                        "description": "モーションを定義するJSONオブジェクト"
                    },
                    "room_name": {
                        "type": "string",
                        "description": "送信先の部屋名（省略可、デフォルト部屋を使用）"
                    }
                },
                "required": ["motion_json"]
            }
        ),
        Tool(
            name="bocco_get_rooms",
            description="BOCCO emoの部屋一覧と接続状況を取得します",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="bocco_list_rooms",
            description="BOCCO emoの全部屋の詳細情報を一覧表示します",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """ツールの呼び出しを処理"""
    try:
        async with BoccoEmoAPI(REFRESH_TOKEN) as api:
            if name == "bocco_send_message":
                message = arguments["message"]
                room_name = arguments.get("room_name")

                # 部屋名が指定されている場合、該当する部屋IDを探す
                room_id = None
                if room_name:
                    for room in api.rooms:
                        if isinstance(room, dict) and room_name.lower() in room.get("name", "").lower():
                            room_id = room["uuid"]
                            break
                    if not room_id:
                        return [TextContent(
                            type="text",
                            text=f"エラー: 部屋「{room_name}」が見つかりません。利用可能な部屋: {[r.get('name') for r in api.rooms if isinstance(r, dict)]}"
                        )]

                result = await api.send_message(message, room_id)

                # 使用した部屋名を取得
                used_room_name = "デフォルト部屋"
                if result["room_id"]:
                    for room in api.rooms:
                        if isinstance(room, dict) and room["uuid"] == result["room_id"]:
                            used_room_name = room.get("name", "Unknown")
                            break

                return [TextContent(
                    type="text",
                    text=f"メッセージ「{message}」を{used_room_name}に送信しました。\nステータス: {result['status']}"
                )]

            elif name == "bocco_send_motion":
                motion_name = arguments["motion_name"]
                room_name = arguments.get("room_name")

                if motion_name not in PREDEFINED_MOTIONS:
                    return [TextContent(
                        type="text",
                        text=f"エラー: モーション '{motion_name}' が見つかりません。利用可能なモーション: {list(PREDEFINED_MOTIONS.keys())}"
                    )]

                # 部屋名が指定されている場合、該当する部屋IDを探す
                room_id = None
                if room_name:
                    for room in api.rooms:
                        if isinstance(room, dict) and room_name.lower() in room.get("name", "").lower():
                            room_id = room["uuid"]
                            break
                    if not room_id:
                        return [TextContent(
                            type="text",
                            text=f"エラー: 部屋「{room_name}」が見つかりません"
                        )]

                motion_data = PREDEFINED_MOTIONS[motion_name]
                result = await api.send_motion(motion_data, room_id)

                # 使用した部屋名を取得
                used_room_name = "デフォルト部屋"
                if result["room_id"]:
                    for room in api.rooms:
                        if isinstance(room, dict) and room["uuid"] == result["room_id"]:
                            used_room_name = room.get("name", "Unknown")
                            break

                return [TextContent(
                    type="text",
                    text=f"モーション「{motion_name}」を{used_room_name}で実行しました。\nステータス: {result['status']}"
                )]

            elif name == "bocco_custom_motion":
                motion_json = arguments["motion_json"]
                room_name = arguments.get("room_name")

                # 部屋名が指定されている場合、該当する部屋IDを探す
                room_id = None
                if room_name:
                    for room in api.rooms:
                        if isinstance(room, dict) and room_name.lower() in room.get("name", "").lower():
                            room_id = room["uuid"]
                            break
                    if not room_id:
                        return [TextContent(
                            type="text",
                            text=f"エラー: 部屋「{room_name}」が見つかりません"
                        )]

                result = await api.send_motion(motion_json, room_id)
                return [TextContent(
                    type="text",
                    text=f"カスタムモーションを送信しました。\nステータス: {result['status']}"
                )]

            elif name == "bocco_get_rooms":
                result = await api.get_rooms_info()
                return [TextContent(
                    type="text",
                    text=f"部屋情報を取得しました。\n{json.dumps(result, ensure_ascii=False, indent=2)}"
                )]

            elif name == "bocco_list_rooms":
                result = await api.get_rooms_info()
                rooms_info = "📍 BOCCO emo 部屋一覧:\n\n"

                try:
                    rooms = result["data"]["rooms"]
                    if not rooms:
                        return [TextContent(
                            type="text",
                            text="部屋が見つかりませんでした。"
                        )]

                    for i, room in enumerate(rooms, 1):
                        if isinstance(room, dict):
                            name = room.get("name", "Unknown")
                            uuid = room.get("uuid", "Unknown")
                            is_default = "🏠 " if uuid == result["data"]["default_room_id"] else "   "
                            rooms_info += f"{is_default}{i}. {name}\n   ID: {uuid}\n\n"

                    rooms_info += f"合計: {result['data']['room_count']}部屋\n"
                    rooms_info += f"デフォルト部屋ID: {result['data']['default_room_id']}"

                    return [TextContent(
                        type="text",
                        text=rooms_info
                    )]
                except Exception as e:
                    return [TextContent(
                        type="text",
                        text=f"部屋一覧の処理でエラーが発生しました: {str(e)}"
                    )]

            else:
                return [TextContent(
                    type="text",
                    text=f"エラー: 不明なツール '{name}'"
                )]

    except Exception as e:
        logger.error(f"ツール実行エラー: {e}")
        return [TextContent(
            type="text",
            text=f"エラーが発生しました: {str(e)}"
        )]

async def main():
    """MCPサーバーの実行"""
    logger.info("BOCCO emo MCP Server 開始...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())


