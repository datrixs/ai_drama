-- ============================================================
-- 皮皮虾短剧 初始数据 SQL（表结构 + 种子数据）
-- 生成时间：2026-09-04 14:58:48
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

-- ==================== 表结构 ====================
BEGIN;

CREATE TABLE "user" (
	username VARCHAR(128) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	email VARCHAR(128), 
	status VARCHAR(64) NOT NULL, 
	parent_user_id VARCHAR(256), 
	sub_user_limit INTEGER, 
	type VARCHAR(64) NOT NULL, 
	remark VARCHAR(128), 
	region VARCHAR(16), 
	username_cn VARCHAR(128), 
	contact_name VARCHAR(128), 
	last_login_time TIMESTAMP WITHOUT TIME ZONE, 
	phone VARCHAR(128), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email)
);
COMMENT ON COLUMN "user".username IS '用户名';
COMMENT ON COLUMN "user".password_hash IS '用户密码hash值';
COMMENT ON COLUMN "user".email IS '邮箱';
COMMENT ON COLUMN "user".status IS '账号状态';
COMMENT ON COLUMN "user".parent_user_id IS '主账号id。如果是主账号，则为None';
COMMENT ON COLUMN "user".sub_user_limit IS '子账号数量上限';
COMMENT ON COLUMN "user".type IS '账号类型';
COMMENT ON COLUMN "user".remark IS '账号备注';
COMMENT ON COLUMN "user".region IS '区域: domestic-国内/overseas-国际';
COMMENT ON COLUMN "user".username_cn IS '用户昵称';
COMMENT ON COLUMN "user".contact_name IS '联系人姓名';
COMMENT ON COLUMN "user".last_login_time IS '最后一次登录时间';
COMMENT ON COLUMN "user".phone IS '手机号';
COMMENT ON COLUMN "user".id IS '主键 UUID';
COMMENT ON COLUMN "user".create_time IS '创建时间';
COMMENT ON COLUMN "user".create_uid IS '创建人id';
COMMENT ON COLUMN "user".update_time IS '最近一次修改时间';
COMMENT ON COLUMN "user".update_uid IS '最近一次修改人id';
COMMENT ON COLUMN "user".is_deleted IS '是否删除';
COMMENT ON COLUMN "user".delete_time IS '删除时间';
CREATE TABLE user_balance (
	user_id VARCHAR(256), 
	balance NUMERIC(10, 2), 
	granted_balance NUMERIC(10, 2), 
	purchased_balance NUMERIC(10, 2), 
	frozen_amount NUMERIC(10, 2), 
	total_spent NUMERIC(10, 2), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN user_balance.user_id IS '用户ID';
COMMENT ON COLUMN user_balance.balance IS '余额（冗余总额=granted+purchased）';
COMMENT ON COLUMN user_balance.granted_balance IS '赠送积分余额（按规则清零）';
COMMENT ON COLUMN user_balance.purchased_balance IS '购买积分余额（永不清零）';
COMMENT ON COLUMN user_balance.frozen_amount IS '冻结金额';
COMMENT ON COLUMN user_balance.total_spent IS '总花费';
COMMENT ON COLUMN user_balance.id IS '主键 UUID';
COMMENT ON COLUMN user_balance.create_time IS '创建时间';
COMMENT ON COLUMN user_balance.create_uid IS '创建人id';
COMMENT ON COLUMN user_balance.update_time IS '最近一次修改时间';
COMMENT ON COLUMN user_balance.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN user_balance.is_deleted IS '是否删除';
COMMENT ON COLUMN user_balance.delete_time IS '删除时间';
CREATE TABLE ai_provider (
	name VARCHAR(128), 
	code VARCHAR(128), 
	base_url VARCHAR(256), 
	description VARCHAR(256), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);
COMMENT ON COLUMN ai_provider.name IS '模型供应商名称';
COMMENT ON COLUMN ai_provider.code IS '模型供应商编号';
COMMENT ON COLUMN ai_provider.base_url IS '大模型调用地址';
COMMENT ON COLUMN ai_provider.description IS '描述';
COMMENT ON COLUMN ai_provider.id IS '主键 UUID';
COMMENT ON COLUMN ai_provider.create_time IS '创建时间';
COMMENT ON COLUMN ai_provider.create_uid IS '创建人id';
COMMENT ON COLUMN ai_provider.update_time IS '最近一次修改时间';
COMMENT ON COLUMN ai_provider.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN ai_provider.is_deleted IS '是否删除';
COMMENT ON COLUMN ai_provider.delete_time IS '删除时间';
CREATE TABLE ai_model (
	provider_id VARCHAR(256), 
	name VARCHAR(256), 
	model_name VARCHAR(256), 
	model_type VARCHAR(256), 
	base_url VARCHAR(256), 
	billing_type VARCHAR(128), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN ai_model.provider_id IS '模型供应商ID';
COMMENT ON COLUMN ai_model.name IS '模型名称（对外展示）';
COMMENT ON COLUMN ai_model.model_name IS '模型名称（实际调用）';
COMMENT ON COLUMN ai_model.model_type IS '大模型类型
    text: 文本模型
    image: 图片模型
    video: 视频模型
    audio: 音频模型';
COMMENT ON COLUMN ai_model.base_url IS '大模型调用地址，若为空使用AIProvider的base_url';
COMMENT ON COLUMN ai_model.billing_type IS '计费方式，token: 按token计费，times：按次计费';
COMMENT ON COLUMN ai_model.id IS '主键 UUID';
COMMENT ON COLUMN ai_model.create_time IS '创建时间';
COMMENT ON COLUMN ai_model.create_uid IS '创建人id';
COMMENT ON COLUMN ai_model.update_time IS '最近一次修改时间';
COMMENT ON COLUMN ai_model.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN ai_model.is_deleted IS '是否删除';
COMMENT ON COLUMN ai_model.delete_time IS '删除时间';
CREATE TABLE ai_model_point (
	model_id VARCHAR(256), 
	input_point NUMERIC(10, 2), 
	output_point NUMERIC(10, 2), 
	is_character BOOLEAN, 
	image_point NUMERIC(10, 2), 
	input_text_point NUMERIC(10, 2), 
	input_image_point NUMERIC(10, 2), 
	output_total_point NUMERIC(10, 2), 
	has_reference BOOLEAN, 
	video_resolution VARCHAR(128), 
	video_point NUMERIC(10, 2), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN ai_model_point.model_id IS 'AIModel表ID';
COMMENT ON COLUMN ai_model_point.input_point IS '输入积分消耗（每百万token），文本类模型计费';
COMMENT ON COLUMN ai_model_point.output_point IS '输出积分消耗（每百万token），文本类模型计费';
COMMENT ON COLUMN ai_model_point.is_character IS '是否是生成角色图';
COMMENT ON COLUMN ai_model_point.image_point IS '图片积分消耗（每张图片），图片类模型计费';
COMMENT ON COLUMN ai_model_point.input_text_point IS '生成图片输入文字消耗的积分';
COMMENT ON COLUMN ai_model_point.input_image_point IS '生成图片输入图片消耗的积分';
COMMENT ON COLUMN ai_model_point.output_total_point IS '生成图片输出消耗的总积分';
COMMENT ON COLUMN ai_model_point.has_reference IS '是否有全能参考（有无参考素材）';
COMMENT ON COLUMN ai_model_point.video_resolution IS '视频分辨率';
COMMENT ON COLUMN ai_model_point.video_point IS '视频每秒消耗的积分，视频类模型计费';
COMMENT ON COLUMN ai_model_point.id IS '主键 UUID';
COMMENT ON COLUMN ai_model_point.create_time IS '创建时间';
COMMENT ON COLUMN ai_model_point.create_uid IS '创建人id';
COMMENT ON COLUMN ai_model_point.update_time IS '最近一次修改时间';
COMMENT ON COLUMN ai_model_point.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN ai_model_point.is_deleted IS '是否删除';
COMMENT ON COLUMN ai_model_point.delete_time IS '删除时间';
CREATE TABLE ai_model_reference_point (
	model_id VARCHAR(256), 
	video_resolution VARCHAR(128), 
	video_output_duration INTEGER, 
	reference_min_duration INTEGER, 
	video_point NUMERIC(10, 2), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN ai_model_reference_point.model_id IS 'AIModel表ID';
COMMENT ON COLUMN ai_model_reference_point.video_resolution IS '视频分辨率';
COMMENT ON COLUMN ai_model_reference_point.video_output_duration IS '视频输出时长（秒）';
COMMENT ON COLUMN ai_model_reference_point.reference_min_duration IS '素材输入总时长低于此值时按最低消耗计';
COMMENT ON COLUMN ai_model_reference_point.video_point IS '视频消耗的最低积分（整个视频）';
COMMENT ON COLUMN ai_model_reference_point.id IS '主键 UUID';
COMMENT ON COLUMN ai_model_reference_point.create_time IS '创建时间';
COMMENT ON COLUMN ai_model_reference_point.create_uid IS '创建人id';
COMMENT ON COLUMN ai_model_reference_point.update_time IS '最近一次修改时间';
COMMENT ON COLUMN ai_model_reference_point.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN ai_model_reference_point.is_deleted IS '是否删除';
COMMENT ON COLUMN ai_model_reference_point.delete_time IS '删除时间';
CREATE TABLE super_res_point (
	target_video_resolution VARCHAR(128), 
	point NUMERIC(10, 2), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN super_res_point.target_video_resolution IS '视频超分目标分辨率视频超分，目标分辨率';
COMMENT ON COLUMN super_res_point.point IS '每秒消耗的积分数量';
COMMENT ON COLUMN super_res_point.id IS '主键 UUID';
COMMENT ON COLUMN super_res_point.create_time IS '创建时间';
COMMENT ON COLUMN super_res_point.create_uid IS '创建人id';
COMMENT ON COLUMN super_res_point.update_time IS '最近一次修改时间';
COMMENT ON COLUMN super_res_point.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN super_res_point.is_deleted IS '是否删除';
COMMENT ON COLUMN super_res_point.delete_time IS '删除时间';
CREATE TABLE ai_model_pricing (
	model_id VARCHAR(36), 
	rule_type VARCHAR(64) NOT NULL, 
	match_config JSON NOT NULL, 
	price_config JSON NOT NULL, 
	is_enabled BOOLEAN, 
	remark TEXT, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_ai_model_pricing_rule_type ON ai_model_pricing (rule_type);
CREATE INDEX ix_ai_model_pricing_model_id ON ai_model_pricing (model_id);
COMMENT ON COLUMN ai_model_pricing.model_id IS 'AIModel表ID；NULL表示全局配置（如超分）';
COMMENT ON COLUMN ai_model_pricing.rule_type IS '计费规则类型，对应策略类';
COMMENT ON COLUMN ai_model_pricing.match_config IS '匹配维度，用于运行时筛选档位（如分辨率、是否角色图）';
COMMENT ON COLUMN ai_model_pricing.price_config IS '价格参数，供策略类计算使用';
COMMENT ON COLUMN ai_model_pricing.is_enabled IS '是否启用';
COMMENT ON COLUMN ai_model_pricing.remark IS '备注';
COMMENT ON COLUMN ai_model_pricing.id IS '主键 UUID';
COMMENT ON COLUMN ai_model_pricing.create_time IS '创建时间';
COMMENT ON COLUMN ai_model_pricing.create_uid IS '创建人id';
COMMENT ON COLUMN ai_model_pricing.update_time IS '最近一次修改时间';
COMMENT ON COLUMN ai_model_pricing.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN ai_model_pricing.is_deleted IS '是否删除';
COMMENT ON COLUMN ai_model_pricing.delete_time IS '删除时间';
CREATE TABLE user_api_config (
	user_id VARCHAR(256), 
	analysis_model VARCHAR(128), 
	character_model VARCHAR(128), 
	location_model VARCHAR(128), 
	storyboard_model VARCHAR(128), 
	edit_model VARCHAR(128), 
	video_model VARCHAR(128), 
	audio_model VARCHAR(128), 
	analysis_concurrency INTEGER, 
	image_concurrency INTEGER, 
	video_concurrency INTEGER, 
	video_ratio VARCHAR(128), 
	video_resolution VARCHAR(128), 
	art_style VARCHAR(128), 
	tts_rate VARCHAR(128), 
	image_resolution VARCHAR(128), 
	capability_defaults VARCHAR(128), 
	ark_api_key VARCHAR(256), 
	jd_api_key VARCHAR(256), 
	custom_models JSON, 
	custom_providers JSON, 
	ark_video_watermark BOOLEAN, 
	volc_private_asset_group_id VARCHAR(256), 
	byteplus_private_asset_group_id VARCHAR(256), 
	endpoint VARCHAR(128), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN user_api_config.user_id IS '用户ID';
COMMENT ON COLUMN user_api_config.analysis_model IS '用户配置的分析模型。对应AIModel.model_name';
COMMENT ON COLUMN user_api_config.character_model IS '用户配置的角色图片模型';
COMMENT ON COLUMN user_api_config.location_model IS '用户配置的场景图片模型';
COMMENT ON COLUMN user_api_config.storyboard_model IS '用户配置的分镜图片模型';
COMMENT ON COLUMN user_api_config.edit_model IS '用户配置的修图模型';
COMMENT ON COLUMN user_api_config.video_model IS '用户配置的视频模型';
COMMENT ON COLUMN user_api_config.audio_model IS '用户配置的语音模型';
COMMENT ON COLUMN user_api_config.analysis_concurrency IS '分析流程并发上限';
COMMENT ON COLUMN user_api_config.image_concurrency IS '图像流程并发上限';
COMMENT ON COLUMN user_api_config.video_concurrency IS '视频流程并发上限';
COMMENT ON COLUMN user_api_config.video_ratio IS '屏幕比例';
COMMENT ON COLUMN user_api_config.video_resolution IS '视频分辨率';
COMMENT ON COLUMN user_api_config.art_style IS '艺术风格';
COMMENT ON COLUMN user_api_config.tts_rate IS '';
COMMENT ON COLUMN user_api_config.image_resolution IS '图像清晰度';
COMMENT ON COLUMN user_api_config.capability_defaults IS '';
COMMENT ON COLUMN user_api_config.ark_api_key IS '火山引擎（Seedream+Seedance）';
COMMENT ON COLUMN user_api_config.jd_api_key IS '京东API key';
COMMENT ON COLUMN user_api_config.custom_models IS '自定义模型列表 + 价格（JSON）';
COMMENT ON COLUMN user_api_config.custom_providers IS '自定义 OpenAI 兼容提供商列表（JSON，包含 API Key）';
COMMENT ON COLUMN user_api_config.ark_video_watermark IS '开启后所有 ARK 火山视频生成请求强制带水印';
COMMENT ON COLUMN user_api_config.volc_private_asset_group_id IS '资产中心全局图同步火山私域时的资产组 Id';
COMMENT ON COLUMN user_api_config.byteplus_private_asset_group_id IS '资产中心全局图同步 BytePlus 时的资产组 Id';
COMMENT ON COLUMN user_api_config.endpoint IS '端点';
COMMENT ON COLUMN user_api_config.id IS '主键 UUID';
COMMENT ON COLUMN user_api_config.create_time IS '创建时间';
COMMENT ON COLUMN user_api_config.create_uid IS '创建人id';
COMMENT ON COLUMN user_api_config.update_time IS '最近一次修改时间';
COMMENT ON COLUMN user_api_config.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN user_api_config.is_deleted IS '是否删除';
COMMENT ON COLUMN user_api_config.delete_time IS '删除时间';
CREATE TABLE sys_dict (
	dict_name VARCHAR(128) NOT NULL, 
	key VARCHAR(128) NOT NULL, 
	value VARCHAR(128) NOT NULL, 
	sort INTEGER, 
	remark VARCHAR(128), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN sys_dict.dict_name IS '数据字典名称';
COMMENT ON COLUMN sys_dict.key IS '键名';
COMMENT ON COLUMN sys_dict.value IS '键值';
COMMENT ON COLUMN sys_dict.sort IS '排序';
COMMENT ON COLUMN sys_dict.remark IS '备注';
COMMENT ON COLUMN sys_dict.id IS '主键 UUID';
COMMENT ON COLUMN sys_dict.create_time IS '创建时间';
COMMENT ON COLUMN sys_dict.create_uid IS '创建人id';
COMMENT ON COLUMN sys_dict.update_time IS '最近一次修改时间';
COMMENT ON COLUMN sys_dict.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN sys_dict.is_deleted IS '是否删除';
COMMENT ON COLUMN sys_dict.delete_time IS '删除时间';
CREATE TABLE project (
	user_id VARCHAR(36) NOT NULL, 
	title VARCHAR(256), 
	description TEXT, 
	novel_text TEXT, 
	novel_meta JSON, 
	file_url VARCHAR(1024), 
	status VARCHAR(32) NOT NULL, 
	phase VARCHAR(32), 
	config JSON, 
	last_access_time TIMESTAMP WITHOUT TIME ZONE, 
	volc_private_asset_group_id VARCHAR(256), 
	byteplus_private_asset_group_id VARCHAR(256), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_project_user_id ON project (user_id);
COMMENT ON COLUMN project.user_id IS '所属用户ID';
COMMENT ON COLUMN project.title IS '项目名称';
COMMENT ON COLUMN project.description IS '项目描述';
COMMENT ON COLUMN project.novel_text IS '小说纯文本';
COMMENT ON COLUMN project.novel_meta IS '小说元信息: {char_count, chapter_count, format, file_name}';
COMMENT ON COLUMN project.file_url IS '小说文件云存储路径';
COMMENT ON COLUMN project.status IS '项目状态: draft/analyzingStory/storyReady/projectCreated/assetsReady/producing/completed';
COMMENT ON COLUMN project.phase IS '当前阶段: text_analysis/image_generation/video_production';
COMMENT ON COLUMN project.config IS '项目配置: {ratio, style, video_resolution, image_resolution, 各模型配置}';
COMMENT ON COLUMN project.last_access_time IS '最近访问时间';
COMMENT ON COLUMN project.volc_private_asset_group_id IS '火山私域素材库资产组ID';
COMMENT ON COLUMN project.byteplus_private_asset_group_id IS 'BytePlus 资产库资产组ID';
COMMENT ON COLUMN project.id IS '主键 UUID';
COMMENT ON COLUMN project.create_time IS '创建时间';
COMMENT ON COLUMN project.create_uid IS '创建人id';
COMMENT ON COLUMN project.update_time IS '最近一次修改时间';
COMMENT ON COLUMN project.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN project.is_deleted IS '是否删除';
COMMENT ON COLUMN project.delete_time IS '删除时间';
CREATE TABLE episode (
	project_id VARCHAR(36) NOT NULL, 
	episode_number INTEGER NOT NULL, 
	title VARCHAR(256), 
	outline TEXT, 
	episode_script TEXT, 
	episode_script_status VARCHAR(32), 
	status VARCHAR(32) NOT NULL, 
	script_json JSON, 
	script_plain_text TEXT, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_episode_project_id ON episode (project_id);
COMMENT ON COLUMN episode.project_id IS '项目ID';
COMMENT ON COLUMN episode.episode_number IS '集号';
COMMENT ON COLUMN episode.title IS '本集标题';
COMMENT ON COLUMN episode.outline IS '本集大纲';
COMMENT ON COLUMN episode.episode_script IS '本集剧本';
COMMENT ON COLUMN episode.episode_script_status IS '剧本生成状态: pending/generating/completed/failed';
COMMENT ON COLUMN episode.status IS '状态: pending/generating/completed/failed';
COMMENT ON COLUMN episode.script_json IS '多模态脚本JSON';
COMMENT ON COLUMN episode.script_plain_text IS '可编辑的脚本纯文本镜像';
COMMENT ON COLUMN episode.id IS '主键 UUID';
COMMENT ON COLUMN episode.create_time IS '创建时间';
COMMENT ON COLUMN episode.create_uid IS '创建人id';
COMMENT ON COLUMN episode.update_time IS '最近一次修改时间';
COMMENT ON COLUMN episode.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN episode.is_deleted IS '是否删除';
COMMENT ON COLUMN episode.delete_time IS '删除时间';
CREATE TABLE storyboard (
	episode_id VARCHAR(36) NOT NULL, 
	segment_index INTEGER NOT NULL, 
	segment_intent TEXT, 
	scene_summary TEXT, 
	shots JSON, 
	style_and_keywords TEXT, 
	image_prompt TEXT, 
	image_url TEXT, 
	reference_images JSON, 
	video_prompt TEXT, 
	video_url TEXT, 
	cover_url TEXT, 
	duration FLOAT, 
	resolution VARCHAR(16), 
	first_frame_url TEXT, 
	last_frame_url TEXT, 
	ark_task_id VARCHAR(256), 
	api_response_data JSON, 
	status VARCHAR(32), 
	gen_error TEXT, 
	raw_text TEXT, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_storyboard_episode_id ON storyboard (episode_id);
COMMENT ON COLUMN storyboard.episode_id IS '剧集ID';
COMMENT ON COLUMN storyboard.segment_index IS '片段序号（从1开始）';
COMMENT ON COLUMN storyboard.segment_intent IS '片段意图描述';
COMMENT ON COLUMN storyboard.scene_summary IS '场景总述';
COMMENT ON COLUMN storyboard.shots IS '镜头列表: [{index, durationHintSec, timeOfDay, sceneAssetId, characterAssetIds, camera, dialogue, action, soundEffect}]';
COMMENT ON COLUMN storyboard.style_and_keywords IS '风格和关键词';
COMMENT ON COLUMN storyboard.image_prompt IS '片段图片生成提示词';
COMMENT ON COLUMN storyboard.image_url IS '片段参考图URL（COS地址）';
COMMENT ON COLUMN storyboard.reference_images IS '参考图列表: [{url, assetId, label}]';
COMMENT ON COLUMN storyboard.video_prompt IS '视频生成提示词';
COMMENT ON COLUMN storyboard.video_url IS '最终视频URL（COS地址）';
COMMENT ON COLUMN storyboard.cover_url IS '视频封面图URL（COS地址）';
COMMENT ON COLUMN storyboard.duration IS '视频时长（秒）';
COMMENT ON COLUMN storyboard.resolution IS '分辨率: 480p/720p/1080p';
COMMENT ON COLUMN storyboard.first_frame_url IS '首帧图片URL';
COMMENT ON COLUMN storyboard.last_frame_url IS '尾帧图片URL';
COMMENT ON COLUMN storyboard.ark_task_id IS '火山引擎视频生成任务ID';
COMMENT ON COLUMN storyboard.api_response_data IS '方舟回调原始数据（用于异步上传 COS 前的源地址 fallback）';
COMMENT ON COLUMN storyboard.status IS '状态: pending/image_generating/image_completed/video_generating/video_completed/failed';
COMMENT ON COLUMN storyboard.gen_error IS '生成错误信息';
COMMENT ON COLUMN storyboard.raw_text IS 'LLM生成的原始文本';
COMMENT ON COLUMN storyboard.id IS '主键 UUID';
COMMENT ON COLUMN storyboard.create_time IS '创建时间';
COMMENT ON COLUMN storyboard.create_uid IS '创建人id';
COMMENT ON COLUMN storyboard.update_time IS '最近一次修改时间';
COMMENT ON COLUMN storyboard.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN storyboard.is_deleted IS '是否删除';
COMMENT ON COLUMN storyboard.delete_time IS '删除时间';
CREATE TABLE episode_concat_record (
	user_id VARCHAR(36) NOT NULL, 
	episode_id VARCHAR(36) NOT NULL, 
	project_id VARCHAR(36) NOT NULL, 
	source_video_urls JSON, 
	segment_count INTEGER NOT NULL, 
	result_video_url VARCHAR(1024), 
	result_storage_key VARCHAR(512), 
	duration_sec FLOAT, 
	status VARCHAR(32) NOT NULL, 
	error_message TEXT, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_episode_concat_record_project_id ON episode_concat_record (project_id);
CREATE INDEX ix_episode_concat_record_episode_id ON episode_concat_record (episode_id);
CREATE INDEX ix_episode_concat_record_user_id ON episode_concat_record (user_id);
COMMENT ON COLUMN episode_concat_record.user_id IS '操作用户ID';
COMMENT ON COLUMN episode_concat_record.episode_id IS '剧集ID';
COMMENT ON COLUMN episode_concat_record.project_id IS '项目ID';
COMMENT ON COLUMN episode_concat_record.source_video_urls IS '合成时使用的源视频URL列表';
COMMENT ON COLUMN episode_concat_record.segment_count IS '源视频片段数量';
COMMENT ON COLUMN episode_concat_record.result_video_url IS '合成产物URL（COS永久）';
COMMENT ON COLUMN episode_concat_record.result_storage_key IS '合成产物COS key';
COMMENT ON COLUMN episode_concat_record.duration_sec IS '合成视频时长（秒）';
COMMENT ON COLUMN episode_concat_record.status IS '状态: pending/processing/completed/failed';
COMMENT ON COLUMN episode_concat_record.error_message IS '失败原因';
COMMENT ON COLUMN episode_concat_record.id IS '主键 UUID';
COMMENT ON COLUMN episode_concat_record.create_time IS '创建时间';
COMMENT ON COLUMN episode_concat_record.create_uid IS '创建人id';
COMMENT ON COLUMN episode_concat_record.update_time IS '最近一次修改时间';
COMMENT ON COLUMN episode_concat_record.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN episode_concat_record.is_deleted IS '是否删除';
COMMENT ON COLUMN episode_concat_record.delete_time IS '删除时间';
CREATE TABLE task_record (
	project_id VARCHAR(36) NOT NULL, 
	task_type VARCHAR(64) NOT NULL, 
	celery_task_id VARCHAR(256), 
	parent_task_id VARCHAR(36), 
	status VARCHAR(32) NOT NULL, 
	worker_id VARCHAR(256), 
	input_params JSON, 
	output_result JSON, 
	retry_count INTEGER NOT NULL, 
	max_retries INTEGER NOT NULL, 
	next_retry_at TIMESTAMP WITHOUT TIME ZONE, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	timeout_at TIMESTAMP WITHOUT TIME ZONE, 
	error_message TEXT, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_task_record_project_id ON task_record (project_id);
COMMENT ON COLUMN task_record.project_id IS '项目ID';
COMMENT ON COLUMN task_record.task_type IS '任务类型: novel_preprocess/comprehensive_extraction/character_gen/...';
COMMENT ON COLUMN task_record.celery_task_id IS 'Celery任务ID';
COMMENT ON COLUMN task_record.parent_task_id IS '父任务ID';
COMMENT ON COLUMN task_record.status IS '任务状态: pending/running/success/failed/timeout/cancelled';
COMMENT ON COLUMN task_record.worker_id IS '执行任务的Worker ID';
COMMENT ON COLUMN task_record.input_params IS '输入参数';
COMMENT ON COLUMN task_record.output_result IS '输出结果';
COMMENT ON COLUMN task_record.retry_count IS '已重试次数';
COMMENT ON COLUMN task_record.max_retries IS '最大重试次数';
COMMENT ON COLUMN task_record.next_retry_at IS '下次重试时间';
COMMENT ON COLUMN task_record.started_at IS '开始执行时间';
COMMENT ON COLUMN task_record.completed_at IS '完成时间';
COMMENT ON COLUMN task_record.timeout_at IS '超时时间';
COMMENT ON COLUMN task_record.error_message IS '错误信息';
COMMENT ON COLUMN task_record.id IS '主键 UUID';
COMMENT ON COLUMN task_record.create_time IS '创建时间';
COMMENT ON COLUMN task_record.create_uid IS '创建人id';
COMMENT ON COLUMN task_record.update_time IS '最近一次修改时间';
COMMENT ON COLUMN task_record.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN task_record.is_deleted IS '是否删除';
COMMENT ON COLUMN task_record.delete_time IS '删除时间';
CREATE TABLE operation_record (
	project_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	action VARCHAR(64) NOT NULL, 
	target_type VARCHAR(32), 
	target_id VARCHAR(36), 
	detail JSON, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_operation_record_project_id ON operation_record (project_id);
COMMENT ON COLUMN operation_record.project_id IS '项目ID';
COMMENT ON COLUMN operation_record.user_id IS '操作用户ID';
COMMENT ON COLUMN operation_record.action IS '操作类型: create_project/upload_novel/start_analysis/adjust/confirm/...';
COMMENT ON COLUMN operation_record.target_type IS '目标类型: project/analysis_version/asset/episode/...';
COMMENT ON COLUMN operation_record.target_id IS '目标ID';
COMMENT ON COLUMN operation_record.detail IS '操作详情';
COMMENT ON COLUMN operation_record.id IS '主键 UUID';
COMMENT ON COLUMN operation_record.create_time IS '创建时间';
COMMENT ON COLUMN operation_record.create_uid IS '创建人id';
COMMENT ON COLUMN operation_record.update_time IS '最近一次修改时间';
COMMENT ON COLUMN operation_record.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN operation_record.is_deleted IS '是否删除';
COMMENT ON COLUMN operation_record.delete_time IS '删除时间';
CREATE TABLE model_call_log (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	project_id VARCHAR(36), 
	task_id VARCHAR(36), 
	request_id VARCHAR(128) NOT NULL, 
	provider_request_id VARCHAR(256), 
	model_provider VARCHAR(64) NOT NULL, 
	model_name VARCHAR(128) NOT NULL, 
	endpoint VARCHAR(512) NOT NULL, 
	api_key_masked VARCHAR(64), 
	request_body JSON, 
	response_status INTEGER, 
	response_body JSON, 
	input_tokens INTEGER, 
	output_tokens INTEGER, 
	total_tokens INTEGER, 
	latency_ms INTEGER, 
	usage_details JSON, 
	media_type VARCHAR(32), 
	input_media JSON, 
	output_media JSON, 
	is_retry BOOLEAN NOT NULL, 
	retry_count INTEGER NOT NULL, 
	max_retries INTEGER NOT NULL, 
	error_message TEXT, 
	call_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	point NUMERIC(10, 2), 
	remaining_point NUMERIC(10, 2), 
	PRIMARY KEY (id, call_time)
);
COMMENT ON COLUMN model_call_log.user_id IS '调用用户';
COMMENT ON COLUMN model_call_log.project_id IS '关联项目';
COMMENT ON COLUMN model_call_log.task_id IS '关联任务';
COMMENT ON COLUMN model_call_log.request_id IS '唯一请求ID';
COMMENT ON COLUMN model_call_log.provider_request_id IS '模型厂商请求ID';
COMMENT ON COLUMN model_call_log.model_provider IS '供应商';
COMMENT ON COLUMN model_call_log.model_name IS '模型名';
COMMENT ON COLUMN model_call_log.endpoint IS 'API端点';
COMMENT ON COLUMN model_call_log.api_key_masked IS '脱敏API Key';
COMMENT ON COLUMN model_call_log.request_body IS '请求体';
COMMENT ON COLUMN model_call_log.response_status IS 'HTTP状态码';
COMMENT ON COLUMN model_call_log.response_body IS '响应体摘要';
COMMENT ON COLUMN model_call_log.input_tokens IS '输入token数';
COMMENT ON COLUMN model_call_log.output_tokens IS '输出token数';
COMMENT ON COLUMN model_call_log.total_tokens IS '总token数';
COMMENT ON COLUMN model_call_log.latency_ms IS '调用耗时(毫秒)';
COMMENT ON COLUMN model_call_log.usage_details IS '供应商特有usage字段';
COMMENT ON COLUMN model_call_log.media_type IS '调用类型: text_text/text_image/image_text/image_image/video';
COMMENT ON COLUMN model_call_log.input_media IS '输入媒体信息 [{type, url, width, height, size_bytes, duration}]';
COMMENT ON COLUMN model_call_log.output_media IS '输出媒体信息 [{type, url, width, height, size_bytes, duration}]';
COMMENT ON COLUMN model_call_log.error_message IS '错误信息';
COMMENT ON COLUMN model_call_log.call_time IS '模型实际调用时间';
COMMENT ON COLUMN model_call_log.create_time IS '记录入库时间';
COMMENT ON COLUMN model_call_log.point IS '消耗积分';
COMMENT ON COLUMN model_call_log.remaining_point IS '扣除后剩余积分';
CREATE TABLE short_video_task (
	user_id VARCHAR(36) NOT NULL, 
	generation_type VARCHAR(20) NOT NULL, 
	prompt_text TEXT, 
	ratio VARCHAR(10), 
	resolution VARCHAR(10), 
	duration INTEGER, 
	generate_audio BOOLEAN, 
	region VARCHAR(16), 
	api_request_params JSON, 
	api_response_data JSON, 
	api_task_id VARCHAR(100), 
	video_url VARCHAR(500), 
	thumbnail_url VARCHAR(500), 
	first_frame_url VARCHAR(500), 
	first_frame_volc_id VARCHAR(100), 
	first_frame_byteplus_id VARCHAR(100), 
	last_frame_url VARCHAR(500), 
	last_frame_volc_id VARCHAR(100), 
	last_frame_byteplus_id VARCHAR(100), 
	reference_media_json TEXT, 
	status VARCHAR(20) NOT NULL, 
	error_message TEXT, 
	progress INTEGER, 
	submitted_at TIMESTAMP WITHOUT TIME ZONE, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_short_video_task_user_id ON short_video_task (user_id);
COMMENT ON COLUMN short_video_task.user_id IS '用户ID';
COMMENT ON COLUMN short_video_task.generation_type IS '生成类型: reference(参考模式)/first_last_frame(首尾帧模式)';
COMMENT ON COLUMN short_video_task.prompt_text IS '用户输入的提示词';
COMMENT ON COLUMN short_video_task.ratio IS '视频比例: 16:9/9:16/1:1 等';
COMMENT ON COLUMN short_video_task.resolution IS '分辨率: 480p/720p';
COMMENT ON COLUMN short_video_task.duration IS '视频时长(秒)';
COMMENT ON COLUMN short_video_task.generate_audio IS '是否生成音频';
COMMENT ON COLUMN short_video_task.region IS '任务提交时的用户区域: domestic-国内/overseas-国际';
COMMENT ON COLUMN short_video_task.api_request_params IS '发送到API的完整请求参数';
COMMENT ON COLUMN short_video_task.api_response_data IS 'API返回的完整响应数据';
COMMENT ON COLUMN short_video_task.api_task_id IS '火山方舟任务ID';
COMMENT ON COLUMN short_video_task.video_url IS '生成的视频地址';
COMMENT ON COLUMN short_video_task.thumbnail_url IS '缩略图地址';
COMMENT ON COLUMN short_video_task.first_frame_url IS '首帧图片URL';
COMMENT ON COLUMN short_video_task.first_frame_volc_id IS '首帧图片火山资产ID';
COMMENT ON COLUMN short_video_task.first_frame_byteplus_id IS '首帧图片BytePlus资产ID';
COMMENT ON COLUMN short_video_task.last_frame_url IS '尾帧图片URL';
COMMENT ON COLUMN short_video_task.last_frame_volc_id IS '尾帧图片火山资产ID';
COMMENT ON COLUMN short_video_task.last_frame_byteplus_id IS '尾帧图片BytePlus资产ID';
COMMENT ON COLUMN short_video_task.reference_media_json IS '参考媒体JSON: {imageUrls:[], videoUrls:[], audioUrls:[]}';
COMMENT ON COLUMN short_video_task.status IS '状态: pending/submitted/queued/processing/succeeded/failed/cancelled';
COMMENT ON COLUMN short_video_task.error_message IS '错误信息';
COMMENT ON COLUMN short_video_task.progress IS '进度百分比 0-100';
COMMENT ON COLUMN short_video_task.submitted_at IS '提交时间';
COMMENT ON COLUMN short_video_task.started_at IS '开始处理时间';
COMMENT ON COLUMN short_video_task.completed_at IS '完成时间';
COMMENT ON COLUMN short_video_task.id IS '主键 UUID';
COMMENT ON COLUMN short_video_task.create_time IS '创建时间';
COMMENT ON COLUMN short_video_task.create_uid IS '创建人id';
COMMENT ON COLUMN short_video_task.update_time IS '最近一次修改时间';
COMMENT ON COLUMN short_video_task.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN short_video_task.is_deleted IS '是否删除';
COMMENT ON COLUMN short_video_task.delete_time IS '删除时间';
CREATE TABLE short_video_asset (
	user_id VARCHAR(36) NOT NULL, 
	project_id VARCHAR(36), 
	asset_name VARCHAR(200), 
	asset_type VARCHAR(20) NOT NULL, 
	asset_url VARCHAR(500), 
	asset_size BIGINT, 
	mime_type VARCHAR(100), 
	volc_asset_id VARCHAR(100), 
	byteplus_asset_id VARCHAR(100), 
	thumbnail_url VARCHAR(500), 
	duration INTEGER, 
	source VARCHAR(20), 
	source_asset_id VARCHAR(36), 
	metadata_json TEXT, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_short_video_asset_user_id ON short_video_asset (user_id);
CREATE INDEX ix_short_video_asset_project_id ON short_video_asset (project_id);
COMMENT ON COLUMN short_video_asset.user_id IS '用户ID';
COMMENT ON COLUMN short_video_asset.project_id IS '关联项目ID(项目资产库时有值)';
COMMENT ON COLUMN short_video_asset.asset_name IS '资源名称(原始上传文件名)';
COMMENT ON COLUMN short_video_asset.asset_type IS '资源类型: image/video/audio';
COMMENT ON COLUMN short_video_asset.asset_url IS '资源地址(COS URL)';
COMMENT ON COLUMN short_video_asset.asset_size IS '文件大小(字节)';
COMMENT ON COLUMN short_video_asset.mime_type IS 'MIME类型';
COMMENT ON COLUMN short_video_asset.volc_asset_id IS '火山引擎资产ID(同步后获得)';
COMMENT ON COLUMN short_video_asset.byteplus_asset_id IS 'BytePlus 资产ID(国际版同步后获得)';
COMMENT ON COLUMN short_video_asset.thumbnail_url IS '缩略图(视频/音频的封面图)';
COMMENT ON COLUMN short_video_asset.duration IS '视频/音频时长(秒)';
COMMENT ON COLUMN short_video_asset.source IS '来源: upload(本地上传)/project_asset(项目资产)/asset_center(资产中心)';
COMMENT ON COLUMN short_video_asset.source_asset_id IS '来源资产ID';
COMMENT ON COLUMN short_video_asset.metadata_json IS '扩展元数据JSON';
COMMENT ON COLUMN short_video_asset.id IS '主键 UUID';
COMMENT ON COLUMN short_video_asset.create_time IS '创建时间';
COMMENT ON COLUMN short_video_asset.create_uid IS '创建人id';
COMMENT ON COLUMN short_video_asset.update_time IS '最近一次修改时间';
COMMENT ON COLUMN short_video_asset.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN short_video_asset.is_deleted IS '是否删除';
COMMENT ON COLUMN short_video_asset.delete_time IS '删除时间';
CREATE TABLE video_super_res_task (
	user_id VARCHAR(36) NOT NULL, 
	is_local_upload BOOLEAN NOT NULL, 
	source_video_url VARCHAR(500) NOT NULL, 
	source_thumbnail_url VARCHAR(500), 
	source_video_name VARCHAR(200), 
	source_video_duration INTEGER, 
	params JSON, 
	request_payload JSON, 
	api_request_params JSON, 
	api_submit_response JSON, 
	api_response_data JSON, 
	api_task_id VARCHAR(100), 
	result_video_url VARCHAR(500), 
	result_thumbnail_url VARCHAR(500), 
	result_storage_key VARCHAR(512), 
	status VARCHAR(20) NOT NULL, 
	error_message TEXT, 
	progress INTEGER, 
	submitted_at TIMESTAMP WITHOUT TIME ZONE, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_video_super_res_task_user_id ON video_super_res_task (user_id);
COMMENT ON COLUMN video_super_res_task.user_id IS '用户ID';
COMMENT ON COLUMN video_super_res_task.is_local_upload IS '是否本地上传(True=COS资源,False=在线URL)';
COMMENT ON COLUMN video_super_res_task.source_video_url IS '源视频URL(COS永久地址或在线URL,取决于is_local_upload)';
COMMENT ON COLUMN video_super_res_task.source_thumbnail_url IS '源视频缩略图URL(COS永久)';
COMMENT ON COLUMN video_super_res_task.source_video_name IS '源视频文件名';
COMMENT ON COLUMN video_super_res_task.source_video_duration IS '源视频时长(秒)';
COMMENT ON COLUMN video_super_res_task.params IS '超分参数JSON(透传火山,字段集与火山API对齐)';
COMMENT ON COLUMN video_super_res_task.request_payload IS '前端创建任务时下发的完整请求体';
COMMENT ON COLUMN video_super_res_task.api_request_params IS '提交到火山API的完整请求参数';
COMMENT ON COLUMN video_super_res_task.api_submit_response IS '火山submit_task同步返回的完整响应';
COMMENT ON COLUMN video_super_res_task.api_response_data IS '火山回调时下发的完整数据';
COMMENT ON COLUMN video_super_res_task.api_task_id IS '火山返回的任务ID';
COMMENT ON COLUMN video_super_res_task.result_video_url IS '超分结果视频URL(COS永久)';
COMMENT ON COLUMN video_super_res_task.result_thumbnail_url IS '超分结果视频缩略图URL(COS永久)';
COMMENT ON COLUMN video_super_res_task.result_storage_key IS '超分结果视频COS存储key';
COMMENT ON COLUMN video_super_res_task.status IS '状态: pending/submitted/processing/succeeded/failed/cancelled';
COMMENT ON COLUMN video_super_res_task.error_message IS '错误信息';
COMMENT ON COLUMN video_super_res_task.progress IS '进度百分比 0-100';
COMMENT ON COLUMN video_super_res_task.submitted_at IS '提交到火山API的时间';
COMMENT ON COLUMN video_super_res_task.started_at IS '开始处理时间';
COMMENT ON COLUMN video_super_res_task.completed_at IS '完成时间';
COMMENT ON COLUMN video_super_res_task.id IS '主键 UUID';
COMMENT ON COLUMN video_super_res_task.create_time IS '创建时间';
COMMENT ON COLUMN video_super_res_task.create_uid IS '创建人id';
COMMENT ON COLUMN video_super_res_task.update_time IS '最近一次修改时间';
COMMENT ON COLUMN video_super_res_task.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN video_super_res_task.is_deleted IS '是否删除';
COMMENT ON COLUMN video_super_res_task.delete_time IS '删除时间';
CREATE TABLE conversation_record (
	project_id VARCHAR(36), 
	episode_id VARCHAR(36), 
	user_id VARCHAR(36) NOT NULL, 
	conversation_type VARCHAR(32) NOT NULL, 
	title VARCHAR(256), 
	messages JSON, 
	result_video_url VARCHAR(1024), 
	result_image_urls JSON, 
	result_data JSON, 
	metadata JSON, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_conversation_record_user_id ON conversation_record (user_id);
COMMENT ON COLUMN conversation_record.project_id IS '项目ID（可选）';
COMMENT ON COLUMN conversation_record.episode_id IS '剧集ID（可选）';
COMMENT ON COLUMN conversation_record.user_id IS '用户ID';
COMMENT ON COLUMN conversation_record.conversation_type IS '对话类型: storyboard_edit/video_generation/asset_design/general';
COMMENT ON COLUMN conversation_record.title IS '对话标题';
COMMENT ON COLUMN conversation_record.messages IS '消息列表: [{role: user/assistant/system, content, timestamp, attachments: [{type, url, name}]}]';
COMMENT ON COLUMN conversation_record.result_video_url IS '对话产生的结果视频URL';
COMMENT ON COLUMN conversation_record.result_image_urls IS '对话产生的结果图片URL列表';
COMMENT ON COLUMN conversation_record.result_data IS '其他结构化结果数据';
COMMENT ON COLUMN conversation_record.metadata IS '元数据: {model_used, token_usage, generation_params}';
COMMENT ON COLUMN conversation_record.id IS '主键 UUID';
COMMENT ON COLUMN conversation_record.create_time IS '创建时间';
COMMENT ON COLUMN conversation_record.create_uid IS '创建人id';
COMMENT ON COLUMN conversation_record.update_time IS '最近一次修改时间';
COMMENT ON COLUMN conversation_record.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN conversation_record.is_deleted IS '是否删除';
COMMENT ON COLUMN conversation_record.delete_time IS '删除时间';
CREATE TABLE sys_permission (
	code VARCHAR(128), 
	name VARCHAR(128), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN sys_permission.code IS '权限代码';
COMMENT ON COLUMN sys_permission.name IS '权限名称';
COMMENT ON COLUMN sys_permission.id IS '主键 UUID';
COMMENT ON COLUMN sys_permission.create_time IS '创建时间';
COMMENT ON COLUMN sys_permission.create_uid IS '创建人id';
COMMENT ON COLUMN sys_permission.update_time IS '最近一次修改时间';
COMMENT ON COLUMN sys_permission.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN sys_permission.is_deleted IS '是否删除';
COMMENT ON COLUMN sys_permission.delete_time IS '删除时间';
CREATE TABLE sys_user_permission (
	user_id VARCHAR(256), 
	permission_code VARCHAR(128), 
	scope_type VARCHAR(128), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN sys_user_permission.user_id IS '用户ID';
COMMENT ON COLUMN sys_user_permission.permission_code IS '权限代码';
COMMENT ON COLUMN sys_user_permission.scope_type IS '作用域类型。SELF:自己，ALL:全部';
COMMENT ON COLUMN sys_user_permission.id IS '主键 UUID';
COMMENT ON COLUMN sys_user_permission.create_time IS '创建时间';
COMMENT ON COLUMN sys_user_permission.create_uid IS '创建人id';
COMMENT ON COLUMN sys_user_permission.update_time IS '最近一次修改时间';
COMMENT ON COLUMN sys_user_permission.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN sys_user_permission.is_deleted IS '是否删除';
COMMENT ON COLUMN sys_user_permission.delete_time IS '删除时间';
CREATE TABLE sub_user_shared_folders (
	sub_user_id VARCHAR(256) NOT NULL, 
	folder_id VARCHAR(256) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_sub_user_shared_folders_sub_user_id ON sub_user_shared_folders (sub_user_id);
COMMENT ON COLUMN sub_user_shared_folders.sub_user_id IS '子账号用户ID';
COMMENT ON COLUMN sub_user_shared_folders.folder_id IS '共享的文件夹ID';
COMMENT ON COLUMN sub_user_shared_folders.id IS '主键 UUID';
COMMENT ON COLUMN sub_user_shared_folders.create_time IS '创建时间';
COMMENT ON COLUMN sub_user_shared_folders.create_uid IS '创建人id';
COMMENT ON COLUMN sub_user_shared_folders.update_time IS '最近一次修改时间';
COMMENT ON COLUMN sub_user_shared_folders.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN sub_user_shared_folders.is_deleted IS '是否删除';
COMMENT ON COLUMN sub_user_shared_folders.delete_time IS '删除时间';
CREATE TABLE global_asset_folders (
	user_id VARCHAR(256) NOT NULL, 
	owner_user_id VARCHAR(256), 
	name VARCHAR(256) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_global_asset_folders_owner_user_id ON global_asset_folders (owner_user_id);
CREATE INDEX ix_global_asset_folders_user_id ON global_asset_folders (user_id);
COMMENT ON COLUMN global_asset_folders.user_id IS '创建者ID';
COMMENT ON COLUMN global_asset_folders.owner_user_id IS '主账号ID（数据隔离）';
COMMENT ON COLUMN global_asset_folders.name IS '文件夹名称';
COMMENT ON COLUMN global_asset_folders.id IS '主键 UUID';
COMMENT ON COLUMN global_asset_folders.create_time IS '创建时间';
COMMENT ON COLUMN global_asset_folders.create_uid IS '创建人id';
COMMENT ON COLUMN global_asset_folders.update_time IS '最近一次修改时间';
COMMENT ON COLUMN global_asset_folders.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN global_asset_folders.is_deleted IS '是否删除';
COMMENT ON COLUMN global_asset_folders.delete_time IS '删除时间';
CREATE TABLE global_characters (
	user_id VARCHAR(256) NOT NULL, 
	owner_user_id VARCHAR(256), 
	folder_id VARCHAR(256), 
	name VARCHAR(256) NOT NULL, 
	aliases TEXT, 
	profile_data TEXT, 
	profile_confirmed BOOLEAN, 
	voice_id VARCHAR(256), 
	voice_type VARCHAR(256), 
	custom_voice_url TEXT, 
	custom_voice_media_id VARCHAR(256), 
	global_voice_id VARCHAR(256), 
	is_management_asset BOOLEAN, 
	visibility VARCHAR(32), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_global_characters_user_id ON global_characters (user_id);
CREATE INDEX ix_global_characters_owner_user_id ON global_characters (owner_user_id);
CREATE INDEX ix_global_characters_folder_id ON global_characters (folder_id);
COMMENT ON COLUMN global_characters.user_id IS '创建者ID';
COMMENT ON COLUMN global_characters.owner_user_id IS '主账号ID';
COMMENT ON COLUMN global_characters.folder_id IS '文件夹ID';
COMMENT ON COLUMN global_characters.name IS '角色名称';
COMMENT ON COLUMN global_characters.aliases IS '角色别名';
COMMENT ON COLUMN global_characters.profile_data IS '角色profile数据JSON';
COMMENT ON COLUMN global_characters.profile_confirmed IS '角色信息是否已确认';
COMMENT ON COLUMN global_characters.voice_id IS '语音ID';
COMMENT ON COLUMN global_characters.voice_type IS '语音类型';
COMMENT ON COLUMN global_characters.custom_voice_url IS '自定义语音URL';
COMMENT ON COLUMN global_characters.custom_voice_media_id IS '自定义语音媒体对象ID';
COMMENT ON COLUMN global_characters.global_voice_id IS '绑定的全局音色ID';
COMMENT ON COLUMN global_characters.is_management_asset IS '是否为平台资产';
COMMENT ON COLUMN global_characters.visibility IS '可见范围: public/partial/private';
COMMENT ON COLUMN global_characters.id IS '主键 UUID';
COMMENT ON COLUMN global_characters.create_time IS '创建时间';
COMMENT ON COLUMN global_characters.create_uid IS '创建人id';
COMMENT ON COLUMN global_characters.update_time IS '最近一次修改时间';
COMMENT ON COLUMN global_characters.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN global_characters.is_deleted IS '是否删除';
COMMENT ON COLUMN global_characters.delete_time IS '删除时间';
CREATE TABLE global_character_appearances (
	character_id VARCHAR(256) NOT NULL, 
	appearance_index INTEGER NOT NULL, 
	change_reason VARCHAR(256), 
	art_style VARCHAR(256), 
	image_model_system_prompt TEXT, 
	description TEXT, 
	descriptions TEXT, 
	image_url TEXT, 
	image_media_id VARCHAR(256), 
	image_urls TEXT, 
	selected_index INTEGER, 
	thumbnail_url TEXT, 
	thumbnail_urls TEXT, 
	previous_image_url TEXT, 
	previous_image_media_id VARCHAR(256), 
	previous_image_urls TEXT, 
	previous_description TEXT, 
	previous_descriptions TEXT, 
	volc_private_asset_id VARCHAR(256), 
	byteplus_asset_id VARCHAR(256), 
	gen_status VARCHAR(32) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_character_appearance_index UNIQUE (character_id, appearance_index)
);
CREATE INDEX ix_global_character_appearances_character_id ON global_character_appearances (character_id);
COMMENT ON COLUMN global_character_appearances.character_id IS '角色ID';
COMMENT ON COLUMN global_character_appearances.appearance_index IS '形象序号（0=主形象）';
COMMENT ON COLUMN global_character_appearances.change_reason IS '变更原因/标签';
COMMENT ON COLUMN global_character_appearances.art_style IS '艺术风格';
COMMENT ON COLUMN global_character_appearances.image_model_system_prompt IS '图生模型系统提示词';
COMMENT ON COLUMN global_character_appearances.description IS '形象描述';
COMMENT ON COLUMN global_character_appearances.descriptions IS '形象描述数组JSON';
COMMENT ON COLUMN global_character_appearances.image_url IS '当前图片URL';
COMMENT ON COLUMN global_character_appearances.image_media_id IS '图片媒体对象ID';
COMMENT ON COLUMN global_character_appearances.image_urls IS '候选图片URL列表JSON';
COMMENT ON COLUMN global_character_appearances.selected_index IS '当前选中的渲染图索引';
COMMENT ON COLUMN global_character_appearances.thumbnail_url IS '当前选中图的缩略图 COS key';
COMMENT ON COLUMN global_character_appearances.thumbnail_urls IS '候选缩略图 COS key 列表JSON（与 image_urls 一一对应）';
COMMENT ON COLUMN global_character_appearances.previous_image_url IS '上一次图片URL';
COMMENT ON COLUMN global_character_appearances.previous_image_media_id IS '上一次图片媒体对象ID';
COMMENT ON COLUMN global_character_appearances.previous_image_urls IS '上一次图片URL列表JSON';
COMMENT ON COLUMN global_character_appearances.previous_description IS '上一次描述词';
COMMENT ON COLUMN global_character_appearances.previous_descriptions IS '上一次描述词数组JSON';
COMMENT ON COLUMN global_character_appearances.volc_private_asset_id IS '火山私域素材ID';
COMMENT ON COLUMN global_character_appearances.byteplus_asset_id IS 'BytePlus 资产ID(国际版同步后获得)';
COMMENT ON COLUMN global_character_appearances.gen_status IS '生成状态: pending/generating/completed/failed';
COMMENT ON COLUMN global_character_appearances.id IS '主键 UUID';
COMMENT ON COLUMN global_character_appearances.create_time IS '创建时间';
COMMENT ON COLUMN global_character_appearances.create_uid IS '创建人id';
COMMENT ON COLUMN global_character_appearances.update_time IS '最近一次修改时间';
COMMENT ON COLUMN global_character_appearances.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN global_character_appearances.is_deleted IS '是否删除';
COMMENT ON COLUMN global_character_appearances.delete_time IS '删除时间';
CREATE TABLE global_locations (
	user_id VARCHAR(256) NOT NULL, 
	owner_user_id VARCHAR(256), 
	folder_id VARCHAR(256), 
	name VARCHAR(256) NOT NULL, 
	art_style VARCHAR(256), 
	summary TEXT, 
	asset_kind VARCHAR(256), 
	is_management_asset BOOLEAN, 
	visibility VARCHAR(32), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_global_locations_owner_user_id ON global_locations (owner_user_id);
CREATE INDEX ix_global_locations_user_id ON global_locations (user_id);
CREATE INDEX ix_global_locations_folder_id ON global_locations (folder_id);
COMMENT ON COLUMN global_locations.user_id IS '创建者ID';
COMMENT ON COLUMN global_locations.owner_user_id IS '主账号ID';
COMMENT ON COLUMN global_locations.folder_id IS '文件夹ID';
COMMENT ON COLUMN global_locations.name IS '场景/道具名称';
COMMENT ON COLUMN global_locations.art_style IS '艺术风格';
COMMENT ON COLUMN global_locations.summary IS '简要描述';
COMMENT ON COLUMN global_locations.asset_kind IS '资产类型：location/prop';
COMMENT ON COLUMN global_locations.is_management_asset IS '是否为平台资产';
COMMENT ON COLUMN global_locations.visibility IS '可见范围: public/partial/private';
COMMENT ON COLUMN global_locations.id IS '主键 UUID';
COMMENT ON COLUMN global_locations.create_time IS '创建时间';
COMMENT ON COLUMN global_locations.create_uid IS '创建人id';
COMMENT ON COLUMN global_locations.update_time IS '最近一次修改时间';
COMMENT ON COLUMN global_locations.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN global_locations.is_deleted IS '是否删除';
COMMENT ON COLUMN global_locations.delete_time IS '删除时间';
CREATE TABLE global_location_images (
	location_id VARCHAR(256) NOT NULL, 
	image_index INTEGER NOT NULL, 
	image_model_system_prompt TEXT, 
	description TEXT, 
	available_slots TEXT, 
	image_url TEXT, 
	image_media_id VARCHAR(256), 
	is_selected BOOLEAN, 
	thumbnail_url TEXT, 
	previous_thumbnail_url TEXT, 
	previous_image_url TEXT, 
	previous_image_media_id VARCHAR(256), 
	previous_description TEXT, 
	volc_private_asset_id VARCHAR(256), 
	byteplus_asset_id VARCHAR(256), 
	gen_status VARCHAR(32) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_location_image_index UNIQUE (location_id, image_index)
);
CREATE INDEX ix_global_location_images_location_id ON global_location_images (location_id);
COMMENT ON COLUMN global_location_images.location_id IS '场景ID';
COMMENT ON COLUMN global_location_images.image_index IS '图片序号';
COMMENT ON COLUMN global_location_images.image_model_system_prompt IS '图生模型系统提示词';
COMMENT ON COLUMN global_location_images.description IS '图片描述';
COMMENT ON COLUMN global_location_images.available_slots IS '可用槽位信息';
COMMENT ON COLUMN global_location_images.image_url IS '图片URL';
COMMENT ON COLUMN global_location_images.image_media_id IS '图片媒体对象ID';
COMMENT ON COLUMN global_location_images.is_selected IS '是否为选中图片';
COMMENT ON COLUMN global_location_images.thumbnail_url IS '缩略图 COS key';
COMMENT ON COLUMN global_location_images.previous_thumbnail_url IS '上一张缩略图 COS key（用于撤销）';
COMMENT ON COLUMN global_location_images.previous_image_url IS '上一次图片URL';
COMMENT ON COLUMN global_location_images.previous_image_media_id IS '上一次图片媒体对象ID';
COMMENT ON COLUMN global_location_images.previous_description IS '上一次描述词';
COMMENT ON COLUMN global_location_images.volc_private_asset_id IS '火山私域素材ID';
COMMENT ON COLUMN global_location_images.byteplus_asset_id IS 'BytePlus 资产ID(国际版同步后获得)';
COMMENT ON COLUMN global_location_images.gen_status IS '生成状态: pending/generating/completed/failed';
COMMENT ON COLUMN global_location_images.id IS '主键 UUID';
COMMENT ON COLUMN global_location_images.create_time IS '创建时间';
COMMENT ON COLUMN global_location_images.create_uid IS '创建人id';
COMMENT ON COLUMN global_location_images.update_time IS '最近一次修改时间';
COMMENT ON COLUMN global_location_images.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN global_location_images.is_deleted IS '是否删除';
COMMENT ON COLUMN global_location_images.delete_time IS '删除时间';
CREATE TABLE global_voices (
	user_id VARCHAR(256) NOT NULL, 
	owner_user_id VARCHAR(256), 
	folder_id VARCHAR(256), 
	name VARCHAR(256) NOT NULL, 
	description TEXT, 
	voice_id VARCHAR(256), 
	voice_type VARCHAR(256), 
	custom_voice_url TEXT, 
	custom_voice_media_id VARCHAR(256), 
	volc_private_asset_id VARCHAR(256), 
	byteplus_asset_id VARCHAR(256), 
	voice_prompt TEXT, 
	gender VARCHAR(32), 
	language VARCHAR(32), 
	duration INTEGER, 
	is_management_asset BOOLEAN, 
	visibility VARCHAR(32), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_global_voices_user_id ON global_voices (user_id);
CREATE INDEX ix_global_voices_folder_id ON global_voices (folder_id);
CREATE INDEX ix_global_voices_owner_user_id ON global_voices (owner_user_id);
COMMENT ON COLUMN global_voices.user_id IS '创建者ID';
COMMENT ON COLUMN global_voices.owner_user_id IS '主账号ID';
COMMENT ON COLUMN global_voices.folder_id IS '文件夹ID';
COMMENT ON COLUMN global_voices.name IS '音色名称';
COMMENT ON COLUMN global_voices.description IS '详细描述';
COMMENT ON COLUMN global_voices.voice_id IS 'qwen-tts voice ID';
COMMENT ON COLUMN global_voices.voice_type IS '音色类型';
COMMENT ON COLUMN global_voices.custom_voice_url IS '上传音频URL';
COMMENT ON COLUMN global_voices.custom_voice_media_id IS '上传音频媒体对象ID';
COMMENT ON COLUMN global_voices.volc_private_asset_id IS '火山私域素材ID';
COMMENT ON COLUMN global_voices.byteplus_asset_id IS 'BytePlus 资产ID(国际版同步后获得)';
COMMENT ON COLUMN global_voices.voice_prompt IS 'AI设计提示词';
COMMENT ON COLUMN global_voices.gender IS '性别';
COMMENT ON COLUMN global_voices.language IS '语言';
COMMENT ON COLUMN global_voices.duration IS '音频时长(秒)';
COMMENT ON COLUMN global_voices.is_management_asset IS '是否为平台资产';
COMMENT ON COLUMN global_voices.visibility IS '可见范围: public/partial/private';
COMMENT ON COLUMN global_voices.id IS '主键 UUID';
COMMENT ON COLUMN global_voices.create_time IS '创建时间';
COMMENT ON COLUMN global_voices.create_uid IS '创建人id';
COMMENT ON COLUMN global_voices.update_time IS '最近一次修改时间';
COMMENT ON COLUMN global_voices.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN global_voices.is_deleted IS '是否删除';
COMMENT ON COLUMN global_voices.delete_time IS '删除时间';
CREATE TABLE asset_share_relations (
	asset_id VARCHAR(256) NOT NULL, 
	asset_type VARCHAR(64), 
	user_id VARCHAR(256) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_asset_share_relations_user_id ON asset_share_relations (user_id);
CREATE INDEX ix_asset_share_relations_asset_type ON asset_share_relations (asset_type);
CREATE INDEX ix_asset_share_relations_asset_id ON asset_share_relations (asset_id);
COMMENT ON COLUMN asset_share_relations.asset_id IS '资产ID';
COMMENT ON COLUMN asset_share_relations.asset_type IS '资产类型: character/location/voice';
COMMENT ON COLUMN asset_share_relations.user_id IS '客户端用户ID';
COMMENT ON COLUMN asset_share_relations.id IS '主键 UUID';
COMMENT ON COLUMN asset_share_relations.create_time IS '创建时间';
COMMENT ON COLUMN asset_share_relations.create_uid IS '创建人id';
COMMENT ON COLUMN asset_share_relations.update_time IS '最近一次修改时间';
COMMENT ON COLUMN asset_share_relations.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN asset_share_relations.is_deleted IS '是否删除';
COMMENT ON COLUMN asset_share_relations.delete_time IS '删除时间';
CREATE TABLE point_transfer_record (
	user_id VARCHAR(128), 
	transfer_from_user_before_point NUMERIC(10, 2), 
	transfer_from_user_after_point NUMERIC(10, 2), 
	transfer_to_user_id VARCHAR(128), 
	transfer_to_user_before_point NUMERIC(10, 2), 
	transfer_to_user_after_point NUMERIC(10, 2), 
	point NUMERIC(10, 2), 
	transfer_type INTEGER, 
	status INTEGER, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN point_transfer_record.user_id IS '用户ID';
COMMENT ON COLUMN point_transfer_record.transfer_from_user_before_point IS '转出账号-转账前可用积分余额';
COMMENT ON COLUMN point_transfer_record.transfer_from_user_after_point IS '转出账号-转账后可用积分余额';
COMMENT ON COLUMN point_transfer_record.transfer_to_user_id IS '转账目标用户ID';
COMMENT ON COLUMN point_transfer_record.transfer_to_user_before_point IS '转入账号-转账前可用积分余额';
COMMENT ON COLUMN point_transfer_record.transfer_to_user_after_point IS '转入账号-转账后可用积分余额';
COMMENT ON COLUMN point_transfer_record.point IS '转账积分';
COMMENT ON COLUMN point_transfer_record.transfer_type IS '转账类型
积分转账类型
0: 内部转账（主账号 -> 主账号）
1: 子账号转账（主账号 <-> 主账号下的子账号）
2: 后台分配（管理后台手动增减积分，系统 <-> 用户）
';
COMMENT ON COLUMN point_transfer_record.status IS '转账状态积分转账状态';
COMMENT ON COLUMN point_transfer_record.id IS '主键 UUID';
COMMENT ON COLUMN point_transfer_record.create_time IS '创建时间';
COMMENT ON COLUMN point_transfer_record.create_uid IS '创建人id';
COMMENT ON COLUMN point_transfer_record.update_time IS '最近一次修改时间';
COMMENT ON COLUMN point_transfer_record.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN point_transfer_record.is_deleted IS '是否删除';
COMMENT ON COLUMN point_transfer_record.delete_time IS '删除时间';
CREATE TABLE membership_change_log (
	user_id VARCHAR(36) NOT NULL, 
	from_level_id VARCHAR(36), 
	to_level_id VARCHAR(36) NOT NULL, 
	change_type INTEGER NOT NULL, 
	subscribe_type VARCHAR(16), 
	effective_time TIMESTAMP WITHOUT TIME ZONE, 
	status INTEGER, 
	order_no VARCHAR(64), 
	pay_amount NUMERIC(15, 2), 
	point_adjust NUMERIC(10, 2), 
	remark VARCHAR(255), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_membership_change_log_user_id ON membership_change_log (user_id);
COMMENT ON COLUMN membership_change_log.user_id IS '用户ID';
COMMENT ON COLUMN membership_change_log.from_level_id IS '原等级ID';
COMMENT ON COLUMN membership_change_log.to_level_id IS '目标等级ID';
COMMENT ON COLUMN membership_change_log.change_type IS '变更类型：1=新购 2=升级 3=降级预购 4=降级兑现 5=到期重购';
COMMENT ON COLUMN membership_change_log.subscribe_type IS '订阅类型';
COMMENT ON COLUMN membership_change_log.effective_time IS '生效时间';
COMMENT ON COLUMN membership_change_log.status IS '状态：1=已生效 2=预约中 3=已取消';
COMMENT ON COLUMN membership_change_log.order_no IS '关联订单号';
COMMENT ON COLUMN membership_change_log.pay_amount IS '本次支付金额';
COMMENT ON COLUMN membership_change_log.point_adjust IS '积分调整数';
COMMENT ON COLUMN membership_change_log.remark IS '备注';
COMMENT ON COLUMN membership_change_log.id IS '主键 UUID';
COMMENT ON COLUMN membership_change_log.create_time IS '创建时间';
COMMENT ON COLUMN membership_change_log.create_uid IS '创建人id';
COMMENT ON COLUMN membership_change_log.update_time IS '最近一次修改时间';
COMMENT ON COLUMN membership_change_log.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN membership_change_log.is_deleted IS '是否删除';
COMMENT ON COLUMN membership_change_log.delete_time IS '删除时间';
CREATE TABLE membership_level (
	name VARCHAR(64) NOT NULL, 
	level_order INTEGER NOT NULL, 
	monthly_price NUMERIC(10, 2), 
	monthly_discount_rate NUMERIC(3, 2), 
	yearly_price NUMERIC(10, 2), 
	yearly_discount_rate NUMERIC(3, 2), 
	can_buy_points BOOLEAN, 
	status INTEGER, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN membership_level.name IS '等级名称';
COMMENT ON COLUMN membership_level.level_order IS '等级排序，数值越大等级越高';
COMMENT ON COLUMN membership_level.monthly_price IS '月付原价';
COMMENT ON COLUMN membership_level.monthly_discount_rate IS '月付折扣率，如0.80=八折';
COMMENT ON COLUMN membership_level.yearly_price IS '年付原价';
COMMENT ON COLUMN membership_level.yearly_discount_rate IS '年付折扣率，如0.80=八折';
COMMENT ON COLUMN membership_level.can_buy_points IS '是否允许单独购买积分';
COMMENT ON COLUMN membership_level.status IS '状态：1=启用 0=禁用';
COMMENT ON COLUMN membership_level.id IS '主键 UUID';
COMMENT ON COLUMN membership_level.create_time IS '创建时间';
COMMENT ON COLUMN membership_level.create_uid IS '创建人id';
COMMENT ON COLUMN membership_level.update_time IS '最近一次修改时间';
COMMENT ON COLUMN membership_level.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN membership_level.is_deleted IS '是否删除';
COMMENT ON COLUMN membership_level.delete_time IS '删除时间';
CREATE TABLE membership_level_privilege (
	level_id VARCHAR(36) NOT NULL, 
	name VARCHAR(64), 
	privilege_key VARCHAR(64) NOT NULL, 
	privilege_value VARCHAR(128) NOT NULL, 
	remark VARCHAR(128), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_membership_level_privilege_level_id ON membership_level_privilege (level_id);
COMMENT ON COLUMN membership_level_privilege.level_id IS '关联会员等级ID';
COMMENT ON COLUMN membership_level_privilege.name IS '权益名称';
COMMENT ON COLUMN membership_level_privilege.privilege_key IS '权益键，如monthly_points/project_limit/ai_concurrency';
COMMENT ON COLUMN membership_level_privilege.privilege_value IS '权益值，如1000/10/5';
COMMENT ON COLUMN membership_level_privilege.remark IS '权益说明';
COMMENT ON COLUMN membership_level_privilege.id IS '主键 UUID';
COMMENT ON COLUMN membership_level_privilege.create_time IS '创建时间';
COMMENT ON COLUMN membership_level_privilege.create_uid IS '创建人id';
COMMENT ON COLUMN membership_level_privilege.update_time IS '最近一次修改时间';
COMMENT ON COLUMN membership_level_privilege.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN membership_level_privilege.is_deleted IS '是否删除';
COMMENT ON COLUMN membership_level_privilege.delete_time IS '删除时间';
CREATE TABLE user_membership (
	user_id VARCHAR(36) NOT NULL, 
	level_id VARCHAR(36) NOT NULL, 
	start_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expire_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	subscribe_type VARCHAR(16) NOT NULL, 
	status INTEGER, 
	next_level_id VARCHAR(36), 
	next_subscribe_type VARCHAR(16), 
	auto_renew BOOLEAN, 
	origin_order_no VARCHAR(64), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_user_membership_expire_time ON user_membership (expire_time);
CREATE INDEX ix_user_membership_user_id ON user_membership (user_id);
CREATE INDEX ix_user_membership_status ON user_membership (status);
COMMENT ON COLUMN user_membership.user_id IS '用户ID';
COMMENT ON COLUMN user_membership.level_id IS '会员等级ID';
COMMENT ON COLUMN user_membership.start_time IS '生效时间';
COMMENT ON COLUMN user_membership.expire_time IS '到期时间';
COMMENT ON COLUMN user_membership.subscribe_type IS '订阅类型：monthly/yearly';
COMMENT ON COLUMN user_membership.status IS '状态：1=有效 0=过期 2=取消';
COMMENT ON COLUMN user_membership.next_level_id IS '降级预购的目标等级ID';
COMMENT ON COLUMN user_membership.next_subscribe_type IS '下次续期的订阅类型';
COMMENT ON COLUMN user_membership.auto_renew IS '是否自动续费（预留）';
COMMENT ON COLUMN user_membership.origin_order_no IS '当前周期原始开通订单号';
COMMENT ON COLUMN user_membership.id IS '主键 UUID';
COMMENT ON COLUMN user_membership.create_time IS '创建时间';
COMMENT ON COLUMN user_membership.create_uid IS '创建人id';
COMMENT ON COLUMN user_membership.update_time IS '最近一次修改时间';
COMMENT ON COLUMN user_membership.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN user_membership.is_deleted IS '是否删除';
COMMENT ON COLUMN user_membership.delete_time IS '删除时间';
CREATE TABLE recharge_order (
	order_no VARCHAR(64) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	pay_serial_number VARCHAR(64), 
	channel_order_no VARCHAR(64), 
	channel_pay_serial_no VARCHAR(100), 
	channel_finish_time TIMESTAMP WITHOUT TIME ZONE, 
	amount NUMERIC(15, 2) NOT NULL, 
	actual_pay_amount NUMERIC(15, 2), 
	fee_amount NUMERIC(15, 2), 
	extra_fee_amount NUMERIC(15, 2), 
	holiday_fee_amount NUMERIC(15, 2), 
	platform_fee_amount NUMERIC(15, 2), 
	pay_method INTEGER NOT NULL, 
	pay_mode VARCHAR(32), 
	pay_url TEXT, 
	status INTEGER NOT NULL, 
	failure_reason VARCHAR(255), 
	finished_time TIMESTAMP WITHOUT TIME ZONE, 
	order_type INTEGER, 
	product_id VARCHAR(36), 
	original_amount NUMERIC(15, 2), 
	subscribe_type VARCHAR(16), 
	change_type INTEGER, 
	from_level_id VARCHAR(36), 
	point_adjust NUMERIC(10, 2), 
	point_amount NUMERIC(10, 2), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (order_no)
);
CREATE INDEX ix_recharge_order_user_id ON recharge_order (user_id);
COMMENT ON COLUMN recharge_order.order_no IS '订单号';
COMMENT ON COLUMN recharge_order.user_id IS '用户ID';
COMMENT ON COLUMN recharge_order.pay_serial_number IS '支付方支付流水号';
COMMENT ON COLUMN recharge_order.channel_order_no IS '渠道订单号';
COMMENT ON COLUMN recharge_order.channel_pay_serial_no IS '渠道流水号';
COMMENT ON COLUMN recharge_order.channel_finish_time IS '渠道订单完成时间';
COMMENT ON COLUMN recharge_order.amount IS '充值金额';
COMMENT ON COLUMN recharge_order.actual_pay_amount IS '支付方实际支付金额';
COMMENT ON COLUMN recharge_order.fee_amount IS '商户手续费金额';
COMMENT ON COLUMN recharge_order.extra_fee_amount IS '商户额外手续费金额';
COMMENT ON COLUMN recharge_order.holiday_fee_amount IS '商户节假日手续费金额';
COMMENT ON COLUMN recharge_order.platform_fee_amount IS '商户平台手续费金额';
COMMENT ON COLUMN recharge_order.pay_method IS '支付方式: 1=杉德扫码';
COMMENT ON COLUMN recharge_order.pay_mode IS '支付方式细节：如扫码、条码支付';
COMMENT ON COLUMN recharge_order.pay_url IS '支付链接/二维码URL';
COMMENT ON COLUMN recharge_order.status IS '状态: 1=待支付, 2=支付中, 3=成功, 4=失败';
COMMENT ON COLUMN recharge_order.failure_reason IS '失败原因';
COMMENT ON COLUMN recharge_order.finished_time IS '订单完成时间';
COMMENT ON COLUMN recharge_order.order_type IS '订单类型：1=充值 2=会员购买 3=积分购买';
COMMENT ON COLUMN recharge_order.product_id IS '商品ID（会员等级ID或积分购买方案ID）';
COMMENT ON COLUMN recharge_order.original_amount IS '原价（划线价展示用）';
COMMENT ON COLUMN recharge_order.subscribe_type IS '订阅类型：monthly/yearly（会员购买时使用）';
COMMENT ON COLUMN recharge_order.change_type IS '变更类型：1=新购 2=升级 3=降级预购 5=到期重购';
COMMENT ON COLUMN recharge_order.from_level_id IS '升级时的原等级ID';
COMMENT ON COLUMN recharge_order.point_adjust IS '升级需补发的赠送积分数';
COMMENT ON COLUMN recharge_order.point_amount IS '购买积分数（积分购买订单专用）';
COMMENT ON COLUMN recharge_order.id IS '主键 UUID';
COMMENT ON COLUMN recharge_order.create_time IS '创建时间';
COMMENT ON COLUMN recharge_order.create_uid IS '创建人id';
COMMENT ON COLUMN recharge_order.update_time IS '最近一次修改时间';
COMMENT ON COLUMN recharge_order.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN recharge_order.is_deleted IS '是否删除';
COMMENT ON COLUMN recharge_order.delete_time IS '删除时间';
CREATE TABLE pay_api_log (
	order_no VARCHAR(64), 
	api_type VARCHAR(16) NOT NULL, 
	request_data TEXT, 
	response_data TEXT, 
	result VARCHAR(16) NOT NULL, 
	error_msg VARCHAR(512), 
	cost_ms INTEGER, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_pay_api_log_order_no ON pay_api_log (order_no);
COMMENT ON COLUMN pay_api_log.order_no IS '关联订单号';
COMMENT ON COLUMN pay_api_log.api_type IS '接口类型：create/query/callback';
COMMENT ON COLUMN pay_api_log.request_data IS '请求报文（加密后）';
COMMENT ON COLUMN pay_api_log.response_data IS '响应报文（脱敏后）';
COMMENT ON COLUMN pay_api_log.result IS '调用结果：success/fail';
COMMENT ON COLUMN pay_api_log.error_msg IS '失败时的错误描述';
COMMENT ON COLUMN pay_api_log.cost_ms IS '调用耗时（毫秒）';
COMMENT ON COLUMN pay_api_log.id IS '主键 UUID';
COMMENT ON COLUMN pay_api_log.create_time IS '创建时间';
COMMENT ON COLUMN pay_api_log.create_uid IS '创建人id';
COMMENT ON COLUMN pay_api_log.update_time IS '最近一次修改时间';
COMMENT ON COLUMN pay_api_log.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN pay_api_log.is_deleted IS '是否删除';
COMMENT ON COLUMN pay_api_log.delete_time IS '删除时间';
CREATE TABLE point_record (
	user_id VARCHAR(36) NOT NULL, 
	point_amount NUMERIC(10, 2) NOT NULL, 
	balance_after NUMERIC(10, 2), 
	record_type INTEGER NOT NULL, 
	point_type INTEGER, 
	source_id VARCHAR(64), 
	level_id VARCHAR(36), 
	grant_month VARCHAR(10), 
	remark VARCHAR(128), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_point_record_user_id ON point_record (user_id);
COMMENT ON COLUMN point_record.user_id IS '用户ID';
COMMENT ON COLUMN point_record.point_amount IS '积分数（正=入账，负=消费）';
COMMENT ON COLUMN point_record.balance_after IS '本次变动后的总积分余额（granted + purchased，历史数据为 NULL）';
COMMENT ON COLUMN point_record.record_type IS '记录类型：1=会员按月赠送 2=积分购买 3=到期降级 4=积分消费 5=转账 6=赠送清零';
COMMENT ON COLUMN point_record.point_type IS '积分类型：1=赠送 2=购买';
COMMENT ON COLUMN point_record.source_id IS '来源ID（订单号或关联记录ID）';
COMMENT ON COLUMN point_record.level_id IS '触发赠送的会员等级ID';
COMMENT ON COLUMN point_record.grant_month IS '赠送周期起始日，如2026-06-05（按月赠送时使用）';
COMMENT ON COLUMN point_record.remark IS '备注说明';
COMMENT ON COLUMN point_record.id IS '主键 UUID';
COMMENT ON COLUMN point_record.create_time IS '创建时间';
COMMENT ON COLUMN point_record.create_uid IS '创建人id';
COMMENT ON COLUMN point_record.update_time IS '最近一次修改时间';
COMMENT ON COLUMN point_record.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN point_record.is_deleted IS '是否删除';
COMMENT ON COLUMN point_record.delete_time IS '删除时间';
CREATE TABLE point_purchase_plan (
	point_amount NUMERIC(10, 2) NOT NULL, 
	original_price NUMERIC(10, 2) NOT NULL, 
	discount_price NUMERIC(10, 2) NOT NULL, 
	is_enabled BOOLEAN, 
	sort_order INTEGER, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
COMMENT ON COLUMN point_purchase_plan.point_amount IS '积分数';
COMMENT ON COLUMN point_purchase_plan.original_price IS '原价（划线价）';
COMMENT ON COLUMN point_purchase_plan.discount_price IS '折扣价（实际购买价）';
COMMENT ON COLUMN point_purchase_plan.is_enabled IS '是否启用';
COMMENT ON COLUMN point_purchase_plan.sort_order IS '排序，数值越小越靠前';
COMMENT ON COLUMN point_purchase_plan.id IS '主键 UUID';
COMMENT ON COLUMN point_purchase_plan.create_time IS '创建时间';
COMMENT ON COLUMN point_purchase_plan.create_uid IS '创建人id';
COMMENT ON COLUMN point_purchase_plan.update_time IS '最近一次修改时间';
COMMENT ON COLUMN point_purchase_plan.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN point_purchase_plan.is_deleted IS '是否删除';
COMMENT ON COLUMN point_purchase_plan.delete_time IS '删除时间';
CREATE TABLE canvas_document (
	user_id VARCHAR(36) NOT NULL, 
	title VARCHAR(128) NOT NULL, 
	description TEXT, 
	thumbnail_url VARCHAR(500), 
	last_opened_at TIMESTAMP WITHOUT TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_canvas_document_user_id ON canvas_document (user_id);
COMMENT ON COLUMN canvas_document.user_id IS '所有者用户ID';
COMMENT ON COLUMN canvas_document.title IS '画布标题';
COMMENT ON COLUMN canvas_document.description IS '画布描述';
COMMENT ON COLUMN canvas_document.thumbnail_url IS '画布缩略图URL';
COMMENT ON COLUMN canvas_document.last_opened_at IS '最近一次打开时间';
COMMENT ON COLUMN canvas_document.id IS '主键 UUID';
COMMENT ON COLUMN canvas_document.create_time IS '创建时间';
COMMENT ON COLUMN canvas_document.create_uid IS '创建人id';
COMMENT ON COLUMN canvas_document.update_time IS '最近一次修改时间';
COMMENT ON COLUMN canvas_document.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN canvas_document.is_deleted IS '是否删除';
COMMENT ON COLUMN canvas_document.delete_time IS '删除时间';
CREATE TABLE canvas_item (
	canvas_id VARCHAR(36) NOT NULL, 
	item_type VARCHAR(16) NOT NULL, 
	parent_id VARCHAR(36), 
	title VARCHAR(128), 
	position_x INTEGER, 
	position_y INTEGER, 
	width INTEGER, 
	height INTEGER, 
	z_index INTEGER, 
	content_json JSON, 
	generation_config_json JSON, 
	last_output_json JSON, 
	cover_url TEXT, 
	last_run_status VARCHAR(16) NOT NULL, 
	last_run_error TEXT, 
	volc_asset_id VARCHAR(128), 
	byteplus_asset_id VARCHAR(128), 
	asset_tag VARCHAR(16), 
	saved_to_asset_center BOOLEAN DEFAULT '0' NOT NULL, 
	voice_url TEXT, 
	voice_cos_key VARCHAR(512), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_canvas_item_parent_id ON canvas_item (parent_id);
CREATE INDEX ix_canvas_item_volc_asset_id ON canvas_item (volc_asset_id);
CREATE INDEX ix_canvas_item_canvas_id ON canvas_item (canvas_id);
CREATE INDEX ix_canvas_item_byteplus_asset_id ON canvas_item (byteplus_asset_id);
COMMENT ON COLUMN canvas_item.canvas_id IS '所属画布ID';
COMMENT ON COLUMN canvas_item.item_type IS '节点类型: text/image/video/audio/group';
COMMENT ON COLUMN canvas_item.parent_id IS '所属组合节点ID（仅单层：指向 item_type=group 的节点；为空表示顶层节点）';
COMMENT ON COLUMN canvas_item.title IS '节点标题';
COMMENT ON COLUMN canvas_item.position_x IS 'X 坐标';
COMMENT ON COLUMN canvas_item.position_y IS 'Y 坐标';
COMMENT ON COLUMN canvas_item.width IS '节点宽度';
COMMENT ON COLUMN canvas_item.height IS '节点高度';
COMMENT ON COLUMN canvas_item.z_index IS '层级';
COMMENT ON COLUMN canvas_item.content_json IS '节点内容：{prompt, ...}';
COMMENT ON COLUMN canvas_item.generation_config_json IS '生成参数：{model, resolution, ratio, count, ...}';
COMMENT ON COLUMN canvas_item.last_output_json IS '最近一次生成的输出';
COMMENT ON COLUMN canvas_item.cover_url IS '节点封面图URL（COS永久URL；图片=压缩缩略图，视频=ffmpeg首帧）';
COMMENT ON COLUMN canvas_item.last_run_status IS '最近一次生成状态: idle/pending/processing/completed/failed';
COMMENT ON COLUMN canvas_item.last_run_error IS '最近一次生成的错误信息';
COMMENT ON COLUMN canvas_item.volc_asset_id IS '火山引擎私域资产ID（国内）';
COMMENT ON COLUMN canvas_item.byteplus_asset_id IS 'BytePlus 私域资产ID（国际）';
COMMENT ON COLUMN canvas_item.asset_tag IS '资产标记: character/location/prop';
COMMENT ON COLUMN canvas_item.saved_to_asset_center IS '是否已保存到资产中心（保存到资产中心接口置 True，避免重复入库）';
COMMENT ON COLUMN canvas_item.voice_url IS '角色音色音频 URL（character 节点用）';
COMMENT ON COLUMN canvas_item.voice_cos_key IS '角色音色 COS key';
COMMENT ON COLUMN canvas_item.id IS '主键 UUID';
COMMENT ON COLUMN canvas_item.create_time IS '创建时间';
COMMENT ON COLUMN canvas_item.create_uid IS '创建人id';
COMMENT ON COLUMN canvas_item.update_time IS '最近一次修改时间';
COMMENT ON COLUMN canvas_item.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN canvas_item.is_deleted IS '是否删除';
COMMENT ON COLUMN canvas_item.delete_time IS '删除时间';
CREATE TABLE canvas_connection (
	canvas_id VARCHAR(36) NOT NULL, 
	source_item_id VARCHAR(36) NOT NULL, 
	target_item_id VARCHAR(36) NOT NULL, 
	source_handle VARCHAR(32), 
	target_handle VARCHAR(32), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_canvas_connection_canvas_id ON canvas_connection (canvas_id);
CREATE INDEX ix_canvas_connection_target_item_id ON canvas_connection (target_item_id);
CREATE INDEX ix_canvas_connection_source_item_id ON canvas_connection (source_item_id);
COMMENT ON COLUMN canvas_connection.canvas_id IS '所属画布ID';
COMMENT ON COLUMN canvas_connection.source_item_id IS '上游节点ID';
COMMENT ON COLUMN canvas_connection.target_item_id IS '下游节点ID';
COMMENT ON COLUMN canvas_connection.source_handle IS '上游节点连接点';
COMMENT ON COLUMN canvas_connection.target_handle IS '下游节点连接点';
COMMENT ON COLUMN canvas_connection.id IS '主键 UUID';
COMMENT ON COLUMN canvas_connection.create_time IS '创建时间';
COMMENT ON COLUMN canvas_connection.create_uid IS '创建人id';
COMMENT ON COLUMN canvas_connection.update_time IS '最近一次修改时间';
COMMENT ON COLUMN canvas_connection.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN canvas_connection.is_deleted IS '是否删除';
COMMENT ON COLUMN canvas_connection.delete_time IS '删除时间';
CREATE TABLE canvas_item_generation (
	item_id VARCHAR(36) NOT NULL, 
	document_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	generation_type VARCHAR(16) NOT NULL, 
	input_json JSON, 
	output_json JSON, 
	ark_task_id VARCHAR(64), 
	model_call_log_id VARCHAR(36), 
	status VARCHAR(16) NOT NULL, 
	error_msg TEXT, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	finished_at TIMESTAMP WITHOUT TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_canvas_item_generation_model_call_log_id ON canvas_item_generation (model_call_log_id);
CREATE INDEX ix_canvas_item_generation_item_id ON canvas_item_generation (item_id);
CREATE INDEX ix_canvas_item_generation_ark_task_id ON canvas_item_generation (ark_task_id);
CREATE INDEX ix_canvas_item_generation_document_id ON canvas_item_generation (document_id);
CREATE INDEX ix_canvas_item_generation_user_id ON canvas_item_generation (user_id);
COMMENT ON COLUMN canvas_item_generation.item_id IS '所属节点ID';
COMMENT ON COLUMN canvas_item_generation.document_id IS '所属画布ID（冗余，便于查询）';
COMMENT ON COLUMN canvas_item_generation.user_id IS '发起用户ID（冗余）';
COMMENT ON COLUMN canvas_item_generation.generation_type IS '生成类型: text/image/video/audio';
COMMENT ON COLUMN canvas_item_generation.input_json IS '本次生成的输入快照';
COMMENT ON COLUMN canvas_item_generation.output_json IS '本次生成的输出';
COMMENT ON COLUMN canvas_item_generation.ark_task_id IS 'Seedance 任务 ID（冗余，回调匹配用）';
COMMENT ON COLUMN canvas_item_generation.model_call_log_id IS '关联的模型调用日志ID（model_call_log.id）';
COMMENT ON COLUMN canvas_item_generation.status IS '状态: idle/pending/processing/completed/failed/canceled';
COMMENT ON COLUMN canvas_item_generation.error_msg IS '错误信息';
COMMENT ON COLUMN canvas_item_generation.started_at IS '开始处理时间';
COMMENT ON COLUMN canvas_item_generation.finished_at IS '完成时间';
COMMENT ON COLUMN canvas_item_generation.id IS '主键 UUID';
COMMENT ON COLUMN canvas_item_generation.create_time IS '创建时间';
COMMENT ON COLUMN canvas_item_generation.create_uid IS '创建人id';
COMMENT ON COLUMN canvas_item_generation.update_time IS '最近一次修改时间';
COMMENT ON COLUMN canvas_item_generation.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN canvas_item_generation.is_deleted IS '是否删除';
COMMENT ON COLUMN canvas_item_generation.delete_time IS '删除时间';
CREATE TABLE analysis_result (
	project_id VARCHAR(36) NOT NULL, 
	current_version_id VARCHAR(36), 
	status VARCHAR(32) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES project (id)
);
CREATE INDEX ix_analysis_result_project_id ON analysis_result (project_id);
COMMENT ON COLUMN analysis_result.project_id IS '项目ID';
COMMENT ON COLUMN analysis_result.current_version_id IS '当前确认的版本ID';
COMMENT ON COLUMN analysis_result.status IS '分析状态: pending/generating/completed';
COMMENT ON COLUMN analysis_result.id IS '主键 UUID';
COMMENT ON COLUMN analysis_result.create_time IS '创建时间';
COMMENT ON COLUMN analysis_result.create_uid IS '创建人id';
COMMENT ON COLUMN analysis_result.update_time IS '最近一次修改时间';
COMMENT ON COLUMN analysis_result.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN analysis_result.is_deleted IS '是否删除';
COMMENT ON COLUMN analysis_result.delete_time IS '删除时间';
CREATE TABLE project_character (
	project_id VARCHAR(36) NOT NULL, 
	name VARCHAR(256) NOT NULL, 
	aliases TEXT, 
	description TEXT, 
	profile_data TEXT, 
	profile_confirmed BOOLEAN NOT NULL, 
	voice_id VARCHAR(128), 
	voice_type VARCHAR(64), 
	custom_voice_url VARCHAR(1024), 
	image_url VARCHAR(1024), 
	previous_image_url VARCHAR(1024), 
	thumbnail_url VARCHAR(1024), 
	previous_thumbnail_url VARCHAR(1024), 
	image_prompt TEXT, 
	image_model_system_prompt TEXT, 
	gen_status VARCHAR(32) NOT NULL, 
	source_global_id VARCHAR(36), 
	volc_private_asset_id VARCHAR(256), 
	byteplus_asset_id VARCHAR(256), 
	volc_asset_url VARCHAR(512), 
	volc_asset_status VARCHAR(32), 
	volc_asset_reason VARCHAR(256), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES project (id)
);
CREATE INDEX ix_project_character_project_id ON project_character (project_id);
COMMENT ON COLUMN project_character.project_id IS '项目ID';
COMMENT ON COLUMN project_character.name IS '角色名';
COMMENT ON COLUMN project_character.aliases IS '别名/曾用名';
COMMENT ON COLUMN project_character.description IS 'AI 生成的人物描述（可由用户修改）';
COMMENT ON COLUMN project_character.profile_data IS '角色设定（分号分隔的属性描述串，由 LLM 生成）';
COMMENT ON COLUMN project_character.profile_confirmed IS '角色设定是否已确认';
COMMENT ON COLUMN project_character.voice_id IS '绑定的音色 ID';
COMMENT ON COLUMN project_character.voice_type IS '音色类型';
COMMENT ON COLUMN project_character.custom_voice_url IS '自定义音色文件 URL';
COMMENT ON COLUMN project_character.image_url IS '当前图片 URL';
COMMENT ON COLUMN project_character.previous_image_url IS '上一张图片 URL（用于撤销）';
COMMENT ON COLUMN project_character.thumbnail_url IS '缩略图 COS key';
COMMENT ON COLUMN project_character.previous_thumbnail_url IS '上一张缩略图 COS key（用于撤销）';
COMMENT ON COLUMN project_character.image_prompt IS '图片生成提示词（可由用户修改后重新生成）';
COMMENT ON COLUMN project_character.image_model_system_prompt IS '图片生成时的系统级提示词';
COMMENT ON COLUMN project_character.gen_status IS '生成状态: pending/generating/completed/failed';
COMMENT ON COLUMN project_character.source_global_id IS '从全局角色复制来源';
COMMENT ON COLUMN project_character.volc_private_asset_id IS '火山私域素材ID';
COMMENT ON COLUMN project_character.byteplus_asset_id IS 'BytePlus 资产ID(国际版同步后获得)';
COMMENT ON COLUMN project_character.volc_asset_url IS 'SD2认证后的asset://URL';
COMMENT ON COLUMN project_character.volc_asset_status IS 'pending/active/stale';
COMMENT ON COLUMN project_character.volc_asset_reason IS '失效原因';
COMMENT ON COLUMN project_character.id IS '主键 UUID';
COMMENT ON COLUMN project_character.create_time IS '创建时间';
COMMENT ON COLUMN project_character.create_uid IS '创建人id';
COMMENT ON COLUMN project_character.update_time IS '最近一次修改时间';
COMMENT ON COLUMN project_character.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN project_character.is_deleted IS '是否删除';
COMMENT ON COLUMN project_character.delete_time IS '删除时间';
CREATE TABLE project_location (
	project_id VARCHAR(36) NOT NULL, 
	name VARCHAR(256) NOT NULL, 
	place TEXT, 
	time TEXT, 
	summary TEXT, 
	description TEXT, 
	image_url VARCHAR(1024), 
	previous_image_url VARCHAR(1024), 
	thumbnail_url VARCHAR(1024), 
	previous_thumbnail_url VARCHAR(1024), 
	image_prompt TEXT, 
	image_model_system_prompt TEXT, 
	gen_status VARCHAR(32) NOT NULL, 
	source_global_id VARCHAR(36), 
	volc_private_asset_id VARCHAR(256), 
	byteplus_asset_id VARCHAR(256), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES project (id)
);
CREATE INDEX ix_project_location_project_id ON project_location (project_id);
COMMENT ON COLUMN project_location.project_id IS '项目ID';
COMMENT ON COLUMN project_location.name IS '场景名';
COMMENT ON COLUMN project_location.place IS '场景地点';
COMMENT ON COLUMN project_location.time IS '场景时间';
COMMENT ON COLUMN project_location.summary IS '场景摘要（来自分析结果）';
COMMENT ON COLUMN project_location.description IS '场景图片描述（可由用户修改）';
COMMENT ON COLUMN project_location.image_url IS '当前图片 URL';
COMMENT ON COLUMN project_location.previous_image_url IS '上一张图片 URL（用于撤销）';
COMMENT ON COLUMN project_location.thumbnail_url IS '缩略图 COS key';
COMMENT ON COLUMN project_location.previous_thumbnail_url IS '上一张缩略图 COS key（用于撤销）';
COMMENT ON COLUMN project_location.image_prompt IS '图片生成提示词（可由用户修改后重新生成）';
COMMENT ON COLUMN project_location.image_model_system_prompt IS '图片生成时的系统级提示词';
COMMENT ON COLUMN project_location.gen_status IS '生成状态: pending/generating/completed/failed';
COMMENT ON COLUMN project_location.source_global_id IS '从全局场景复制来源';
COMMENT ON COLUMN project_location.volc_private_asset_id IS '火山私域素材ID';
COMMENT ON COLUMN project_location.byteplus_asset_id IS 'BytePlus 资产ID(国际版同步后获得)';
COMMENT ON COLUMN project_location.id IS '主键 UUID';
COMMENT ON COLUMN project_location.create_time IS '创建时间';
COMMENT ON COLUMN project_location.create_uid IS '创建人id';
COMMENT ON COLUMN project_location.update_time IS '最近一次修改时间';
COMMENT ON COLUMN project_location.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN project_location.is_deleted IS '是否删除';
COMMENT ON COLUMN project_location.delete_time IS '删除时间';
CREATE TABLE project_prop (
	project_id VARCHAR(36) NOT NULL, 
	name VARCHAR(256) NOT NULL, 
	aliases TEXT, 
	description TEXT, 
	image_url VARCHAR(1024), 
	previous_image_url VARCHAR(1024), 
	thumbnail_url VARCHAR(1024), 
	previous_thumbnail_url VARCHAR(1024), 
	image_prompt TEXT, 
	image_model_system_prompt TEXT, 
	gen_status VARCHAR(32) NOT NULL, 
	source_global_id VARCHAR(36), 
	volc_private_asset_id VARCHAR(256), 
	byteplus_asset_id VARCHAR(256), 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES project (id)
);
CREATE INDEX ix_project_prop_project_id ON project_prop (project_id);
COMMENT ON COLUMN project_prop.project_id IS '项目ID';
COMMENT ON COLUMN project_prop.name IS '道具名';
COMMENT ON COLUMN project_prop.aliases IS '别名/英文名';
COMMENT ON COLUMN project_prop.description IS 'AI 生成的道具描述（可由用户修改）';
COMMENT ON COLUMN project_prop.image_url IS '当前图片 URL';
COMMENT ON COLUMN project_prop.previous_image_url IS '上一张图片 URL（用于撤销）';
COMMENT ON COLUMN project_prop.thumbnail_url IS '缩略图 COS key';
COMMENT ON COLUMN project_prop.previous_thumbnail_url IS '上一张缩略图 COS key（用于撤销）';
COMMENT ON COLUMN project_prop.image_prompt IS '图片生成提示词（可由用户修改后重新生成）';
COMMENT ON COLUMN project_prop.image_model_system_prompt IS '图片生成时的系统级提示词';
COMMENT ON COLUMN project_prop.gen_status IS '生成状态: pending/generating/completed/failed';
COMMENT ON COLUMN project_prop.source_global_id IS '从全局道具复制来源';
COMMENT ON COLUMN project_prop.volc_private_asset_id IS '火山私域素材ID';
COMMENT ON COLUMN project_prop.byteplus_asset_id IS 'BytePlus 资产ID(国际版同步后获得)';
COMMENT ON COLUMN project_prop.id IS '主键 UUID';
COMMENT ON COLUMN project_prop.create_time IS '创建时间';
COMMENT ON COLUMN project_prop.create_uid IS '创建人id';
COMMENT ON COLUMN project_prop.update_time IS '最近一次修改时间';
COMMENT ON COLUMN project_prop.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN project_prop.is_deleted IS '是否删除';
COMMENT ON COLUMN project_prop.delete_time IS '删除时间';
CREATE TABLE analysis_version (
	analysis_result_id VARCHAR(36) NOT NULL, 
	parent_version_id VARCHAR(36), 
	version_number INTEGER NOT NULL, 
	global_setting JSON, 
	character_profiles JSON, 
	scene_descriptions JSON, 
	prop_descriptions JSON, 
	character_details JSON, 
	scene_details JSON, 
	prop_details JSON, 
	episode_outlines JSON, 
	first_ep_storyboard JSON, 
	adjustment_context JSON, 
	prompt_snapshot TEXT, 
	model_config JSON, 
	token_usage JSON, 
	is_confirmed BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	create_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	create_uid VARCHAR(36), 
	update_time TIMESTAMP WITHOUT TIME ZONE, 
	update_uid VARCHAR(36), 
	is_deleted BOOLEAN, 
	delete_time TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(analysis_result_id) REFERENCES analysis_result (id)
);
CREATE INDEX ix_analysis_version_analysis_result_id ON analysis_version (analysis_result_id);
COMMENT ON COLUMN analysis_version.analysis_result_id IS '分析结果ID';
COMMENT ON COLUMN analysis_version.parent_version_id IS '基于哪个版本调整';
COMMENT ON COLUMN analysis_version.version_number IS '版本号';
COMMENT ON COLUMN analysis_version.global_setting IS '全局设定: {novel_summary, world_setting, style_tone, character_relations, suggested_episodes, episode_mapping}';
COMMENT ON COLUMN analysis_version.character_profiles IS '人物特征列表（Layer 2 格式化 JSON 数组）';
COMMENT ON COLUMN analysis_version.scene_descriptions IS '场景描写列表（Layer 2 格式化 JSON 数组）';
COMMENT ON COLUMN analysis_version.prop_descriptions IS '道具描写列表（Layer 2 格式化 JSON 数组）';
COMMENT ON COLUMN analysis_version.character_details IS '人物原始结构化数据（Layer 1）';
COMMENT ON COLUMN analysis_version.scene_details IS '场景原始结构化数据（Layer 1）';
COMMENT ON COLUMN analysis_version.prop_details IS '道具原始结构化数据（Layer 1）';
COMMENT ON COLUMN analysis_version.episode_outlines IS '每集剧本大纲';
COMMENT ON COLUMN analysis_version.first_ep_storyboard IS '第一集分镜';
COMMENT ON COLUMN analysis_version.adjustment_context IS '增量调整上下文快照';
COMMENT ON COLUMN analysis_version.prompt_snapshot IS 'Prompt快照';
COMMENT ON COLUMN analysis_version.model_config IS '模型配置';
COMMENT ON COLUMN analysis_version.token_usage IS 'Token使用量';
COMMENT ON COLUMN analysis_version.is_confirmed IS '是否已确认';
COMMENT ON COLUMN analysis_version.id IS '主键 UUID';
COMMENT ON COLUMN analysis_version.create_time IS '创建时间';
COMMENT ON COLUMN analysis_version.create_uid IS '创建人id';
COMMENT ON COLUMN analysis_version.update_time IS '最近一次修改时间';
COMMENT ON COLUMN analysis_version.update_uid IS '最近一次修改人id';
COMMENT ON COLUMN analysis_version.is_deleted IS '是否删除';
COMMENT ON COLUMN analysis_version.delete_time IS '删除时间';

-- ==================== 种子数据 ====================

-- 表 sys_permission（9 条）
INSERT INTO "sys_permission" ("code", "name", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('project:create', '创建项目', '0e56abfe-f47b-41cb-a8c3-1ca9d71559a1', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_permission" ("code", "name", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('project:read', '查看项目', '62941e62-85bf-4cf8-b879-47e802019ca4', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_permission" ("code", "name", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('project:update', '编辑项目', '5a8ddb22-a8d8-4748-a3c5-7a5490f13596', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_permission" ("code", "name", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('project:delete', '删除项目', '87b9e92d-efa7-4f27-970e-669ed4a575de', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_permission" ("code", "name", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('asset:create', '创建资产', 'fb64179f-ef0c-4d80-a1db-0d02b9c3872b', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_permission" ("code", "name", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('asset:read', '查看资产', 'b4faa769-7e75-47e8-b23b-ec953accc904', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_permission" ("code", "name", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('asset:update', '编辑资产', 'fc980055-503e-450f-aeb5-b134453ad1f9', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_permission" ("code", "name", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('asset:delete', '删除资产', '731f2efb-8108-409e-ab5d-e60c2b0d5b11', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_permission" ("code", "name", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('main_user_asset:read', '查看主账号资产', '904fcd00-e7b9-4033-b610-f6f64b512cba', NOW(), NULL, NULL, NULL, FALSE, NULL);

-- 表 user（1 条）
INSERT INTO "user" ("username", "password_hash", "email", "status", "parent_user_id", "sub_user_limit", "type", "remark", "region", "username_cn", "contact_name", "last_login_time", "phone", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('test', '$2b$12$ofwCO6tENjqD/3fXo5NKb.67.y71SkqmLguQeB4FCvtnvmVZSUMgW', NULL, 'enable', NULL, 10, 'pro', NULL, NULL, NULL, NULL, NULL, NULL, '555ac8f5-3613-4206-85f1-afc72ae6c982', NOW(), NULL, NULL, NULL, FALSE, NULL);

-- 表 user_balance（1 条）
INSERT INTO "user_balance" ("user_id", "balance", "granted_balance", "purchased_balance", "frozen_amount", "total_spent", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('555ac8f5-3613-4206-85f1-afc72ae6c982', 0.00, 0.00, 0.00, 0.00, 0.00, 'c2401789-ebf9-4649-a28f-f75cd2e31676', NOW(), NULL, NULL, NULL, FALSE, NULL);

-- 表 user_api_config（1 条）
INSERT INTO "user_api_config" ("user_id", "analysis_model", "character_model", "location_model", "storyboard_model", "edit_model", "video_model", "audio_model", "analysis_concurrency", "image_concurrency", "video_concurrency", "video_ratio", "video_resolution", "art_style", "tts_rate", "image_resolution", "capability_defaults", "ark_api_key", "jd_api_key", "custom_models", "custom_providers", "ark_video_watermark", "volc_private_asset_group_id", "byteplus_private_asset_group_id", "endpoint", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('555ac8f5-3613-4206-85f1-afc72ae6c982', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 5, 5, 5, '9:16', '720p', 'american-comic', '+50%', '2K', NULL, NULL, NULL, NULL, NULL, FALSE, NULL, NULL, NULL, 'f66e8fdb-fa80-4b56-b4b7-9876975cfc2d', NOW(), NULL, NULL, NULL, FALSE, NULL);

-- 表 ai_provider（3 条）
INSERT INTO "ai_provider" ("name", "code", "base_url", "description", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('火山引擎 Ark', 'volcengine', 'https://ark.cn-beijing.volces.com/api/v3', '字节跳动-火山引擎', '98b9c2f4-40cd-4c53-b1a7-b2c39aff679c', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_provider" ("name", "code", "base_url", "description", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('ChatGPT', 'chatgpt', 'https://agentrs.jd.com/api/saas/openai-u/v1', '京东-API代理', 'fe056b8b-b038-4c7e-9b7c-7bedce8914b8', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_provider" ("name", "code", "base_url", "description", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('Deepseek', 'deepseek', 'https://agentrs.jd.com/api/saas/openai-u/v1', '京东-API代理', '414d5dab-8d52-4cf9-91fb-a43d2009d18b', NOW(), NULL, NULL, NULL, FALSE, NULL);

-- 表 ai_model（14 条）
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('98b9c2f4-40cd-4c53-b1a7-b2c39aff679c', 'Doubao Seed 1.8', 'doubao-seed-1-8-251228', 'text', NULL, NULL, '26b5fd75-8081-4bc1-937e-545a34f5279a', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('98b9c2f4-40cd-4c53-b1a7-b2c39aff679c', 'Doubao Seed 2.0 Pro', 'doubao-seed-2-0-pro-260215', 'text', NULL, NULL, '3ede4fc2-f855-4ada-b72e-caaaf690efad', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('98b9c2f4-40cd-4c53-b1a7-b2c39aff679c', 'Doubao Seed 2.0 Lite', 'doubao-seed-2-0-lite-260215', 'text', NULL, NULL, '02989270-d5e5-478a-babf-897c86fe0be1', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('98b9c2f4-40cd-4c53-b1a7-b2c39aff679c', 'Doubao Seed 2.0 Mini', 'doubao-seed-2-0-mini-260215', 'text', NULL, NULL, 'ab84e8e7-36a8-42ad-922c-9ce2d1825fa2', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('98b9c2f4-40cd-4c53-b1a7-b2c39aff679c', 'Doubao Seed 1.6', 'doubao-seed-1-6-251015', 'text', NULL, NULL, 'b09da241-f1e7-4ced-9127-a292c4c36b03', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('98b9c2f4-40cd-4c53-b1a7-b2c39aff679c', 'Doubao Seed 1.6 Lite', 'doubao-seed-1-6-lite-251015', 'text', NULL, NULL, '1e0a1b8d-d4ea-4fe3-add7-ede57c3da998', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('98b9c2f4-40cd-4c53-b1a7-b2c39aff679c', 'Seedream 4.5', 'doubao-seedream-4-5-251128', 'image', NULL, 'times', 'dd81c172-8cf8-4afa-bf23-05eb159db921', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('98b9c2f4-40cd-4c53-b1a7-b2c39aff679c', 'Seedream 5.0 Lite', 'doubao-seedream-5-0-260128', 'image', NULL, 'times', '5537c304-49ca-4e42-9218-dcfde7039bcf', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('98b9c2f4-40cd-4c53-b1a7-b2c39aff679c', 'Seedance 2.0', 'doubao-seedance-2-0-260128', 'video', NULL, NULL, '561df83b-2216-449c-8252-dd29e2acc4a4', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('98b9c2f4-40cd-4c53-b1a7-b2c39aff679c', 'Seedance 2.0 Fast', 'doubao-seedance-2-0-fast-260128', 'video', NULL, NULL, '34a5fe32-96cb-4005-94dc-8ef36506faf1', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('fe056b8b-b038-4c7e-9b7c-7bedce8914b8', 'gpt-image-2', 'gpt-image-2', 'image', NULL, 'token', '7acf7f3c-c445-4956-88b8-e9ca5c822c4f', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('414d5dab-8d52-4cf9-91fb-a43d2009d18b', 'DeepSeek-V4-pro', 'DeepSeek-V4-pro', 'text', NULL, NULL, '0f23e6f7-1750-4dca-bb87-8384423b47ae', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('414d5dab-8d52-4cf9-91fb-a43d2009d18b', 'DeepSeek-V4-Flash', 'DeepSeek-V4-Flash', 'text', NULL, NULL, '3860b36e-ccb0-4f7d-b015-492cc00d175e', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model" ("provider_id", "name", "model_name", "model_type", "base_url", "billing_type", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('414d5dab-8d52-4cf9-91fb-a43d2009d18b', 'DeepSeek-R1-0528', 'DeepSeek-R1-0528', 'text', NULL, NULL, 'be168be1-d8eb-4a93-8c02-e5f3715b3b7e', NOW(), NULL, NULL, NULL, FALSE, NULL);

-- 表 sys_dict（5 条）
INSERT INTO "sys_dict" ("dict_name", "key", "value", "sort", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('user_status', 'enable', '1', 1, '正常', '3f53e16c-f37e-4fb6-b634-51b0678acc2e', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_dict" ("dict_name", "key", "value", "sort", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('user_status', 'disable', '0', 2, '禁用', 'b2dcd559-c0f2-4da6-aedf-cf19d07f4d9f', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_dict" ("dict_name", "key", "value", "sort", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('user_type', 'normal', 'normal', 1, '普通版', 'f92f8464-b209-4934-ab89-6a64a06f88d2', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_dict" ("dict_name", "key", "value", "sort", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('user_type', 'lite', 'lite', 2, '轻量版', '23232390-5977-4793-bb66-d25826cc1386', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "sys_dict" ("dict_name", "key", "value", "sort", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('user_type', 'pro', 'pro', 3, '专业版', '3b5b9e3a-8e0e-4f2d-8f58-61bd50a38257', NOW(), NULL, NULL, NULL, FALSE, NULL);

-- 表 ai_model_pricing（86 条）
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('02989270-d5e5-478a-babf-897c86fe0be1', 'text_token', '{}'::json, '{"input_point_per_million": 216, "output_point_per_million": 1296}'::json, TRUE, NULL, 'eb686492-f67d-4cab-9a74-7fd07068900b', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('ab84e8e7-36a8-42ad-922c-9ce2d1825fa2', 'text_token', '{}'::json, '{"input_point_per_million": 96, "output_point_per_million": 960}'::json, TRUE, NULL, 'ca5ea335-15db-490f-81d7-b6ecb0d7578b', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('b09da241-f1e7-4ced-9127-a292c4c36b03', 'text_token', '{}'::json, '{"input_point_per_million": 288, "output_point_per_million": 2880}'::json, TRUE, NULL, 'e8a28865-422b-42f7-a9a1-8c3204c37120', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('1e0a1b8d-d4ea-4fe3-add7-ede57c3da998', 'text_token', '{}'::json, '{"input_point_per_million": 144, "output_point_per_million": 1440}'::json, TRUE, NULL, 'ef739a7a-2d67-449b-b869-22779c8926c5', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('3860b36e-ccb0-4f7d-b015-492cc00d175e', 'text_token', '{}'::json, '{"input_point_per_million": 120, "output_point_per_million": 240}'::json, TRUE, NULL, 'dd6f7c94-73bf-40aa-bf6d-3b84aee7b405', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('0f23e6f7-1750-4dca-bb87-8384423b47ae', 'text_token', '{}'::json, '{"input_point_per_million": 1440, "output_point_per_million": 2880}'::json, TRUE, NULL, 'e557a838-10aa-43e6-8e88-467f8c45a116', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('be168be1-d8eb-4a93-8c02-e5f3715b3b7e', 'text_token', '{}'::json, '{"input_point_per_million": 480, "output_point_per_million": 1920}'::json, TRUE, NULL, '227aede7-4c21-46b0-946d-09a6d9ed7031', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('5537c304-49ca-4e42-9218-dcfde7039bcf', 'image_per_piece', '{"is_character": false}'::json, '{"image_point": 33}'::json, TRUE, NULL, '0474c037-9a95-4f45-81ec-c21075918e57', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('5537c304-49ca-4e42-9218-dcfde7039bcf', 'image_per_piece', '{"is_character": true}'::json, '{"image_point": 66}'::json, TRUE, NULL, '01fa1e98-4395-45a5-a332-7f0b40103e14', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('dd81c172-8cf8-4afa-bf23-05eb159db921', 'image_per_piece', '{"is_character": false}'::json, '{"image_point": 38}'::json, TRUE, NULL, '6e8e4d19-cda6-449f-9550-7397954c60f8', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('dd81c172-8cf8-4afa-bf23-05eb159db921', 'image_per_piece', '{"is_character": true}'::json, '{"image_point": 75}'::json, TRUE, NULL, '6c34d22a-0577-4a87-83d2-a64081a88374', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('7acf7f3c-c445-4956-88b8-e9ca5c822c4f', 'image_token_full', '{}'::json, '{"input_text_point": 5760, "input_image_point": 9216, "output_total_point": 3456}'::json, TRUE, NULL, '8c6ff9e2-5646-4905-b84f-06956be00766', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_second', '{"has_reference": false, "video_resolution": "480P"}'::json, '{"video_point_per_second": 105}'::json, TRUE, NULL, '7804ad0f-5901-4b56-9b35-3b8e3dbe7cd2', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_second', '{"has_reference": false, "video_resolution": "720P"}'::json, '{"video_point_per_second": 225}'::json, TRUE, NULL, '20d79140-81f2-4f73-8193-f05a364c5fc2', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_second', '{"has_reference": false, "video_resolution": "1080P"}'::json, '{"video_point_per_second": 563}'::json, TRUE, NULL, '092a1777-68e7-4e50-b1d8-6015b8f272e3', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_second', '{"has_reference": false, "video_resolution": "480P"}'::json, '{"video_point_per_second": 84}'::json, TRUE, NULL, 'ea7d9489-5c51-4ae9-84be-7ab920eb2058', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_second', '{"has_reference": false, "video_resolution": "720P"}'::json, '{"video_point_per_second": 180}'::json, TRUE, NULL, '15a8d0aa-8c19-4792-9da2-5ff8906d0a13', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_second', '{"has_reference": true, "video_resolution": "480P"}'::json, '{"video_point_per_second": 63}'::json, TRUE, NULL, '7c06a6d0-5a9b-4cd7-9519-df1abed9b22a', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_second', '{"has_reference": true, "video_resolution": "720P"}'::json, '{"video_point_per_second": 135}'::json, TRUE, NULL, '9c2b40b5-cff7-40fe-b048-d6fdbb661d4b', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_second', '{"has_reference": true, "video_resolution": "1080P"}'::json, '{"video_point_per_second": 338}'::json, TRUE, NULL, '31ebe24e-c780-47eb-b2c1-49350efb5456', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_second', '{"has_reference": true, "video_resolution": "480P"}'::json, '{"video_point_per_second": 51}'::json, TRUE, NULL, '778324b5-967f-4511-ae9a-42a4c7e8dfec', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_second', '{"has_reference": true, "video_resolution": "720P"}'::json, '{"video_point_per_second": 108}'::json, TRUE, NULL, '1c7de123-7c38-485b-b3b8-5c8609c0ecfb', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 4}'::json, '{"reference_min_duration": 3, "video_point": 441}'::json, TRUE, NULL, '663e5e2f-c15c-4ca0-8750-38948ae5220f', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 5}'::json, '{"reference_min_duration": 4, "video_point": 567}'::json, TRUE, NULL, '1d1a873f-7adf-406b-9503-811d0be0eda9', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 6}'::json, '{"reference_min_duration": 4, "video_point": 630}'::json, TRUE, NULL, '46ecb0b6-3661-4501-98cd-14a16e7ea854', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 7}'::json, '{"reference_min_duration": 5, "video_point": 756}'::json, TRUE, NULL, '89cfc249-e246-482f-9694-5979c36a8b00', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 8}'::json, '{"reference_min_duration": 6, "video_point": 882}'::json, TRUE, NULL, 'b78fd417-7491-4557-868b-a6aedec1793c', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 9}'::json, '{"reference_min_duration": 6, "video_point": 945}'::json, TRUE, NULL, 'b9a808c6-cce1-40f2-aa41-e4803c1c8edc', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 10}'::json, '{"reference_min_duration": 7, "video_point": 1071}'::json, TRUE, NULL, 'cb7d744d-48b4-4095-8614-7a65bd0dceb2', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 11}'::json, '{"reference_min_duration": 8, "video_point": 1197}'::json, TRUE, NULL, '6db4468a-d7a6-47c4-85f1-37b48c749cb1', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 12}'::json, '{"reference_min_duration": 8, "video_point": 1260}'::json, TRUE, NULL, '2aa27aa7-6589-4a45-8fbf-a69b08d1f758', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 13}'::json, '{"reference_min_duration": 9, "video_point": 1386}'::json, TRUE, NULL, '7ba9d954-1dad-4589-9d7c-030ccdb623ea', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 14}'::json, '{"reference_min_duration": 10, "video_point": 1512}'::json, TRUE, NULL, '39418734-e91b-48ee-880c-7d3f1a52579c', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 15}'::json, '{"reference_min_duration": 10, "video_point": 1575}'::json, TRUE, NULL, '2b8fcdd8-413e-4a1c-a458-606b8a6d7abb', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 4}'::json, '{"reference_min_duration": 3, "video_point": 357}'::json, TRUE, NULL, 'fd164b65-36cf-4072-b496-8d4c17260acf', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 5}'::json, '{"reference_min_duration": 4, "video_point": 459}'::json, TRUE, NULL, 'd82f8307-039e-4fc8-87ff-8e8b23319800', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 6}'::json, '{"reference_min_duration": 4, "video_point": 510}'::json, TRUE, NULL, '300d23f1-b92d-40cc-95b7-e57983ab6301', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 7}'::json, '{"reference_min_duration": 5, "video_point": 612}'::json, TRUE, NULL, '1e49789c-b347-4e0d-9e6a-c14620dbf3cd', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 8}'::json, '{"reference_min_duration": 6, "video_point": 714}'::json, TRUE, NULL, '16d06967-3641-4fe4-9c87-adaff0076fe5', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 9}'::json, '{"reference_min_duration": 6, "video_point": 756}'::json, TRUE, NULL, 'ccfa6594-9df5-4b15-9669-e456f6bdb330', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 10}'::json, '{"reference_min_duration": 7, "video_point": 867}'::json, TRUE, NULL, '3e9aa849-db9e-46b8-b1c1-e02065e04a84', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 11}'::json, '{"reference_min_duration": 8, "video_point": 969}'::json, TRUE, NULL, '7678bb8c-208b-48be-b8ee-75aef32b3bdb', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 12}'::json, '{"reference_min_duration": 8, "video_point": 1020}'::json, TRUE, NULL, 'efdb02b7-66fd-4fc4-9c08-144dc118734d', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 13}'::json, '{"reference_min_duration": 9, "video_point": 1122}'::json, TRUE, NULL, '81d23c7a-21ae-4670-b2df-52bd71cac032', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 14}'::json, '{"reference_min_duration": 10, "video_point": 1224}'::json, TRUE, NULL, 'b021af6f-fdf2-4280-a30c-a1f798844329', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "480P", "video_output_duration": 15}'::json, '{"reference_min_duration": 10, "video_point": 1275}'::json, TRUE, NULL, '7932de99-f34f-4695-953f-ab163fd3ae0c', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 4}'::json, '{"reference_min_duration": 3, "video_point": 945}'::json, TRUE, NULL, 'cf104cb2-d679-4fab-ba16-04519e5e97ea', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 5}'::json, '{"reference_min_duration": 4, "video_point": 1215}'::json, TRUE, NULL, '61781f30-ffe6-4aa1-9c11-f7a6cae56edf', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 6}'::json, '{"reference_min_duration": 4, "video_point": 1350}'::json, TRUE, NULL, '165c87dd-5bdf-478d-8cab-8f61d2708341', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 7}'::json, '{"reference_min_duration": 5, "video_point": 1620}'::json, TRUE, NULL, '04ed9c5c-d9f7-4ac7-9c5b-f4ed9c050bf4', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 8}'::json, '{"reference_min_duration": 6, "video_point": 1890}'::json, TRUE, NULL, 'ab99a9d2-38c0-4be7-b90d-d54ca7339641', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 9}'::json, '{"reference_min_duration": 6, "video_point": 2025}'::json, TRUE, NULL, 'b743c3e6-4728-4d3f-8e2e-7dfcdb423cb0', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 10}'::json, '{"reference_min_duration": 7, "video_point": 2295}'::json, TRUE, NULL, 'dc464696-7344-4b03-9ca8-e5e3693eadde', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 11}'::json, '{"reference_min_duration": 8, "video_point": 2565}'::json, TRUE, NULL, 'a7033d5a-3f1f-43fc-83ba-dd858eb55209', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 12}'::json, '{"reference_min_duration": 8, "video_point": 2700}'::json, TRUE, NULL, '2edf7d27-2698-41a5-8b9c-e363a42a8311', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 13}'::json, '{"reference_min_duration": 9, "video_point": 2970}'::json, TRUE, NULL, 'c7d7093b-49c6-4739-9520-2c3089827d82', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 14}'::json, '{"reference_min_duration": 10, "video_point": 3240}'::json, TRUE, NULL, 'dcbaf307-4e0f-4f38-88b8-f18b5397e12a', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 15}'::json, '{"reference_min_duration": 10, "video_point": 3375}'::json, TRUE, NULL, '9d063819-86b4-4b4e-aa20-ebf753aa0223', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 4}'::json, '{"reference_min_duration": 3, "video_point": 756}'::json, TRUE, NULL, 'a9d1bcea-3926-4a8e-ba8d-074b68fe39f1', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 5}'::json, '{"reference_min_duration": 4, "video_point": 972}'::json, TRUE, NULL, '2b535382-ce11-44ad-9d1a-eedc3459f6c3', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 6}'::json, '{"reference_min_duration": 4, "video_point": 1080}'::json, TRUE, NULL, 'a6aa49c4-82b4-4942-9ea1-a7187fb02506', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 7}'::json, '{"reference_min_duration": 5, "video_point": 1296}'::json, TRUE, NULL, '8f49a75d-1e70-49a4-8b9d-07b4636bf096', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 8}'::json, '{"reference_min_duration": 6, "video_point": 1512}'::json, TRUE, NULL, '9bde12a8-5c0d-4077-8b9a-32f0c85e1a3a', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 9}'::json, '{"reference_min_duration": 6, "video_point": 1620}'::json, TRUE, NULL, '48ec4ce7-0a1c-448b-a947-9509df8c2663', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 10}'::json, '{"reference_min_duration": 7, "video_point": 1836}'::json, TRUE, NULL, 'c4473056-4dee-4e19-b6b4-1866cec4ae8b', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 11}'::json, '{"reference_min_duration": 8, "video_point": 2052}'::json, TRUE, NULL, 'c0b2df77-8821-4fb7-b400-043281ef2895', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 12}'::json, '{"reference_min_duration": 8, "video_point": 2160}'::json, TRUE, NULL, '6bff9054-4a50-4932-a5fe-bde036434d25', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 13}'::json, '{"reference_min_duration": 9, "video_point": 2376}'::json, TRUE, NULL, '85b6f720-1dbb-4c00-8174-4ab61cad30ba', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 14}'::json, '{"reference_min_duration": 10, "video_point": 2592}'::json, TRUE, NULL, 'bc6274d5-d075-452d-9374-64bddaac4132', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('34a5fe32-96cb-4005-94dc-8ef36506faf1', 'video_ref_min', '{"video_resolution": "720P", "video_output_duration": 15}'::json, '{"reference_min_duration": 10, "video_point": 2700}'::json, TRUE, NULL, '303e1fbf-f25e-421d-a282-791875a2ebf2', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 4}'::json, '{"reference_min_duration": 3, "video_point": 2363}'::json, TRUE, NULL, 'ac95c533-724a-43ab-b6b1-a01ec11b4134', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 5}'::json, '{"reference_min_duration": 4, "video_point": 3038}'::json, TRUE, NULL, '53dc70cf-3f1a-415e-8e02-8f2f30e03b74', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 6}'::json, '{"reference_min_duration": 4, "video_point": 3375}'::json, TRUE, NULL, '636c5c89-519b-445d-ae78-506712f21435', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 7}'::json, '{"reference_min_duration": 5, "video_point": 4050}'::json, TRUE, NULL, 'a4c2f65a-211d-4e26-8ad9-19bfc8fda759', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 8}'::json, '{"reference_min_duration": 6, "video_point": 4725}'::json, TRUE, NULL, '0210b070-9c8d-4468-9e83-663cbea41596', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 9}'::json, '{"reference_min_duration": 6, "video_point": 5063}'::json, TRUE, NULL, 'abdbaa58-3531-42f2-b346-5c331068e73a', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 10}'::json, '{"reference_min_duration": 7, "video_point": 5738}'::json, TRUE, NULL, 'da9856f1-dce2-4b06-b01c-897a1c074df0', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 11}'::json, '{"reference_min_duration": 8, "video_point": 6413}'::json, TRUE, NULL, '21a11c1a-d012-40d0-aca0-ab9b87b75949', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 12}'::json, '{"reference_min_duration": 8, "video_point": 6750}'::json, TRUE, NULL, '787a2773-bd26-487f-b914-6e69b7571cea', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 13}'::json, '{"reference_min_duration": 9, "video_point": 7452}'::json, TRUE, NULL, '815d6edf-68d1-44e5-8e9a-9ecfcf65fe14', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 14}'::json, '{"reference_min_duration": 10, "video_point": 8100}'::json, TRUE, NULL, 'c302e858-7a42-43dd-9a32-c858118e69d9', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('561df83b-2216-449c-8252-dd29e2acc4a4', 'video_ref_min', '{"video_resolution": "1080P", "video_output_duration": 15}'::json, '{"reference_min_duration": 10, "video_point": 8438}'::json, TRUE, NULL, '7272420a-d301-440d-b07a-0d305bf0ca34', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES (NULL, 'super_res', '{"target_video_resolution": "720P"}'::json, '{"point_per_second": 6}'::json, TRUE, NULL, '24305dbc-7bfa-4449-92e8-e04112b0fa7d', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES (NULL, 'super_res', '{"target_video_resolution": "1080P"}'::json, '{"point_per_second": 12}'::json, TRUE, NULL, '10955e31-64db-49be-b753-585b17ed9de1', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES (NULL, 'super_res', '{"target_video_resolution": "2K"}'::json, '{"point_per_second": 24}'::json, TRUE, NULL, 'aa31d24b-210a-429c-b0bb-0c3f4004c9e1', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "ai_model_pricing" ("model_id", "rule_type", "match_config", "price_config", "is_enabled", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES (NULL, 'super_res', '{"target_video_resolution": "4K"}'::json, '{"point_per_second": 48}'::json, TRUE, NULL, 'edef0da8-3f17-4fc1-ae60-69eb0682a561', NOW(), NULL, NULL, NULL, FALSE, NULL);

-- 表 membership_level（3 条）
INSERT INTO "membership_level" ("name", "level_order", "monthly_price", "monthly_discount_rate", "yearly_price", "yearly_discount_rate", "can_buy_points", "status", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('免费版', 1, 0, NULL, 0, 1.0, FALSE, 1, '0d90cdbf-d7f8-43a0-a6af-aa4c10b269e1', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "membership_level" ("name", "level_order", "monthly_price", "monthly_discount_rate", "yearly_price", "yearly_discount_rate", "can_buy_points", "status", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('专业版', 10, 99, NULL, 599, 1.0, TRUE, 1, 'd460e12f-2cdb-4b9c-b87c-b0ecd1e09aa7', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "membership_level" ("name", "level_order", "monthly_price", "monthly_discount_rate", "yearly_price", "yearly_discount_rate", "can_buy_points", "status", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('企业版', 100, 2999, NULL, 28790, 1.0, TRUE, 1, '465fd379-a455-40da-8ce1-fe1964bcd304', NOW(), NULL, NULL, NULL, FALSE, NULL);

-- 表 membership_level_privilege（3 条）
INSERT INTO "membership_level_privilege" ("level_id", "name", "privilege_key", "privilege_value", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('0d90cdbf-d7f8-43a0-a6af-aa4c10b269e1', NULL, 'monthly_points', '1200', '每月赠送积分', 'b52e6e9d-2f11-44f1-bd17-9a9b641bf8cc', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "membership_level_privilege" ("level_id", "name", "privilege_key", "privilege_value", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('d460e12f-2cdb-4b9c-b87c-b0ecd1e09aa7', NULL, 'monthly_points', '12000', '每月赠送12000积分', 'e7512157-4687-47ae-b785-e0e5885f17c9', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "membership_level_privilege" ("level_id", "name", "privilege_key", "privilege_value", "remark", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES ('465fd379-a455-40da-8ce1-fe1964bcd304', NULL, 'monthly_points', '400000', '每月赠送400000积分', '2a18ad11-b583-43e8-9246-b04ffa678db2', NOW(), NULL, NULL, NULL, FALSE, NULL);

-- 表 point_purchase_plan（5 条）
INSERT INTO "point_purchase_plan" ("point_amount", "original_price", "discount_price", "is_enabled", "sort_order", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES (50, 0.5, 0.5, TRUE, 1, '8479c0c1-8be7-4ec0-9f25-177f37c20f4a', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "point_purchase_plan" ("point_amount", "original_price", "discount_price", "is_enabled", "sort_order", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES (100, 1.0, 1.0, TRUE, 2, 'd6f4b998-7ec5-49d6-a262-4b56c5011b1b', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "point_purchase_plan" ("point_amount", "original_price", "discount_price", "is_enabled", "sort_order", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES (1000, 10.0, 10.0, TRUE, 3, 'b643d3b7-6015-4860-b730-7f2ee79b7dba', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "point_purchase_plan" ("point_amount", "original_price", "discount_price", "is_enabled", "sort_order", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES (5000, 50.0, 50.0, TRUE, 4, '843c1a91-dcd1-439f-a4fb-d21891dd6e9a', NOW(), NULL, NULL, NULL, FALSE, NULL);
INSERT INTO "point_purchase_plan" ("point_amount", "original_price", "discount_price", "is_enabled", "sort_order", "id", "create_time", "create_uid", "update_time", "update_uid", "is_deleted", "delete_time") VALUES (10000, 100.0, 100.0, TRUE, 5, '4f52c393-c997-4008-aa50-fae200011323', NOW(), NULL, NULL, NULL, FALSE, NULL);
COMMIT;
