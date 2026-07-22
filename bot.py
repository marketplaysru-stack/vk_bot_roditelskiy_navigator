import sys
import os
import requests
import json
import urllib.parse
import threading
import time
import re
import traceback
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import random

# ===== ПРИНУДИТЕЛЬНЫЙ ВЫВОД ЛОГОВ =====
sys.stdout.reconfigure(line_buffering=True)

# ===== НАСТРОЙКА ЛОГГИРОВАНИЯ =====
DATA_DIR = "/data"
os.makedirs(DATA_DIR, exist_ok=True)
LOG_FILE = os.path.join(DATA_DIR, "bot_parent.log")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

def log(msg):
    logging.info(msg)

# ===== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ =====
BOT_TOKEN = os.getenv("BOT_TOKEN_NEW")
VK_TOKEN = os.getenv("VK_TOKEN_PARENT")
VK_GROUP_ID = os.getenv("VK_GROUP_ID_PARENT")
AGNES_API_KEY = os.getenv("AGNES_API_KEY")
PORT = int(os.getenv("PORT", 8081))

if not BOT_TOKEN:
    log("❌ BOT_TOKEN_NEW не задан")
    sys.exit(1)
if not VK_TOKEN:
    log("❌ VK_TOKEN_PARENT не задан")
    sys.exit(1)
if not VK_GROUP_ID:
    log("❌ VK_GROUP_ID_PARENT не задан")
    sys.exit(1)
try:
    VK_GROUP_ID = int(VK_GROUP_ID)
except ValueError:
    log(f"❌ VK_GROUP_ID_PARENT должен быть числом, получено: {VK_GROUP_ID}")
    sys.exit(1)
if not AGNES_API_KEY:
    log("⚠️ AGNES_API_KEY не задан (картинки только через Pollinations)")

log("🚀 Запуск родительского бота (с увеличенным таймаутом и fallback)")
log(f"📌 Группа ID: {VK_GROUP_ID}")

SCHEDULE_FILE = os.path.join(DATA_DIR, "schedule.json")
STATS_FILE = os.path.join(DATA_DIR, "post_history_parent.json")
log(f"📂 Файл расписания: {SCHEDULE_FILE}")
log(f"📂 Файл статистики: {STATS_FILE}")

# ===== ПРОВЕРКА ПРАВ ТОКЕНА VK =====
def check_vk_token_permissions():
    log("🔍 Проверка прав токена VK...")
    try:
        resp = requests.get(
            "https://api.vk.com/method/photos.getWallUploadServer",
            params={"group_id": abs(VK_GROUP_ID), "access_token": VK_TOKEN, "v": "5.131"},
            timeout=10
        )
        if resp.status_code != 200:
            log(f"⚠️ Не удалось проверить права: HTTP {resp.status_code}")
            return False
        data = resp.json()
        if "error" in data:
            if data["error"]["error_code"] == 27:
                log("❌ Токен НЕ имеет права 'photos'! Бот будет публиковать без фото.")
                return False
            else:
                log(f"⚠️ Ошибка при проверке прав: {data['error']['error_msg']}")
                return False
        log("✅ Токен имеет право 'photos'.")
        return True
    except Exception as e:
        log(f"⚠️ Исключение при проверке прав: {e}")
        return False

HAS_PHOTO_PERMISSION = check_vk_token_permissions()
if not HAS_PHOTO_PERMISSION:
    log("⚠️ Бот будет публиковать только текст (без фото) из-за отсутствия прав.")

# ===== Health-сервер =====
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_health_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    server.serve_forever()

health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()
log(f"🟢 Health-сервер запущен (порт {PORT})")

# ===== ПРОВЕРКА TELEGRAM =====
try:
    r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=10)
    if r.status_code == 200:
        bot_info = r.json()["result"]
        log(f"✅ Подключение к Telegram: @{bot_info['username']}")
    else:
        log(f"❌ Ошибка доступа к Telegram: {r.status_code}")
        sys.exit(1)
