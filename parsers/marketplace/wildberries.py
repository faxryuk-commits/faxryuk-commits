from typing import Dict, List, Any, Optional
from urllib.parse import urlencode, quote
from .base_marketplace import BaseMarketplaceParser
import re


class WildberriesParser(BaseMarketplaceParser):
    """Парсер для Wildberries"""
    
    BASE_URL = "https://www.wildberries.ru"
    SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v4/search"
    
    def __init__(self, **kwargs):
        super().__init__(base_url=self.BASE_URL, **kwargs)
        # Добавляем специфичные заголовки для Wildberries API
        # Wildberries требует определенные заголовки для работы API
        self.session.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Origin': 'https://www.wildberries.ru',
            'Referer': 'https://www.wildberries.ru/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        })
        # Инициализируем сессию - получаем куки с главной страницы
        self._init_session()
    
    def _init_session(self):
        """Инициализирует сессию, получая куки с главной страницы"""
        import logging
        import time
        logger = logging.getLogger(__name__)
        
        try:
            # Делаем запрос на главную страницу для получения кук
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            response = self.session.get(self.BASE_URL, headers=headers, timeout=15)
            if response.status_code == 200:
                logger.info("Сессия Wildberries инициализирована, куки получены")
                # Небольшая задержка для стабильности
                time.sleep(0.5)
            elif response.status_code == 429:
                logger.warning("Rate limit при инициализации, жду 5 секунд")
                time.sleep(5)
                # Пробуем еще раз
                response = self.session.get(self.BASE_URL, headers=headers, timeout=15)
                if response.status_code == 200:
                    logger.info("Сессия инициализирована после ожидания")
            else:
                logger.warning(f"Не удалось получить куки, статус: {response.status_code}")
        except Exception as e:
            logger.warning(f"Ошибка инициализации сессии: {e}")
    
    def parse_search(
        self,
        query: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Парсит результаты поиска с retry логикой
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
        
        Returns:
            Список товаров
        """
        import logging
        import time
        logger = logging.getLogger(__name__)
        
        max_retries = 3
        retry_delay = 2  # секунды
        
        # Используем delay из базового класса, но не менее 1 секунды
        base_delay = max(self.delay, 1.0)
        
        for attempt in range(max_retries):
            try:
                # Сначала пробуем API
                url = self._build_search_url(query)
                logger.info(f"Запрос к Wildberries API (попытка {attempt + 1}/{max_retries}): {url}")
                
                # Устанавливаем правильные заголовки для API запроса
                api_headers = {
                    'Accept': 'application/json',
                    'Accept-Language': 'ru-RU,ru;q=0.9',
                    'Referer': f'{self.BASE_URL}/',
                    'Origin': self.BASE_URL,
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site',
                }
                
                response = self._make_request(url, headers=api_headers)
                
                # Проверяем статус ответа
                if response:
                    logger.info(f"Статус ответа API: {response.status_code}")
                    
                    if response.status_code == 200:
                        products = self._extract_products(response.text)
                        
                        if products:
                            if limit:
                                products = products[:limit]
                            logger.info(f"Получено товаров: {len(products)}")
                            # Небольшая задержка после успешного запроса для стабильности
                            time.sleep(0.5)
                            return products
                        else:
                            logger.warning("API вернул 200, но товары не найдены в ответе")
                            
                            # Пробуем использовать shardKey для получения товаров из другого endpoint
                            try:
                                import json
                                data = json.loads(response.text)
                                if isinstance(data, dict) and 'shardKey' in data:
                                    shard_key = data.get('shardKey', '')
                                    rs = data.get('rs', 100)
                                    
                                    # Пробуем получить товары через shard endpoint
                                    if shard_key and 'presets/' in shard_key:
                                        logger.info(f"Пробуем получить товары через shardKey: {shard_key}")
                                        shard_url = f"https://catalog.wb.ru/{shard_key}/v4/filters"
                                        
                                        # Альтернативный способ - используем другой формат запроса без некоторых параметров
                                        alt_url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?query={quote(query)}&resultset=catalog&limit={rs}&sort=popular&page=1&appType=1&curr=rub&dest=-1257786"
                                        
                                        # Также пробуем через catalog endpoint
                                        catalog_url = f"https://catalog.wb.ru/v2/search?query={quote(query)}&limit={rs}&sort=popular"
                                        
                                        # Пробуем альтернативный endpoint
                                        alt_response = self._make_request(alt_url, headers=api_headers)
                                        if alt_response and alt_response.status_code == 200:
                                            alt_products = self._extract_products(alt_response.text)
                                            if alt_products:
                                                logger.info(f"Альтернативный endpoint вернул {len(alt_products)} товаров")
                                                if limit:
                                                    alt_products = alt_products[:limit]
                                                return alt_products
                                        
                                        # Пробуем catalog endpoint
                                        catalog_response = self._make_request(catalog_url, headers=api_headers)
                                        if catalog_response and catalog_response.status_code == 200:
                                            catalog_products = self._extract_products(catalog_response.text)
                                            if catalog_products:
                                                logger.info(f"Catalog endpoint вернул {len(catalog_products)} товаров")
                                                if limit:
                                                    catalog_products = catalog_products[:limit]
                                                return catalog_products
                            except Exception as e:
                                logger.debug(f"Ошибка при попытке использовать shardKey: {e}")
                            
                            # Пробуем веб-версию как fallback
                            break
                    elif response.status_code == 429:
                        # Rate limit - ждем дольше с экспоненциальной задержкой
                        wait_time = base_delay * (2 ** (attempt + 1))
                        logger.warning(f"Rate limit (429), жду {wait_time:.1f} секунд перед повтором")
                        time.sleep(wait_time)
                        # Переинициализируем сессию после rate limit
                        self._init_session()
                        continue
                    elif response.status_code in [498, 403, 503]:
                        # Временные проблемы - ждем и пробуем снова
                        wait_time = base_delay * (attempt + 1)
                        logger.warning(f"API вернул статус {response.status_code}, жду {wait_time:.1f} секунд перед повтором")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"API вернул статус {response.status_code}")
                
                # Если не удалось или последняя попытка - пробуем веб-версию
                if attempt == max_retries - 1 or not response:
                    logger.warning("Не удалось получить ответ от API, пробуем веб-версию")
                    break
                    
            except Exception as e:
                logger.error(f"Ошибка при запросе к API (попытка {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = base_delay * (attempt + 1)
                    logger.info(f"Жду {wait_time:.1f} секунд перед следующей попыткой")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning("Все попытки API исчерпаны, пробуем веб-версию")
                    break
        
        # Fallback на веб-версию
        try:
            # Задержка перед веб-версией для стабильности
            time.sleep(1)
            
            web_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Referer': f'{self.BASE_URL}/',
            }
            web_url = f"{self.BASE_URL}/catalog/0/search.aspx?search={quote(query)}"
            logger.info(f"Пробуем веб-версию: {web_url}")
            
            # Пробуем веб-версию с retry для 498
            web_max_retries = 2
            for web_attempt in range(web_max_retries):
                response = self._make_request(web_url, headers=web_headers)
                
                if response and response.status_code == 200:
                    products = self._extract_products(response.text)
                    if limit:
                        products = products[:limit]
                    logger.info(f"Веб-версия вернула {len(products)} товаров")
                    return products
                elif response and response.status_code == 498:
                    # Статус 498 - возможная блокировка, ждем и пробуем еще раз
                    if web_attempt < web_max_retries - 1:
                        wait_time = base_delay * (web_attempt + 1) * 2
                        logger.warning(f"Веб-версия вернула 498, жду {wait_time:.1f} секунд перед повтором")
                        time.sleep(wait_time)
                        # Переинициализируем сессию
                        self._init_session()
                        continue
                    else:
                        logger.error(f"Веб-версия вернула 498 после {web_max_retries} попыток - возможная блокировка")
                        return []
                elif not response:
                    # Response = None означает, что произошла ошибка
                    if web_attempt < web_max_retries - 1:
                        wait_time = base_delay * (web_attempt + 1)
                        logger.warning(f"Веб-версия вернула None (ошибка), жду {wait_time:.1f} секунд перед повтором")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("Не удалось получить ответ от веб-версии после всех попыток")
                        return []
                else:
                    logger.error(f"Не удалось получить ответ от веб-версии, статус: {response.status_code}")
                    return []
            
            return []
        except Exception as e:
            logger.error(f"Ошибка при запросе к веб-версии: {e}", exc_info=True)
            return []
    
    def _build_search_url(self, query: str) -> str:
        """Формирует URL для поиска через API"""
        params = {
            'query': query,
            'resultset': 'catalog',
            'limit': 100,
            'sort': 'popular',
            'page': 1,
            'appType': 1,
            'curr': 'rub',
            'dest': -1257786,  # Москва
            'lang': 'ru',
            'locale': 'ru',
            'reg': 0,
            'regions': '80,38,83,4,64,33,68,70,30,40,86,75,69,1,31,66,22,48,71',
        }
        return f"{self.SEARCH_URL}?{urlencode(params)}"
    
    def _extract_products_from_html(self, html: str) -> List[Dict[str, Any]]:
        """Альтернативный метод: извлечение товаров из HTML веб-версии"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            soup = self._parse_html(html)
            products = []
            
            # Ищем карточки товаров - пробуем разные селекторы
            product_cards = []
            selectors = [
                soup.find_all('article', class_='product-card'),
                soup.find_all('div', class_='product-card'),
                soup.find_all('div', {'data-product-id': True}),
                soup.find_all('article', {'data-product-id': True}),
                soup.find_all('div', class_=lambda x: x and 'product' in ' '.join(x).lower()),
                soup.find_all('article'),
                # По структуре - div с data-nm-id
                soup.find_all('div', {'data-nm-id': True}),
            ]
            
            for selector_result in selectors:
                if selector_result:
                    product_cards = selector_result
                    logger.info(f"Найдено {len(product_cards)} карточек товаров используя селектор")
                    break
            
            if not product_cards:
                logger.warning("Стандартные селекторы не сработали, пробуем универсальный подход")
                # Ищем все ссылки с catalog в href
                catalog_links = soup.find_all('a', href=lambda x: x and '/catalog/' in str(x))
                logger.info(f"Найдено {len(catalog_links)} ссылок на товары")
                for link in catalog_links:
                    parent = link.find_parent('article') or link.find_parent('div')
                    if parent and parent not in product_cards:
                        product_cards.append(parent)
                logger.info(f"Добавлено {len(product_cards)} карточек через ссылки")
            
            for card in product_cards:
                try:
                    # Извлекаем ID
                    product_id = card.get('data-product-id') or \
                                card.get('data-nm-id') or \
                                card.find('a', href=True)
                    
                    if product_id and isinstance(product_id, str):
                        import re
                        match = re.search(r'/(\d+)', product_id)
                        if match:
                            product_id = match.group(1)
                    
                    if not product_id:
                        # Пробуем из ссылки
                        link = card.find('a', href=True)
                        if link:
                            href = link.get('href', '')
                            # Пробуем разные паттерны для ID
                            patterns = [
                                r'/catalog/(\d+)/',
                                r'/(\d+)',
                                r'nm_id=(\d+)',
                                r'product_id=(\d+)',
                            ]
                            for pattern in patterns:
                                match = re.search(pattern, href)
                                if match:
                                    product_id = match.group(1)
                                    break
                    
                    # Название - пробуем разные варианты
                    name = ''
                    name_selectors = [
                        ('span', {'class': lambda x: x and 'name' in ' '.join(x).lower()}),
                        ('a', {'class': lambda x: x and 'name' in ' '.join(x).lower()}),
                        ('h3', None),
                        ('h2', None),
                        ('span', {'data-product-name': True}),
                        ('a', {'href': lambda x: x and '/catalog/' in str(x)}),
                    ]
                    
                    for tag, attrs in name_selectors:
                        if attrs is None:
                            name_elem = card.find(tag)
                        else:
                            name_elem = card.find(tag, attrs)
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            if name and len(name) > 3:
                                break
                    
                    # Если не нашли, берем текст из ссылки
                    if not name or len(name) < 3:
                        link = card.find('a', href=True)
                        if link:
                            name = link.get_text(strip=True) or link.get('title', '') or link.get('aria-label', '')
                    
                    # Цена
                    price_elem = card.find('span', class_='price') or \
                                card.find('ins', class_='price') or \
                                card.find('span', {'data-product-price': True})
                    price_text = price_elem.get_text(strip=True) if price_elem else '0'
                    price = self._parse_price(price_text)
                    
                    # Рейтинг
                    rating_elem = card.find('span', class_='product-card__rating') or \
                                 card.find('div', class_='rating')
                    rating = 0
                    if rating_elem:
                        rating_text = rating_elem.get_text(strip=True)
                        import re
                        match = re.search(r'(\d+[,.]?\d*)', rating_text)
                        if match:
                            try:
                                rating = float(match.group(1).replace(',', '.'))
                            except:
                                pass
                    
                    if name:
                        # Формируем URL
                        url = ''
                        if product_id:
                            url = f"{self.BASE_URL}/catalog/{product_id}/detail.aspx"
                        else:
                            # Пробуем найти ссылку
                            link = card.find('a', href=True)
                            if link:
                                href = link.get('href', '')
                                if href.startswith('http'):
                                    url = href
                                elif href.startswith('/'):
                                    url = f"{self.BASE_URL}{href}"
                            # Fallback
                            if not url and name:
                                url = f"{self.BASE_URL}/catalog/0/search.aspx?search={quote(name[:50])}"
                        
                        product = {
                            'id': str(product_id) if product_id else None,
                            'name': name.strip() if name else '',
                            'brand': '',
                            'price': price,
                            'rating': rating,
                            'reviews_count': 0,
                            'url': url,
                            'image_url': '',
                            'source': 'wildberries'
                        }
                        
                        if self.validate_data(product) and name:
                            products.append(product)
                        else:
                            logger.debug(f"Товар не прошел валидацию: name={bool(name)}, url={bool(url)}")
                        
                except Exception as e:
                    logger.warning(f"Ошибка обработки карточки: {e}")
                    continue
            
            return products
            
        except Exception as e:
            logger.error(f"Ошибка парсинга HTML: {e}")
            return []
    
    def _parse_price(self, price_text: str) -> float:
        """Парсит цену из текста"""
        import re
        # Удаляем все кроме цифр
        cleaned = re.sub(r'[^\d]', '', price_text.replace(' ', ''))
        try:
            return float(cleaned) / 100  # Wildberries хранит цены в копейках
        except:
            return 0.0
    
    def _extract_products(self, html: str) -> List[Dict[str, Any]]:
        """Извлекает товары из JSON ответа API"""
        import json
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Пробуем распарсить JSON
            try:
                data = json.loads(html)
            except json.JSONDecodeError:
                logger.warning(f"Ответ не является JSON. Первые 500 символов: {html[:500]}")
                # Пробуем альтернативный способ - веб-версия
                return self._extract_products_from_html(html)
            
            products = []
            
            # Проверяем разные возможные структуры ответа
            products_data = None
            
            # Логируем структуру ответа для отладки
            logger.debug(f"Структура ответа API: {list(data.keys())}")
            
            # Пробуем разные пути к данным
            if 'data' in data:
                data_obj = data['data']
                logger.debug(f"Тип data: {type(data_obj)}, ключи: {list(data_obj.keys()) if isinstance(data_obj, dict) else 'list'}")
                
                if isinstance(data_obj, dict):
                    # Пробуем разные ключи
                    if 'products' in data_obj:
                        products_data = data_obj['products']
                    elif 'items' in data_obj:
                        products_data = data_obj['items']
                    elif 'goods' in data_obj:
                        products_data = data_obj['goods']
                    # Может быть вложенная структура
                    elif 'catalog' in data_obj:
                        catalog = data_obj['catalog']
                        if isinstance(catalog, dict) and 'products' in catalog:
                            products_data = catalog['products']
                        elif isinstance(catalog, list):
                            products_data = catalog
                    # Проверяем, есть ли массив товаров напрямую
                    for key in ['products', 'items', 'goods', 'results', 'data']:
                        if key in data_obj and isinstance(data_obj[key], list) and len(data_obj[key]) > 0:
                            # Проверяем, похож ли первый элемент на товар
                            first_item = data_obj[key][0]
                            if isinstance(first_item, dict) and ('id' in first_item or 'nmId' in first_item or 'name' in first_item):
                                products_data = data_obj[key]
                                break
                elif isinstance(data_obj, list):
                    products_data = data_obj
            
            # Также пробуем корневые ключи
            if not products_data:
                for key in ['products', 'items', 'goods', 'results']:
                    if key in data and isinstance(data[key], list):
                        products_data = data[key]
                        break
            
            if products_data:
                logger.info(f"Найдено {len(products_data)} товаров в ответе API")
                for item in products_data:
                    try:
                        # Пробуем разные варианты ключей для ID
                        product_id = (
                            item.get('id') or 
                            item.get('nmId') or 
                            item.get('nm_id') or
                            item.get('goodsId') or
                            item.get('goods_id')
                        )
                        
                        # Пробуем разные варианты ключей для названия
                        name = (
                            item.get('name') or 
                            item.get('title') or 
                            item.get('goodsName') or
                            item.get('productName') or
                            item.get('brandName') or
                            ''
                        )
                        
                        # Пробуем разные варианты ключей для цены
                        price = 0
                        price_keys = ['salePriceU', 'priceU', 'price', 'salePrice', 'finalPrice', 'priceWithDiscount']
                        for key in price_keys:
                            if key in item:
                                price_val = item[key]
                                if isinstance(price_val, (int, float)):
                                    # Если цена в копейках (больше 1000), делим на 100
                                    price = price_val / 100 if price_val > 1000 else price_val
                                    break
                        
                        # Пробуем разные варианты ключей для бренда
                        brand = (
                            item.get('brand') or 
                            item.get('brandName') or
                            item.get('brand_name') or
                            item.get('supplier') or
                            None
                        )
                        
                        # Пробуем разные варианты ключей для рейтинга
                        rating = (
                            item.get('rating') or 
                            item.get('reviewRating') or
                            item.get('stars') or
                            0
                        )
                        
                        # Пробуем разные варианты ключей для отзывов
                        reviews_count = (
                            item.get('feedbacks') or 
                            item.get('reviewCount') or
                            item.get('reviewsCount') or
                            item.get('feedbacksCount') or
                            0
                        )
                        
                        # Формируем URL
                        url = ''
                        if product_id:
                            url = f"{self.BASE_URL}/catalog/{product_id}/detail.aspx"
                        elif name:
                            url = f"{self.BASE_URL}/catalog/0/search.aspx?search={quote(name[:50])}"
                        
                        # Формируем изображение
                        image_url = ''
                        if product_id:
                            root = item.get('root') or item.get('rootId')
                            image_url = self._get_image_url(product_id, root)
                        elif 'image' in item:
                            image_url = item['image']
                        
                        product = {
                            'id': str(product_id) if product_id else None,
                            'name': name.strip() if name else '',
                            'brand': brand,
                            'price': float(price),
                            'rating': float(rating),
                            'reviews_count': int(reviews_count),
                            'url': url,
                            'image_url': image_url,
                            'source': 'wildberries'
                        }
                        
                        if self.validate_data(product) and product.get('name'):
                            products.append(product)
                        else:
                            logger.debug(f"Товар не прошел валидацию: name={bool(product.get('name'))}, url={bool(product.get('url'))}, структура: {list(item.keys())[:5]}")
                    except Exception as e:
                        logger.warning(f"Ошибка обработки товара: {e}", exc_info=True)
                        continue
            
            if not products:
                logger.warning(f"Товары не найдены в JSON. Структура ответа: {list(data.keys())[:5]}")
                # Логируем структуру для отладки
                if 'data' in data:
                    logger.debug(f"Data structure: {type(data['data'])} - {list(data['data'].keys()) if isinstance(data['data'], dict) else 'list'}")
                # Пробуем веб-версию как fallback
                if not html.startswith('{'):
                    logger.info("Пробуем извлечь товары из HTML веб-версии")
                    return self._extract_products_from_html(html)
                else:
                    # Если это JSON, но товаров нет, делаем глубокий анализ структуры
                    logger.warning("Товары не найдены в стандартных путях, делаю глубокий анализ структуры ответа")
                    
                    def find_product_arrays(obj, path="", max_depth=5, current_depth=0):
                        """Рекурсивно ищем массивы товаров в структуре с ограничением глубины"""
                        if current_depth >= max_depth:
                            return []
                        
                        arrays = []
                        if isinstance(obj, dict):
                            # Сначала проверяем известные ключи
                            for known_key in ['products', 'items', 'goods', 'results', 'data', 'value', 'catalog', 'list']:
                                if known_key in obj:
                                    val = obj[known_key]
                                    if isinstance(val, list) and len(val) > 0:
                                        first = val[0] if val else {}
                                        if isinstance(first, dict):
                                            # Проверяем признаки товара
                                            has_product_signs = any(k in first for k in ['id', 'nmId', 'nm_id', 'goodsId', 'name', 'title', 'brandName', 'price', 'salePriceU', 'priceU'])
                                            if has_product_signs:
                                                arrays.append((f"{path}.{known_key}" if path else known_key, val))
                                    elif isinstance(val, dict):
                                        arrays.extend(find_product_arrays(val, f"{path}.{known_key}" if path else known_key, max_depth, current_depth + 1))
                            
                            # Затем рекурсивно проверяем все ключи
                            for key, value in obj.items():
                                if key not in ['products', 'items', 'goods', 'results', 'data', 'value', 'catalog', 'list']:
                                    if isinstance(value, dict):
                                        arrays.extend(find_product_arrays(value, f"{path}.{key}" if path else key, max_depth, current_depth + 1))
                                    elif isinstance(value, list) and len(value) > 0:
                                        first = value[0] if value else {}
                                        if isinstance(first, dict) and any(k in first for k in ['id', 'nmId', 'name', 'title', 'price']):
                                            arrays.append((f"{path}.{key}" if path else key, value))
                        elif isinstance(obj, list) and len(obj) > 0:
                            first = obj[0]
                            if isinstance(first, dict) and any(k in first for k in ['id', 'nmId', 'name', 'title', 'price']):
                                arrays.append((path or "root", obj))
                        
                        return arrays
                    
                    # Ищем массивы товаров
                    found_arrays = find_product_arrays(data)
                    
                    if found_arrays:
                        logger.info(f"Найдены потенциальные массивы товаров в путях: {[path for path, _ in found_arrays]}")
                        
                        # Сортируем по приоритету (известные ключи в начале)
                        priority_keys = ['products', 'items', 'goods', 'results', 'data']
                        found_arrays.sort(key=lambda x: (
                            0 if any(pk in x[0] for pk in priority_keys) else 1,
                            len(x[1])  # Больше элементов = выше приоритет
                        ), reverse=True)
                        
                        # Пробуем каждый найденный массив
                        for path, products_data in found_arrays:
                            logger.info(f"Пробуем использовать массив из '{path}' с {len(products_data)} элементами")
                            processed_count = 0
                            
                            for item in products_data:
                                try:
                                    if not isinstance(item, dict):
                                        continue
                                    
                                    # Пробуем разные варианты ключей для всех полей
                                    product_id = (
                                        item.get('id') or item.get('nmId') or item.get('nm_id') or 
                                        item.get('goodsId') or item.get('goods_id') or
                                        item.get('productId') or item.get('product_id')
                                    )
                                    
                                    name = (
                                        item.get('name') or item.get('title') or 
                                        item.get('goodsName') or item.get('productName') or
                                        item.get('brandName') or item.get('brand_name') or
                                        ''
                                    )
                                    
                                    if not name or len(name.strip()) < 2:
                                        continue
                                    
                                    # Цена
                                    price = 0
                                    for price_key in ['salePriceU', 'priceU', 'price', 'salePrice', 'finalPrice', 'priceWithDiscount', 'cost']:
                                        if price_key in item:
                                            price_val = item[price_key]
                                            if isinstance(price_val, (int, float)):
                                                # Если цена в копейках (больше 1000), делим на 100
                                                price = price_val / 100 if price_val > 1000 else price_val
                                                break
                                    
                                    # Формируем URL
                                    url = ''
                                    if product_id:
                                        url = f"{self.BASE_URL}/catalog/{product_id}/detail.aspx"
                                    else:
                                        url = f"{self.BASE_URL}/catalog/0/search.aspx?search={quote(name[:50])}"
                                    
                                    product = {
                                        'id': str(product_id) if product_id else None,
                                        'name': name.strip(),
                                        'price': float(price),
                                        'rating': float(item.get('rating', 0) or item.get('reviewRating', 0) or 0),
                                        'reviews_count': int(item.get('feedbacks', 0) or item.get('reviewCount', 0) or 0),
                                        'url': url,
                                        'image_url': self._get_image_url(product_id, item.get('root')) if product_id else '',
                                        'brand': item.get('brand') or item.get('brandName') or None,
                                        'source': 'wildberries'
                                    }
                                    
                                    if self.validate_data(product):
                                        products.append(product)
                                        processed_count += 1
                                        
                                        # Ограничиваем для теста
                                        if processed_count >= 10:
                                            break
                                except Exception as e:
                                    logger.debug(f"Ошибка обработки элемента из {path}: {e}")
                                    continue
                            
                            # Если нашли товары, используем этот массив
                            if products:
                                logger.info(f"Успешно извлечено {len(products)} товаров из массива '{path}'")
                                break
                    else:
                        # Если ничего не найдено, логируем структуру для анализа
                        logger.warning(f"Товары не найдены ни в одном массиве. Структура ответа (первые 500 символов): {str(data)[:500]}")
                        logger.debug(f"Корневые ключи: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            
            return products
            
        except Exception as e:
            logger.error(f"Ошибка извлечения товаров: {e}", exc_info=True)
            # Fallback на веб-версию
            try:
                return self._extract_products_from_html(html)
            except:
                return []
    
    def _get_image_url(self, product_id: int, root: Optional[int] = None) -> str:
        """Формирует URL изображения товара"""
        if not root:
            root = product_id // 100000
        basket = '01'  # Можно менять для разных CDN
        return f"https://basket-{basket}.wbbasket.ru/vol{root}/part{product_id//1000}/{product_id}/images/big/1.webp"
    
    def _extract_product_details(self, html: str) -> Dict[str, Any]:
        """Извлекает детальную информацию о товаре"""
        soup = self._parse_html(html)
        
        details = {
            'description': '',
            'characteristics': {},
            'source': 'wildberries'
        }
        
        # Извлечение описания
        desc_elem = soup.find('div', class_='product-page__description')
        if desc_elem:
            details['description'] = desc_elem.get_text(strip=True)
        
        # Извлечение характеристик
        char_section = soup.find('div', class_='product-page__characteristics')
        if char_section:
            for row in char_section.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) == 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    details['characteristics'][key] = value
        
        return details

