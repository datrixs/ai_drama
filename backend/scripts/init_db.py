import sys
import uuid
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal, engine
from app.models import Base, User, AIProvider, AIModel, SysDict, SysPermission, AIModelPricing
from app.enums import PricingRuleType
from app.crud import user_api_config_crud, user_balance_crud, sys_dict_crud, ai_model_crud

from seed_membership import (
    _init_membership_levels,
    _init_membership_privileges,
    _init_point_purchase_plans,
)


def _init_default_user(db: Session):
    """
    创建默认用户
    用户：test
    密码：123456
    """
    try:
        existing_user = db.query(User).filter_by(username=settings.DEFAULT_USER_NAME).first()

        if not existing_user:
            user = User(
                id=str(uuid.uuid4()),
                username=settings.DEFAULT_USER_NAME,
                password_hash=get_password_hash(settings.DEFAULT_USER_PASSWORD),
                status="enable",
                parent_user_id=None,
                sub_user_limit=10,
                type="pro"
            )
            db.add(user)
            db.flush()
            print(f"默认用户 '{settings.DEFAULT_USER_NAME}' 创建成功")

            # 初始化用户余额表
            user_balance_crud.init_user_balance(db=db, user_id=user.id)
            print(f"默认用户 '{settings.DEFAULT_USER_NAME}' 初始化余额表成功")

            # 初始化默认API配置
            user_api_config = user_api_config_crud.get_default_api_config(user.id)
            db.add(user_api_config)
            print(f"默认用户 '{settings.DEFAULT_USER_NAME}' API配置创建成功")
        else:
            print(f"默认用户 '{settings.DEFAULT_USER_NAME}' 已存在，跳过创建")
    except Exception as e:
        print("创建默认用户失败")
        raise e