except Exception as e:
    log(f"❌ Не удалось подключиться к Telegram: {e}")
    sys.exit(1)

try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=10)
    log("✅ Вебхук удалён")
except Exception as e:
    log(f"⚠️ Ошибка удаления вебхука: {e}")

# ===== РАБОТА С РАСПИСАНИЕМ =====
def load_schedule():
    try:
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                log(f"📂 Загружено {len(data)} записей из {SCHEDULE_FILE}")
                return data
        else:
            log(f"📂 Файл {SCHEDULE_FILE} не найден, создаём новый")
            save_schedule([])
            return []
    except Exception as e:
        log(f"⚠️ Ошибка загрузки: {e}")
        return []

def save_schedule(schedule):
    try:
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(schedule, f, ensure_ascii=False, indent=2)
        log(f"💾 Сохранено {len(schedule)} записей в {SCHEDULE_FILE}")
    except Exception as e:
        log(f"⚠️ Ошибка сохранения: {e}")

# ============================================================
# ===== ГЕНЕРАЦИЯ ТЕКСТА (с увеличенным таймаутом и fallback) =====
# ============================================================

def generate_post_text(topic):
    log(f"🔤 Генерация текста для темы: {topic}")
    system_prompt = (
        "Ты — эксперт в области воспитания детей, семейной психологии, образования и здорового развития. "
        "Напиши полезный, тёплый и поддерживающий пост для родителей по теме. "
        "Структура: 70% полезный контент, 20% примеры/обсуждение, 10% вопрос к аудитории. "
        "Используй эмодзи, разделители. В конце добавь 5 хештегов."
    )
    user_prompt = f"Тема: {topic}"
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
            timeout=60  # увеличен до 60 секунд
        )
        if response.status_code != 200:
            log(f"   ❌ Ошибка HTTP {response.status_code}")
            # fallback: простой текст
            return f"❓ {topic}\n\nПоделитесь своим опытом в комментариях! 👇\n\n#родительство #дети #семья #воспитание #советы"
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            if content:
                log(f"   Текст получен, длина {len(content)}")
                return content
        log("   ❌ Пустой ответ от Agnes, используем fallback")
        return f"❓ {topic}\n\nПоделитесь своим опытом в комментариях! 👇\n\n#родительство #дети #семья #воспитание #советы"
    except requests.exceptions.Timeout:
        log("   ❌ Таймаут при генерации текста (Agnes не ответил за 60 сек), используем fallback")
        return f"❓ {topic}\n\nПоделитесь своим опытом в комментариях! 👇\n\n#родительство #дети #семья #воспитание #советы"
    except Exception as e:
        log(f"   ❌ Ошибка генерации текста: {e}, используем fallback")
        return f"❓ {topic}\n\nПоделитесь своим опытом в комментариях! 👇\n\n#родительство #дети #семья #воспитание #советы"

# ============================================================
# ===== МОДУЛЬ СТАТИСТИКИ =====
# ============================================================

def load_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        log(f"⚠️ Ошибка загрузки статистики: {e}")
        return []

def save_stats(stats):
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"⚠️ Ошибка сохранения статистики: {e}")

