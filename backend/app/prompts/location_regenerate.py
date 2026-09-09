TEMPLATE_ZH = """你是"场景重塑师"。请根据当前的场景描述，为指定场景重新生成 3 条全新的场景描述变体。

【场景信息】
- 场景名：{location_name}
- 当前描述（作为参考，需要生成不同的变体）：
{current_descriptions}

【生成要求】
1. **开头必须明确写明场景名称**：
   - 每条描述开头必须以「{location_name}」的形式标注空间属性
   - 示例：「皇宫」殿内铺设着... / 「客厅」窗外阳光透过...
   - 这样AI在生成图片时能明确理解这是什么类型的空间

2. 根据当前描述的核心元素，生成 3 条各有特色、互不相同的场景描述变体
3. 必须与当前描述有明显差异（换一种氛围/布局/细节），但保持场景核心特征
4. 描述内容应包含：
   - 空间结构：整体布局、空间大小、层次感
   - 建筑/地形：建筑风格、地形特征、主要构造物
   - 光影氛围：光源类型、明暗对比、色调倾向
   - 材质细节：地面、墙面、物体的材质质感
   - 环境元素：植物、天气、装饰物等
   - 独特标识：该场景的标志性元素或特殊物件
   - 至少 3 个可供后续固定人物位置的稳定锚点或区域
   - 每个锚点周边可落位的空白区域

5. 描述规范：
   - 禁止写主角人物具体动作、剧情
   - 【人群处理规则】如果当前描述中包含人群元素，新描述也应保持人群元素
     * 可以调整人群的位置、密度、状态，但保持有人群存在
     * 人群描述使用模糊词汇："人群"、"宾客"、"路人"等
   - 使用中文输出，长度 80-150 字
   - 不包含艺术风格、画风描述（系统自动添加）
   - 【年代一致性】根据场景特征判断年代，建筑、装饰、物品必须符合该年代特征
   - 【时间一致性】如场景名包含"白天/黑夜/黄昏"等，描述中的光影必须匹配

6. 额外输出 2-6 个固定可站位置：
   - 与该场景的共通构图一致
   - 每个站位必须是一条完整的位置描述短语，不是短词，不是对象
   - 依附于明确场景锚物或区域
   - 禁止抽象站位
   - 禁止写人物姿态、动作、情绪
   - 站位中提到的锚点必须在三条 descriptions 中都成立

【输出格式】只返回以下 JSON，不要任何其他内容。⚠️ 所有引号（""''等）在 JSON 字符串值中必须替换为「」，严禁出现未转义的英文双引号 "。
{{
  "descriptions": [
    "「场景名」新描述1（80-150字）",
    "「场景名」新描述2（80-150字）",
    "「场景名」新描述3（80-150字）"
  ],
  "available_slots": [
    "皇宫正中龙椅前方台阶下的位置",
    "右后方殿门内侧靠墙的位置"
  ]
}}"""

TEMPLATE_EN = """You are a scene variant regenerator.
Generate 3 new scene description variants for the same location.

Location name:
{location_name}

Current descriptions (reference):
{current_descriptions}

Requirements:
1. Generate 3 clearly different but same-location variants.
2. Keep the scene name prefix in each line: "[{location_name}] ..."
3. Output in English only.
4. Keep environment-only description (no protagonist actions).
5. Keep each variant specific enough for controllable image generation, with visible structure, depth, and stable anchors.
6. Also generate 2-6 shared `available_slots` for this location.
7. Each `available_slots` item must be one complete descriptive placement phrase, not a short token and not an object.
8. Do not mention posture, action, or emotion in `available_slots`.
9. Every anchor mentioned in `available_slots` must remain valid across all three regenerated descriptions.

Output format:
Return JSON only. ⚠️ JSON SAFETY: All quotation marks MUST be converted to corner brackets「」in JSON string values:
{{
  "descriptions": [
    "[{location_name}] variant 1",
    "[{location_name}] variant 2",
    "[{location_name}] variant 3"
  ],
  "available_slots": [
    "the position beneath the throne steps at the center of the hall",
    "the position against the inner wall beside the rear doorway"
  ]
}}"""


def build_prompt(
    location_name: str,
    current_descriptions: str,
    locale: str = "zh",
) -> str:
    template = TEMPLATE_ZH if locale == "zh" else TEMPLATE_EN
    return template.format(
        location_name=location_name,
        current_descriptions=current_descriptions,
    )
