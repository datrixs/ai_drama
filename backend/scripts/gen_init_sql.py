"""
生成开源初始数据 SQL（sql/init.sql）：表结构 + 种子数据

用法：
    cd backend
    python scripts/gen_init_sql.py

原理：
- 无需连接数据库：表结构由 SQLAlchemy 元数据编译输出，等价于 create_all 实际执行的 DDL；
- 种子数据复用 init_db.py 的初始化函数，通过"记录式伪 Session"收集生成的对象，
  保证 sql/init.sql 与 `python scripts/init_db.py` 写入的数据完全一致；
- 运行前需存在 backend/.env.example（为 Settings 提供占位环境变量）。
"""
import json
import os
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent

# 环境变量占位：仅用于通过 Settings 必填校验，不连接任何真实服务
env_example = BACKEND_DIR / ".env.example"
for line in env_example.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)
os.environ.setdefault("DEFAULT_USER_NAME", "test")
os.environ.setdefault("DEFAULT_USER_PASSWORD", "123456")

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from sqlalchemy import create_mock_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

from app.models import Base
import init_db as init_db_module
from seed_membership import (
    _init_membership_levels,
    _init_membership_privileges,
    _init_point_purchase_plans,
)

OUTPUT_PATH = BACKEND_DIR.parent / "sql" / "init.sql"


class FakeQuery:
    """伪查询：从未落库的记录对象中按过滤条件查找首个匹配"""

    def __init__(self, recorder, model):
        self.recorder = recorder
        self.model = model
        self.filters = {}

    def _match(self, obj):
        for key, value in self.filters.items():
            if getattr(obj, key, None) != value:
                return False
        return True

    def filter_by(self, **kwargs):
        self.filters.update(kwargs)
        return self

    def filter(self, *criteria):
        for criterion in criteria:
            try:
                self.filters[criterion.left.name] = criterion.right.value
            except AttributeError:
                pass
        return self

    def first(self):
        for obj in self.recorder.objects:
            if isinstance(obj, self.model) and self._match(obj):
                return obj
        return None

    def all(self):
        return [o for o in self.recorder.objects if isinstance(o, self.model) and self._match(o)]


class RecorderSession:
    """伪 Session：记录 add() 的对象，query().first() 从记录中查找（模拟全新空库）"""

    def __init__(self):
        self.objects = []

    def add(self, obj):
        self.objects.append(obj)

    def query(self, model, *args, **kwargs):
        return FakeQuery(self, model)

    def flush(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def collect_seed_objects():
    db = RecorderSession()
    init_db_module._init_permission(db=db)
    init_db_module._init_default_user(db=db)
    init_db_module._init_ai_provider(db=db)
    init_db_module._init_sys_dict(db=db)
    init_db_module._init_ai_model_pricing(db=db)
    level_map = _init_membership_levels(db)
    _init_membership_privileges(db, level_map)
    _init_point_purchase_plans(db)
    return db.objects


def generate_ddl() -> list[str]:
    dialect = postgresql.dialect()
    statements = []

    def dump(sql, *multiparams, **params):
        text = str(sql.compile(dialect=dialect)).strip().rstrip(";")
        statements.append(text + ";")

    mock_engine = create_mock_engine("postgresql+psycopg2://", dump)
    Base.metadata.create_all(mock_engine, checkfirst=False)
    return statements


def render_value(column, value) -> str:
    if value is None:
        # 未落库对象拿不到 Python 侧默认值，按列语义补齐
        if column.name == "create_time":
            return "NOW()"
        if column.name == "is_deleted":
            return "FALSE"
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, datetime):
        return f"'{value:%Y-%m-%d %H:%M:%S}'"
    if isinstance(value, uuid.UUID):
        value = str(value)
    if isinstance(value, (dict, list)):
        cast = "::jsonb" if isinstance(column.type, JSONB) else "::json"
        escaped = json.dumps(value, ensure_ascii=False).replace("'", "''")
        return f"'{escaped}'{cast}"
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def generate_inserts(objects) -> list[str]:
    grouped: dict[str, list] = {}
    for obj in objects:
        grouped.setdefault(obj.__tablename__, []).append(obj)

    statements = []
    for table_name, objs in grouped.items():
        table = Base.metadata.tables[table_name]
        columns = list(table.columns)
        column_names = ", ".join(f'"{c.name}"' for c in columns)
        statements.append(f"-- 表 {table_name}（{len(objs)} 条）")
        for obj in objs:
            values = ", ".join(render_value(c, getattr(obj, c.name, None)) for c in columns)
            statements.append(f'INSERT INTO "{table_name}" ({column_names}) VALUES ({values});')
        statements.append("")
    return statements


def main():
    objects = collect_seed_objects()
    ddl = generate_ddl()
    inserts = generate_inserts(objects)

    header = f"""-- ============================================================
-- 皮皮虾短剧 初始数据 SQL（表结构 + 种子数据）
-- 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}
-- 生成方式：python backend/scripts/gen_init_sql.py
--
-- 使用方法（PostgreSQL >= 15）：
--   1. 创建数据库：CREATE DATABASE "pipixia-drama";
--   2. 导入本文件：psql -U postgres -d "pipixia-drama" -f sql/init.sql
--      （或使用 pgAdmin / DBeaver 等工具执行本文件）
--
-- 与脚本初始化等价：也可以建库后执行
--   cd backend && python scripts/init_db.py（自动建表并写入相同种子数据）
--
-- 默认账号：test / 123456（生产环境请务必修改密码）
-- ============================================================
"""

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as fp:
        fp.write(header + "\n")
        fp.write("-- ==================== 表结构 ====================\n")
        fp.write("BEGIN;\n\n")
        fp.write("\n".join(ddl) + "\n\n")
        fp.write("-- ==================== 种子数据 ====================\n\n")
        fp.write("\n".join(inserts))
        fp.write("COMMIT;\n")

    total = len(objects)
    print(f"已生成 {OUTPUT_PATH}")
    print(f"表结构语句：{len(ddl)} 条，种子数据对象：{len(objects)} 个")


if __name__ == "__main__":
    main()
