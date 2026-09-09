"""
WebSocket 端点 — 基于 Redis Pub/Sub 的实时事件推送
"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.security import decode_token
from app.core.ws import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()

HEARTBEAT_INTERVAL = 30  # 秒


async def _heartbeat(websocket: WebSocket, stop_event: asyncio.Event, user_id: str):
    """定期发送心跳"""
    try:
        while not stop_event.is_set():
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            if not stop_event.is_set():
                await websocket.send_json({"type": "ping"})
    except Exception as e:
        logger.warning(f"WS 心跳异常 user_id={user_id} error={e}")
        stop_event.set()


@router.websocket("/{user_id}/ws")
async def ws_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(...),
    last_event_id: str = Query(None),
):
    # JWT 认证
    try:
        payload = decode_token(token)
        token_user_id = payload.get("sub")
        if str(token_user_id) != str(user_id):
            await websocket.close(code=4001, reason="用户不匹配")
            return
    except Exception:
        await websocket.close(code=4001, reason="Token 无效")
        return

    await websocket.accept()
    logger.info(f"WS 已连接 user_id={user_id}")

    # 回放遗漏事件
    if last_event_id:
        try:
            missed = ws_manager.replay_since(user_id, last_event_id)
            for evt in missed:
                await websocket.send_json(evt)
        except Exception as e:
            logger.warning(f"事件回放失败 user_id={user_id} error={e}")

    # 订阅 Redis Pub/Sub
    channel = f"ws:user:{user_id}"
    pubsub = ws_manager.redis.pubsub()
    await asyncio.get_event_loop().run_in_executor(None, pubsub.subscribe, channel)

    stop_event = asyncio.Event()
    heartbeat_task = asyncio.create_task(_heartbeat(websocket, stop_event, user_id))

    try:
        while not stop_event.is_set():
            message = await asyncio.get_event_loop().run_in_executor(
                None, pubsub.get_message, True, 30
            )
            if message and message["type"] == "message":
                logger.info(f"WS 转发消息到 user_id={user_id}")
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                await websocket.send_text(data)
    except WebSocketDisconnect:
        logger.info(f"WS 断开 user_id={user_id}")
    except Exception as e:
        logger.error(f"WS 异常 user_id={user_id} error={e}")
    finally:
        stop_event.set()
        heartbeat_task.cancel()
        await asyncio.get_event_loop().run_in_executor(None, pubsub.unsubscribe, channel)
        pubsub.close()
        logger.info(f"WS 清理完成 user_id={user_id}")
