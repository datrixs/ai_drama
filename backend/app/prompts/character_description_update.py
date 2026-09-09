TEMPLATE_ZH = """你是一个专业的角色形象描述更新专家。

【任务】
根据用户对角色图片的修改，更新角色的形象描述词。

【原始角色描述】
{original_description}

【用户修改指令】
{modify_instruction}

{image_context}

【更新规则】
1. 仔细理解用户的修改指令，找出需要修改的具体特征
2. 如果有参考图片，请识别参考图片中的关键视觉特征（如服装款式、颜色、材质、配饰等）
3. 将修改内容准确融入原始描述中，替换或补充相关部分
4. 保持描述的流畅性和一致性
5. 保留未被修改的原有特征
6. 遵循以下描述规范：
   - 禁止写表情、姿态、动作
   - 禁止写背景/环境/道具
   - 禁止描写身体部位颜色（皮肤色、唇色、眼睛颜色等）
   - 使用中文输出，长度 80-150 字

【输出格式】
只返回JSON格式，禁止返回任何其他内容。⚠️ 所有引号（""''等）在 JSON 字符串值中必须替换为「」，严禁出现未转义的英文双引号 "：
{{
  "prompt": "更新后的完整角色描述"
}}"""

TEMPLATE_EN = """You are a character appearance prompt editor.
Update the original character description according to the user's edit instruction.

Original description:
{original_description}

User instruction:
{modify_instruction}

Reference image context (may be empty):
{image_context}

Rules:
1. Keep unchanged traits unless user explicitly asks to change them.
2. Merge requested changes into a single complete prompt.
3. Output in English only.
4. No expression, action, background, or props.
5. No skin color, eye color, or lip color.

Output format:
Return JSON only. ⚠️ JSON SAFETY: All quotation marks MUST be converted to corner brackets「」in JSON string values:
{{
  "prompt": "updated full character description"
}}"""


def build_prompt(
    original_description: str,
    modify_instruction: str,
    image_context: str = "",
    locale: str = "zh",
) -> str:
    template = TEMPLATE_ZH if locale == "zh" else TEMPLATE_EN
    return template.format(
        original_description=original_description,
        modify_instruction=modify_instruction,
        image_context=image_context,
    )
