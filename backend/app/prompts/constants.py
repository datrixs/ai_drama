ART_STYLES = {
    "american-comic": {
        "label": "漫画风",
        "prompt_zh": "高质量漫画风格，清晰的墨线勾边，鲜明的平涂上色，适度夸张的人物表情和动态，卡通渲染质感，简洁干净的画面，2D漫画插画风格。禁止3D渲染，禁止写实纹理，禁止复杂渐变阴影；",
        "prompt_en": "High-quality comic style, clean ink outlines, vivid flat coloring, moderately exaggerated expressions and dynamics, cartoon rendering, clean and simple composition, 2D comic illustration style, no 3D rendering, no realistic textures, no complex gradient shadows.",
    },
    "chinese-comic": {
        "label": "精致国漫",
        "prompt_zh": "现代精致国漫风格，细腻工笔线条，东方美学色彩搭配，柔和渐变上色，精致的服饰和发饰细节，华丽唯美的画面氛围，高饱和度通透色彩，2D动漫渲染，超清画质。禁止日系赛璐璐风格，禁止欧美卡通比例，禁止低饱和度灰调；",
        "prompt_en": "Modern premium Chinese comic style, delicate gongbi line art, Eastern aesthetic color palette, soft gradient coloring, intricate costume and accessory details, gorgeous and elegant atmosphere, high saturation translucent colors, 2D anime rendering, ultra-clear quality, no Japanese cel-shading style, no Western cartoon proportions, no low-saturation gray tones.",
    },
    "japanese-anime": {
        "label": "日系动漫风",
        "prompt_zh": "现代日系动漫风格，赛璐璐平涂上色，干净利落的线条勾勒，柔和明亮的色彩，精致的五官刻画，日式动漫角色比例，萌系或帅气风格，高质量2D动画画质，视觉小说CG质感。禁止写实渲染，禁止国漫工笔线条，禁止欧美卡通风格；",
        "prompt_en": "Japanese anime style, cel-shaded flat coloring, clean crisp line art, soft bright color palette, refined facial features, anime character proportions, moe or bishounen style, high-quality 2D animation quality, visual novel CG aesthetics, no realistic rendering, no Chinese comic gongbi line art, no Western cartoon style.",
    },
    "realistic": {
        "label": "真人风格",
        # "prompt_zh": "真实摄影照片风格，电影级画面质感，真实人物面孔，真实皮肤纹理和毛孔细节，自然光影效果，非动漫非卡通非插画风格，照片级真实感，真人演员形象，色彩饱满通透，画面干净精致，高分辨率人像摄影",
        "prompt_zh": "真实摄影照片风格，电影级画面质感，照片级真实感，真实材质纹理细节，自然光影效果，真实物理环境，色彩饱满通透，画面干净精致，非动漫非卡通非插画风格，所有人物必须是真实真人形象，高分辨率摄影，场景必须呈现真实建筑材质、自然植被、真实天气和光线，整体效果如同实景拍摄的电影剧照。严禁任何2D渲染，严禁动漫化、卡通化、插画风格处理，严禁非真实人物比例",
        "prompt_en": "Photorealistic cinematic style, photo-realistic, authentic material and texture details, natural lighting and shadows, realistic physical environment, rich transparent colors, clean and refined image quality, NOT anime NOT cartoon NOT illustration, all human figures must be realistic real people, high-resolution photography, scenes must depict real architectural materials, natural vegetation, realistic weather and lighting, like a live-action film still, absolutely no 2D rendering, strictly no anime, cartoon, or illustration style treatment, strictly no non-realistic human proportions.",
    },
}

VALID_ART_STYLES = list(ART_STYLES.keys())

CHARACTER_PROMPT_SUFFIX = (
    "角色设定图，画面分为左右两个区域：【左侧区域】占约1/3宽度，是角色的正面特写"
    "（如果是人类则展示完整正脸，如果是动物/生物则展示最具辨识度的正面形态）；"
    "【右侧区域】占约2/3宽度，是角色三视图横向排列"
    "（从左到右依次为：正面全身、侧面全身、背面全身），三视图高度一致。"
    "纯白色背景，无其他元素。"
    # "角色单人肖像，正面或四分之三侧面，完整呈现发型与服装，纯色简洁背景，高画质。"
)

CHARACTER_ASSET_IMAGE_RATIO = "3:2"

LOCATION_PROMPT_SUFFIX = "必须使用宽广完整的场景全景构图，清楚展示主要结构、前景/中景/背景和空间边界，空场景无人，广角全景，完整呈现空间布局与光影氛围，高画质"
# LOCATION_PROMPT_SUFFIX = "空场景无人，广角全景，完整呈现空间布局与光影氛围，高画质"

PROP_PROMPT_SUFFIX = (
    "道具设定图，画面分为左右两个区域：【左侧区域】占约1/3宽度，是道具主体的主视图特写；"
    "【右侧区域】占约2/3宽度，是同一道具的三视图横向排列"
    "（从左到右依次为：正面、侧面、背面），三视图高度一致。"
    "纯白色背景，主体居中完整展示，无人物、无手部、无桌面陈设、无环境背景、无其他元素。"
    # "道具特写，纯色背景，高画质"
)

LOCATION_ASSET_IMAGE_RATIO = "1:1"
PROP_ASSET_IMAGE_RATIO = "3:2"


def get_art_style_prompt(art_style: str, locale: str = "zh") -> str:
    style = ART_STYLES.get(art_style)
    if not style:
        return ""
    return style["prompt_zh"] if locale == "zh" else style.get("prompt_en", style["prompt_zh"])


def add_character_prompt_suffix(prompt: str) -> str:
    if CHARACTER_PROMPT_SUFFIX in prompt:
        return prompt
    return f"{prompt}，{CHARACTER_PROMPT_SUFFIX}"


def add_location_prompt_suffix(prompt: str) -> str:
    if LOCATION_PROMPT_SUFFIX in prompt:
        return prompt
    return f"{prompt}，{LOCATION_PROMPT_SUFFIX}"


def add_prop_prompt_suffix(prompt: str) -> str:
    if PROP_PROMPT_SUFFIX in prompt:
        return prompt
    return f"{prompt}，{PROP_PROMPT_SUFFIX}"


def normalize_image_generation_count(count: int | None, default: int = 3, min_val: int = 1, max_val: int = 6) -> int:
    from app.core.config import settings
    default = settings.IMAGE_GENERATION_COUNT_DEFAULT or default
    max_val = settings.IMAGE_GENERATION_COUNT_MAX or max_val
    if count is None or count < min_val:
        return default
    return min(count, max_val)