def fetch_post_stats(post_id, owner_id):
    try:
        params = {
            "posts": f"{owner_id}_{post_id}",
            "access_token": VK_TOKEN,
            "v": "5.131"
        }
        response = requests.post("https://api.vk.com/method/wall.getById", data=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "response" in data and len(data["response"]) > 0:
                post = data["response"][0]
                likes = post.get("likes", {}).get("count", 0)
                reposts = post.get("reposts", {}).get("count", 0)
                comments = post.get("comments", {}).get("count", 0)
                views = post.get("views", {}).get("count", 0)
                return {"likes": likes, "reposts": reposts, "comments": comments, "views": views}
        return None
    except Exception as e:
        log(f"⚠️ Ошибка получения статистики: {e}")
        return None

def update_post_history(niche, topic, post_id, stats):
    history = load_stats()
    views = stats.get("views", 1)
    engagement = (stats.get("likes", 0) + stats.get("reposts", 0) + stats.get("comments", 0)) / views * 100
    record = {
        "timestamp": datetime.now().isoformat(),
        "niche": niche,
        "topic": topic,
        "post_id": post_id,
        "likes": stats.get("likes", 0),
        "reposts": stats.get("reposts", 0),
        "comments": stats.get("comments", 0),
        "views": views,
        "engagement": engagement
    }
    history.append(record)
    save_stats(history)
    log(f"📊 Сохранена статистика поста {post_id}: likes={stats['likes']}, engagement={engagement:.2f}%")
    return record

# ============================================================
# ===== ГЕНЕРАЦИЯ КАРТИНКИ (улучшенные реалистичные люди, европеоидная раса, Москва) =====
# ============================================================

def build_image_prompt(topic):
    base = (
        f"Семья, родители и дети, счастливые моменты, уют, тепло, связанные с темой: {topic}. "
        "Люди — типичные москвичи, европеоидная внешность: светлая кожа, русые или светлые волосы, "
        "европейские черты лица, реалистичные, без искажений, с высокой детализацией кожи и глаз. "
        "Одежда современная, городская, соответствует московскому стилю. "
        "Действие происходит в Москве: уютные дворы, парки, улицы с характерной архитектурой. "
        "Фотореализм, 8K, сверхдетализированное изображение, естественные пропорции, "
        "мягкое естественное освещение, тёплые тона. Без текста и надписей."
    )
    return base

def generate_image_pollinations(prompt):
    log("   🖼️ Pollinations...")
    try:
        short_prompt = prompt[:200] + " Moscow family, European features, photorealistic, 8k, highly detailed"
        prompt_encoded = urllib.parse.quote(short_prompt)
        url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1024&height=1024&nologo=true"
        log("   ✅ URL сформирован")
        return url
    except Exception as e:
        log(f"   ❌ Pollinations исключение: {e}")
        return None

def generate_image_agnes(prompt):
    log("   🖼️ Agnes (резерв)...")
    if not AGNES_API_KEY:
        return None
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt,
        "size": "1024x1024",
        "n": 1
    }
    try:
        response = requests.post(
            "https://apihub.agnes-ai.com/v1/images/generations",
            headers=headers,
            json=data,
            timeout=30
        )
        if response.status_code != 200:
            log(f"   ❌ HTTP {response.status_code}")
            return None
        json_resp = response.json()
        if json_resp.get("data") and len(json_resp["data"]) > 0:
            url = json_resp["data"][0]["url"]
            log("   ✅ Agnes успешно")
            return url
        return None
    except Exception as e:
        log(f"   ❌ Agnes ошибка: {e}")
        return None

def generate_image(topic):
    log(f"🖼️ Генерация картинки для темы: {topic}")
    prompt = build_image_prompt(topic)
    log(f"   Промпт: {prompt[:150]}...")
    url = generate_image_pollinations(prompt)
    if url:
        return url
    url = generate_image_agnes(prompt)
    if url:
        return url
    log("❌ Все источники недоступны")
    return None

def download_image(url):
    log(f"📥 Скачивание картинки: {url[:60]}...")
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            content = response.content
            if b"<html" not in content[:100] and len(content) > 100:
                log(f"   Успешно, размер {len(content)} байт")
                return content
        log(f"   ❌ Ошибка скачивания: статус {response.status_code}")
        return None
    except Exception as e:
        log(f"   ❌ Исключение при скачивании: {e}")
        return None

# ===== ПУБЛИКАЦИЯ В VK =====
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

