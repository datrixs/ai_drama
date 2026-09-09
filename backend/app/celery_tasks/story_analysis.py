"""
故事分析 Celery 任务
包含：首次分析 Workflow（单次 LLM 调用）、增量调整 Workflow

当前版本：合并为单次 LLM 调用（comprehensive_analysis_gen）
旧版本子任务函数在文件底部注释保留
"""
import json
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.core.celery import celery
from app.core.logging import logger
from app.core.model_provider import ModelCaller
from app.core.project_logger import get_project_logger
from app.core.prompts.story_analysis import (
    COMPREHENSIVE_ANALYSIS_SYSTEM,
    COMPREHENSIVE_ANALYSIS_USER,
    INCREMENTAL_ADJUSTMENT_PROMPT,
)
from app.core.ws import ws_manager
from app.crud.project_crud import project as project_crud
from app.crud.project_analyze_crud import analysis_result as ar_crud
from app.crud.project_analyze_crud import analysis_version as av_crud
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.project_analyze import AnalysisResult, AnalysisVersion
from app.services.point import InsufficientBalanceError

# 不可重试的确定性错误：重试结果不变，应直接终止任务
# 例如：积分余额不足、项目/版本不存在等业务或参数类错误
_NON_RETRYABLE_ERRORS = (InsufficientBalanceError, ValueError, KeyError)


# ============ 辅助函数 ============

def _get_project(db: Session, project_id: str) -> Project:
    proj = project_crud.get(id=project_id, db=db)
    if not proj:
        raise ValueError(f"项目 {project_id} 不存在")
    return proj


def _get_version(db: Session, version_id: str) -> AnalysisVersion:
    version = db.get(AnalysisVersion, version_id)
    if not version:
        raise ValueError(f"版本 {version_id} 不存在")
    return version


def _update_project_status(db: Session, project_id: str, status: str):
    proj = _get_project(db, project_id)
    proj.status = status
    db.add(proj)
    db.commit()


def _update_analysis_status(db: Session, project_id: str, status: str):
    result = ar_crud.get_by_project(db, project_id)
    if result:
        result.status = status
        db.add(result)
        db.commit()


def _notify_progress(project_id: str, user_id: str, step: str, progress: int):
    ws_manager.publish_project_event(
        user_id=user_id,
        project_id=project_id,
        event_type="analysis_progress",
        data={"step": step, "progress": progress},
    )


