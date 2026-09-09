import json
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.core.ws import ws_manager
from app.crud.base_crud import CRUDBase
from app.crud.point_crud import point_record_crud
from app.crud.user_balance_crud import user_balance_crud
from app.enums.base import WSEventType
from app.enums.membership import PayStatus, OrderType, PointRecordType, MembershipChangeType
from app.models.payment import RechargeOrder
from app.models.point_record import PointRecord, PointPurchasePlan
from app.models.membership import MembershipLevel, MembershipLevelPrivilege, UserMembership
from app.models.pay_api_log import PayApiLog
from app.schemas.pay_order import MembershipOrderCreate, PointOrderCreate, OrderCreateInfo, PointOrderCreateInfo, PayOrderItem
from app.utils.pay.sandpay import CupQrcodeSandPayClient, SandPayClient
from app.utils.membership_pricing import get_level_price, get_monthly_points


class CRUDRecharge(CRUDBase):

    def _get_pay_config(self) -> dict:
        """获取杉德支付配置"""
        return dict(
            access_mid=settings.SANDPAY_ACCESS_MID,
            version=settings.SANDPAY_API_VERSION,
            private_key=settings.SANDPAY_PRIVATE_KEY_PATH,
            sand_public_key=settings.SANDPAY_PUBLIC_KEY_PATH,
            private_key_password=settings.SANDPAY_PRIVATE_KEY_PASSWORD,
        )

    def _log_api_call(self, db: Session, order_no: str, api_type: str,
                      request_data: str, response_data: str,
                      result: str, error_msg: str = None, cost_ms: int = 0):
        """记录支付接口调用日志"""
        log = PayApiLog(
            order_no=order_no,
            api_type=api_type,
            request_data=request_data,
            response_data=response_data,
            result=result,
            error_msg=error_msg,
            cost_ms=cost_ms,
        )
        db.add(log)

    def _generate_order_no(self, prefix: str) -> str:
        """生成订单号：前缀 + 时间戳 + 6位随机数"""
        import random
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        rand = f"{random.randint(100000, 999999)}"
        return f"{prefix}{ts}{rand}"

    def create_membership_order(self, db: Session, order_in: MembershipOrderCreate,
                                current_user) -> OrderCreateInfo:
        """创建会员购买订单（识别新购/升级/降级预购）"""
        if current_user.parent_user_id is not None:
            raise ValueError("子账号无法购买会员，请联系主账号开通")
        from app.crud.membership_change_crud import (
            membership_change_crud,
            SCENE_NEW_PURCHASE, SCENE_REPURCHASE, SCENE_UPGRADE_SAME,
            SCENE_REJECT_SAME, SCENE_REJECT_DOWNGRADE_BOOKED,
            SCENE_REJECT_CROSS_YEAR_TO_MONTH, SCENE_REJECT_CROSS_TYPE,
            SCENE_REJECT_DOWNGRADE,
        )
        from app.enums.membership import MembershipStatus

        # 1. 查询目标等级并校验
        level = db.query(MembershipLevel).filter(
            MembershipLevel.id == order_in.level_id,
            MembershipLevel.status == 1,
            MembershipLevel.is_deleted == False,
        ).first()
        if not level:
            raise ValueError("会员等级不存在或已禁用")

        # 2. 查询当前有效会员
        membership = db.query(UserMembership).filter(
            UserMembership.user_id == current_user.id,
            UserMembership.status == MembershipStatus.ACTIVE,
            UserMembership.is_deleted == False,
        ).first()

        # 3. 场景识别
        scene = membership_change_crud.identify_change(
            db, membership, level, order_in.subscribe_type,
        )

        now = datetime.now()
        from_level_id = None
        point_adjust = Decimal("0.00")

        if scene["scene"] in (
            SCENE_REJECT_SAME, SCENE_REJECT_DOWNGRADE_BOOKED,
            SCENE_REJECT_CROSS_YEAR_TO_MONTH, SCENE_REJECT_CROSS_TYPE,
            SCENE_REJECT_DOWNGRADE,
        ):
            raise ValueError("暂不支持当前类型的调整")

        if scene["scene"] in (SCENE_NEW_PURCHASE, SCENE_REPURCHASE):
            # 新购/重购：等级现价
            pay_amount = get_level_price(level, order_in.subscribe_type)
            change_type = (MembershipChangeType.REPURCHASE
                           if scene["scene"] == SCENE_REPURCHASE
                           else MembershipChangeType.NEW_PURCHASE)
        elif scene["scene"] == SCENE_UPGRADE_SAME:
            # 同类型升级：补差价
            quote = membership_change_crud.quote_upgrade_same(
                db, membership, scene["old_level"], level, now,
            )
            pay_amount = quote.pay_amount
            point_adjust = quote.point_adjust
            from_level_id = membership.level_id
            change_type = MembershipChangeType.UPGRADE
        # TODO: 跨类型升级（月→年）暂不开放，恢复时取消注释
        # elif scene["scene"] == SCENE_UPGRADE_CROSS:
        #     quote = membership_change_crud.quote_upgrade_cross(
        #         db, membership, scene["old_level"], level, order_in.subscribe_type, now,
        #     )
        #     pay_amount = quote.pay_amount
        #     point_adjust = quote.point_adjust
        #     from_level_id = membership.level_id
        #     change_type = MembershipChangeType.UPGRADE
        # TODO: 降级预购暂不开放，恢复时取消注释
        # elif scene["scene"] == SCENE_DOWNGRADE:
        #     pay_amount = membership_change_crud.quote_downgrade(
        #         level, membership.subscribe_type,
        #     )
        #     from_level_id = membership.level_id
        #     change_type = MembershipChangeType.DOWNGRADE_BOOK
        else:
            raise ValueError("不支持的操作")

        if pay_amount <= 0:
            raise ValueError("支付金额必须大于0")

        # 4. 创建订单
        order_no = self._generate_order_no("VIP")
        db_order = RechargeOrder(
            user_id=current_user.id,
            order_no=order_no,
            amount=pay_amount,
            original_amount=level.yearly_price if order_in.subscribe_type == "yearly" else level.monthly_price,
            pay_method=1,
            status=PayStatus.PENDING,
            order_type=OrderType.VIP_PURCHASE,
            product_id=level.id,
            subscribe_type=order_in.subscribe_type,
            change_type=change_type,
            from_level_id=from_level_id,
            point_adjust=point_adjust,
        )
        db.add(db_order)
        db.flush()

        # 5. 调用杉德支付
        pay_config = self._get_pay_config()
        start_time = time.time()
        try:
            description = f"皮皮虾短剧-{level.name}-{order_in.subscribe_type}"
            extra_dict = dict(
                description=description,
                notify_url=settings.SANDPAY_VIP_CALLBACK_URL,
            )
            pay_res = CupQrcodeSandPayClient(pay_config).call(
                order_no, float(pay_amount), extra_dict=extra_dict,
            )
            cost_ms = int((time.time() - start_time) * 1000)
            self._log_api_call(db, order_no, "create",
                               json.dumps(extra_dict, ensure_ascii=False),
                               json.dumps(pay_res, ensure_ascii=False),
                               "success", cost_ms=cost_ms)
        except Exception as e:
            cost_ms = int((time.time() - start_time) * 1000)
            self._log_api_call(db, order_no, "create", "", "",
                               "fail", error_msg=str(e), cost_ms=cost_ms)
            raise ValueError(f"支付接口调用失败: {e}")

        qr_code = pay_res.get("credential", {}).get("qrCode", "")
        if not qr_code:
            raise ValueError("获取支付二维码失败，请稍后重试")

        # 6. 更新订单支付链接
        db_order.pay_url = qr_code
        db.commit()

        from datetime import timedelta
        expire_time = datetime.now() + timedelta(seconds=settings.PAY_TIME_OUT)
        return OrderCreateInfo(
            order_no=order_no,
            original_amount=str(db_order.original_amount),
            pay_amount=str(pay_amount),
            qr_code_url=qr_code,
            expire_time=expire_time,
        )

    def create_point_order(self, db: Session, order_in: PointOrderCreate,
                           current_user) -> PointOrderCreateInfo:
        """创建积分购买订单（支持方案购买和自定义充值两种模式）"""
        if current_user.parent_user_id is not None:
            raise ValueError("子账号无法购买积分，请联系主账号划拨")

        if order_in.plan_id:
            # ── 方案购买模式 ──
            plan = db.query(PointPurchasePlan).filter(
                PointPurchasePlan.id == order_in.plan_id,
                PointPurchasePlan.is_enabled == True,
                PointPurchasePlan.is_deleted == False,
            ).first()
            if not plan:
                raise ValueError("积分购买方案不存在或已禁用")

        # 校验用户会员等级是否允许购买积分
        membership = db.query(UserMembership).filter(
            UserMembership.user_id == current_user.id,
            UserMembership.status == 1,
            UserMembership.is_deleted == False,
        ).first()
        if not membership:
            raise ValueError("请先开通会员后再购买积分")
        level = db.query(MembershipLevel).filter(
            MembershipLevel.id == membership.level_id,
            MembershipLevel.is_deleted == False,
        ).first()
        if not level or not level.can_buy_points:
            raise ValueError("当前会员等级不支持购买积分")

        if order_in.plan_id:
            # ── 方案购买：价格来自方案 ──
            pay_amount = plan.discount_price
            original_amount = plan.original_price
            point_amount = plan.point_amount
            product_id = plan.id
        else:
            # ── 自定义充值模式 ──
            point_amount = Decimal(order_in.point_amount)

            if point_amount < settings.POINTS_MIN_RECHARGE:
                raise ValueError(f"最低充值 {settings.POINTS_MIN_RECHARGE} 积分")

            # 固定汇率 1元=100积分
            pay_amount = point_amount / Decimal(settings.POINTS_RECHARGE_RATIO)
            original_amount = pay_amount
            product_id = None

        # 3. 创建订单
        order_no = self._generate_order_no("PTS")
        db_order = RechargeOrder(
            user_id=current_user.id,
            order_no=order_no,
            amount=pay_amount,
            original_amount=original_amount,
            pay_method=1,
            status=PayStatus.PENDING,
            order_type=OrderType.POINT_PURCHASE,
            product_id=product_id,
            point_amount=point_amount,
        )
        db.add(db_order)
        db.flush()

        # 4. 调用杉德支付
        pay_config = self._get_pay_config()
        start_time = time.time()
        try:
            description = f"皮皮虾短剧-积分购买-{point_amount}积分"
            extra_dict = dict(
                description=description,
                notify_url=settings.SANDPAY_RECHARGE_CALLBACK_URL,
            )
            pay_res = CupQrcodeSandPayClient(pay_config).call(
                order_no, float(pay_amount), extra_dict=extra_dict,
            )
            cost_ms = int((time.time() - start_time) * 1000)
            self._log_api_call(db, order_no, "create",
                               json.dumps(extra_dict, ensure_ascii=False),
                               json.dumps(pay_res, ensure_ascii=False),
                               "success", cost_ms=cost_ms)
        except Exception as e:
            cost_ms = int((time.time() - start_time) * 1000)
            self._log_api_call(db, order_no, "create", "", "",
                               "fail", error_msg=str(e), cost_ms=cost_ms)
            raise ValueError(f"支付接口调用失败: {e}")

        qr_code = pay_res.get("credential", {}).get("qrCode", "")
        if not qr_code:
            raise ValueError("获取支付二维码失败，请稍后重试")

        # 5. 更新订单状态为支付中
        db_order.pay_url = qr_code
        db_order.status = PayStatus.PAYING
        db.commit()

        from datetime import timedelta
        expire_time = datetime.now() + timedelta(seconds=settings.PAY_TIME_OUT)
        return PointOrderCreateInfo(
            order_no=order_no,
            original_amount=str(original_amount),
            pay_amount=str(pay_amount),
            qr_code_url=qr_code,
            expire_time=expire_time,
            point_amount=str(point_amount),
        )

    async def membership_pay_callback(self, db: Session, request: Request) -> dict:
        """会员购买支付回调"""
        form_data = await request.form()
        callback_in = dict(form_data)
        logger.info(f"会员购买回调参数: {callback_in}")

        # 1. 验签
        sign = callback_in.get("sign")
        if not sign:
            raise ValueError("签名不存在")
        pay_config = self._get_pay_config()
        sandpay_client = SandPayClient(pay_config)
        if not sandpay_client.verify_sign(
            content=callback_in.get("bizData"),
            sign=sign,
            sign_type=callback_in.get("signType"),
            public_key=sandpay_client.sand_public_key,
        ):
            raise ValueError("签名校验失败")

        # 2. 解析业务数据
        biz_data = callback_in.get("bizData")
        if not biz_data:
            raise ValueError("业务数据不存在")
        biz_data = json.loads(biz_data)

        order_no = biz_data.get("outOrderNo")
        recharge_order = db.query(RechargeOrder).filter(
            RechargeOrder.order_no == order_no,
        ).with_for_update().first()
        if not recharge_order:
            raise ValueError("订单不存在")

        # 4. 幂等：已处理过的直接返回成功
        callback_response = {"respCode": "000000", "respMsg": "成功"}
        if recharge_order.status not in (PayStatus.PENDING, PayStatus.PAYING):
            self._log_api_call(db, order_no or "", "callback",
                               json.dumps(callback_in, ensure_ascii=False),
                               json.dumps(callback_response, ensure_ascii=False),
                               "success")
            return callback_response

        # 5. 处理支付结果
        if biz_data.get("resultStatus") == "success":
            if biz_data.get("eventType") == 'recv':
                # 校验金额
                if Decimal(biz_data.get("amount", "0")) != recharge_order.amount:
                    logger.error(f"会员购买回调金额不一致: order={recharge_order.amount}, callback={biz_data.get('amount')}")
                    raise ValueError("金额不一致")

                # 更新订单状态
                recharge_order.status = PayStatus.SUCCESS
                recharge_order.pay_serial_number = biz_data.get("sandSerialNo")
                recharge_order.channel_pay_serial_no = biz_data.get("channelSerialNo")
                recharge_order.channel_order_no = biz_data.get("channelOrderNo")
                recharge_order.actual_pay_amount = biz_data.get("buyerPayAmt")
                recharge_order.fee_amount = biz_data.get("feeAmt")
                recharge_order.extra_fee_amount = biz_data.get("extraFeeAmt")
                recharge_order.holiday_fee_amount = biz_data.get("holidayFeeAmt")
                recharge_order.platform_fee_amount = biz_data.get("plFeeAmt")
                recharge_order.pay_mode = biz_data.get("payMode")
                recharge_order.finished_time = datetime.now()

                # 按 change_type 分流处理
                from app.crud.membership_crud import membership_crud
                from app.crud.membership_change_crud import membership_change_crud

                ct = recharge_order.change_type
                if ct == MembershipChangeType.UPGRADE:
                    # 升级：用订单创建时确定的 point_adjust 补发积分（确定性，不重算）
                    membership = db.query(UserMembership).filter(
                        UserMembership.user_id == recharge_order.user_id,
                        UserMembership.status == 1,
                        UserMembership.is_deleted == False,
                    ).with_for_update().first()
                    if membership:
                        membership_change_crud.execute_upgrade(
                            db, membership, recharge_order, datetime.now(),
                        )
                    else:
                        logger.error(f"升级回调: 用户{recharge_order.user_id}无有效会员，订单{order_no}可能需人工处理")
                # TODO: 降级预购暂不开放，恢复时取消注释
                # elif ct == MembershipChangeType.DOWNGRADE_BOOK:
                #     membership = db.query(UserMembership).filter(
                #         UserMembership.user_id == recharge_order.user_id,
                #         UserMembership.status == 1,
                #         UserMembership.is_deleted == False,
                #     ).with_for_update().first()
                #     if membership:
                #         membership_change_crud.book_downgrade(
                #             db, membership, recharge_order, datetime.now(),
                #         )
                #     else:
                #         logger.error(f"降级预购回调: 用户{recharge_order.user_id}无有效会员，订单{order_no}可能需人工处理")
                else:
                    # 新购/重购
                    membership_crud.activate_membership(
                        db, recharge_order.user_id, recharge_order.product_id,
                        recharge_order.subscribe_type, recharge_order.order_no,
                    )
                    # 首月积分到账
                    self._grant_first_month_points(db, recharge_order, recharge_order.finished_time)
                # 记录回调日志（response_data 为返回给杉德的响应）
        self._log_api_call(db, order_no or "", "callback",
                           json.dumps(callback_in, ensure_ascii=False),
                           json.dumps(callback_response, ensure_ascii=False),
                           "success")
        db.commit()
        # WS 推送支付结果
        self._notify_pay_result(recharge_order)

        return callback_response

    async def point_pay_callback(self, db: Session, request: Request) -> dict:
        """积分购买支付回调"""
        form_data = await request.form()
        callback_in = dict(form_data)
        logger.info(f"积分购买回调参数: {callback_in}")

        # 1. 验签
        sign = callback_in.get("sign")
        if not sign:
            raise ValueError("签名不存在")
        pay_config = self._get_pay_config()
        sandpay_client = SandPayClient(pay_config)
        if not sandpay_client.verify_sign(
            content=callback_in.get("bizData"),
            sign=sign,
            sign_type=callback_in.get("signType"),
            public_key=sandpay_client.sand_public_key,
        ):
            raise ValueError("签名校验失败")

        # 2. 解析业务数据
        biz_data = callback_in.get("bizData")
        if not biz_data:
            raise ValueError("业务数据不存在")
        biz_data = json.loads(biz_data)

        order_no = biz_data.get("outOrderNo")
        recharge_order = db.query(RechargeOrder).filter(
            RechargeOrder.order_no == order_no,
        ).with_for_update().first()
        if not recharge_order:
            raise ValueError("订单不存在")

        # 4. 幂等
        callback_response = {"respCode": "000000", "respMsg": "成功"}
        if recharge_order.status not in (PayStatus.PENDING, PayStatus.PAYING):
            self._log_api_call(db, order_no or "", "callback",
                               json.dumps(callback_in, ensure_ascii=False),
                               json.dumps(callback_response, ensure_ascii=False),
                               "success")
            return callback_response

        # 5. 处理支付结果
        if biz_data.get("resultStatus") == "success":
            if biz_data.get("eventType") == 'recv':
                if Decimal(biz_data.get("amount", "0")) != recharge_order.amount:
                    logger.error(f"积分购买回调金额不一致: order={recharge_order.amount}, callback={biz_data.get('amount')}")
                    raise ValueError("金额不一致")

                # 更新订单状态
                recharge_order.status = PayStatus.SUCCESS
                recharge_order.pay_serial_number = biz_data.get("sandSerialNo")
                recharge_order.channel_pay_serial_no = biz_data.get("channelSerialNo")
                recharge_order.channel_order_no = biz_data.get("channelOrderNo")
                recharge_order.actual_pay_amount = biz_data.get("buyerPayAmt")
                recharge_order.fee_amount = biz_data.get("feeAmt")
                recharge_order.extra_fee_amount = biz_data.get("extraFeeAmt")
                recharge_order.holiday_fee_amount = biz_data.get("holidayFeeAmt")
                recharge_order.platform_fee_amount = biz_data.get("plFeeAmt")
                recharge_order.pay_mode = biz_data.get("payMode")
                recharge_order.finished_time = datetime.now()

                # 积分到账：优先使用订单记录中的 point_amount，回退到方案查询
                point_amount = recharge_order.point_amount
                if point_amount is None or point_amount <= 0:
                    plan = db.query(PointPurchasePlan).filter(
                        PointPurchasePlan.id == recharge_order.product_id,
                    ).first()
                    point_amount = plan.point_amount if plan else Decimal("0")
                user_balance_crud.credit_purchased(
                    db, recharge_order.user_id, point_amount,
                    source_id=recharge_order.order_no, remark="积分购买到账",
                )
        # 记录回调日志（response_data 为返回给杉德的响应）
        self._log_api_call(db, order_no or "", "callback",
                           json.dumps(callback_in, ensure_ascii=False),
                           json.dumps(callback_response, ensure_ascii=False),
                           "success")
        db.commit()

        # WS 推送支付结果
        self._notify_pay_result(recharge_order)

        return callback_response

    def _notify_pay_result(self, order: RechargeOrder):
        """通过 WebSocket 推送支付结果给用户"""
        try:
            ws_manager.publish(user_id=order.user_id, event={
                "event_id": str(uuid.uuid4()),
                "event_type": WSEventType.PAY_ORDER_STATUS,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "order_no": order.order_no,
                    "order_type": order.order_type,
                    "status": order.status,
                    "amount": str(order.amount),
                },
            })
        except Exception as e:
            logger.error(f"支付结果WS推送失败: order_no={order.order_no}, error={e}")

    def _grant_first_month_points(self, db: Session, order: RechargeOrder,
                                   grant_time: datetime = None):
        """首月积分赠送"""
        point_amount = get_monthly_points(db, order.product_id)
        if point_amount <= 0:
            return

        # 周期起始日：优先使用调用方传入的时间，避免跨午夜不一致
        grant_dt = grant_time or datetime.now()
        grant_date_str = grant_dt.strftime("%Y-%m-%d")

        # 幂等检查（按订单号去重，确保每次购买独立发积分）
        exists = db.query(PointRecord).filter(
            PointRecord.user_id == order.user_id,
            PointRecord.record_type == PointRecordType.MONTHLY_GRANT,
            PointRecord.source_id == order.order_no,
        ).first()
        if exists:
            return

        user_balance_crud.credit_granted(
            db, order.user_id, point_amount,
            source_id=order.order_no, remark="会员购买首月积分赠送",
            grant_month=grant_date_str,
            level_id=order.product_id,
        )

    def query_order_status(self, db: Session, order_no: str, current_user):
        """查询订单状态"""
        order = db.query(RechargeOrder).filter(
            RechargeOrder.order_no == order_no,
            RechargeOrder.user_id == current_user.id,
        ).first()
        if not order:
            raise ValueError("订单不存在")
        return order

    def get_user_orders(self, db: Session, user_id: str, page: int = 1, size: int = 10,
                        order_type: int = None, status: int = None):
        """查询用户订单列表"""
        query = db.query(RechargeOrder).filter(
            RechargeOrder.user_id == user_id,
            RechargeOrder.is_deleted == False,
        )
        if order_type is not None:
            query = query.filter(RechargeOrder.order_type == order_type)
        if status is not None:
            query = query.filter(RechargeOrder.status == status)
        query = query.order_by(RechargeOrder.create_time.desc())
        total = query.count()
        items = query.offset((page - 1) * size).limit(size).all()
        order_nos = [o.order_no for o in items]
        granted_map = point_record_crud.sum_granted_by_sources(db, order_nos)
        data = []
        for o in items:
            item = PayOrderItem.model_validate(o).model_dump()
            item["purchased_points"] = str(o.point_amount) if o.point_amount else None
            granted = granted_map.get(o.order_no)
            item["granted_points"] = str(granted) if granted is not None else None
            data.append(item)
        return {"data": data, "pagination": {"page": page, "size": size, "total_count": total}}

    def get_combined_records(self, db: Session, user_id: str, page: int = 1, size: int = 10,
                             type: str = None, status: int = None):
        """查询充值与积分流水合并记录（订单事件 + 纯流水事件）

        订单事件：recharge_order(order_type IN 会员购买/积分购买，含全部状态)，积分靠
        source_id 关联 point_record 取；纯流水事件：point_record(source_id IS NULL 的
        每月赠送 + 过期清零)。成功订单的 point_record 合并进订单事件去重，不单独成流水。
        按 create_time 倒序内存分页。type=daily_grant 为 UI 预留，无数据源，返回空。
        status 筛选：订单按 RechargeOrder.status 过滤；流水 status 恒为成功(3)，故选
        非 3 的状态时不查流水。
        """
        empty = {"data": [], "pagination": {"page": page, "size": size, "total_count": 0}}
        if type == "daily_grant":
            return empty

        def fmt_dt(v):
            return v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v

        # events 元素为 (原始 create_time, payload)：排序用原始时间，payload 不含临时键
        events = []

        # 订单事件：会员购买(2) / 积分购买(3)，含待支付/支付中/失败等全部状态
        if type in (None, "membership", "point_purchase"):
            if type is None:
                order_types = [OrderType.VIP_PURCHASE, OrderType.POINT_PURCHASE]
            elif type == "membership":
                order_types = [OrderType.VIP_PURCHASE]
            else:
                order_types = [OrderType.POINT_PURCHASE]
            order_q = db.query(RechargeOrder).filter(
                RechargeOrder.user_id == user_id,
                RechargeOrder.is_deleted == False,
                RechargeOrder.order_type.in_(order_types),
            )
            if status is not None:
                order_q = order_q.filter(RechargeOrder.status == status)
            orders = order_q.all()
            order_nos = [o.order_no for o in orders if o.order_no]
            points_map = point_record_crud.sum_points_by_order_sources(db, user_id, order_nos) if order_nos else {}
            for o in orders:
                events.append((o.create_time, {
                    "id": str(o.id),
                    "type": "membership" if o.order_type == OrderType.VIP_PURCHASE else "point_purchase",
                    "order_no": o.order_no,
                    "amount": str(o.amount) if o.amount is not None else None,
                    "points": str(points_map[o.order_no]) if o.order_no in points_map else None,
                    "subscribe_type": o.subscribe_type,
                    "status": o.status,
                    "remark": None,
                    "create_time": fmt_dt(o.create_time),
                    "finished_time": fmt_dt(o.finished_time),
                }))

        # 纯流水事件：每月赠送(source_id IS NULL) / 过期清零
        record_types = []
        if type in (None, "monthly_grant"):
            record_types.append(PointRecordType.MONTHLY_GRANT)
        if type in (None, "expire_clear"):
            record_types.append(PointRecordType.GRANT_CLEAR)
        # 流水 status 恒为成功(3)：仅当未指定 status 或指定为成功时才查流水
        if record_types and (status is None or status == PayStatus.SUCCESS):
            records = point_record_crud.get_grant_clear_records(db, user_id, record_types)
            for r in records:
                events.append((r.create_time, {
                    "id": str(r.id),
                    "type": "monthly_grant" if r.record_type == PointRecordType.MONTHLY_GRANT else "expire_clear",
                    "order_no": None,
                    "amount": None,
                    "points": str(r.point_amount) if r.point_amount is not None else None,
                    "subscribe_type": None,
                    "status": PayStatus.SUCCESS,
                    "remark": r.remark,
                    "create_time": fmt_dt(r.create_time),
                    "finished_time": fmt_dt(r.create_time),
                }))

        events.sort(key=lambda e: e[0] or datetime.min, reverse=True)
        total = len(events)
        start = (page - 1) * size
        page_items = [payload for _, payload in events[start:start + size]]

        return {"data": page_items, "pagination": {"page": page, "size": size, "total_count": total}}


recharge_crud = CRUDRecharge(RechargeOrder)
