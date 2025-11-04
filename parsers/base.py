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
        
        # Настройка заголовков
        session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        return session
    
    def _make_request(
        self,
        url: str,
        method: str = "GET",
        **kwargs
    ) -> Optional[requests.Response]:
        """Выполняет HTTP запрос с обработкой ошибок"""
        try:
            # Применяем прокси если нужно
            if self.use_proxy and self.proxy:
                kwargs['proxies'] = {
                    'http': self.proxy,
                    'https': self.proxy
                }
            
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            
            # Задержка между запросами
            time.sleep(self.delay)
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к {url}: {e}")
            return None
    
    @abstractmethod
    def parse(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Основной метод парсинга. Должен быть реализован в дочерних классах"""
        pass
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Валидация данных перед сохранением"""
        return data is not None and isinstance(data, dict)

