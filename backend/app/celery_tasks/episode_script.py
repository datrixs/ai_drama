"""分集剧本生成 Celery 任务 — 每个任务处理一批（最多3集）"""
import json
import re

from loguru import logger
from sqlalchemy.orm import Session

from app.core.celery import celery
from app.core.model_provider import ModelCaller
from app.core.project_logger import get_project_logger
from app.core.prompts.episode_script import EPISODE_SCRIPT_SYSTEM, EPISODE_SCRIPT_USER
from app.core.ws import ws_manager
from app.crud.episode_crud import episode_crud
from app.db.session import SessionLocal
from app.enums.base import WSEventType
from app.models.project import Project
from app.models.project_analyze import AnalysisResult, AnalysisVersion


def _safe_parse_json(text: str) -> dict | list:
    """安全解析 JSON，处理 markdown 代码块包裹"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


def _build_context(db: Session, project_id: str) -> dict:
    """构建剧本生成所需的上下文"""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise ValueError(f"项目不存在: {project_id}")

    novel_text = proj.novel_text or ""

    # novel_text 较短时（被截断为预览），从 COS 下载原始文件
    if proj.file_url and len(novel_text) <= 5000:
        from app.utils.tencent_cos_utils import cos_client
        file_key = cos_client.url_to_key(proj.file_url)
        if file_key:
            logger.info(f"从COS下载原始小说文件 key={file_key}")
            raw_bytes = cos_client.download_object_as_bytes(file_key)
            if raw_bytes:
                ext = file_key.rsplit(".", 1)[-1].lower() if "." in file_key else "txt"
                if ext == "docx":
                    from docx import Document
                    import io as _io
                    try:
                        doc = Document(_io.BytesIO(raw_bytes))
                        novel_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                    except Exception:
                        # 后缀与实际内容不符时按文本兜底解码
                        try:
                            novel_text = raw_bytes.decode("utf-8")
                        except UnicodeDecodeError:
                            novel_text = raw_bytes.decode("gbk")
                else:
                    try:
                        novel_text = raw_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        novel_text = raw_bytes.decode("gbk")
                logger.info(f"从COS下载完成，文本长度: {len(novel_text)}")
            else:
                logger.warning(f"从COS下载原始文件失败: {file_key}")

    if len(novel_text) > 30000:
        logger.warning(
            f"小说文本较长 ({len(novel_text)} 字符)，可能超出模型 token 限制，"
            f"project_id={project_id}"
        )

    ar = db.query(AnalysisResult).filter(
        AnalysisResult.project_id == project_id
    ).first()
    version = None
    if ar and ar.current_version_id:
        version = db.query(AnalysisVersion).filter(
            AnalysisVersion.id == ar.current_version_id
        ).first()

    return {
        "novel_text": novel_text,
        "character_profiles": json.dumps(
            version.character_profiles if version else [],
            ensure_ascii=False, indent=2
        ),
        "scene_descriptions": json.dumps(
            version.scene_descriptions if version else [],
            ensure_ascii=False, indent=2
        ),
        "prop_descriptions": json.dumps(
            version.prop_descriptions if version else [],
            ensure_ascii=False, indent=2
        ),
    }


def _notify(user_id: str, project_id: str, data: dict):
    ws_manager.publish_project_event(user_id, project_id, WSEventType.EPISODE_SCRIPT_PROGRESS, data)


@celery.task(bind=True, max_retries=2, soft_time_limit=1200)
def generate_episode_script_batch_task(
    self,
    project_id: str,
    user_id: str,
    batch_items: list[dict],
    batch_total: int,
    batch_index: int,
    model_config: dict,
):
    """
    单批剧本生成任务（最多 3 集）

    Args:
        project_id: 项目ID
        user_id: 用户ID
        batch_items: [{"episode_id": ..., "episode_number": ...}, ...]
        batch_total: 总集数（用于 WS 通知）
        batch_index: 当前批次序号（从 1 开始）
        model_config: 序列化的模型配置快照
    """
    db = SessionLocal()
    plog = get_project_logger(project_id)
    try:
        ep_numbers = [it["episode_number"] for it in batch_items]
        plog.task_log(self.request.id, "episode_script",
                      f"开始分集剧本生成，批次 {batch_index} ，集号: {ep_numbers}")

        context = _build_context(db, project_id)

        # 加载本批次的 Episode 对象
        episodes = []
        for item in batch_items:
            ep = episode_crud.get(id=item["episode_id"], db=db)
            if ep:
                episodes.append(ep)

        if not episodes:
            plog.task_log(self.request.id, "episode_script",
                          f"批次 {batch_index} 无有效剧集，跳过")
            return

        # 通知生成中
        for ep in episodes:
            _notify(user_id, project_id, {
                "episode_number": ep.episode_number,
                "status": "generating",
                "batch_total": batch_total,
                "batch_index": batch_index,
            })

        # 构建大纲文本
        outlines_text = "\n\n".join(
            f"第{ep.episode_number}集：{ep.title}\n大纲：{ep.outline}"
            for ep in episodes
        )

        user_prompt = EPISODE_SCRIPT_USER.format(
            novel_text=context["novel_text"],
            character_profiles=context["character_profiles"],
            scene_descriptions=context["scene_descriptions"],
            prop_descriptions=context["prop_descriptions"],
            episode_outlines=outlines_text,
        )

        plog.task_log(self.request.id, "episode_script",
                      f"批次 {batch_index} 发送模型请求，prompt 长度: {len(user_prompt)}")

        caller = ModelCaller.from_config_snapshot(model_config, db=db)
        result = caller.call(
            model_key="analysis_model",
            prompt=user_prompt,
            system_prompt=EPISODE_SCRIPT_SYSTEM,
            temperature=0.3,
            max_tokens=16384,
            timeout=1200,
            project_id=project_id,
        )

        parsed = _safe_parse_json(result.content)
        if not isinstance(parsed, list):
            parsed = [parsed]

        # 将生成结果写入数据库
        for item in parsed:
            ep_num = item.get("episode_number")
            script = item.get("script", "")
            if not ep_num or not script:
                continue

            ep = episode_crud.get_by_number(db, project_id, ep_num)
            if ep:
                ep.episode_script = script
                ep.episode_script_status = "completed"
                db.add(ep)

                _notify(user_id, project_id, {
                    "episode_number": ep_num,
                    "status": "completed",
                    "batch_total": batch_total,
                    "batch_index": batch_index,
                })

        db.commit()
        plog.task_log(self.request.id, "episode_script",
                      f"批次 {batch_index} 完成")

    except Exception as exc:
        plog.task_log(self.request.id, "episode_script",
                      f"批次 {batch_index} 失败: {exc}")
        db.rollback()
        # 标记本批所有集为 failed
        for item in batch_items:
            ep = episode_crud.get(id=item["episode_id"], db=db)
            if ep:
                ep.episode_script_status = "failed"
                db.add(ep)
                _notify(user_id, project_id, {
                    "episode_number": item["episode_number"],
                    "status": "failed",
                    "error": str(exc),
                })
        db.commit()
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
