"""
会员等级种子数据初始化脚本

使用方式:
    cd backend
    python scripts/seed_membership.py

功能:
    - 创建 3 个会员等级: 免费版、专业版、企业版
    - 为每个等级插入权益 KV 数据
    - 幂等: 按 name 判断是否已存在，已存在则跳过
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models import Base
from app.models.membership import MembershipLevel, MembershipLevelPrivilege
from app.models.point_record import PointPurchasePlan


# ── 会员等级定义 ──────────────────────────────────────────────

MEMBERSHIP_LEVELS = [
    {
        "name": "免费版",
        "level_order": 1,
        "monthly_price": 0,
        "yearly_price": 0,
        "yearly_discount_rate": 1.00,
        "monthly_discount_rate": 1.00,
        "can_buy_points": False,
        "status": 1,
    },
    {
        "name": "专业版",
        "level_order": 10,
        "monthly_price": 99,
        "yearly_price": 599,
        "yearly_discount_rate": 1.00,
        "monthly_discount_rate": 1.00,
        "can_buy_points": True,
        "status": 1,
    },
    {
        "name": "企业版",
        "level_order": 100,
        "monthly_price": 2999,
        "yearly_price": 28790,
        "yearly_discount_rate": 1.00,
        "monthly_discount_rate": 1.00,
        "can_buy_points": True,
        "status": 1,
    },
]

# ── 权益定义（按等级名称分组）──────────────────────────────────

MEMBERSHIP_PRIVILEGES = {
    "免费版": [
        {"key": "monthly_points", "value": "1200", "remark": "每月赠送积分"},
        # {"key": "project_limit", "value": "3", "remark": "项目数量限制"},
        # {"key": "ai_concurrency", "value": "1", "remark": "AI 任务并发数"},
        # {"key": "video_max_duration", "value": "60", "remark": "单视频最大时长（秒）"},
        # {"key": "export_watermark", "value": "true", "remark": "导出带水印"},
        # {"key": "storage_limit", "value": "500", "remark": "存储空间上限（MB）"},
        # {"key": "priority_support", "value": "false", "remark": "优先技术支持"},
        # {"key": "custom_branding", "value": "false", "remark": "自定义品牌水印/Logo"},
        # {"key": "team_member_limit", "value": "1", "remark": "团队成员上限"},
    ],
    "专业版": [
        {"key": "monthly_points", "value": "12000", "remark": "每月赠送12000积分"},
        # {"key": "project_limit", "value": "50", "remark": "项目数量限制"},
        # {"key": "ai_concurrency", "value": "3", "remark": "AI 任务并发数"},
        # {"key": "video_max_duration", "value": "300", "remark": "单视频最大时长（秒）"},
        # {"key": "export_watermark", "value": "false", "remark": "导出无水印"},
        # {"key": "storage_limit", "value": "5000", "remark": "存储空间上限（MB）"},
        # {"key": "priority_support", "value": "true", "remark": "优先技术支持"},
        # {"key": "custom_branding", "value": "false", "remark": "自定义品牌水印/Logo"},
        # {"key": "team_member_limit", "value": "5", "remark": "团队成员上限"},
    ],
    "企业版": [
        {"key": "monthly_points", "value": "400000", "remark": "每月赠送400000积分"},
        # {"key": "project_limit", "value": "-1", "remark": "项目数量限制（无限）"},
        # {"key": "ai_concurrency", "value": "10", "remark": "AI 任务并发数"},
        # {"key": "video_max_duration", "value": "-1", "remark": "单视频最大时长（无限）"},
        # {"key": "export_watermark", "value": "false", "remark": "导出无水印"},
        # {"key": "storage_limit", "value": "-1", "remark": "存储空间上限（无限）"},
        # {"key": "priority_support", "value": "true", "remark": "优先技术支持"},
        # {"key": "custom_branding", "value": "true", "remark": "自定义品牌水印/Logo"},
        # {"key": "team_member_limit", "value": "50", "remark": "团队成员上限"},
    ],
}

# ── 积分购买方案定义 ──────────────────────────────────────────

POINT_PURCHASE_PLANS = [
    {
        "point_amount": 50,
        "original_price": 0.50,
        "discount_price": 0.50,
        "is_enabled": True,
        "sort_order": 1,
    },
    {
        "point_amount": 100,
        "original_price": 1.00,
        "discount_price": 1.00,
        "is_enabled": True,
        "sort_order": 2,
    },
    {
        "point_amount": 1000,
        "original_price": 10.00,
        "discount_price": 10.00,
        "is_enabled": True,
        "sort_order": 3,
    },
    {
        "point_amount": 5000,
        "original_price": 50.00,
        "discount_price": 50.00,
        "is_enabled": True,
        "sort_order": 4,
    },
    {
        "point_amount": 10000,
        "original_price": 100.00,
        "discount_price": 100.00,
        "is_enabled": True,
        "sort_order": 5,
    },
]


def _init_membership_levels(db: Session) -> dict[str, str]:
    """插入会员等级记录，返回 {name: level_id} 映射"""
    level_map: dict[str, str] = {}

    for level_data in MEMBERSHIP_LEVELS:
        existing = db.query(MembershipLevel).filter_by(name=level_data["name"]).first()
        if existing:
            level_map[level_data["name"]] = existing.id
            print(f"  会员等级 '{level_data['name']}' 已存在，跳过")
            continue

        level = MembershipLevel(
            id=str(uuid.uuid4()),
            name=level_data["name"],
            level_order=level_data["level_order"],
            monthly_price=level_data["monthly_price"],
            yearly_price=level_data["yearly_price"],
            yearly_discount_rate=level_data["yearly_discount_rate"],
            can_buy_points=level_data["can_buy_points"],
            status=level_data["status"],
        )
        db.add(level)
        db.flush()
        level_map[level_data["name"]] = level.id
        print(f"  会员等级 '{level_data['name']}' 创建成功")

    return level_map


def _init_membership_privileges(db: Session, level_map: dict[str, str]) -> None:
    """为每个等级插入权益 KV 数据"""
    for level_name, privileges in MEMBERSHIP_PRIVILEGES.items():
        level_id = level_map.get(level_name)
        if not level_id:
            print(f"  等级 '{level_name}' 未找到，跳过权益插入")
            continue

        created_count = 0
        for p in privileges:
            existing = (
                db.query(MembershipLevelPrivilege)
                .filter_by(level_id=level_id, privilege_key=p["key"])
                .first()
            )
            if existing:
                continue

            privilege = MembershipLevelPrivilege(
                id=str(uuid.uuid4()),
                level_id=level_id,
                privilege_key=p["key"],
                privilege_value=p["value"],
                remark=p["remark"],
            )
            db.add(privilege)
            created_count += 1

        db.flush()
        print(f"  等级 '{level_name}' 权益: 新增 {created_count} 条，"
              f"总计 {len(privileges)} 条")


def _init_point_purchase_plans(db: Session) -> None:
    """插入积分购买方案记录"""
    created_count = 0
    for plan_data in POINT_PURCHASE_PLANS:
        existing = db.query(PointPurchasePlan).filter_by(
            point_amount=plan_data["point_amount"]
        ).first()
        if existing:
            print(f"  积分方案 {plan_data['point_amount']}积分 已存在，跳过")
            continue

        plan = PointPurchasePlan(
            id=str(uuid.uuid4()),
            point_amount=plan_data["point_amount"],
            original_price=plan_data["original_price"],
            discount_price=plan_data["discount_price"],
            is_enabled=plan_data["is_enabled"],
            sort_order=plan_data["sort_order"],
        )
        db.add(plan)
        created_count += 1

    db.flush()
    print(f"  积分购买方案: 新增 {created_count} 条，总计 {len(POINT_PURCHASE_PLANS)} 条")


def seed_membership() -> None:
    """主函数：初始化会员等级种子数据"""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("开始初始化会员等级数据...")
        level_map = _init_membership_levels(db)
        print("开始初始化会员等级权益...")
        _init_membership_privileges(db, level_map)
        print("开始初始化积分购买方案...")
        _init_point_purchase_plans(db)
    except Exception as e:
        db.rollback()
        print(f"初始化失败，数据已回滚: {e}")
        raise
    else:
        db.commit()
        print("会员等级种子数据初始化完成")
    finally:
        db.close()


if __name__ == "__main__":
    seed_membership()