def post_to_vk(image_bytes, text):
    log(f"📤 Начало публикации в родительскую группу (ID {VK_GROUP_ID})")
    group_id = VK_GROUP_ID
    token = VK_TOKEN

    if image_bytes is None:
        log("   Публикация без фото")
        result = vk_api_request("wall.post", {"owner_id": group_id, "message": text, "from_group": 1}, token=token, retries=2)
        if result is None:
            return False, "Ошибка публикации текста", False, None
        post_id = result.get("post_id")
        log(f"✅ Пост опубликован (без фото) в группе {group_id}, ID: {post_id}")
        return True, None, False, post_id

    if not HAS_PHOTO_PERMISSION:
        log("   ⚠️ Токен не имеет права 'photos', публикуем без фото")
        result = vk_api_request("wall.post", {"owner_id": group_id, "message": text, "from_group": 1}, token=token, retries=2)
        if result is None:
            return False, "Ошибка публикации текста (нет прав photos)", False, None
        post_id = result.get("post_id")
        log(f"✅ Пост опубликован (без фото) в группе {group_id}, ID: {post_id}")
        return True, None, False, post_id

    log("   Публикация с фото")
    try:
        log("   Шаг 1: Получение upload_url...")
        upload_resp = vk_api_request("photos.getWallUploadServer", {"group_id": abs(group_id)}, token=token, retries=2)
        if upload_resp is None:
            log("   ❌ upload_url не получен, публикуем без фото")
            result = vk_api_request("wall.post", {"owner_id": group_id, "message": text, "from_group": 1}, token=token, retries=2)
            if result is None:
                return False, "Ошибка публикации", False, None
            post_id = result.get("post_id")
            log(f"✅ Пост опубликован (без фото) в группе {group_id}, ID: {post_id}")
            return True, None, False, post_id
        upload_url = upload_resp["upload_url"]

        log("   Шаг 2: Загрузка фото...")
        files = {"photo": ("image.jpg", image_bytes, "image/jpeg")}
        resp = requests.post(upload_url, files=files, timeout=30)
        if resp.status_code != 200:
            log(f"   ❌ Ошибка загрузки: HTTP {resp.status_code}, публикуем без фото")
            result = vk_api_request("wall.post", {"owner_id": group_id, "message": text, "from_group": 1}, token=token, retries=2)
            if result is None:
                return False, "Ошибка публикации после загрузки", False, None
            post_id = result.get("post_id")
            log(f"✅ Пост опубликован (без фото) в группе {group_id}, ID: {post_id}")
            return True, None, False, post_id
        data = resp.json()
        if data.get("error"):
            log(f"   ❌ Ошибка загрузки: {data['error']}, публикуем без фото")
            result = vk_api_request("wall.post", {"owner_id": group_id, "message": text, "from_group": 1}, token=token, retries=2)
            if result is None:
                return False, "Ошибка публикации после загрузки", False, None
            post_id = result.get("post_id")
            log(f"✅ Пост опубликован (без фото) в группе {group_id}, ID: {post_id}")
            return True, None, False, post_id
        if not all(k in data for k in ("server", "photo", "hash")):
            log(f"   ❌ Неполный ответ загрузки: {data}, публикуем без фото")
            result = vk_api_request("wall.post", {"owner_id": group_id, "message": text, "from_group": 1}, token=token, retries=2)
            if result is None:
                return False, "Ошибка публикации после загрузки", False, None
            post_id = result.get("post_id")
            log(f"✅ Пост опубликован (без фото) в группе {group_id}, ID: {post_id}")
            return True, None, False, post_id

        log("   Шаг 3: Сохранение фото...")
        save_params = {
            "group_id": abs(group_id),
            "server": data["server"],
            "photo": data["photo"],
            "hash": data["hash"]
        }
        save_resp = vk_api_request("photos.saveWallPhoto", save_params, token=token, retries=2)
        if save_resp is None:
            log("   ❌ Ошибка сохранения фото, публикуем без фото")
            result = vk_api_request("wall.post", {"owner_id": group_id, "message": text, "from_group": 1}, token=token, retries=2)
            if result is None:
                return False, "Ошибка публикации после сохранения", False, None
            post_id = result.get("post_id")
            log(f"✅ Пост опубликован (без фото) в группе {group_id}, ID: {post_id}")
            return True, None, False, post_id

        photo = save_resp[0]
        attachment = f"photo{photo['owner_id']}_{photo['id']}"

        log("   Шаг 4: Публикация поста...")
        post_params = {
            "owner_id": group_id,
            "message": text,
            "attachments": attachment,
            "from_group": 1
        }
        post_resp = vk_api_request("wall.post", post_params, token=token, retries=2)
        if post_resp is None:
            log("   ❌ Ошибка публикации с фото, пробуем без фото")
            result = vk_api_request("wall.post", {"owner_id": group_id, "message": text, "from_group": 1}, token=token, retries=2)
            if result is None:
                return False, "Ошибка публикации", False, None
            post_id = result.get("post_id")
            log(f"✅ Пост опубликован (без фото) в группе {group_id}, ID: {post_id}")
            return True, None, False, post_id

        post_id = post_resp.get("post_id")
        log(f"✅ Пост опубликован с фото в группе {group_id}, ID: {post_id}")
        return True, None, True, post_id

    except Exception as e:
        log(f"   ❌ Исключение в post_to_vk: {e}")
        result = vk_api_request("wall.post", {"owner_id": group_id, "message": text, "from_group": 1}, token=token, retries=2)
        if result is not None:
            post_id = result.get("post_id")
            log(f"✅ Пост опубликован (без фото) после исключения, ID: {post_id}")
            return True, None, False, post_id
        return False, f"Исключение: {str(e)}", False, None

