"""
WebSocket 消息管理 - 基于 Redis 的消息缓冲与发布
"""
import json
import logging
import uuid
from typing import Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class WSMessageManager:
    """WebSocket 消息管理器（基于 Redis Pub/Sub）"""

    BUFFER_TTL = 600  # 10 分钟
    MAX_EVENTS = 500

    def __init__(self):
        self._redis: redis.Redis | None = None

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
        return self._redis

    def publish(self, user_id: str, event: dict) -> None:
        """发布事件到 Redis"""
        try:
            key = f"ws:buffer:{user_id}"
            event_json = json.dumps(event, ensure_ascii=False, default=str)
            logger.info(f"WS 发布事件: type={event.get('event_type')} user={user_id}")
            pipe = self.redis.pipeline()
            pipe.lpush(key, event_json)
            pipe.ltrim(key, 0, self.MAX_EVENTS - 1)
            pipe.expire(key, self.BUFFER_TTL)
            pipe.publish(f"ws:user:{user_id}", event_json)
            pipe.execute()
        except Exception as e:
            logger.error(f"WS事件发布失败 user_id={user_id} error={e}")

    def publish_project_event(
        self,
        user_id: str,
        project_id: str,
        event_type: str,
        data: dict | None = None,
    ) -> None:
        """发布项目相关事件"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "project_id": project_id,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "data": data or {},
        }
        self.publish(user_id, event)

    def publish_asset_hub_event(
        self,
        user_id: str,
        event_type: str,
        data: dict | None = None,
    ) -> None:
        """发布全局资产中心事件"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "data": data or {},
        }
        self.publish(user_id, event)

    def replay_since(self, user_id: str, last_event_id: str) -> list[dict]:
        """回放 last_event_id 之后的所有事件"""
        key = f"ws:buffer:{user_id}"
        events = self.redis.lrange(key, 0, -1)
        result = []
        for raw in reversed(events):
            event = json.loads(raw)
            if event.get("event_id") == last_event_id:
                break
            result.append(event)
        return list(reversed(result))


# 全局单例
ws_manager = WSMessageManager()