def _init_ai_provider(db: Session):
    """
    初始化模型供应商，根据code判断是否已存在
    """
    try:
        provider_list = [
            {
                "name": "火山引擎 Ark",
                "code": "volcengine",
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "description": "字节跳动-火山引擎",
                "model_list": [
                    # 文本模型：text
                    {
                        "name": "Doubao Seed 1.8",
                        "model_name": "doubao-seed-1-8-251228",
                        "model_type": "text",
                        "base_url": None
                    },
                    {
                        "name": "Doubao Seed 2.0 Pro",
                        "model_name": "doubao-seed-2-0-pro-260215",
                        "model_type": "text",
                        "base_url": None
                    },
                    {
                        "name": "Doubao Seed 2.0 Lite",
                        "model_name": "doubao-seed-2-0-lite-260215",
                        "model_type": "text",
                        "base_url": None
                    },
                    {
                        "name": "Doubao Seed 2.0 Mini",
                        "model_name": "doubao-seed-2-0-mini-260215",
                        "model_type": "text",
                        "base_url": None
                    },
                    {
                        "name": "Doubao Seed 1.6",
                        "model_name": "doubao-seed-1-6-251015",
                        "model_type": "text",
                        "base_url": None
                    },
                    {
                        "name": "Doubao Seed 1.6 Lite",
                        "model_name": "doubao-seed-1-6-lite-251015",
                        "model_type": "text",
                        "base_url": None
                    },
                    # 图像模型：Image
                    {
                        "name": "Seedream 4.5",
                        "model_name": "doubao-seedream-4-5-251128",
                        "model_type": "image",
                        "base_url": None,
                        "billing_type": "times"
                    },
                    {
                        "name": "Seedream 5.0 Lite",
                        "model_name": "doubao-seedream-5-0-260128",
                        "model_type": "image",
                        "base_url": None,
                        "billing_type": "times"
                    },
                    # 视频
                    {
                        "name": "Seedance 2.0",
                        "model_name": "doubao-seedance-2-0-260128",
                        "model_type": "video",
                        "base_url": None
                    },
                    {
                        "name": "Seedance 2.0 Fast",
                        "model_name": "doubao-seedance-2-0-fast-260128",
                        "model_type": "video",
                        "base_url": None
                    },
                ]
            },
            {
                "name": "ChatGPT",
                "code": "chatgpt",
                "base_url": "https://agentrs.jd.com/api/saas/openai-u/v1",
                "description": "京东-API代理",
                "model_list": [
                    # 图像模型
                    {
                        "name": "gpt-image-2",
                        "model_name": "gpt-image-2",
                        "model_type": "image",
                        "base_url": None,
                        "billing_type": "token"
                    },
                ]
            },
            {
                "name": "Deepseek",
                "code": "deepseek",
                "base_url": "https://agentrs.jd.com/api/saas/openai-u/v1",
                "description": "京东-API代理",
                "model_list": [
                    # 文本模型
                    {
                        "name": "DeepSeek-V4-pro",
                        "model_name": "DeepSeek-V4-pro",
                        "model_type": "text",
                        "base_url": None
                    },
                    {
                        "name": "DeepSeek-V4-Flash",
                        "model_name": "DeepSeek-V4-Flash",
                        "model_type": "text",
                        "base_url": None
                    },
                    {
                        "name": "DeepSeek-R1-0528",
                        "model_name": "DeepSeek-R1-0528",
                        "model_type": "text",
                        "base_url": None
                    },
                ]
            },
        ]

        for provider_data in provider_list:
            existing = db.query(AIProvider).filter_by(code=provider_data["code"]).first()
            if not existing:
                provider = AIProvider(
                    id=str(uuid.uuid4()),
                    name=provider_data["name"],
                    code=provider_data["code"],
                    base_url=provider_data["base_url"],
                    description=provider_data["description"],
                )
                db.add(provider)
                db.flush()
                print(f"模型供应商 '{provider_data['name']}' 创建成功")

                # 创建模型
                for model_data in provider_data.get("model_list", []):
                    model = AIModel(
                        id=str(uuid.uuid4()),
                        provider_id=provider.id,
                        name=model_data["name"],
                        model_name=model_data["model_name"],
                        model_type=model_data["model_type"],
                        base_url=model_data["base_url"],
                        billing_type=model_data.get("billing_type"),
                    )
                    db.add(model)
                db.flush()
                print(f"模型供应商 '{provider_data['name']}' 模型创建成功")
            else:
                print(f"模型供应商 '{provider_data['name']}' 已存在，跳过创建")
    except Exception as e:
        print("初始化模型供应商失败")
        raise e

def _init_sys_dict(db: Session):
    try:
        sys_dict_list = [
            # 用户状态
            ("user_status", "enable", "1", 1, "正常"),
            ("user_status", "disable", "0", 2, "禁用"),
            # 用户类型
            ("user_type", "normal", "normal", 1, "普通版"),
            ("user_type", "lite", "lite", 2, "轻量版"),
            ("user_type", "pro", "pro", 3, "专业版"),
        ]

        for sys_dict in sys_dict_list:
            existing = sys_dict_crud.is_exist(db=db, dict_name=sys_dict[0], key=sys_dict[1])
            if not existing:
                sys_dict_obj = SysDict(
                    id=uuid4(),
                    dict_name=sys_dict[0],
                    key=sys_dict[1],
                    value=sys_dict[2],
                    sort=sys_dict[3],
                    remark=sys_dict[4]
                )
                db.add(sys_dict_obj)

    except Exception as e:
        print("初始化数据字典失败")
        raise e