# ===== ВЫПОЛНЕНИЕ ПОСТА =====
def execute_scheduled_post(item):
    if item.get("niche") != "родительский":
        return

    niche = "родительский"
    topic = item["topic"]
    log(f"📢 Публикую пост: '{topic}' (родительский)")

    log("🔤 Шаг 1: Генерация текста...")
    post_text = generate_post_text(topic)
    if not post_text:
        log("❌ Текст не сгенерирован, используем fallback")
        post_text = f"❓ {topic}\n\nПоделитесь своим опытом в комментариях! 👇\n\n#родительство #дети #семья #воспитание #советы"
    log(f"✅ Текст получен, длина {len(post_text)}")

    log("🖼️ Шаг 2: Генерация картинки...")
    image_url = generate_image(topic)
    image_bytes = None
    if image_url:
        log(f"✅ URL: {image_url[:60]}...")
        image_bytes = download_image(image_url)
        if image_bytes:
            log(f"✅ Картинка скачана, размер {len(image_bytes)} байт")
        else:
            log("⚠️ Картинка не скачалась")
    else:
        log("⚠️ Картинка не сгенерирована")

    log("📤 Шаг 3: Публикация...")
    success, error, photo_uploaded, post_id = post_to_vk(image_bytes, post_text)
    if success:
        log("✅ Пост опубликован!")
        if post_id:
            time.sleep(3)
            stats = fetch_post_stats(post_id, VK_GROUP_ID)
            if stats:
                update_post_history(niche, topic, post_id, stats)
    else:
        log(f"❌ Ошибка: {error}")

# ===== ПЛАНИРОВЩИК =====
def scheduler_loop():
    log("🔄 Планировщик запущен")
    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            log(f"⏰ Текущее время: {now}")
            schedule = load_schedule()
            if not schedule:
                log("📭 Расписание пустое")
            else:
                for item in schedule:
                    if item.get("niche") == "родительский" and item["time"] == now and not item.get("done", False):
                        log(f"📢 Найдено задание: {item['topic']}")
                        execute_scheduled_post(item)
                        item["done"] = True
                        save_schedule(schedule)
        except Exception as e:
            log(f"⚠️ Ошибка планировщика: {e}")
        time.sleep(30)

