from flask import Flask, render_template, request, url_for
import requests
import json 
import logging
import os
import time

app = Flask(__name__)

# --- 0. Мультиязычные Словари ---
LANG_TEXT = {
    'ru': {
        'title': "AI D&D Конвертер Персонажей (Локальный AI)",
        'subtitle': "Введите концепцию героя из любой вселенной, и ваш локальный AI создаст готовый лист персонажа D&D 5-й редакции 3-го уровня.",
        'language_label': "Язык ответа:",
        'language_ru': "Русский",
        'language_en': "Английский",
        'name_label': "Имя персонажа:",
        'name_placeholder': "Например, Марио",
        'universe_label': "Вселенная:",
        'universe_placeholder': "Например, Super Mario Bros.",
        'description_label': "Описание сил и особенностей:",
        'description_placeholder': "Например, Прыгучий, крепкий (грибы), использует огненные шары, очень храбрый водопроводчик.",
        'button': "Сгенерировать Персонажа",
        'result_header': "Готовый Лист Персонажа:"
    },
    'en': {
        'title': "AI D&D Character Converter (Local AI)",
        'subtitle': "Enter a hero concept from any universe, and your local AI will generate a ready-to-use D&D 5th Edition Level 3 character sheet.",
        'language_label': "Response Language:",
        'language_ru': "Russian",
        'language_en': "English",
        'name_label': "Character Name:",
        'name_placeholder': "E.g., Mario",
        'universe_label': "Universe:",
        'universe_placeholder': "E.g., Super Mario Bros.",
        'description_label': "Description of powers and features:",
        'description_placeholder': "E.g., Jumpy, sturdy (mushrooms), uses fireballs, very brave plumber.",
        'button': "Generate Character",
        'result_header': "Ready Character Sheet:"
    }
}


# --- 1. КОНФИГУРАЦИЯ OLLAMA ---

# Локальный URL Ollama (должен быть запущен)
OLLAMA_BASE_URL = "http://localhost:11434" 

# Название модели, которую вы загрузили через 'ollama pull'
OLLAMA_MODEL = "mistral" 

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- 2. МАСТЕР-ПРОМПТ (Остается без изменений) ---

MASTER_PROMPT_TEMPLATE = """
Ты — Мастер Подземелий, эксперт по Dungeons & Dragons 5-й редакции. Твоя задача — создать полный билд персонажа 3-го уровня для D&D 5e на основе следующего вымышленного героя.

ОТВЕЧАЙ СТРОГО НА {language} ЯЗЫКЕ.(уберите это если не для сайта)
Твой ответ должен быть креативным, но строго соответствовать правилам D&D 5e.

**Инструкции:**
1.  Используй СТАНДАРТНЫЙ НАБОР ХАРАКТЕРИСТИК: 15, 14, 13, 12, 10, 8.
2.  Используй Markdown для форматирования.

**Данные о Персонаже:**
Имя: {name}(замените на информацию персонажа)
Вселенная: {universe}(замените на информацию персонажа)
Описание сил и особенностей: {description}(замените на информацию персонажа)

**Твой ответ должен включать следующие разделы:**

1.  **Концепция (Имя и Вселенная):**
2.  **Раса (Race) и Предыстория (Background):** (Обоснуй выбор)
3.  **Класс (Class) и Подкласс (Subclass):** (Обоснуй выбор и укажи Уровень 4)
4.  **Характеристики (Ability Scores):** (Распредели 15, 14, 13, 12, 10, 8 с учетом расовых бонусов)
5.  **Ключевые Навыки (Skills) и Черты (Features):** (Укажи 4-6 самых важных навыков, и черту для персонажа)
6.  **Экипировка (Starting Equipment):** (Главное оружие/броня/фокус, и добавь снаряжение от предыстории)
7.  **Личность(Personality):** (Напиши его Мировоззрение(Alignment), Черту характера(Personality), Идеалы(Ideals), Привязанности(Bouds), и Слабости(Flaws) основываясь на оригинале)
8.  **Рекомендации по Прокачке (с 1 Урованя до 4 Уровень и далее):**
"""

# --- 3. ОСНОВНАЯ ЛОГИКА OLLAMA ---

def generate_dnd_sheet(name, universe, description, language) -> str:
    """Отправляет запрос на локальный сервер Ollama."""
    
    prompt = MASTER_PROMPT_TEMPLATE.format(
        language=language,
        name=name,
        universe=universe,
        description=description
    )

    url = f"{OLLAMA_BASE_URL}/api/chat" 
    
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "options": {
            "temperature": 0.7,
            "num_predict": 4096
        }
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() 
        data = response.json()
        
        if 'message' in data and 'content' in data['message']:
            generated_text = data['message']['content']
            return generated_text.replace('\n', '<br>').replace('**', '<strong>') 
        else:
            logging.error(f"Unexpected API response from Ollama: {data}")
            return f"Неожиданный ответ от локального AI. Убедитесь, что модель {OLLAMA_MODEL} загружена."
            
    except requests.exceptions.ConnectionError:
        return f"Критическая ОШИБКА: Не удалось подключиться к серверу Ollama по адресу {OLLAMA_BASE_URL}. Убедитесь, что Ollama запущен."
    except requests.exceptions.RequestException as req_err:
        logging.error(f"HTTP Error: {req_err}")
        return f"Ошибка HTTP при обращении к Ollama. Детали: {req_err}"
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}") 
        return f"Критическая ошибка: {e}"

# --- 4. МАРШРУТЫ FLASK ---

@app.route('/', methods=['GET', 'POST'])
@app.route('/<lang_code>', methods=['GET', 'POST'])
def index(lang_code='ru'):
    if lang_code not in LANG_TEXT:
        lang_code = 'ru' 
        
    texts = LANG_TEXT[lang_code]
    
    # Формат языка для промпта Ollama
    ollama_lang = 'Русском' if lang_code == 'ru' else 'Английском'

    if request.method == 'POST':
        name = request.form.get('name', 'Неизвестный')
        universe = request.form.get('universe', '')
        description = request.form.get('description', '')
        
        dnd_sheet_html = generate_dnd_sheet(name, universe, description, ollama_lang)
        
        return render_template('index.html', 
                               result=dnd_sheet_html, 
                               name=name,
                               texts=texts,
                               lang_code=lang_code)

    return render_template('index.html', result=None, texts=texts, lang_code=lang_code)

# --- 5. ЗАПУСК СЕРВЕРА ---
if __name__ == '__main__':
    # Обязательно установите: pip install requests Flask
    app.run(debug=True)