def _safe_parse_json(text: str) -> dict | list:
    """安全解析 JSON，处理 markdown 代码块包裹"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


def _build_initial_context(result: dict) -> dict:
    """构建首次分析的增量上下文快照"""
    gs = result.get("global_setting", {})
    return {
        "novel_summary": gs.get("novel_summary", ""),
        "world_setting": gs.get("world_setting", ""),
        "style_tone": gs.get("style_tone", ""),
        "character_relations": gs.get("character_relations", ""),
        "adjustment_history": [],
    }


# ============ 子任务：小说预处理 ============

@celery.task(bind=True, max_retries=2, default_retry_delay=15)
def novel_preprocess(self, project_id: str) -> dict:
    """小说预处理：分章、元信息"""
    db = SessionLocal()
    plog = get_project_logger(project_id)
    try:
        plog.task_log(self.request.id, "novel_preprocess", f"任务开始 project={project_id}")
        proj = _get_project(db, project_id)
        novel_text = proj.novel_text or ""

        # file_url 存在且 novel_text 较短（被截断为预览），从COS下载原始文件
        if proj.file_url and len(novel_text) <= 5000:
            from app.utils.tencent_cos_utils import cos_client
            file_key = cos_client.url_to_key(proj.file_url)
            if file_key:
                plog.task_log(self.request.id, "novel_preprocess", f"从COS下载原始文件 key={file_key}")
                raw_bytes = cos_client.download_object_as_bytes(file_key)
                if not raw_bytes:
                    raise ValueError(f"从COS下载原始文件失败: {file_key}")
                # 根据扩展名解析文本
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

        chapter_pattern = r'第[一二三四五六七八九十百千万零\d]+[章节回]'
        chapters = re.split(f'(?={chapter_pattern})', novel_text)
        chapters = [c.strip() for c in chapters if c.strip()]

        if len(chapters) <= 1 and len(novel_text) > 5000:
            chunk_size = 5000
            chapters = [novel_text[i:i+chunk_size] for i in range(0, len(novel_text), chunk_size)]

        novel_meta = {
            "char_count": len(novel_text),
            "chapter_count": len(chapters),
            "format": "txt",
            "file_name": "",
        }

        proj.novel_meta = novel_meta
        db.add(proj)
        db.commit()

        plog.task_log(self.request.id, "novel_preprocess",
                      f"任务完成 char_count={novel_meta['char_count']} chapters={novel_meta['chapter_count']}")
        return {
            "novel_text": novel_text,
            "chapters": chapters,
            "novel_meta": novel_meta,
        }
    except Exception as exc:
        plog.task_log(self.request.id, "novel_preprocess", f"任务失败 error={exc}", )
        # 确定性错误（积分不足、参数错误等）重试无意义，直接抛出
        if isinstance(exc, _NON_RETRYABLE_ERRORS):
            raise
        raise self.retry(exc=exc)
    finally:
        db.close()


# ============ 子任务：合并分析（单次 LLM 调用） ============

@celery.task(bind=True, max_retries=3, default_retry_delay=30)
def comprehensive_analysis_gen(
    self,
    project_id: str,
    version_id: str,
    novel_text: str,
    novel_meta: dict,
    model_config: dict,
) -> dict:
    """合并分析：单次 LLM 调用完成全局提取 + 角色/场景/道具格式化 + 剧集大纲"""
    db = SessionLocal()
    plog = get_project_logger(project_id)
    raw_content = None
    try:
        plog.task_log(self.request.id, "comprehensive_analysis_gen",
                      f"任务开始 project={project_id} novel_len={novel_meta.get('char_count', 0)}")
        caller = ModelCaller.from_config_snapshot(model_config, db=db)
        user_prompt = COMPREHENSIVE_ANALYSIS_USER.format(novel_text=novel_text)

        plog.task_log(self.request.id, "comprehensive_analysis_gen", f"发送模型请求 prompt_len={len(user_prompt)}")

        result = caller.call(
            model_key="analysis_model", prompt=user_prompt,
            system_prompt=COMPREHENSIVE_ANALYSIS_SYSTEM,
            temperature=0.3, max_tokens=16384, timeout=1200,
            project_id=project_id, task_id=self.request.id,
        )
        raw_content = result.content
        parsed = _safe_parse_json(raw_content)

        # 记录 token 使用量
        version = _get_version(db, version_id)
        version.token_usage = {
            "comprehensive_analysis_gen": {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_tokens": result.total_tokens,
            }
        }
        db.add(version)
        db.commit()

        plog.task_log(self.request.id, "comprehensive_analysis_gen",
                      f"任务完成 input_tokens={result.input_tokens} output_tokens={result.output_tokens}")
        return parsed
    except Exception as exc:
        plog.task_log(self.request.id, "comprehensive_analysis_gen",
                      f"任务失败 error={exc} raw_output={(raw_content or 'N/A')[:2000]}")
        # 确定性错误（积分不足、参数错误等）重试无意义，直接抛出
        if isinstance(exc, _NON_RETRYABLE_ERRORS):
            raise
        raise self.retry(exc=exc)
    finally:
        db.close()


# ============ 首次分析 Workflow ============

@celery.task(bind=True, soft_time_limit=1200, max_retries=1)
def story_analysis_workflow(self, project_id: str, version_id: str, model_config: dict):
    """首次分析 Workflow - 预处理 + 单次 LLM 合并分析"""
    task_id = self.request.id
    db = SessionLocal()
    plog = get_project_logger(project_id)
    try:
        proj = _get_project(db, project_id)
        user_id = proj.user_id
        plog.task_log(task_id, "story_analysis_workflow", f"状态变更 draft → analyzingStory")

        # === Layer 0: 小说预处理 ===
        _notify_progress(project_id, user_id, "preprocess", 5)
        preprocess_result = novel_preprocess(project_id)
        novel_text = preprocess_result["novel_text"]
        novel_meta = preprocess_result["novel_meta"]

        # === Layer 1（合并）: 单次 LLM 调用 ===
        _notify_progress(project_id, user_id, "extraction", 15)
        analysis_result = comprehensive_analysis_gen(
            project_id=project_id,
            version_id=version_id,
            novel_text=novel_text,
            novel_meta=novel_meta,
            model_config=model_config,
        )

        # 构建增量上下文快照
        context_snapshot = _build_initial_context(analysis_result)

        _notify_progress(project_id, user_id, "storyboard", 90)

        # === 汇总写入数据库 ===
        version = _get_version(db, version_id)
        version.global_setting = analysis_result.get("global_setting", {})
        version.character_profiles = analysis_result.get("character_profiles", [])
        version.scene_descriptions = analysis_result.get("scene_descriptions", [])
        version.prop_descriptions = analysis_result.get("prop_descriptions", [])
        version.episode_outlines = analysis_result.get("episode_outlines", [])
        version.adjustment_context = context_snapshot
        db.add(version)

        # 更新项目状态
        proj = _get_project(db, project_id)
        proj.status = "storyReady"
        db.add(proj)

        # 更新分析结果
        result = ar_crud.get_by_project(db, project_id)
        if result:
            result.status = "completed"
            result.current_version_id = version_id
            db.add(result)

        db.commit()

        # # 从 episode_outlines 自动创建 Episode 记录
        # if analysis_result.get("episode_outlines"):
        #     from app.crud.episode_crud import episode_crud
        #     episode_crud.sync_from_outlines(
        #         db, project_id, analysis_result["episode_outlines"], user_id=proj.user_id
        #     )
        #     db.commit()

        ws_manager.publish_project_event(
            user_id=user_id,
            project_id=project_id,
            event_type="analysis_completed",
            data={"version_id": version_id, "project_status": "storyReady"},
        )

        plog.task_log(task_id, "story_analysis_workflow", f"状态变更 analyzingStory → storyReady")

    except Exception as exc:
        plog.task_log(task_id, "story_analysis_workflow", f"任务失败 error={exc}")
        try:
            _update_project_status(db, project_id, "draft")
            _update_analysis_status(db, project_id, "failed")

            proj = _get_project(db, project_id)
            ws_manager.publish_project_event(
                user_id=proj.user_id,
                project_id=project_id,
                event_type="analysis_failed",
                data={"error_message": str(exc)},
            )
        except Exception as inner_exc:
            logger.error(f"失败处理异常: {inner_exc}")
        # 确定性错误（积分不足、参数错误等）重试无意义，直接抛出
        if isinstance(exc, _NON_RETRYABLE_ERRORS):
            raise
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


# ============ 增量调整 Workflow ============

@celery.task(bind=True, soft_time_limit=1200, max_retries=2)
def story_analysis_adjust(self, project_id: str, version_id: str, adjustment: str, model_config: dict):
    """增量调整 Workflow"""
    task_id = self.request.id
    db = SessionLocal()
    plog = get_project_logger(project_id)
    try:
        proj = _get_project(db, project_id)
        user_id = proj.user_id
        plog.task_log(task_id, "story_analysis_adjust", f"增量调整开始 version_id={version_id}")

        result = ar_crud.get_by_project(db, project_id)
        if not result:
            raise ValueError("分析结果不存在")

        current_version = av_crud.get_current_version(db, result.id)
        if not current_version:
            raise ValueError("当前版本不存在")

        context_snapshot = current_version.adjustment_context or {}
        adjustment_history = context_snapshot.get("adjustment_history", [])

        caller = ModelCaller.from_config_snapshot(model_config, db=db)
        prompt = INCREMENTAL_ADJUSTMENT_PROMPT.format(
            context_snapshot=json.dumps({
                "global_setting": current_version.global_setting,
                "character_profiles": current_version.character_profiles,
                "scene_descriptions": current_version.scene_descriptions,
                "prop_descriptions": current_version.prop_descriptions,
                "episode_outlines": current_version.episode_outlines,
            }, ensure_ascii=False, default=str),
            adjustment_history=json.dumps(adjustment_history, ensure_ascii=False),
            user_instruction=adjustment,
        )

        _notify_progress(project_id, user_id, "adjustment_start", 30)
        model_result = caller.call(
            model_key="analysis_model", prompt=prompt,
            temperature=0.5, max_tokens=16384, timeout=1200,
            project_id=project_id, task_id=self.request.id,
        )
        _notify_progress(project_id, user_id, "adjustment_done", 80)

        updated = _safe_parse_json(model_result.content)
        change_summary = updated.pop("change_summary", "")

        # 合并：逐字段判断，非空则使用新值，空则继承上一版本
        new_version = _get_version(db, version_id)

        if "global_setting" in updated and updated["global_setting"]:
            new_version.global_setting = updated["global_setting"]
        else:
            new_version.global_setting = current_version.global_setting

        if "character_profiles" in updated and updated["character_profiles"]:
            new_version.character_profiles = updated["character_profiles"]
        else:
            new_version.character_profiles = current_version.character_profiles

        if "scene_descriptions" in updated and updated["scene_descriptions"]:
            new_version.scene_descriptions = updated["scene_descriptions"]
        else:
            new_version.scene_descriptions = current_version.scene_descriptions

        if "prop_descriptions" in updated and updated["prop_descriptions"]:
            new_version.prop_descriptions = updated["prop_descriptions"]
        else:
            new_version.prop_descriptions = current_version.prop_descriptions

        if "episode_outlines" in updated and updated["episode_outlines"]:
            new_version.episode_outlines = updated["episode_outlines"]
        else:
            new_version.episode_outlines = current_version.episode_outlines

        # 更新调整历史和上下文快照
        context_snapshot["adjustment_history"] = adjustment_history + [
            {
                "turn": new_version.version_number - 1,
                "instruction": adjustment,
                "summary_of_changes": change_summary,
            }
        ]
        context_snapshot["current_character_profiles"] = new_version.character_profiles
        context_snapshot["current_scene_descriptions"] = new_version.scene_descriptions
        context_snapshot["current_prop_descriptions"] = new_version.prop_descriptions
        context_snapshot["current_episode_outlines"] = new_version.episode_outlines

        new_version.adjustment_context = context_snapshot
        db.add(new_version)

        proj = _get_project(db, project_id)
        proj.status = "projectCreated"
        db.add(proj)

        result.status = "completed"
        result.current_version_id = version_id
        db.add(result)

        db.commit()

        # # 更新 Episode 记录（大纲可能已调整）
        # if new_version.episode_outlines:
        #     from app.crud.episode_crud import episode_crud
        #     episode_crud.sync_from_outlines(
        #         db, project_id, new_version.episode_outlines, user_id
        #     )
        #     db.commit()

        ws_manager.publish_project_event(
            user_id=user_id,
            project_id=project_id,
            event_type="adjustment_completed",
            data={"version_id": version_id, "project_status": "projectCreated"},
        )

        plog.task_log(task_id, "story_analysis_adjust", f"增量调整完成 version_id={version_id}")

    except Exception as exc:
        plog.task_log(task_id, "story_analysis_adjust", f"任务失败 error={exc}")
        try:
            _update_project_status(db, project_id, "projectCreated")
            proj = _get_project(db, project_id)
            ws_manager.publish_project_event(
                user_id=proj.user_id,
                project_id=project_id,
                event_type="adjustment_failed",
                data={"error_message": str(exc)},
            )
        except Exception as inner_exc:
            logger.error(f"失败处理异常: {inner_exc}")
        # 确定性错误（积分不足、参数错误等）重试无意义，直接抛出
        if isinstance(exc, _NON_RETRYABLE_ERRORS):
            raise
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


# ============ 旧版子任务函数（注释保留，合并前的多 Layer 方案） ============
#
# @celery.task(bind=True, max_retries=3, default_retry_delay=30)
# def comprehensive_extraction(self, project_id: str, version_id: str, novel_text: str, novel_meta: dict, model_config: dict) -> dict:
#     """详尽提取：唯一接触完整小说的步骤"""
#     db = SessionLocal()
#     plog = get_project_logger(project_id)
#     try:
#         plog.task_log(self.request.id, "comprehensive_extraction",
#                       f"任务开始 project={project_id} novel_len={novel_meta.get('char_count', 0)}")
#         caller = ModelCaller.from_config_snapshot(model_config, db=db)
#         prompt = COMPREHENSIVE_EXTRACTION_PROMPT.format(novel_text=novel_text[:60000])
#         plog.task_log(self.request.id, "comprehensive_extraction", f"发送模型请求 prompt_len={len(prompt)}")
#         result = caller.call(
#             model_key="analysis_model", prompt=prompt,
#             temperature=0.3, max_tokens=8192, timeout=180,
#             project_id=project_id, task_id=self.request.id,
#         )
#         extraction = _safe_parse_json(result.content)
#         version = _get_version(db, version_id)
#         version.token_usage = {
#             "comprehensive_extraction": {
#                 "input_tokens": result.input_tokens,
#                 "output_tokens": result.output_tokens,
#                 "total_tokens": result.total_tokens,
#             }
#         }
#         db.add(version)
#         db.commit()
#         plog.task_log(self.request.id, "comprehensive_extraction",
#                       f"任务完成 input_tokens={result.input_tokens} output_tokens={result.output_tokens}")
#         return extraction
#     except Exception as exc:
#         plog.task_log(self.request.id, "comprehensive_extraction", f"任务失败 error={exc}")
#         raise self.retry(exc=exc)
#     finally:
#         db.close()
#
#
# @celery.task(bind=True, max_retries=3, default_retry_delay=30)
# def character_gen(self, project_id: str, version_id: str, character_details: list | str, character_relations: str, model_config: dict) -> list:
#     """人物特征格式化润色"""
#     plog = get_project_logger(project_id)
#     db = SessionLocal()
#     raw_content = None
#     try:
#         plog.task_log(self.request.id, "character_gen", f"任务开始 project={project_id}")
#         caller = ModelCaller.from_config_snapshot(model_config, db=db)
#         details_str = json.dumps(character_details, ensure_ascii=False) if isinstance(character_details, list) else character_details
#         prompt = CHARACTER_GEN_PROMPT.format(character_details=details_str, character_relations=character_relations)
#         result = caller.call(
#             model_key="analysis_model", prompt=prompt,
#             temperature=0.5, max_tokens=4096, timeout=90,
#             project_id=project_id, task_id=self.request.id,
#         )
#         raw_content = result.content
#         parsed = _safe_parse_json(raw_content)
#         if not isinstance(parsed, list):
#             parsed = [parsed] if isinstance(parsed, dict) else []
#         plog.task_log(self.request.id, "character_gen", f"任务完成 characters={len(parsed)}")
#         return parsed
#     except Exception as exc:
#         plog.task_log(self.request.id, "character_gen", f"任务失败 error={exc} raw_output={(raw_content or 'N/A')[:2000]}")
#         raise self.retry(exc=exc)
#     finally:
#         db.close()
#
#
# @celery.task(bind=True, max_retries=3, default_retry_delay=30)
# def scene_gen(self, project_id: str, version_id: str, scene_details: list | str, model_config: dict) -> list:
#     """场景描写格式化润色"""
#     plog = get_project_logger(project_id)
#     db = SessionLocal()
#     raw_content = None
#     try:
#         plog.task_log(self.request.id, "scene_gen", f"任务开始 project={project_id}")
#         caller = ModelCaller.from_config_snapshot(model_config, db=db)
#         details_str = json.dumps(scene_details, ensure_ascii=False) if isinstance(scene_details, list) else scene_details
#         prompt = SCENE_GEN_PROMPT.format(scene_details=details_str)
#         result = caller.call(
#             model_key="analysis_model", prompt=prompt,
#             temperature=0.5, max_tokens=4096, timeout=90,
#             project_id=project_id, task_id=self.request.id,
#         )
#         raw_content = result.content
#         parsed = _safe_parse_json(raw_content)
#         if not isinstance(parsed, list):
#             parsed = [parsed] if isinstance(parsed, dict) else []
#         plog.task_log(self.request.id, "scene_gen", f"任务完成 scenes={len(parsed)}")
#         return parsed
#     except Exception as exc:
#         plog.task_log(self.request.id, "scene_gen", f"任务失败 error={exc} raw_output={(raw_content or 'N/A')[:2000]}")
#         raise self.retry(exc=exc)
#     finally:
#         db.close()
#
#
# @celery.task(bind=True, max_retries=3, default_retry_delay=30)
# def prop_gen(self, project_id: str, version_id: str, prop_details: list | str, model_config: dict) -> list:
#     """道具描写格式化润色"""
#     plog = get_project_logger(project_id)
#     db = SessionLocal()
#     raw_content = None
#     try:
#         plog.task_log(self.request.id, "prop_gen", f"任务开始 project={project_id}")
#         caller = ModelCaller.from_config_snapshot(model_config, db=db)
#         details_str = json.dumps(prop_details, ensure_ascii=False) if isinstance(prop_details, list) else prop_details
#         prompt = PROP_GEN_PROMPT.format(prop_details=details_str)
#         result = caller.call(
#             model_key="analysis_model", prompt=prompt,
#             temperature=0.5, max_tokens=4096, timeout=90,
#             project_id=project_id, task_id=self.request.id,
#         )
#         raw_content = result.content
#         parsed = _safe_parse_json(raw_content)
#         if not isinstance(parsed, list):
#             parsed = [parsed] if isinstance(parsed, dict) else []
#         plog.task_log(self.request.id, "prop_gen", f"任务完成 props={len(parsed)}")
#         return parsed
#     except Exception as exc:
#         plog.task_log(self.request.id, "prop_gen", f"任务失败 error={exc} raw_output={(raw_content or 'N/A')[:2000]}")
#         raise self.retry(exc=exc)
#     finally:
#         db.close()
#
#
# @celery.task(bind=True, max_retries=3, default_retry_delay=30)
# def episode_outline_gen(self, project_id: str, version_id: str, extraction: dict, chapters: list, model_config: dict) -> dict:
#     """生成每集大纲"""
#     plog = get_project_logger(project_id)
#     db = SessionLocal()
#     try:
#         plog.task_log(self.request.id, "episode_outline_gen", f"任务开始 project={project_id}")
#         caller = ModelCaller.from_config_snapshot(model_config, db=db)
#         prompt = EPISODE_OUTLINE_PROMPT.format(
#             novel_summary=extraction.get("novel_summary", ""),
#             world_setting=extraction.get("world_setting", ""),
#             character_relations=extraction.get("character_relations", ""),
#             chapter_summaries=json.dumps(extraction.get("chapter_summaries", []), ensure_ascii=False),
#             episode_mapping=json.dumps(extraction.get("episode_mapping", []), ensure_ascii=False),
#         )
#         result = caller.call(
#             model_key="analysis_model", prompt=prompt,
#             temperature=0.5, max_tokens=4096, timeout=120,
#             project_id=project_id, task_id=self.request.id,
#         )
#         outlines = _safe_parse_json(result.content)
#         plog.task_log(self.request.id, "episode_outline_gen", f"任务完成 episodes={len(outlines) if isinstance(outlines, list) else 1}")
#         return {"outlines": outlines if isinstance(outlines, list) else [outlines]}
#     except Exception as exc:
#         plog.task_log(self.request.id, "episode_outline_gen", f"任务失败 error={exc}")
#         raise self.retry(exc=exc)
#     finally:
#         db.close()
#
#
# @celery.task(bind=True, max_retries=3, default_retry_delay=30)
# def first_ep_storyboard_gen(
#     self,
#     project_id: str,
#     version_id: str,
#     extraction: dict,
#     first_outline: dict,
#     character_profiles: str,
#     scene_descriptions: str,
#     model_config: dict,
# ) -> dict:
#     """生成第一集分镜"""
#     plog = get_project_logger(project_id)
#     db = SessionLocal()
#     try:
#         plog.task_log(self.request.id, "first_ep_storyboard_gen", f"任务开始 project={project_id}")
#         caller = ModelCaller.from_config_snapshot(model_config, db=db)
#         prompt = FIRST_EP_STORYBOARD_PROMPT.format(
#             novel_summary=extraction.get("novel_summary", ""),
#             first_episode_outline=json.dumps(first_outline, ensure_ascii=False),
#             character_profiles=character_profiles,
#             scene_descriptions=scene_descriptions,
#             character_details_raw=json.dumps(extraction.get("character_details", []), ensure_ascii=False),
#         )
#         result = caller.call(
#             model_key="analysis_model", prompt=prompt,
#             temperature=0.5, max_tokens=8192, timeout=120,
#             project_id=project_id, task_id=self.request.id,
#         )
#         storyboard = _safe_parse_json(result.content)
#         plog.task_log(self.request.id, "first_ep_storyboard_gen", "任务完成")
#         return storyboard
#     except Exception as exc:
#         plog.task_log(self.request.id, "first_ep_storyboard_gen", f"任务失败 error={exc}")
#         raise self.retry(exc=exc)
#     finally:
#         db.close()
