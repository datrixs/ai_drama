import math

from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.models import AIModel, AIModelPoint, AIModelReferencePoint
from app.schemas import (AIModelCreateSchema, AIModelUpdateSchema, AIModelPointCreateSchema, AIModelPointUpdateSchema,
                         AIModelReferencePointCreateSchema, AIModelReferencePointUpdateSchema)
from app.enums import AIModelType

MILLION = 1000000
HUNDRED = 100


class CRUDAIModel(CRUDBase[AIModel, AIModelCreateSchema, AIModelUpdateSchema]):

    def get_by_model_name(self, db: Session, model_name: str):
        """
        根据model_name获取模型
        """
        return self.get_queryset(db).filter(self.model.model_name==model_name).first()


class CRUDAIModelPoint(CRUDBase[AIModelPoint, AIModelPointCreateSchema, AIModelPointUpdateSchema]):
    def get_by_model_id(self, db: Session, model_id: str):
        """
        根据model_id获取某个模型的积分信息
        """
        return self.get_queryset(db).filter(self.model.model_id==model_id).first()

    def calculate_point_by_text(self, db: Session, ai_model: AIModel, input_token: int, output_token: int):
        """
        计算文本类型的积分消耗
        """
        # 模型积分对象
        model_point_obj = self.get_by_model_id(db=db, model_id=ai_model.id)

        if ai_model.model_type != AIModelType.TEXT.value:
            raise Exception(f"大模型为：{ai_model.model_name}, 不是文本对象，请使用调用其他方法计算积分")

        if not input_token or not output_token:
            raise Exception(f"参数input_token、output_token不能为空")

        # 输入、输出token换算比例
        input_point_per_million = model_point_obj.input_point
        output_point_per_million = model_point_obj.output_point

        # 计算输入token对应的积分
        input_point = input_token * input_point_per_million / MILLION
        output_point = output_token * output_point_per_million / MILLION
        # 向上取整
        total_point = math.ceil(input_point + output_point)

        return total_point

    def calculate_point_by_image(self, db: Session, ai_model: AIModel, is_character: bool):
        """
        计算图像类型的积分消耗
        """
        if is_character == True:
            model_point_obj = self.get_queryset(db).filter(self.model.model_id==ai_model.id, self.model.is_character==True).first()
        else:
            model_point_obj = self.get_queryset(db).filter(self.model.model_id==ai_model.id, self.model.is_character==False).first()

        return model_point_obj.image_point

    def calculate_point_by_video(self, db: Session, ai_model: AIModel, has_reference: bool, video_resolution: str, video_output_duration: int):
        """
        计算视频类型的积分消耗（不含视频类型全能参考、含参考seedance2.0 fast-1080P）
        """
        model_point_obj = self.get_queryset(db).filter(
            self.model.model_id==ai_model.id,
            self.model.has_reference==has_reference,
            self.model.video_resolution==video_resolution
        ).first()

        # 总积分消耗 = 每秒消耗 * 输出视频时长
        video_point = video_output_duration * model_point_obj.video_point

        return video_point


class CRUDAIModelReferencePoint(CRUDBase[AIModelReferencePoint, AIModelReferencePointCreateSchema, AIModelReferencePointUpdateSchema]):
    def calculate_point_by_video_reference(
        self,
        db: Session,
        ai_model: AIModel,
        video_resolution: str,
        video_output_duration: int,
        reference_video_duration: int
    ):
        """
        计算全能参考视频的积分消耗（视频参考，但不含seedance2.0 fast-1080P）

        计算规则：
        - 从 ai_model_reference_point 表中获取最低积分消耗配置

        Args:
            db: Session
            ai_model: AIModel 对象
            video_resolution: 视频清晰度，例如 "480P", "1080P"
            video_output_duration: 输出视频时长，单位秒
            reference_video_duration: 参考视频时长，单位秒

        Returns:
            Decimal: 计算得到的积分消耗
        """
        from loguru import logger

        model_reference_point_obj = self.get_queryset(db).filter(
            self.model.model_id==ai_model.id,
            self.model.video_resolution==video_resolution,
            self.model.video_output_duration==video_output_duration,
        ).first()

        if not model_reference_point_obj:
            logger.warning(
                f"[积分] 未找到全能参考视频配置: model_id={ai_model.id} "
                f"resolution={video_resolution} duration={video_output_duration}"
            )
            return ai_model_point_crud.calculate_point_by_video(
                db=db,
                ai_model=ai_model,
                has_reference=True,
                video_resolution=video_resolution,
                video_output_duration=video_output_duration
            )

        if reference_video_duration <= model_reference_point_obj.reference_min_duration:
            # 参考视频时长 <= 最低要求 → 使用最低积分消耗
            logger.debug(
                f"[积分] 参考视频时长({reference_video_duration}s) <= 最低要求({model_reference_point_obj.reference_min_duration}s) "
                f"→ 使用最低积分: {model_reference_point_obj.video_point}"
            )
            return model_reference_point_obj.video_point
        else:
            # 参考视频时长 > 最低要求 → 按实际输出视频时长计算积分
            video_point = ai_model_point_crud.calculate_point_by_video(
                db=db,
                ai_model=ai_model,
                has_reference=True,
                video_resolution=video_resolution,
                video_output_duration=reference_video_duration
            )
            logger.debug(
                f"[积分] 参考视频时长({reference_video_duration}s) > 最低要求({model_reference_point_obj.reference_min_duration}s) "
                f"→ 按秒计算积分: {video_point}"
            )
            return video_point


ai_model_crud = CRUDAIModel(AIModel)
ai_model_point_crud = CRUDAIModelPoint(AIModelPoint)
ai_model_reference_point_crud = CRUDAIModelReferencePoint(AIModelReferencePoint)