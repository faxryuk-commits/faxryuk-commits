"""
Конфигурация парсеров
"""

# Общие настройки
DEFAULT_DELAY = 2.0  # Задержка между запросами (секунды)
DEFAULT_TIMEOUT = 30  # Таймаут запросов (секунды)

# Настройки прокси
USE_PROXY = False
PROXY_URL = None  # Например: "http://user:pass@proxy.example.com:8080"

# Настройки хранилища
DATA_DIR = "data"
STORAGE_TYPE = "json"  # json, sqlite (в будущем)

# Настройки для конкретных парсеров
MARKETPLACE_CONFIG = {
    "wildberries": {
        "delay": 2.0,
        "timeout": 30,
    },
    "ozon": {
        "delay": 2.5,
        "timeout": 30,
    }
}

MAPS_CONFIG = {
    "google_maps": {
        "delay": 2.0,
        "timeout": 30,
    },
    "yandex_maps": {
        "delay": 2.0,
        "timeout": 30,
    },
    "2gis": {
        "delay": 2.0,
        "timeout": 30,
        "default_city": "moscow",
    }
}

# User-Agent настройки
USER_AGENT_ROTATION = True

# Логирование
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = None  # Если None - вывод в консоль
