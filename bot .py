import sys
import os
import requests
import json
import time

# ===== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (те же, что и в боте) =====
BOT_TOKEN = os.getenv("BOT_TOKEN_NEW")
VK_TOKEN = os.getenv("VK_TOKEN_PARENT")
VK_GROUP_ID = os.getenv("VK_GROUP_ID_PARENT")
AGNES_API_KEY = os.getenv("AGNES_API_KEY")
PORT = int(os.getenv("PORT", 8081))

if not BOT_TOKEN or not VK_TOKEN or not VK_GROUP_ID or not AGNES_API_KEY:
    print("❌ Ошибка: не все переменные окружения заданы")
    sys.exit(1)

def log(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}")

log("🚀 Тестовый запуск: публикация одного поста")

# ===== 1. ГЕНЕРАЦИЯ ТЕКСТА =====
log("🔤 Генерация текста...")
system_prompt = (
    "Ты — эксперт в области воспитания детей, семейной психологии, образования и здорового развития. "
    "Напиши полезный, тёплый и поддерживающий пост для родителей на тему: 'Семейная прогулка в Москве'. "
    "Структура: 70% полезный контент, 20% примеры/обсуждение, 10% вопрос к аудитории. "
    "Используй эмодзи, разделители. В конце добавь 5 хештегов."
)
user_prompt = "Тема: Семейная прогулка в Москве"
headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
data = {
    "model": "agnes-2.0-flash",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    "temperature": 0.85
}

try:
    response = requests.post(
        "https://apihub.agnes-ai.com/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=30
    )
    if response.status_code == 200:
        result = response.json()
        post_text = result["choices"][0]["message"]["content"]
        log(f"✅ Текст получен, длина {len(post_text)}")
    else:
        log(f"❌ Ошибка генерации текста: {response.status_code}")
        post_text = "❓ Семейная прогулка в Москве\n\nПоделитесь своим опытом в комментариях! 👇\n\n#родительство #дети #семья #воспитание #советы"
except Exception as e:
    log(f"❌ Исключение при генерации текста: {e}")
    post_text = "❓ Семейная прогулка в Москве\n\nПоделитесь своим опытом в комментариях! 👇\n\n#родительство #дети #семья #воспитание #советы"

# ===== 2. ГЕНЕРАЦИЯ КАРТИНКИ =====
log("🖼️ Генерация картинки...")
prompt = (
    "Hyperrealistic cinematic photograph, square 1:1 format, family, parents and children, happy moments, warmth, "
    "Семейная прогулка в Москве. "
    "People should look like typical Moscow residents: European appearance, fair skin, light brown or blonde hair, European facial features. "
    "Faces must be hyperrealistic, with natural skin texture, visible pores, eyelashes, eyebrows, expressive eyes, natural proportions. "
    "No cartoonishness, no grotesque, no distortions. "
    "Clothing modern, urban. Action takes place in Moscow: cozy courtyards, parks, streets. "
    "Photorealism, 8K, ultra-detailed image, soft natural lighting, warm tones. "
    "No text or inscriptions. "
    "Extreme detail, shallow depth of field, professional photography, Hasselblad H6D, 100mm lens, f/2.8."
)

headers_img = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
data_img = {
    "model": "agnes-image-2.1-flash",
    "prompt": prompt,
    "size": "1024x1024",
    "n": 1
}

image_bytes = None
try:
    response_img = requests.post(
        "https://apihub.agnes-ai.com/v1/images/generations",
        headers=headers_img,
        json=data_img,
        timeout=45
    )
    if response_img.status_code == 200:
        img_json = response_img.json()
        if img_json.get("data") and len(img_json["data"]) > 0:
            img_url = img_json["data"][0]["url"]
            log(f"✅ URL картинки: {img_url[:60]}...")
            # Скачиваем картинку
            resp_dl = requests.get(img_url, timeout=30)
            if resp_dl.status_code == 200:
                image_bytes = resp_dl.content
                log(f"✅ Картинка скачана, размер {len(image_bytes)} байт")
            else:
                log(f"❌ Не удалось скачать картинку: {resp_dl.status_code}")
        else:
            log("❌ Пустой ответ от Agnes")
    else:
        log(f"❌ Ошибка генерации картинки: {response_img.status_code}")
