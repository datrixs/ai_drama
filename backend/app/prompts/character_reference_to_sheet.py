TEMPLATE_ZH = """# 参考图转角色设定图提示词（图生图模式）

基于提供的参考图片，提取角色的面部五官特征、发型、体型和服装款式作为参考。

## 画风优先级规则

画风由用户选择的风格指令决定，严格遵循风格指令进行生成。
参考图仅用于保持角色身份特征（五官、发型、体型、服装结构），不能覆盖用户指定画风。
仅在未提供风格指令时，才可参考原图画风。

## 生成规则

1. 忽略原图的具体色调和光线
2. 使用自然柔和的摄影棚灯光
3. 绘制正常美观的人体比例
4. 不要复制原图的画质、模糊、噪点或瑕疵
5. 生成的图像必须清晰锐利、细节丰富、专业品质
6. 角色表情应为自然平静的中性表情，目光正视镜头

## 缺失部位自动补齐

如果参考图是半身或部分身体，请根据服装风格和人物特征合理补全未露出的部位：
- **缺少下半身**：根据上衣风格推断并绘制匹配的裤装/裙装
- **缺少脚部**：根据整体穿搭风格添加合适的鞋款
- **缺少手部/手臂**：根据姿态合理补全
- 保持整体风格一致，确保补全的部分与可见部分协调统一"""

TEMPLATE_EN = """# Reference Image To Character Sheet Prompt (img2img)

Use the provided reference image to extract face traits, hairstyle, body shape, and outfit structure.

## Style priority
Follow the user-selected style instruction as the highest-priority rule.
Use reference images only to preserve character identity traits (face, hairstyle, body shape, outfit structure), and do not let reference style override the requested style.
Only if no explicit style instruction is provided, you may preserve the original visual style.

## Generation rules
1. Ignore the original image color cast and lighting defects
2. Use clean, soft studio lighting
3. Keep natural, aesthetically correct body proportions
4. Do not copy blur, noise, compression artifacts, or defects
5. Output must be clear, sharp, and production-quality
6. Character expression should be neutral and calm, looking at camera

## Missing-part completion
If only half body or partial body is visible, infer and complete hidden parts consistently:
- Infer matching lower-body clothing
- Infer suitable footwear
- Infer missing hands/arms in a natural way"""


def build_prompt(locale: str = "zh") -> str:
    return TEMPLATE_ZH if locale == "zh" else TEMPLATE_EN
