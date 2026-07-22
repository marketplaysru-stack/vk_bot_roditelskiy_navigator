# ===== vk_feeds.py =====
import requests
import hashlib
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ===== КОНФИГУРАЦИЯ =====
# Список групп ВК (с минусом) и соответствующие ниши
VK_FEED_SOURCES = {
    "строительный": [
        -12345678,   # ЗАМЕНИТЕ НА РЕАЛЬНЫЙ ID ГРУППЫ
    ],
    "ai": [
        -98765432,
    ],
    "родительский": [
        -11111111,
    ],
}

# Файл для хранения ID уже обработанных постов
PROCESSED_IDS_FILE = "/data/processed_vk_posts.txt"

# Параметры фильтрации
MAX_POST_AGE_DAYS = 3   # не брать посты старше N дней
MIN_TEXT_LENGTH = 50    # минимальная длина текста для обработки

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def load_processed_ids():
    try:
        with open(PROCESSED_IDS_FILE, 'r') as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def save_processed_ids(ids):
    with open(PROCESSED_IDS_FILE, 'w') as f:
        for pid in ids:
            f.write(f"{pid}\n")

def get_vk_api_token():
    """Берёт токен VK из переменных окружения (используем тот же, что для публикации)."""
    return os.getenv("VK_TOKEN_PARENT")  # или VK_TOKEN_AI / VK_TOKEN_BUILDER

# ===== РЕРАЙТ ЧЕРЕЗ AGNES AI =====

def rewrite_with_agnes(original_text, niche=""):
    """
    Отправляет оригинальный текст в Agnes AI для переработки.
    Возвращает переработанный текст или None при ошибке.
    """
    AGNES_API_KEY = os.getenv("AGNES_API_KEY")
    if not AGNES_API_KEY:
        logger.warning("   AGNES_API_KEY не задан, пропускаем рерайт")
        return None

    prompt = (
        "Ты — профессиональный копирайтер. Перепиши следующий текст в уникальный, интересный пост для блога. "
        "Сохрани основную мысль, но изложи её по-своему, добавь эмодзи, разбей на абзацы, сделай текст живым и вовлекающим. "
        "Добавь заголовок. В конце добавь 3–5 хештегов по теме. Исходный текст:\n\n"
        f"{original_text}"
    )
    if niche:
        prompt += f"\n\nНиша: {niche}"

    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "agnes-2.0-flash",
        "messages": [
            {"role": "system", "content": "Ты — профессиональный копирайтер и SMM-специалист."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.85
    }
    try:
        response = requests.post(
            "https://apihub.agnes-ai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        if response.status_code == 200:
            result = response.json()
            rewritten = result["choices"][0]["message"]["content"]
            logger.info("   ✅ Рерайт выполнен")
            return rewritten
        else:
            logger.error(f"   ❌ Ошибка рерайта: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"   ❌ Исключение при рерайте: {e}")
        return None

# ===== ОСНОВНАЯ ФУНКЦИЯ ДЛЯ СБОРА И ОБРАБОТКИ ПОСТОВ =====

def fetch_and_generate_topics_from_vk(limit=3):
    """
    Проверяет указанные группы ВК, берёт последние посты,
    делает рерайт через Agnes и возвращает список тем для новых постов.
    """
    token = get_vk_api_token()
    if not token:
        logger.error("❌ VK_TOKEN не задан, невозможно получить посты из групп")
        return []

    processed_ids = load_processed_ids()
    new_topics = []
    new_ids = set()
    cutoff_date = datetime.now() - timedelta(days=MAX_POST_AGE_DAYS)

    logger.info("🔍 Проверка новых постов в группах ВК...")

    for niche, group_ids in VK_FEED_SOURCES.items():
        for group_id in group_ids:
            try:
                params = {
                    "owner_id": group_id,
                    "count": limit,
                    "access_token": token,
                    "v": "5.131"
                }
                response = requests.get("https://api.vk.com/method/wall.get", params=params, timeout=30)
                if response.status_code != 200:
                    logger.error(f"   ❌ Ошибка запроса к группе {group_id}: {response.status_code}")
                    continue
                data = response.json()
                if "error" in data:
                    logger.error(f"   ❌ VK API ошибка: {data['error']['error_msg']}")
                    continue

                posts = data.get("response", {}).get("items", [])
                for post in posts:
                    post_id = f"{group_id}_{post['id']}"
                    if post_id in processed_ids or post_id in new_ids:
                        continue

                    # Проверяем дату поста (timestamp)
                    post_date = datetime.fromtimestamp(post['date'])
                    if post_date < cutoff_date:
                        continue

                    text = post.get('text', '').strip()
                    if not text or len(text) < MIN_TEXT_LENGTH:
                        continue

                    # Рерайт через Agnes
                    rewritten = rewrite_with_agnes(text, niche)
                    if rewritten:
                        # Используем переработанный текст как тему
                        # Обрезаем до разумной длины, чтобы использовать как тему для генератора
                        topic = rewritten[:200] + ("..." if len(rewritten) > 200 else "")
                        source_url = f"https://vk.com/wall{group_id}_{post['id']}"
                        new_topics.append({
                            "niche": niche,
                            "topic": topic,
                            "source": source_url,
                            "rewritten": rewritten,   # можно сохранить для дальнейшего использования
                        })
                        new_ids.add(post_id)
                    else:
                        # Если рерайт не удался, используем первые 100 символов как тему
                        topic = text[:100].replace('\n', ' ').strip()
                        if topic:
                            new_topics.append({
                                "niche": niche,
                                "topic": f"{topic} (обзор)",
                                "source": f"https://vk.com/wall{group_id}_{post['id']}",
                            })
                            new_ids.add(post_id)

            except Exception as e:
                logger.error(f"   ❌ Исключение при обработке группы {group_id}: {e}")

    save_processed_ids(processed_ids.union(new_ids))
    logger.info(f"✅ Найдено {len(new_topics)} новых тем из групп ВК.")
    return new_topics