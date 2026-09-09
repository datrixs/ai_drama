import json
from datetime import datetime
from decimal import Decimal

import redis
from loguru import logger

from app.core.config import settings


class ModelCallLogWriter:
    """模型调用日志写入器 - Redis 缓冲 + 批量写入 PG，Redis 不可用时降级直写 PG"""

    BUFFER_KEY = "log:buffer:model_call"
    MAX_RETRY = 3

    def __init__(self):
        self._redis: redis.Redis | None = None
        self._redis_available: bool = True

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                settings.LOG_REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
        return self._redis

    def _check_redis(self) -> bool:
        try:
            self.redis.ping()
            self._redis_available = True
            return True
        except Exception:
            self._redis_available = False
            logger.warning("日志 Redis 不可用，降级为直接写入 PG")
            return False

    def write(self, record: dict):
        """写入日志记录：优先 Redis 缓冲，不可用时降级直写 PG"""
        from app.core.logging import logger as _logger
        _logger.debug(f"[日志写入] write 被调用: id={record.get('id')} model={record.get('model_name')} user={record.get('user_id')} point={record.get('point')} error={record.get('error_message')} skip_billing={record.get('_skip_auto_billing')}")

        if "call_time" not in record:
            record["call_time"] = datetime.now().isoformat()
        record["create_time"] = datetime.now().isoformat()

        if self._redis_available:
            try:
                pipe = self.redis.pipeline()
                pipe.lpush(self.BUFFER_KEY, json.dumps(record, ensure_ascii=False, default=str))
                pipe.ltrim(self.BUFFER_KEY, 0, settings.LOG_REDIS_BUFFER_MAX - 1)
                pipe.llen(self.BUFFER_KEY)
                results = pipe.execute()
                _logger.debug(f"[日志写入] Redis 缓冲成功: id={record.get('id')} buffer_key={self.BUFFER_KEY}")

                buffer_len = results[-1]
                if buffer_len >= settings.LOG_FLUSH_THRESHOLD:
                    self._trigger_flush()
                return
            except Exception as e:
                logger.warning(f"日志写入 Redis 失败，降级直写 PG error={e}")
                self._redis_available = False

        _logger.debug(f"[日志写入] 降级直写 PG: id={record.get('id')}")
        self._write_direct_to_pg(record)

    def _trigger_flush(self):
        """派发 flush 任务到 log_flush 队列"""
        try:
            from app.celery_tasks.log_flush import flush_model_call_log
            flush_model_call_log.delay()
            from app.core.logging import logger as _logger
            _logger.debug("[日志写入] 触发异步 flush 任务")
        except Exception as e:
            logger.error(f"触发 flush 任务失败 error={e}")

    def _calculate_point(self, record: dict, session) -> Decimal:
        """根据日志记录计算消耗积分，调用失败或无法计算时返回0 - 委托给 PointService"""
        response_status = record.get("response_status")
        error_message = record.get("error_message")
        
        if error_message or (response_status is not None and response_status != 200):
            return Decimal("0")

        skip_billing = record.get("_skip_auto_billing")
        if (skip_billing is True or skip_billing == "true") and record.get("point") is not None:
            return Decimal(str(record["point"]))
        
        if response_status is None and record.get("point") is not None:
            return Decimal(str(record["point"]))

        try:
            from app.services.point import PointService

            model_name = record.get("model_name", "")
            if not model_name:
                return Decimal("0")

            model_type = record.get("model_type")
            if model_type == "TEXT" or not model_type:
                input_tokens = record.get("input_tokens", 0) or 0
                output_tokens = record.get("output_tokens", 0) or 0
                if input_tokens == 0 and output_tokens == 0:
                    return Decimal("0")
                return PointService.calculate_point(
                    session,
                    model_name=model_name,
                    input_token=input_tokens,
                    output_token=output_tokens,
                )
            elif model_type == "IMAGE":
                request_body = record.get("request_body", {})
                is_character = request_body.get("is_character", False)
                n = request_body.get("n", 1)
                size = request_body.get("size")
                calc_kwargs = {"is_character": is_character, "n": n}
                if size:
                    calc_kwargs["size"] = size
                return PointService.calculate_point(
                    session,
                    model_name=model_name,
                    **calc_kwargs,
                )
            else:
                return PointService.calculate_point(session, model_name=model_name)
        except Exception as e:
            logger.warning(f"积分计算失败 error={e} model_name={record.get('model_name')}")
            return Decimal("0")

    def _get_user_balance(self, session, user_id: str) -> Decimal:
        """获取用户当前余额"""
        try:
            from app import crud
            logger.debug(f"[日志写入] _get_user_balance: user_id={user_id}")
            user_balance = crud.user_balance_crud.get_by_user_id(db=session, user_id=user_id)
            if user_balance:
                logger.debug(f"[日志写入] 获取用户余额成功: user_id={user_id} balance={user_balance.balance} type={type(user_balance.balance)}")
                result = user_balance.balance
                logger.debug(f"[日志写入] 返回余额: {result}")
                return result
            else:
                logger.warning(f"[日志写入] 用户余额记录不存在: user_id={user_id}")
                return Decimal("0")
        except Exception as e:
            logger.warning(f"[日志写入] 获取用户余额失败 error={type(e).__name__}: {e} user_id={user_id}")
            return Decimal("0")

    def _deduct_user_balance(self, record: dict, session, point: Decimal) -> Decimal:
        """从用户余额中扣除本次消耗的积分，返回扣除后的剩余余额"""
        user_id = record.get("user_id")
        skip_billing = record.get("_skip_auto_billing")
        logger.debug(f"[日志写入] _deduct_user_balance: user_id={user_id} point={point} _skip_auto_billing={skip_billing} type={type(skip_billing)}")
        
        if not user_id or user_id == "system":
            logger.debug(f"[日志写入] 跳过: user_id无效")
            return Decimal("0")
        
        if point <= 0 or skip_billing is True or skip_billing == "true":
            logger.debug(f"[日志写入] 获取用户当前余额: point={point} skip_billing={skip_billing}")
            balance = self._get_user_balance(session, user_id)
            logger.debug(f"[日志写入] 获取余额结果: {balance}")
            return balance
        
        try:
            from app import crud
            balance = crud.user_balance_crud.deduct_balance(db=session, user_id=user_id, amount=point)
            result = balance.balance if balance else self._get_user_balance(session, user_id)
            logger.debug(f"[日志写入] 扣除后余额: {result}")
            return result
        except Exception as e:
            logger.warning(f"[日志写入] 积分扣除失败 error={e} user_id={user_id} point={point}")
            return self._get_user_balance(session, user_id)

    def _write_direct_to_pg(self, record: dict):
        """降级方案：直接写入 PG"""
        from app.core.logging import logger as _logger
        from app.db.session import SessionLocal
        from app.models.model_call_log import ModelCallLog

        session = SessionLocal()
        try:
            record["point"] = self._calculate_point(record, session)
            record["remaining_point"] = self._deduct_user_balance(record, session, record["point"])
            record.pop("_skip_auto_billing", None)
            _logger.debug(f"[日志写入] 直写 PG 开始: id={record.get('id')} point={record.get('point')} remaining_point={record.get('remaining_point')} keys={list(record.keys())}")
            obj = ModelCallLog(**record)
            session.add(obj)
            session.commit()
            _logger.debug(f"[日志写入] 直写 PG 成功: id={record.get('id')}")
        except Exception as e:
            session.rollback()
            _logger.error(f"[日志写入] 直写 PG 失败 error={e} record_id={record.get('id')} record_keys={list(record.keys())}")
        finally:
            session.close()

    def flush_to_db(self, batch_size: int = None) -> int:
        """从 Redis 批量写入 PG（由 Beat 定时调用），失败记录放回 Redis 重试"""
        from app.core.logging import logger as _logger

        if not self._redis_available:
            if not self._check_redis():
                return 0

        batch_size = batch_size or settings.LOG_FLUSH_BATCH_SIZE
        from app.db.session import SessionLocal
        from app.models.model_call_log import ModelCallLog

        records = []
        for _ in range(batch_size):
            try:
                raw = self.redis.rpop(self.BUFFER_KEY)
            except Exception as e:
                self._redis_available = False
                logger.warning(f"日志刷写时 Redis 断开 error={e}")
                break
            if raw is None:
                break
            records.append(json.loads(raw))

        if not records:
            return 0

        _logger.debug(f"[日志写入] flush_to_db 从 Redis 读取 {len(records)} 条记录")
        failed: list[dict] = []
        session = SessionLocal()
        written = 0
        try:
            for r in records:
                try:
                    r["point"] = self._calculate_point(r, session)
                    r["remaining_point"] = self._deduct_user_balance(r, session, r["point"])
                    db_record = r.copy()
                    db_record.pop("_skip_auto_billing", None)
                    db_record.pop("_retry_count", None)
                    obj = ModelCallLog(**db_record)
                    session.add(obj)
                    session.flush()
                    written += 1
                except Exception as e:
                    session.rollback()
                    retry_count = r.get("_retry_count", 0) + 1
                    if retry_count < self.MAX_RETRY:
                        r["_retry_count"] = retry_count
                        failed.append(r)
                        _logger.warning(f"[日志写入] flush 记录写入失败，放回缓冲区重试 ({retry_count}/{self.MAX_RETRY}) error={e} record_id={r.get('id')}")
                    else:
                        _logger.error(f"[日志写入] flush 记录超过最大重试次数，丢弃 error={e} record_id={r.get('id')} model={r.get('model_name')} data={json.dumps(r, ensure_ascii=False, default=str)[:500]}")
            if written > 0:
                session.commit()
            if failed:
                self._requeue_failed(failed)
            _logger.info(f"[日志写入] flush_to_db 完成: 总计={len(records)} 成功={written} 重试={len(failed)}")
            return written
        except Exception as e:
            session.rollback()
            logger.error(f"日志刷写提交失败 error={e} written={written}")
            raise
        finally:
            session.close()

    def _requeue_failed(self, records: list[dict]):
        """将失败记录批量放回 Redis 缓冲区头部"""
        try:
            pipe = self.redis.pipeline()
            for r in records:
                pipe.lpush(self.BUFFER_KEY, json.dumps(r, ensure_ascii=False, default=str))
            pipe.execute()
        except Exception as e:
            self._redis_available = False
            logger.error(f"失败记录放回 Redis 失败，记录将丢失 error={e} count={len(records)}")


model_call_log_writer = ModelCallLogWriter()
