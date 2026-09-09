"""
积分服务 - 统一处理所有积分相关操作

提供以下功能：
1. 积分计算（文本/图片/视频模型）
2. 用户余额操作（扣除/退还/查询）
3. 预扣积分机制（预扣-结算-退款流程）

内部通过 BillingEngine（策略模式）实现计费逻辑，对外接口保持不变。
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from loguru import logger

from app import crud
from app.enums.ai_model import AIModelType
from app.enums import PricingRuleType
from app.services.billing import BillingEngine


class InsufficientBalanceError(Exception):
    """用户积分余额不足"""

    def __init__(
        self,
        message: str = "积分余额不足",
        user_id: str = "",
        estimated_point: Decimal = Decimal("0"),
    ):
        super().__init__(message)
        self.user_id = user_id
        self.estimated_point = estimated_point


class PointService:
    """
    积分服务类 - 统一管理积分计算和余额操作

    使用方式：
        # 在需要使用积分服务的地方
        from app.services.point import PointService

        # 计算积分
        point = PointService.calculate_point(db, model_id, input_token=1000, output_token=500)

        # 预扣积分
        PointService.pre_deduct(db, user_id, estimated_point)

        # 结算差额
        PointService.settle(db, user_id, estimated_point, actual_point)

        # 退还积分
        PointService.refund(db, user_id, amount)
    """

    # ==================== 积分计算 ====================

    @staticmethod
    def calculate_point(
        db: Session,
        model_id: str = None,
        model_name: str = None,
        **kwargs
    ) -> Decimal:
        """
        根据模型和消耗计算积分

        参数说明：
        - 文本模型：需要 input_token、output_token
        - 图片模型：需要 is_character（是否生成角色图）、n（生成数量，默认1）
          可选：input_n（输入图片数，首张免费）、resolution_tier（分辨率档位，如 "low"/"high"）
        - 视频模型：需要 has_reference、video_resolution、video_output_duration、reference_duration

        调用示例：
            # 文本模型
            PointService.calculate_point(db, model_id="xxx", input_token=1000, output_token=500)

            # 图片模型（文生图，输出1k以下，1张）
            PointService.calculate_point(db, model_id="xxx", is_character=False, n=1, resolution_tier="low")

            # 图片模型（图生图，输出1k以上，输入2张，输出1张）
            PointService.calculate_point(db, model_id="xxx", is_character=False, n=1, input_n=2, resolution_tier="high")

            # 视频模型（不带全能参考）
            PointService.calculate_point(db, model_id="xxx", has_reference=False, video_resolution="1080P", video_output_duration=30)
            
            # 视频模型（全能参考）
            PointService.calculate_point(db, model_id="xxx", has_reference=True, video_resolution="1080P", video_output_duration=30, reference_duration=15)
        """
        if not model_id and not model_name:
            raise ValueError("必须提供 model_id 或 model_name")

        ai_model = None
        if model_id:
            ai_model = crud.ai_model_crud.get(db=db, id=model_id)
        elif model_name:
            clean_name = model_name.split("/", 1)[1] if "/" in model_name else model_name
            ai_model = crud.ai_model_crud.get_by_model_name(db=db, model_name=clean_name)

        if not ai_model:
            logger.warning(f"[积分] 未找到模型: model_id={model_id} model_name={model_name}")
            return Decimal("0")

        model_type = ai_model.model_type

        if model_type == AIModelType.TEXT.value:
            return PointService._calculate_text_point(db, ai_model, **kwargs)
        elif model_type == AIModelType.IMAGE.value:
            return PointService._calculate_image_point(db, ai_model, **kwargs)
        elif model_type == AIModelType.VIDEO.value:
            return PointService._calculate_video_point(db, ai_model, **kwargs)
        else:
            logger.warning(f"[积分] 未知模型类型: {model_type}")
            return Decimal("0")

    @staticmethod
    def calculate_super_res_point(db: Session, video_duration: int, video_resolution: str):
        """
        计算超分使用的积分
        """
        logger.info(f"[计算超分使用的积分] video_duration={video_duration}, video_resolution={video_resolution}")

        # 兼容小写字母p
        video_resolution = video_resolution.upper() if isinstance(video_resolution, str) else video_resolution

        match_params = {"target_video_resolution": video_resolution}
        calc_params = {"video_duration": video_duration}
        total_point = BillingEngine.calculate_actual(
            db, None, PricingRuleType.SUPER_RES.value, match_params, calc_params
        )

        if total_point <= 0:
            logger.error(f"[计算超分使用的积分] 未获取到超分配置项，检查video_resolution参数是否标准，再检查ai_model_pricing表")

        logger.info(f"[计算超分使用的积分] 视频时长={video_duration}，目标清晰度={video_resolution}，共计消耗={total_point}")
        return total_point


    @staticmethod
    def _calculate_text_point(db: Session, ai_model, **kwargs) -> Decimal:
        """计算文本模型积分消耗（实际结算）"""
        input_token = kwargs.get("input_token")
        output_token = kwargs.get("output_token")

        if not input_token or not output_token:
            logger.warning("[积分] 文本模型缺少 input_token 或 output_token 参数")
            return Decimal("0")

        calc_params = {"input_token": input_token, "output_token": output_token}
        return BillingEngine.calculate_actual(
            db, ai_model.id, PricingRuleType.TEXT_TOKEN.value, {}, calc_params
        )

    @staticmethod
    def _calculate_image_point(db: Session, ai_model, **kwargs) -> Decimal:
        """计算图片模型积分消耗（按张计费）"""
        is_character = kwargs.get("is_character", False)
        n = kwargs.get("n", 1)
        input_n = kwargs.get("input_n", 0)
        resolution_tier = kwargs.get("resolution_tier")

        # 从 size 推导分辨率档位（如 "2400x1600" → max边>1024 → "high"）
        if not resolution_tier:
            size = kwargs.get("size")
            if size:
                try:
                    parts = size.lower().split("x")
                    max_side = max(int(parts[0]), int(parts[1]))
                    resolution_tier = "low" if max_side <= 1024 else "high"
                except (ValueError, IndexError):
                    pass

        logger.debug(f"[计算图片积分] is_character={is_character} n={n} input_n={input_n} resolution_tier={resolution_tier}")

        if n <= 0 or n > 10:
            logger.warning(f"[积分] 图片数量超出范围: n={n}")
            return Decimal("0")

        match_params = {"is_character": is_character}
        if resolution_tier:
            match_params["resolution_tier"] = resolution_tier

        calc_params = {"n": n, "input_n": input_n}
        return BillingEngine.estimate(
            db, ai_model.id, PricingRuleType.IMAGE_PER_PIECE.value, match_params, calc_params
        )

    @staticmethod
    def _calculate_video_point(db: Session, ai_model, **kwargs) -> Decimal:
        """计算视频模型积分消耗（基础费用 + 可选的全能参考附加费用）"""
        logger.debug(f"[积分] 计算视频模型，参数kwargs: {kwargs}")

        has_reference = kwargs.get("has_reference")

        # 兼容分辨率入参大小写敏感，例如"480p" -> "480P"
        video_resolution = kwargs.get("video_resolution")
        video_resolution = video_resolution.upper() if isinstance(video_resolution, str) else video_resolution

        video_output_duration = kwargs.get("video_output_duration")
        reference_duration = kwargs.get("reference_duration")

        if has_reference is None:
            logger.error("[积分] 视频模型缺少 has_reference 参数，导致无法计算积分")
            return Decimal("0")

        if not video_output_duration or video_output_duration <= 0:
            logger.error(f"[积分] 视频模型缺少或无效的 video_output_duration 参数: {video_output_duration}，导致无法计算积分")
            return Decimal("0")

        if video_output_duration > 3600:
            logger.error(f"[积分] 视频时长超过限制: {video_output_duration}秒，导致无法计算积分")
            return Decimal("0")

        if not video_resolution:
            logger.error("[积分] 缺少 video_resolution 参数，导致无法计算积分")
            return Decimal("0")

        # 1. 基础费用：video_second 策略
        match_params = {
            "has_reference": has_reference,
            "video_resolution": video_resolution,
        }
        calc_params = {"video_output_duration": video_output_duration}
        base_point = BillingEngine.estimate(
            db, ai_model.id, PricingRuleType.VIDEO_SECOND.value, match_params, calc_params
        )
        logger.debug(f"[积分] 清晰度={video_resolution}, 视频时长={video_output_duration}秒, 基础消耗={base_point}积分")

        # 2. 附加费用：video_ref_min 策略（仅 has_reference=True 且有参考时长时）
        ref_point = Decimal("0")
        if has_reference and reference_duration:
            ref_match = {"video_resolution": video_resolution, "video_output_duration": video_output_duration}
            ref_calc = {"reference_duration": reference_duration, "video_resolution": video_resolution}
            ref_point = BillingEngine.estimate(
                db, ai_model.id, PricingRuleType.VIDEO_REF_MIN.value, ref_match, ref_calc
            )
        elif has_reference and not reference_duration:
            logger.error(f"[积分] 带参考视频，缺少 reference_duration 参数，video_output_duration={video_output_duration}")

        real_point = base_point + ref_point
        logger.debug(f"[积分] 视频实际消耗{real_point}积分，其中基础消耗{base_point}积分，参考附加消耗{ref_point}积分")
        return real_point

    # ==================== 文本模型积分预估 ====================

    @staticmethod
    def estimate_text_point(
        db: Session,
        ai_model,
        prompt_text: str = "",
        max_tokens: int = 8192,
        **kwargs
    ) -> Decimal:
        """
        文本模型积分预估（用于预扣）

        根据提示文本长度和语言类型估算输入token，使用max_tokens作为输出上限。
        内部委托 BillingEngine（text_token 策略）。
        """
        calc_params = {"prompt_text": prompt_text, "max_tokens": max_tokens}
        return BillingEngine.estimate(
            db, ai_model.id, PricingRuleType.TEXT_TOKEN.value, {}, calc_params
        )

    @staticmethod
    def estimate_image_point_by_count(
        db: Session,
        ai_model,
        n: int = 1,
        is_character: bool = False,
    ) -> Decimal:
        """
        图片模型积分预估（精确值），根据图片数量、是否是人物三视图计算积分。
        适用于 火山图片模型 计算积分。
        """
        return PointService._calculate_image_point(db, ai_model, n=n, is_character=is_character)

    @staticmethod
    def estimate_image_point_by_prompt(
        db: Session,
        ai_model,
        prompt: str,
        image_info_list: list = None,
    ) -> Decimal:
        """
        图片模型积分预估，根据提示词长度、输入图片宽高、输入图片数量 计算积分。
        适用于 gpt-image-2（按 token 计费）计算积分。

        文生图：
        仅估算文字输入产生的积分，计算时忽略image_info_list。

        图生图：
        估算文字输入产生的积分 + 图片输入产生的积分

        image_info_list格式说明：
            [
                # width 图片宽度，单位像素点。
                # height 图片高度，单位像素点。
                {"image_url": "xx", "width": 1080, "height": 2048},
                {"image_url": "xx", "width": 2048, "height": 2048},
            ]

        内部委托 BillingEngine（image_token_full 策略）。
        """
        calc_params = {"prompt": prompt, "image_info_list": image_info_list or []}
        return BillingEngine.estimate(
            db, ai_model.id, PricingRuleType.IMAGE_TOKEN_FULL.value, {}, calc_params
        )


    @staticmethod
    def estimate_video_point(
        db: Session,
        ai_model,
        has_reference: bool = False,
        video_resolution: str = None,
        video_output_duration: int = 0,
        reference_duration: int = 0,
    ) -> Decimal:
        """
        视频模型积分预估（精确值）

        Args:
            db: 数据库会话
            ai_model: AI模型对象
            has_reference: 是否有全能参考
            video_resolution: 视频分辨率（如 "1080P"）
            video_output_duration: 输出视频时长（秒）
            reference_duration: 参考素材时长（秒）

        Returns:
            Decimal: 预估积分
        """
        return PointService._calculate_video_point(
            db,
            ai_model,
            has_reference=has_reference,
            video_resolution=video_resolution,
            video_output_duration=video_output_duration,
            reference_duration=reference_duration,
        )

    # ==================== 用户余额操作 ====================

    @staticmethod
    def get_user_balance(db: Session, user_id: str) -> Decimal:
        """获取用户当前余额"""
        balance = crud.user_balance_crud.get_by_user_id(db=db, user_id=user_id)
        return balance.balance if balance else Decimal("0")

    @staticmethod
    def deduct_balance(db: Session, user_id: str, amount: Decimal, source_id: str = None, is_commit: bool = False) -> None:
        """
        扣除用户积分（source_id 用于后续退款反查构成，建议传入业务唯一标识）

        Args:
            db: 数据库会话
            user_id: 用户ID
            amount: 扣除金额（Decimal）

        Raises:
            ValueError: 余额不足或记录不存在
        """
        user_balance = crud.user_balance_crud.deduct_balance(db=db, user_id=user_id, amount=amount, source_id=source_id, is_commit=is_commit)
        logger.info(f"[扣除积分] user_id={user_id}, amount={amount}, source_id={source_id}")
        logger.info(f"[扣除积分] 用户可用积分余额：{user_balance.balance}")
        return user_balance

    @staticmethod
    def refund_balance(db: Session, user_id: str, amount: Decimal,
                       source_id: str = None) -> None:
        """退还用户积分（按 source_id 反查预扣构成，优先回补购买余额、再补赠送余额）"""
        crud.user_balance_crud.refund_balance(
            db=db, user_id=user_id, amount=amount, source_id=source_id,
        )

    # ==================== 预扣积分机制 ====================

    @staticmethod
    def pre_deduct(db: Session, user_id: str, estimated_point: Decimal,
                   source_id: str = None) -> Decimal:
        """预扣积分（source_id 关联本次预扣，退款/结算时反查还原扣减构成）"""
        if estimated_point <= 0:
            # estimated<=0 不扣费,但仍 commit 结束事务:前面 _is_token_billing_image_model 的只读
            # 查询已在 autocommit=False 下隐式 BEGIN,不结束会一路挂到后面的 litellm.image_generation
            # (最长 300s 同步阻塞),形成 idle in transaction(持读锁、占连接)。故 early-return 也要提交。
            db.commit()
            logger.debug(f"[积分] 跳过预扣: estimated_point={estimated_point}")
            return Decimal("0")

        available = PointService.get_user_balance(db, user_id)
        logger.debug(f"[积分] 预扣检查: user_id={user_id} available={available} estimated={estimated_point}")

        if available < estimated_point:
            raise InsufficientBalanceError(
                message=f"积分余额不足: 余额={available}, 预估需要={estimated_point}",
                user_id=user_id,
                estimated_point=estimated_point,
            )

        crud.user_balance_crud.deduct_balance(db, user_id, estimated_point, source_id=source_id)
        db.commit()
        logger.debug(f"[积分] 预扣成功: user_id={user_id} amount={estimated_point} source_id={source_id}")
        return estimated_point

    @staticmethod
    def settle(db: Session, user_id: str, estimated_point: Decimal, actual_point: Decimal,
               source_id: str = None) -> None:
        """结算差额：actual > estimated 补扣差额；actual < estimated 退还多扣部分。

        source_id 与预扣保持一致，退款时优先回补购买余额、再补赠送余额。
        """
        if estimated_point <= 0:
            db.commit()
            return

        diff = actual_point - estimated_point
        logger.debug(f"[积分] 结算差额: user_id={user_id} estimated={estimated_point} actual={actual_point} diff={diff}")

        if diff == 0:
            db.commit()
            return

        try:
            if diff > 0:
                crud.user_balance_crud.deduct_balance(db, user_id, diff, source_id=source_id)
            else:
                crud.user_balance_crud.refund_balance(db, user_id, abs(diff), source_id=source_id)
            db.commit()
            logger.debug(f"[积分] 结算成功: user_id={user_id} diff={diff}")
        except Exception as e:
            db.rollback()
            logger.error(f"[积分] 结算失败: user_id={user_id} estimated={estimated_point} actual={actual_point} error={e}")
            raise

    @staticmethod
    def refund(db: Session, user_id: str, estimated_point: Decimal,
               source_id: str = None) -> None:
        """退还预扣积分（模型调用失败时）；source_id 与预扣一致以还原扣减构成。"""
        if estimated_point <= 0:
            db.commit()
            return

        try:
            crud.user_balance_crud.refund_balance(db, user_id, estimated_point, source_id=source_id)
            db.commit()
            logger.debug(f"[积分] 退还成功: user_id={user_id} amount={estimated_point}")
        except Exception as e:
            logger.warning(f"[积分] 退还失败: user_id={user_id} amount={estimated_point} error={e}")

    # ==================== 便捷方法 ====================

    @staticmethod
    def estimate_point(
        db: Session,
        model_name: str,
        model_type: str = None,
        **kwargs
    ) -> Decimal:
        """
        根据模型名和类型预估积分（便捷方法）

        Args:
            db: 数据库会话
            model_name: 模型名称（可带provider前缀）
            model_type: 模型类型（可选，用于优化查询）
            **kwargs: 其他参数

        Returns:
            Decimal: 预估积分
        """
        if not db:
            logger.debug(f"[积分] 跳过预估: db=None")
            return Decimal("0")

        clean_name = model_name.split("/", 1)[1] if "/" in model_name else model_name
        logger.debug(f"[积分] clean_name: {clean_name}")
        ai_model = crud.ai_model_crud.get_by_model_name(db=db, model_name=clean_name)

        if not ai_model:
            logger.warning(f"[积分] 未找到模型: {clean_name}")
            return Decimal("0")

        if ai_model.model_type == AIModelType.TEXT.value:
            prompt_text = ""
            for key in ("prompt", "system_prompt", "text_prompt"):
                val = kwargs.get(key)
                if val:
                    prompt_text += val

            messages = kwargs.get("messages")
            if messages:
                for msg in messages:
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        prompt_text += content
                    elif isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict):
                                prompt_text += part.get("text", "")

            max_tokens = kwargs.get("max_tokens", 8192)
            return PointService.estimate_text_point(db, ai_model, prompt_text, max_tokens)

        elif ai_model.model_type == AIModelType.IMAGE.value:
            # 数据驱动：根据 ai_model_pricing 表中配置的 rule_type 判断计费方式
            rule_types = crud.ai_model_pricing_crud.get_rule_types_by_model(db=db, model_id=ai_model.id)
            is_token_billing = any(rt.startswith("image_token") for rt in rule_types)

            if is_token_billing:
                # 按 token 计费的图片模型（gpt-image-2 / Gemini banana 等）
                prompt = kwargs.get("prompt", "")
                image_info_list = kwargs.get("image_info_list", [])
                return PointService.estimate_image_point_by_prompt(db, ai_model, prompt, image_info_list)
            else:
                # 按张计费的图片模型
                return PointService._calculate_image_point(db, ai_model, **kwargs)
        
        elif ai_model.model_type == AIModelType.VIDEO.value:
            has_reference = kwargs.get("has_reference", False)
            video_resolution = kwargs.get("video_resolution")
            video_output_duration = kwargs.get("video_output_duration", 0)
            reference_duration = kwargs.get("reference_duration", 0)
            return PointService.estimate_video_point(
                db, ai_model, has_reference, video_resolution, video_output_duration, reference_duration
            )
        
        else:
            logger.debug(f"[积分] 暂不支持的模型类型: {ai_model.model_type}")
            return Decimal("0")

    @staticmethod
    def calculate_actual_point(
        db: Session,
        model_name: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> Decimal:
        """
        调用完成后计算实际文本积分

        Args:
            db: 数据库会话
            model_name: 模型名称
            input_tokens: 实际输入token数
            output_tokens: 实际输出token数

        Returns:
            Decimal: 实际消耗积分
        """
        if not db:
            return Decimal("0")

        clean_name = model_name.split("/", 1)[1] if "/" in model_name else model_name
        ai_model = crud.ai_model_crud.get_by_model_name(db=db, model_name=clean_name)
        
        if not ai_model:
            return Decimal("0")

        return PointService.calculate_point(
            db,
            model_id=ai_model.id,
            input_token=input_tokens,
            output_token=output_tokens,
        )

    @staticmethod
    def calculate_actual_point_for_image2(
            db: Session,
            model_name: str,
            input_text_tokens: int = 0,
            input_image_tokens: int = 0,
            output_tokens: int = 0,
    ) -> Decimal:
        """
        调用完成后计算实际积分，仅image2可用

        内部委托 BillingEngine（image_token_full 策略）。

        Args:
            db: 数据库会话
            model_name: 模型名称
            input_text_tokens: 实际输入文本token数
            input_image_tokens: 实际输入图片token数
            output_tokens: 实际输出token数

        Returns:
            Decimal: 实际消耗积分
        """
        logger.info(f"[计算image2实际消耗积分] model_name={model_name} ")
        logger.info(f"[计算image2实际消耗积分] input_text_tokens={input_text_tokens} input_image_tokens={input_image_tokens}, output_tokens={output_tokens}")

        if not db:
            return Decimal("0")

        clean_name = model_name.split("/", 1)[1] if "/" in model_name else model_name
        ai_model = crud.ai_model_crud.get_by_model_name(db=db, model_name=clean_name)

        if not ai_model:
            logger.warning(f"[计算image2实际消耗积分] 未找到模型: {clean_name}")
            return Decimal("0")

        calc_params = {
            "input_text_tokens": input_text_tokens,
            "input_image_tokens": input_image_tokens,
            "output_tokens": output_tokens,
        }
        return BillingEngine.calculate_actual(
            db, ai_model.id, PricingRuleType.IMAGE_TOKEN_FULL.value, {}, calc_params
        )

    @staticmethod
    def calculate_actual_point_for_banana(
            db: Session,
            model_name: str,
            output_tokens: int = 0,
    ) -> Decimal:
        """
        调用完成后计算实际积分，仅gemini banana可用

        内部委托 BillingEngine（image_token_output 策略）。

        Returns:
            Decimal: 实际消耗积分
        """
        logger.info(f"[计算banana实际消耗积分] model_name={model_name} ")
        logger.info(f"[计算banana实际消耗积分] output_tokens={output_tokens}")

        if not db:
            return Decimal("0")

        clean_name = model_name.split("/", 1)[1] if "/" in model_name else model_name
        ai_model = crud.ai_model_crud.get_by_model_name(db=db, model_name=clean_name)

        if not ai_model:
            logger.warning(f"[计算banana实际消耗积分] 未找到模型: {clean_name}")
            return Decimal("0")

        calc_params = {"output_tokens": output_tokens}
        return BillingEngine.calculate_actual(
            db, ai_model.id, PricingRuleType.IMAGE_TOKEN_OUTPUT.value, {}, calc_params
        )
