# ===== image_prompts.py для родительского бота (улучшенный) =====
import random

# ===== БАЗОВЫЙ ПРОМПТ =====
BASE_PROMPT = (
    "Hyperrealistic cinematic photograph, square 1:1 format, ultra-detailed, 8K, macro and micro details. "
    "Scene: family moment related to '{topic}'. "
    "People: typical Moscow residents, European appearance, fair skin, light brown or blonde hair. "
    "Faces hyperrealistic: visible pores, fine wrinkles, individual eyelashes, expressive eyes with natural reflections, subtle skin texture. "
    "Hands and fingers: anatomically correct, natural proportions, realistic skin folds and knuckles, no extra fingers, no distortions. "
    "Clothing: modern, casual, with natural fabric textures (wool, cotton, denim) and visible seams, folds, creases. "
    "Environment: Moscow setting with authentic details. "
    "Lighting: soft natural light, golden hour or overcast, with dramatic shadows and highlights enhancing depth. "
    "Include subtle graphic elements: stylized icons, geometric shapes, abstract patterns, arrows, badges, or minimalist logos integrated harmoniously into the composition (as watermarks, overlays, or foreground/background elements) – but NO TEXT, NO TYPOGRAPHY, NO LETTERS, NO NUMBERS. "
    "Add extreme macro details: dew drops on leaves, individual dust particles in light beams, fine hair strands, fabric threads, skin micro-texture, reflections in eyes, lens flares, bokeh effects. "
    "Professional photography style: Hasselblad H6D, 100mm macro lens, f/2.8, shallow depth of field, focus on the main subject, natural film grain, no CGI, no plastic look."
)

# ===== ВАРИАНТЫ ДЛЯ РАЗНООБРАЗИЯ =====
ANGLES = [
    "extreme close-up on faces",
    "medium close-up with hands visible",
    "wide shot with family",
    "over-the-shoulder view",
    "low angle looking up",
    "eye-level perspective",
    "profile view",
    "three-quarter view"
]

LIGHTING_STYLES = [
    "warm golden hour sunlight streaming through windows, creating long shadows and highlights",
    "soft overcast daylight with gentle shadows and diffused light",
    "dramatic cinematic lighting with high contrast and rim lights",
    "natural window light, soft and diffused, with window reflections",
    "sunset glow with warm orange and pink hues",
    "indoor warm lamp light combined with cool daylight from window"
]

MOODS = [
    "joyful, genuine laughter, happy family moment",
    "tender, loving, warm embrace between parent and child",
    "surprised, amazed, delighted expression",
    "calm, peaceful, relaxed family time",
    "playful, fun, energetic interaction",
    "focused, attentive, engaged in activity"
]

BACKGROUNDS = [
    "Moscow courtyard with birch trees and children's playground, soft bokeh",
    "bright modern apartment with panoramic windows and city view",
    "green park with benches and walking paths, sun-dappled",
    "cozy kitchen with family having breakfast, rustic details",
    "bookstore or library corner, warm lighting",
    "snowy Moscow street with festive lights, winter atmosphere"
]

# ===== ФУНКЦИЯ ГЕНЕРАЦИИ ПРОМПТА =====
def build_image_prompt(topic):
    angle = random.choice(ANGLES)
    lighting = random.choice(LIGHTING_STYLES)
    mood = random.choice(MOODS)
    background = random.choice(BACKGROUNDS)

    # Дополнительный текст для борьбы с одинаковыми лицами и мультяшностью
    extra = (
        " IMPORTANT: The image must contain diverse individuals – different ages, genders, and appearances. "
        "Avoid identical faces or clones. Each person should look unique and realistic. "
        "Faces should be natural, not exaggerated. No cartoonish or stylized art style. Photorealism only. "
        "No plastic skin, no airbrushing. Include subtle imperfections: freckles, moles, uneven skin tone. "
        "Clothing should have realistic folds and texture."
    )

    prompt = BASE_PROMPT.format(topic=topic) + (
        f" Camera angle: {angle}. "
        f"Lighting: {lighting}. "
        f"Mood: {mood}. "
        f"Background: {background}. "
        "Include graphic overlays: subtle icons, arrows, or abstract shapes to enhance visual appeal, but strictly NO TEXT. "
        "Ensure perfect anatomy: realistic hands, natural finger positions, no extra limbs, correct proportions. "
        "Add micro-details: dew drops, dust particles, individual hair strands, skin pores, fabric textures, eye reflections. "
        "Ensure diversity: no two people look alike. "
        "PHOTOREALISTIC, NOT CARTOON. "
        "Make faces realistic with subtle imperfections. "
        "No plastic skin, no airbrushing. "
        "Clothing should have realistic folds and texture. "
    ) + extra
    return prompt

# ===== ТЕХНИЧЕСКИЕ ПАРАМЕТРЫ =====
AGNES_IMAGE_PARAMS = {
    "model": "agnes-image-2.1-flash",
    "size": "1536x1536",
    "n": 1
}

GIGACHAT_IMAGE_PARAMS = {
    "model": "GigaChat-Image",
    "size": "1536x1536",
    "n": 1
}

POLLINATIONS_IMAGE_PARAMS = {
    "width": 1536,
    "height": 1536,
    "nologo": True
}

TIMEOUT_AGNES = 180
TIMEOUT_GIGACHAT = 180
TIMEOUT_POLLINATIONS = 60
DOWNLOAD_TIMEOUT = 90
DOWNLOAD_RETRIES = 4
DOWNLOAD_DELAY = 2
DOWNLOAD_BACKOFF = 2

SUFFIX_AGNES = ""
SUFFIX_GIGACHAT = ""
SUFFIX_POLLINATIONS = " hyperrealistic, extreme detail, no text, diverse faces, photorealistic"