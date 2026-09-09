TEMPLATE_ZH = """你是一个专业的场景描述更新专家。

【任务】
根据用户对场景图片的修改，更新场景的描述词。

【场景名称】
{location_name}

【原始场景描述】
{original_description}

【用户修改指令】
{modify_instruction}

{image_context}

【更新规则】
1. **开头必须明确写明场景名称**：
   - 描述开头必须以「{location_name}」的形式标注空间属性
   - 示例：「皇宫」殿内铺设着... / 「客厅」窗外阳光透过...
   - 这样AI在生成图片时能明确理解这是什么类型的空间

2. 仔细理解用户的修改指令，找出需要修改的具体特征
3. 如果有参考图片，请识别参考图片中的关键视觉特征（如建筑风格、装饰元素、光线氛围、色调等）
4. 将修改内容准确融入原始描述中，替换或补充相关部分
5. 保持描述的流畅性和一致性
6. 保留未被修改的原有特征
7. 遵循以下描述规范：
   - 只描述场景本身，禁止描述人物
   - 使用中文输出，长度 80-140 字
   - 必须让空间结构、关键锚点、前后层次具体可见，不能退化成泛场景描述
   - 若用户修改后引入新的关键锚点或删掉旧锚点，描述必须同步更新
8. 同时重新生成 2-6 个固定可站位置，且必须与更新后的场景描述一致
9. 每个可站位置必须是一条完整的位置描述短语，不是短词，不是对象
10. 可站位置中禁止写人物姿态、动作、情绪，只写位置
11. 可站位置里提到的关键锚点必须在更新后的场景描述中明确出现

【输出格式】
只返回JSON格式，禁止返回任何其他内容。⚠️ 所有引号（""''等）在 JSON 字符串值中必须替换为「」，严禁出现未转义的英文双引号 "：
{{
  "prompt": "「场景名」更新后的完整场景描述",
  "available_slots":[
    "教室后排靠窗那组课桌外侧的位置",
    "讲台前方黑板正下方的位置"
  ]
}}"""

TEMPLATE_EN = """You are a scene description editor.
Update the original location description based on user instruction.

Location name:
{location_name}

Original description:
{original_description}

User instruction:
{modify_instruction}

Reference image context (may be empty):
{image_context}

Rules:
1. Keep unchanged scene elements unless explicitly modified.
2. Return one complete updated description in English.
3. Keep scene name at the beginning: "[{location_name}] ..."
4. No protagonist actions or story narration.
5. Keep the scene spatially specific, with visible structure, depth, and stable anchors.
6. Also regenerate 2-6 `available_slots` that match the updated scene.
7. Each `available_slots` item must be one complete descriptive placement phrase, not a short token and not an object.
8. Do not mention posture, action, or emotion in `available_slots`.
9. Every anchor mentioned in `available_slots` must also appear clearly in the updated scene description.

Output format:
Return JSON only. ⚠️ JSON SAFETY: All quotation marks MUST be converted to corner brackets「」in JSON string values:
{{
  "prompt": "updated location description",
  "available_slots": [
    "the outer-side position beside the rear window desks",
    "the open floor directly below the center of the blackboard"
  ]
}}"""


def build_prompt(
    location_name: str,
    original_description: str,
    modify_instruction: str,
    image_context: str = "",
    locale: str = "zh",
) -> str:
    template = TEMPLATE_ZH if locale == "zh" else TEMPLATE_EN
    return template.format(
        location_name=location_name,
        original_description=original_description,
        modify_instruction=modify_instruction,
        image_context=image_context,
    )