def _init_permission(db: Session):
    """
    初始化权限相关表数据
    """
    try:
        # 初始化系统权限表（sys_permission）
        permission_list = [
            # 项目
            {"code": "project:create", "name": "创建项目"},
            {"code": "project:read", "name": "查看项目"},
            {"code": "project:update", "name": "编辑项目"},
            {"code": "project:delete", "name": "删除项目"},
            # 资产中心
            {"code": "asset:create", "name": "创建资产"},
            {"code": "asset:read", "name": "查看资产"},
            {"code": "asset:update", "name": "编辑资产"},
            {"code": "asset:delete", "name": "删除资产"},
            # 主账号的资产
            {"code": "main_user_asset:read", "name": "查看主账号资产"},
        ]
        for permission in permission_list:
            permission_obj = db.query(SysPermission).filter_by(code=permission["code"]).first()
            if not permission_obj:
                sys_permission_obj = SysPermission(
                    id=str(uuid4()),
                    code=permission["code"],
                    name=permission["name"],
                )
                db.add(sys_permission_obj)
                print(f"- 添加权限：{permission["code"]}")
            else:
                print(f"- 权限（{permission["code"]}）已存在，跳过添加")

        print("初始化系统权限表成功")
    except Exception as e:
        print("初始化系统权限表失败")
        raise e


