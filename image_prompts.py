# ============================================================
# ===== НАСТРОЙКИ ГЕНЕРАЦИИ КАРТИНОК (отдельный файл) =====
# ============================================================

# Базовый шаблон промпта с гиперреалистичными лицами
IMAGE_PROMPT_TEMPLATE = (
    "Hyperrealistic cinematic photograph, square 1:1 format, family, parents and children, happy moments, warmth, related to topic: {topic}. "
    "People must be typical Moscow residents: European appearance, fair skin, light brown or blonde hair, European facial features. "
    "Faces must be hyperrealistic: natural skin texture, visible pores, eyelashes, eyebrows, expressive eyes, natural proportions. "
    "No cartoonishness, no grotesque, no distortions. "
    "Modern urban clothing. Action takes place in Moscow: cozy courtyards, parks, streets. "
    "Photorealism, 8K, ultra-detailed, soft natural lighting, warm tones. "
    "No text or inscriptions. "
    "Extreme detail, shallow depth of field, Hasselblad H6D, 100mm lens, f/2.8."
)

# Дополнительные суффиксы для каждого источника (можно менять)
SUFFIX_AGNES = ""
SUFFIX_GIGACHAT = ""
SUFFIX_POLLINATIONS = " hyperrealistic faces, European, Moscow, photorealistic, 8k"

# Параметры для каждого источника
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

# Настройки скачивания
DOWNLOAD_TIMEOUT = 60
DOWNLOAD_RETRIES = 3
DOWNLOAD_DELAY = 2
DOWNLOAD_BACKOFF = 2

# Порядок источников (можно менять местами)
IMAGE_SOURCES = [
    "agnes",
    "gigachat",
    "pollinations"
]

# Таймауты для каждого источника (в секундах)
TIMEOUT_AGNES = 120
TIMEOUT_GIGACHAT = 120
TIMEOUT_POLLINATIONS = 30