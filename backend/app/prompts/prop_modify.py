TEMPLATE_ZH = """你是一个专业的道具资产描述更新专家。

【任务】
根据用户对道具图片的修改，更新道具的视觉描述词。

【道具名称】
{prop_name}

【原始道具描述】
{original_description}

【用户修改指令】
{modify_instruction}

{image_context}

【更新规则】
1. 只描述道具本体的静态视觉信息，不写用途、剧情、角色动作、镜头、背景环境。
2. 优先保留原描述里未被修改的结构、材质、颜色和装饰细节。
3. 如果有参考图片，请吸收参考图中的材质、轮廓、纹样、配色等关键视觉特征。
4. 输出必须适合白底居中的道具资产图生成。
5. 必须明确道具的主体结构、材质、颜色、表面处理、装饰细节和数量关系。
6. 禁止出现人物、手部、桌面、房间、场景、光影氛围、剧情用途等信息。
7. 使用中文输出，长度 40-100 字。

【输出格式】
只返回 JSON，禁止返回任何其他内容。⚠️ 所有引号（""''等）在 JSON 字符串值中必须替换为「」，严禁出现未转义的英文双引号 "：
{{
  "prompt": "更新后的道具视觉描述"
}}"""

TEMPLATE_EN = """You are a prop asset description editor.

Task:
Update the visual prop description based on the user's image-edit instruction.

Prop name:
{prop_name}

Original description:
{original_description}

User instruction:
{modify_instruction}

Reference image context (may be empty):
{image_context}

Rules:
1. Describe only the prop itself. No usage, plot function, character action, camera direction, or scene background.
2. Preserve unchanged structure, material, color, and decorative details unless explicitly modified.
3. If reference images are provided, absorb their material, silhouette, pattern, and color cues.
4. The result must be suitable for an isolated prop asset sheet on a white background.
5. Include the prop's core structure, material, color, surface finish, decorative details, and quantity relationship when relevant.
6. Do not mention people, hands, tables, rooms, environment, atmosphere, or story purpose.
7. Return one concise English visual description.

Output format:
Return JSON only. ⚠️ JSON SAFETY: All quotation marks MUST be converted to corner brackets「」in JSON string values:
{{
  "prompt": "updated prop visual description"
}}"""


def build_prompt(
    prop_name: str,
    original_description: str,
    modify_instruction: str,
    image_context: str = "",
    locale: str = "zh",
) -> str:
    template = TEMPLATE_ZH if locale == "zh" else TEMPLATE_EN
    return template.format(
        prop_name=prop_name,
        original_description=original_description,
        modify_instruction=modify_instruction,
        image_context=image_context,
    )