def _init_ai_model_pricing(db: Session):
    """
    初始化模型计费配置表(ai_model_pricing)

    将原 ai_model_point + ai_model_reference_point + super_res_point 三张表的数据
    统一写入 ai_model_pricing 新表（行式存储 + 策略模式）。
    """
    try:
        # ==================== 文本模型 → text_token ====================
        text_model_list = [
            {"model_name": "doubao-seed-2-0-lite-260215",   "input_point_per_million": 216,  "output_point_per_million": 1296},
            {"model_name": "doubao-seed-2-0-mini-260215",   "input_point_per_million": 96,   "output_point_per_million": 960},
            {"model_name": "doubao-seed-1-6-251015",         "input_point_per_million": 288,  "output_point_per_million": 2880},
            {"model_name": "doubao-seed-1-6-lite-251015",    "input_point_per_million": 144,  "output_point_per_million": 1440},
            {"model_name": "DeepSeek-V4-Flash",              "input_point_per_million": 120,  "output_point_per_million": 240},
            {"model_name": "DeepSeek-V4-pro",                "input_point_per_million": 1440, "output_point_per_million": 2880},
            {"model_name": "DeepSeek-R1-0528",               "input_point_per_million": 480,  "output_point_per_million": 1920},
        ]
        for item in text_model_list:
            model_obj = ai_model_crud.get_by_model_name(db, item["model_name"])
            if model_obj:
                db.add(AIModelPricing(
                    id=str(uuid4()),
                    model_id=model_obj.id,
                    rule_type=PricingRuleType.TEXT_TOKEN.value,
                    match_config={},
                    price_config={
                        "input_point_per_million": item["input_point_per_million"],
                        "output_point_per_million": item["output_point_per_million"],
                    },
                    is_enabled=True,
                ))

        # ==================== 图片模型（按张计费）→ image_per_piece ====================
        image_per_piece_list = [
            {"model_name": "doubao-seedream-5-0-260128",  "is_character": False, "image_point": 33},
            {"model_name": "doubao-seedream-5-0-260128",  "is_character": True,  "image_point": 66},
            {"model_name": "doubao-seedream-4-5-251128",  "is_character": False, "image_point": 38},
            {"model_name": "doubao-seedream-4-5-251128",  "is_character": True,  "image_point": 75},
        ]
        for item in image_per_piece_list:
            model_obj = ai_model_crud.get_by_model_name(db, item["model_name"])
            if model_obj:
                db.add(AIModelPricing(
                    id=str(uuid4()),
                    model_id=model_obj.id,
                    rule_type=PricingRuleType.IMAGE_PER_PIECE.value,
                    match_config={"is_character": item["is_character"]},
                    price_config={"image_point": item["image_point"]},
                    is_enabled=True,
                ))

        # ==================== 图片模型（按token计费, gpt-image-2）→ image_token_full ====================
        image_token_full_list = [
            {"model_name": "gpt-image-2", "input_text_point": 5760, "input_image_point": 9216, "output_total_point": 3456},
        ]
        for item in image_token_full_list:
            model_obj = ai_model_crud.get_by_model_name(db, item["model_name"])
            if model_obj:
                db.add(AIModelPricing(
                    id=str(uuid4()),
                    model_id=model_obj.id,
                    rule_type=PricingRuleType.IMAGE_TOKEN_FULL.value,
                    match_config={},
                    price_config={
                        "input_text_point": item["input_text_point"],
                        "input_image_point": item["input_image_point"],
                        "output_total_point": item["output_total_point"],
                    },
                    is_enabled=True,
                ))

        # ==================== 视频模型（按秒计费）→ video_second ====================
        video_second_list = [
            # 无全能参考
            {"model_name": "doubao-seedance-2-0-260128",      "has_reference": False, "video_resolution": "480P",  "video_point_per_second": 105},
            {"model_name": "doubao-seedance-2-0-260128",      "has_reference": False, "video_resolution": "720P",  "video_point_per_second": 225},
            {"model_name": "doubao-seedance-2-0-260128",      "has_reference": False, "video_resolution": "1080P", "video_point_per_second": 563},
            {"model_name": "doubao-seedance-2-0-fast-260128", "has_reference": False, "video_resolution": "480P",  "video_point_per_second": 84},
            {"model_name": "doubao-seedance-2-0-fast-260128", "has_reference": False, "video_resolution": "720P",  "video_point_per_second": 180},
            # 有全能参考
            {"model_name": "doubao-seedance-2-0-260128",      "has_reference": True,  "video_resolution": "480P",  "video_point_per_second": 63},
            {"model_name": "doubao-seedance-2-0-260128",      "has_reference": True,  "video_resolution": "720P",  "video_point_per_second": 135},
            {"model_name": "doubao-seedance-2-0-260128",      "has_reference": True,  "video_resolution": "1080P", "video_point_per_second": 338},
            {"model_name": "doubao-seedance-2-0-fast-260128", "has_reference": True,  "video_resolution": "480P",  "video_point_per_second": 51},
            {"model_name": "doubao-seedance-2-0-fast-260128", "has_reference": True,  "video_resolution": "720P",  "video_point_per_second": 108},
        ]
        for item in video_second_list:
            model_obj = ai_model_crud.get_by_model_name(db, item["model_name"])
            if model_obj:
                db.add(AIModelPricing(
                    id=str(uuid4()),
                    model_id=model_obj.id,
                    rule_type=PricingRuleType.VIDEO_SECOND.value,
                    match_config={
                        "has_reference": item["has_reference"],
                        "video_resolution": item["video_resolution"],
                    },
                    price_config={"video_point_per_second": item["video_point_per_second"]},
                    is_enabled=True,
                ))

        # ==================== 视频模型（全能参考附加费用）→ video_ref_min ====================
        # 数据量大，从原始列表导入
        video_ref_min_list = _build_video_ref_min_seed_data()
        for item in video_ref_min_list:
            model_obj = ai_model_crud.get_by_model_name(db, item["model_name"])
            if model_obj:
                db.add(AIModelPricing(
                    id=str(uuid4()),
                    model_id=model_obj.id,
                    rule_type=PricingRuleType.VIDEO_REF_MIN.value,
                    match_config={
                        "video_resolution": item["video_resolution"],
                        "video_output_duration": item["video_output_duration"],
                    },
                    price_config={
                        "reference_min_duration": item["reference_min_duration"],
                        "video_point": item["video_point"],
                    },
                    is_enabled=True,
                ))

        # ==================== 视频超分 → super_res（model_id=NULL）====================
        super_res_list = [
            {"target_video_resolution": "720P",  "point_per_second": 6},
            {"target_video_resolution": "1080P", "point_per_second": 12},
            {"target_video_resolution": "2K",    "point_per_second": 24},
            {"target_video_resolution": "4K",    "point_per_second": 48},
        ]
        for item in super_res_list:
            db.add(AIModelPricing(
                id=str(uuid4()),
                model_id=None,
                rule_type=PricingRuleType.SUPER_RES.value,
                match_config={"target_video_resolution": item["target_video_resolution"]},
                price_config={"point_per_second": item["point_per_second"]},
                is_enabled=True,
            ))

        print("初始化模型计费配置表(ai_model_pricing)成功")
    except Exception as e:
        print("初始化模型计费配置表(ai_model_pricing)失败")
        raise e