# ===== ОБРАБОТЧИКИ КОМАНД =====
def process_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    log(f"📩 Получено: {text}")

    if text.startswith("/start"):
        send_message(chat_id,
            "👋 Родительский бот.\n"
            "/post_in тема минуты\n"
            "/run_now тема\n"
            "/list\n/debug\n/clear\n/stats"
        )
        return

    if text.startswith("/clear"):
        save_schedule([])
        send_message(chat_id, "✅ Расписание очищено.")
        return

    if text.startswith("/stats"):
        history = load_stats()
        if not history:
            send_message(chat_id, "📭 Нет данных.")
            return
        msg = "📊 Топ по вовлечённости:\n"
        sorted_posts = sorted(history, key=lambda x: x.get("engagement", 0), reverse=True)[:5]
        for i, p in enumerate(sorted_posts, 1):
            topic = p.get("topic", "Без темы")[:50]
            eng = p.get("engagement", 0)
            likes = p.get("likes", 0)
            msg += f"{i}. {topic}... ❤️{likes} вовл.{eng:.1f}%\n"
        send_message(chat_id, msg[:4000])
        return

    if text.startswith("/run_now"):
        topic = text.replace("/run_now", "").strip()
        if not topic:
            send_message(chat_id, "❌ Укажи тему")
            return
        send_message(chat_id, f"⏳ Публикую...")
        def publish():
            item = {"niche": "родительский", "topic": topic, "time": datetime.now().strftime("%Y-%m-%d %H:%M")}
            execute_scheduled_post(item)
        threading.Thread(target=publish).start()
        return

    if text.startswith("/post_in"):
        parts = text.replace("/post_in", "").strip()
        match = re.search(r'(\d+)$', parts)
        if not match:
            send_message(chat_id, "❌ Укажи минуты")
            return
        minutes = int(match.group(1))
        topic = parts[:match.start()].strip()
        if not topic:
            send_message(chat_id, "❌ Укажи тему")
            return
        publish_time = datetime.now() + timedelta(minutes=minutes)
        full_time = publish_time.strftime("%Y-%m-%d %H:%M")
        schedule = load_schedule()
        new_id = str(int(time.time()))
        schedule.append({"id": new_id, "niche": "родительский", "topic": topic, "time": full_time, "done": False})
        save_schedule(schedule)
        send_message(chat_id, f"✅ Пост на {full_time}")
        return

    if text.startswith("/list"):
        schedule = load_schedule()
        if not schedule:
            send_message(chat_id, "📭 Нет постов")
        else:
            lines = []
            for item in schedule:
                status = "✅" if item.get("done") else "⏳"
                lines.append(f"{status} {item['topic']} -> {item['time']}")
            send_message(chat_id, "\n".join(lines[:10]))
        return

    if text.startswith("/debug"):
        try:
            if os.path.exists(SCHEDULE_FILE):
                with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                    send_message(chat_id, f"📄 {f.read()[:500]}")
            else:
                send_message(chat_id, "❌ Файл не найден")
        except Exception as e:
            send_message(chat_id, f"❌ Ошибка: {e}")
        return

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        log(f"⚠️ Ошибка отправки: {e}")

# ===== ПОЛУЧЕНИЕ ОБНОВЛЕНИЙ =====
def get_updates(offset):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": 10, "allowed_updates": ["message"]}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("result"):
                log(f"📨 Получены обновления: {len(data['result'])}")
                return data["result"]
        else:
            log(f"⚠️ getUpdates ошибка: {resp.status_code}")
    except Exception as e:
        log(f"⚠️ getUpdates исключение: {e}")
    return []

# ===== ГЛАВНЫЙ ЦИКЛ =====
if __name__ == "__main__":
    log("🤖 Родительский бот запущен")
    threading.Thread(target=scheduler_loop, daemon=True).start()
    update_id = 0
    while True:
        updates = get_updates(update_id + 1)
        for upd in updates:
            update_id = upd["update_id"]
            if "message" in upd:
                process_message(upd["message"])
        time.sleep(0.5)