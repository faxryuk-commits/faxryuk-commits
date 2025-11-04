from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import time
import logging
from fake_useragent import UserAgent
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Базовый класс для всех парсеров"""
    
    def __init__(
        self,
        delay: float = 1.0,
        timeout: int = 30,
        use_proxy: bool = False,
        proxy: Optional[str] = None
    ):
        """
        Args:
            delay: Задержка между запросами в секундах
            timeout: Таймаут запросов
            use_proxy: Использовать прокси
            proxy: Адрес прокси-сервера
        """
        self.delay = delay
        self.timeout = timeout
        self.use_proxy = use_proxy
        self.proxy = proxy
        self.ua = UserAgent()
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Создает сессию с настройками повторов"""
        session = requests.Session()
        
        # Настройка retry стратегии
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Настройка заголовков (имитация реального браузера)
        user_agent = self.ua.random
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        })
        
        return session
    
    def _make_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Optional[requests.Response]:
        """Выполняет HTTP запрос с обработкой ошибок"""
        try:
            # Объединяем заголовки: базовые + дополнительные
            request_headers = self.session.headers.copy()
            if headers:
                request_headers.update(headers)
            
            # Применяем прокси если нужно
            if self.use_proxy and self.proxy:
                kwargs['proxies'] = {
                    'http': self.proxy,
                    'https': self.proxy
                }
            
            response = self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                timeout=self.timeout,
                **kwargs
            )
            
            # Логируем статус для отладки
            if response.status_code != 200:
                # Специальная обработка для статуса 498 (часто используется для блокировок)
                if response.status_code == 498:
                    logger.warning(f"Запрос к {url} вернул статус 498 (possible rate limit or block)")
                else:
                    logger.warning(f"Запрос к {url} вернул статус {response.status_code}")
            
            # Для 498 не выбрасываем исключение, возвращаем response для обработки
            if response.status_code != 498:
                response.raise_for_status()
            
            # Задержка между запросами
            time.sleep(self.delay)
            
            return response
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка запроса к {url}: {e} (статус: {e.response.status_code if hasattr(e, 'response') else 'unknown'})")
            # Возвращаем response даже при ошибке для анализа
            if hasattr(e, 'response'):
                return e.response
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к {url}: {e}")
            return None
    
    @abstractmethod
    def parse(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Основной метод парсинга. Должен быть реализован в дочерних классах"""
        pass
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Валидация данных перед сохранением
        
        Проверяет наличие обязательных полей и их типы:
        - Для Product: name (str), url (str), source (str)
        - Для Organization: name (str), source (str)
        """
        if not data or not isinstance(data, dict):
            return False
        
        # Определяем тип данных по полю source или другим признакам
        source = data.get('source', '').lower()
        
        # Валидация для Product
        if source in ['wildberries', 'ozon', 'uzum'] or 'price' in data:
            required_fields = ['name', 'url', 'source']
            for field in required_fields:
                if field not in data:
                    return False
                value = data[field]
                if not value or (isinstance(value, str) and not value.strip()):
                    return False
            # Проверяем типы
            if not isinstance(data.get('name'), str):
                return False
            if not isinstance(data.get('url'), str):
                return False
            if not isinstance(data.get('source'), str):
                return False
        
        # Валидация для Organization
        elif source in ['google_maps', 'yandex_maps', '2gis'] or 'coordinates' in data:
            required_fields = ['name', 'source']
            for field in required_fields:
                if field not in data:
                    return False
                value = data[field]
                if not value or (isinstance(value, str) and not value.strip()):
                    return False
            if not isinstance(data.get('name'), str):
                return False
            if not isinstance(data.get('source'), str):
                return False
        
        return True