def _build_video_ref_min_seed_data():
    """
    构建视频全能参考附加费用的种子数据（从原 ai_model_reference_point 迁移）
    """
    data = []
    # 格式: (model_name, resolution, [(duration, min_duration, point), ...])
    configs = [
        # seedance 2.0 - 480P
        ("doubao-seedance-2-0-260128", "480P", [
            (4, 3, 441), (5, 4, 567), (6, 4, 630), (7, 5, 756), (8, 6, 882),
            (9, 6, 945), (10, 7, 1071), (11, 8, 1197), (12, 8, 1260),
            (13, 9, 1386), (14, 10, 1512), (15, 10, 1575),
        ]),
        # seedance 2.0 fast - 480P
        ("doubao-seedance-2-0-fast-260128", "480P", [
            (4, 3, 357), (5, 4, 459), (6, 4, 510), (7, 5, 612), (8, 6, 714),
            (9, 6, 756), (10, 7, 867), (11, 8, 969), (12, 8, 1020),
            (13, 9, 1122), (14, 10, 1224), (15, 10, 1275),
        ]),
        # seedance 2.0 - 720P
        ("doubao-seedance-2-0-260128", "720P", [
            (4, 3, 945), (5, 4, 1215), (6, 4, 1350), (7, 5, 1620), (8, 6, 1890),
            (9, 6, 2025), (10, 7, 2295), (11, 8, 2565), (12, 8, 2700),
            (13, 9, 2970), (14, 10, 3240), (15, 10, 3375),
        ]),
        # seedance 2.0 fast - 720P
        ("doubao-seedance-2-0-fast-260128", "720P", [
            (4, 3, 756), (5, 4, 972), (6, 4, 1080), (7, 5, 1296), (8, 6, 1512),
            (9, 6, 1620), (10, 7, 1836), (11, 8, 2052), (12, 8, 2160),
            (13, 9, 2376), (14, 10, 2592), (15, 10, 2700),
        ]),
        # seedance 2.0 - 1080P
        ("doubao-seedance-2-0-260128", "1080P", [
            (4, 3, 2363), (5, 4, 3038), (6, 4, 3375), (7, 5, 4050), (8, 6, 4725),
            (9, 6, 5063), (10, 7, 5738), (11, 8, 6413), (12, 8, 6750),
            (13, 9, 7452), (14, 10, 8100), (15, 10, 8438),
        ]),
    ]

    for model_name, resolution, items in configs:
        for duration, min_duration, point in items:
            data.append({
                "model_name": model_name,
                "video_resolution": resolution,
                "video_output_duration": duration,
                "reference_min_duration": min_duration,
                "video_point": point,
            })
    return data


def init_db() -> None:
    """
    初始化数据库：创建所有表并写入全部种子数据（全新部署）
    """
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 初始化权限相关表数据
        _init_permission(db=db)

        # 创建默认用户（含余额表、默认API配置）
        _init_default_user(db=db)

        # 初始化模型供应商与模型
        _init_ai_provider(db=db)

        # 初始化数据字典
        _init_sys_dict(db=db)

        # 初始化模型计费配置表
        _init_ai_model_pricing(db=db)

        # 初始化会员等级、权益与积分购买方案
        level_map = _init_membership_levels(db)
        _init_membership_privileges(db, level_map)
        _init_point_purchase_plans(db)
    except Exception as e:
        db.rollback()
        print("初始化报错，数据回滚")
        raise e
    else:
        db.commit()
        print("全部数据初始化完成")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