except Exception as e:
    log(f"❌ Исключение при генерации картинки: {e}")

# ===== 3. ПУБЛИКАЦИЯ В VK =====
log("📤 Публикация в VK...")
group_id = int(VK_GROUP_ID)

def vk_api_request(method, params, token, retries=2):
    base_url = "https://api.vk.com/method/"
    params = params.copy()
    params["access_token"] = token
    params["v"] = "5.131"
    post_methods = ["wall.post", "wall.getById", "photos.saveWallPhoto"]
    use_post = method in post_methods
    for attempt in range(retries):
        try:
            if use_post:
                response = requests.post(base_url + method, data=params, timeout=30)
            else:
                response = requests.get(base_url + method, params=params, timeout=30)
            if response.status_code != 200:
                log(f"   ⚠️ HTTP {response.status_code}, попытка {attempt+1}/{retries}")
                continue
            json_resp = response.json()
            if "error" in json_resp:
                log(f"   ⚠️ VK ошибка: {json_resp['error']['error_msg']}, попытка {attempt+1}/{retries}")
                continue
            return json_resp["response"]
        except Exception as e:
            log(f"   ⚠️ Исключение VK: {e}, попытка {attempt+1}/{retries}")
            time.sleep(1)
    log(f"   ❌ VK API {method} не удался после {retries} попыток")
    return None

if image_bytes is None:
    log("   Публикация без фото")
    result = vk_api_request("wall.post", {"owner_id": group_id, "message": post_text, "from_group": 1}, token=VK_TOKEN, retries=2)
    if result:
        log(f"✅ Пост опубликован (без фото), ID: {result.get('post_id')}")
    else:
        log("❌ Ошибка публикации текста")
else:
    log("   Публикация с фото")
    # Получение upload_url
    upload_resp = vk_api_request("photos.getWallUploadServer", {"group_id": abs(group_id)}, token=VK_TOKEN, retries=2)
    if not upload_resp:
        log("❌ Не удалось получить upload_url")
        sys.exit(1)
    upload_url = upload_resp["upload_url"]

    # Загрузка фото
    files = {"photo": ("image.jpg", image_bytes, "image/jpeg")}
    resp = requests.post(upload_url, files=files, timeout=30)
    if resp.status_code != 200:
        log(f"❌ Ошибка загрузки фото: {resp.status_code}")
        sys.exit(1)
    data = resp.json()
    if data.get("error"):
        log(f"❌ Ошибка загрузки: {data['error']}")
        sys.exit(1)
    if not all(k in data for k in ("server", "photo", "hash")):
        log(f"❌ Неполный ответ загрузки: {data}")
        sys.exit(1)

    # Сохранение фото
    save_params = {
        "group_id": abs(group_id),
        "server": data["server"],
        "photo": data["photo"],
        "hash": data["hash"]
    }
    save_resp = vk_api_request("photos.saveWallPhoto", save_params, token=VK_TOKEN, retries=2)
    if not save_resp:
        log("❌ Ошибка сохранения фото")
        sys.exit(1)
    photo = save_resp[0]
    attachment = f"photo{photo['owner_id']}_{photo['id']}"

    # Публикация поста с фото
    post_params = {
        "owner_id": group_id,
        "message": post_text,
        "attachments": attachment,
        "from_group": 1
    }
    post_resp = vk_api_request("wall.post", post_params, token=VK_TOKEN, retries=2)
    if post_resp:
        log(f"✅ Пост опубликован с фото, ID: {post_resp.get('post_id')}")
    else:
        log("❌ Ошибка публикации с фото")

log("🏁 Тест завершён.")