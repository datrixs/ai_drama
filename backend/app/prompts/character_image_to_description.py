TEMPLATE_ZH = """# 图片反推角色描述提示词

请分析这张角色图片，生成一段详细的角色外貌描述（用于 AI 图片生成）。

## 输出要求

生成一段完整的角色视觉描述，包含以下要素：

1. 性别和年龄段（如：约二十五岁的男性）
2. 发型发色（如：黑色短发、微卷的棕色长发）
3. 脸型五官特征（如：剑眉星目、高鼻梁、薄唇）
4. 体态身材（如：身形修长、体格健壮）
5. 服装风格（如：深蓝色西装、白色衬衫、皮质腰带）
6. 配饰特征（如：左手戴银色手表、胸前别金色胸针）
7. 整体气质关键词（如：精英气质、禁欲系、高冷、温柔暖男）

## 缺失内容补齐规则

如果参考图只展示了部分身体（如上半身、头像），请根据已有信息合理推断并补全：
- **缺少下半身**：根据上衣风格推断裤装/裙装类型（如西装上衣配深蓝色西裤、休闲上衣配牛仔裤）
- **缺少鞋子**：根据整体穿搭风格推断鞋款（如正装配皮鞋、休闲装配运动鞋或帆布鞋）
- **缺少配饰细节**：根据角色气质合理添加配饰（如商务风配手表、休闲风配手环）

## 禁止描写

- 皮肤颜色
- 眼睛颜色
- 表情
- 动作
- 背景
- 姿势

## 输出格式

一段连贯的描述文字，约200-300字，直接可用于图片生成提示词。
只返回描述文字，不要有任何标题、序号或其他格式。"""

TEMPLATE_EN = """# Character Image To Description Prompt

Analyze the provided character image and write one detailed English visual description for image generation.

## Required content
Include all of the following:
1. Gender and approximate age range
2. Hair style and hair color
3. Face shape and facial features
4. Body build and silhouette
5. Clothing style and clothing details
6. Accessories and signature details
7. Overall style keywords

## Missing-part completion
If the image only shows part of the body, infer the missing parts consistently.
- Missing lower body: infer matching pants/skirt style
- Missing shoes: infer shoes that fit the outfit
- Missing accessory details: infer a few reasonable accessories

## Forbidden content
Do not mention:
- Skin color
- Eye color
- Facial expression
- Pose or action
- Background

## Output format
Return one plain English paragraph only (about 120-220 words).
Do not return markdown, bullets, titles, or JSON."""


def build_prompt(locale: str = "zh") -> str:
    return TEMPLATE_ZH if locale == "zh" else TEMPLATE_EN
