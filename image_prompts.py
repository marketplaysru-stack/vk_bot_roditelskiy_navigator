# ============================================================
# ===== УЛУЧШЕННЫЕ НАСТРОЙКИ ГЕНЕРАЦИИ КАРТИНОК =====
# ============================================================

import random

# ============================================================
# ===== БАЗОВЫЙ ШАБЛОН С ГИПЕРРЕАЛИСТИЧНЫМИ ЛИЦАМИ =====
# ============================================================

# Основной промпт с акцентом на фотореализм, свет, текстуры, эмоции
IMAGE_PROMPT_TEMPLATE = (
    "Hyperrealistic cinematic photograph, square 1:1 format, family scene: {topic}. "
    "People: typical Moscow residents, European appearance, fair skin, light brown or blonde hair. "
    "Faces hyperrealistic: natural skin texture, visible pores, fine wrinkles, individual eyelashes, expressive eyes with natural reflections, subtle facial expressions. "
    "No cartoonishness, no grotesque, no distortions. "
    "Natural skin, realistic eyes, genuine emotions (joy, tenderness, surprise, warmth). "
    "Clothing modern, urban, suitable for Moscow: casual, stylish, comfortable. "
    "Setting: Moscow — cozy courtyard with birch trees, modern apartment with large windows, or a sunny park with children's playground. "
    "Photorealism, 8K, ultra-detailed, shallow depth of field (f/2.8), natural soft lighting, warm golden hour tones or soft overcast light. "
    "No text, no inscriptions. "
    "Professional photography style: Hasselblad H6D, 100mm lens, natural bokeh, film grain, fine textures."
)

# ============================================================
# ===== ДОПОЛНИТЕЛЬНЫЕ ВАРИАНТЫ ДЛЯ РАЗНООБРАЗИЯ =====
# ============================================================

# Варианты ракурсов (выбирается случайно)
ANGLES = [
    "medium close-up",
    "extreme close-up on faces",
    "wide shot with family",
    "over-the-shoulder view",
    "low angle looking up",
    "eye-level perspective",
    "profile view",
    "three-quarter view"
]

# Варианты освещения
LIGHTING_STYLES = [
    "warm golden hour sunlight streaming through windows",
    "soft overcast daylight with gentle shadows",
    "dramatic cinematic lighting with high contrast",
    "natural window light, soft and diffused",
    "sunset glow with long shadows",
    "indoor warm lamp light combined with cool daylight from window"
]

# Варианты настроения и эмоций
MOODS = [
    "joyful, genuine laughter, happy family moment",
    "tender, loving, warm embrace between parent and child",
    "surprised, amazed, delighted expression",
    "calm, peaceful, relaxed family time",
    "playful, fun, energetic interaction",
    "focused, attentive, engaged in activity"
]

# Варианты фонов
BACKGROUNDS = [
    "Moscow courtyard with birch trees and children's playground",
    "bright modern apartment with panoramic windows",
    "green park with benches and walking paths",
    "cozy kitchen with family having breakfast",
    "bookstore or library corner",
    "snowy Moscow street with festive lights (winter)"
]

# Суффиксы для каждого источника
SUFFIX_AGNES = ""
SUFFIX_GIGACHAT = ""
SUFFIX_POLLINATIONS = " hyperrealistic faces, European, Moscow, photorealistic, 8k, detailed skin, natural light"

# ============================================================
# ===== ФУНКЦИЯ ДЛЯ ГЕНЕРАЦИИ РАЗНООБРАЗНОГО ПРОМПТА =====
# ============================================================

def build_image_prompt(topic):
    """
    Генерирует промпт с случайными вариациями для разнообразия картинок.
    """
    angle = random.choice(ANGLES)
    lighting = random.choice(LIGHTING_STYLES)
    mood = random.choice(MOODS)
    background = random.choice(BACKGROUNDS)

    prompt = (
        f"Hyperrealistic cinematic photograph, square 1:1 format, family scene related to: {topic}. "
        f"{mood}. "
        f"People: typical Moscow residents, European appearance, fair skin, light brown or blonde hair, realistic facial features. "
        f"Faces hyperrealistic: natural skin texture, visible pores, fine wrinkles, individual eyelashes, "
        f"expressive eyes with natural reflections, genuine emotions (joy, tenderness, surprise). "
        f"No cartoonishness, no grotesque, no distortions. "
        f"Natural skin, realistic eyes. "
        f"Clothing modern, urban, suitable for Moscow: casual, stylish, comfortable. "
        f"Setting: {background}. "
        f"Camera angle: {angle}. Lighting: {lighting}. "
        f"Photorealism, 8K, ultra-detailed, shallow depth of field (f/2.8), "
        f"soft natural lighting, warm golden hour tones or soft overcast light. "
        f"No text, no inscriptions. "
        f"Professional photography style: Hasselblad H6D, 100mm lens, natural bokeh, film grain, fine textures."
    )
    return prompt

# ============================================================
# ===== ТЕХНИЧЕСКИЕ ПАРАМЕТРЫ =====
# ============================================================

AGNES_IMAGE_PARAMS = {
    "model": "agnes-image-2.1-flash",
    "size": "1024x1024",
    "n": 1
}

GIGACHAT_IMAGE_PARAMS = {
    "model": "GigaChat-Image",
    "size": "1024x1024",
    "n": 1
}

POLLINATIONS_IMAGE_PARAMS = {
    "width": 1024,
    "height": 1024,
    "nologo": True
}

# Порядок источников (можно менять местами)
IMAGE_SOURCES = [
    "agnes",
    "gigachat",
    "pollinations"
]

# Таймауты для каждого источника (сек)
TIMEOUT_AGNES = 120
TIMEOUT_GIGACHAT = 120
TIMEOUT_POLLINATIONS = 30

# Настройки скачивания
DOWNLOAD_TIMEOUT = 60
DOWNLOAD_RETRIES = 3
DOWNLOAD_DELAY = 2
DOWNLOAD_BACKOFF = 2