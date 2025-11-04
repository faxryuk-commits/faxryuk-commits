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
        logger = logging.getLogger(__name__)
        
        try:
            # Делаем запрос на главную страницу для получения кук
            response = self.session.get(self.BASE_URL, timeout=10)
            if response.status_code == 200:
                logger.info("Сессия Wildberries инициализирована, куки получены")
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
        Парсит результаты поиска
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
        
        Returns:
            Список товаров
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Сначала пробуем API
        url = self._build_search_url(query)
        logger.info(f"Запрос к Wildberries API: {url}")
        
        # Устанавливаем правильные заголовки для API запроса
        api_headers = {
            'Accept': 'application/json',
            'Referer': f'{self.BASE_URL}/',
            'Origin': self.BASE_URL,
        }
        
        response = self._make_request(url, headers=api_headers)
        
        # Проверяем статус ответа
        if response:
            logger.info(f"Статус ответа API: {response.status_code}")
            if response.status_code != 200:
                logger.warning(f"API вернул статус {response.status_code}")
        
        if not response or response.status_code != 200:
            logger.warning("Не удалось получить ответ от API, пробуем веб-версию")
            # Fallback на веб-версию с правильными заголовками
            web_headers = {
                'Accept': 'text/html,application/xhtml+xml',
                'Referer': f'{self.BASE_URL}/',
            }
            web_url = f"{self.BASE_URL}/catalog/0/search.aspx?search={quote(query)}"
            response = self._make_request(web_url, headers=web_headers)
            if not response:
                logger.error("Не удалось получить ответ от веб-версии")
                return []
        
        products = self._extract_products(response.text)
        
        if limit:
            products = products[:limit]
        
        logger.info(f"Получено товаров: {len(products)}")
        return products
    
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
                logger.info(f"Найдено {len(products_data)} товаров в ответе API (путь: {key if 'key' in locals() else 'unknown'})")
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
                    # Если это JSON, но товаров нет, логируем всю структуру для отладки
                    logger.warning(f"Товары не найдены. Полная структура ответа (первые 1000 символов): {str(data)[:1000]}")
                    
                    # Пробуем найти любые массивы в ответе
                    def find_arrays(obj, path=""):
                        """Рекурсивно ищем массивы в структуре"""
                        arrays = []
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if isinstance(value, list) and len(value) > 0:
                                    # Проверяем, похож ли первый элемент на товар
                                    first = value[0] if value else {}
                                    if isinstance(first, dict) and any(k in first for k in ['id', 'nmId', 'name', 'title']):
                                        arrays.append((f"{path}.{key}" if path else key, value))
                                elif isinstance(value, dict):
                                    arrays.extend(find_arrays(value, f"{path}.{key}" if path else key))
                        elif isinstance(obj, list) and len(obj) > 0:
                            first = obj[0]
                            if isinstance(first, dict) and any(k in first for k in ['id', 'nmId', 'name', 'title']):
                                arrays.append((path or "root", obj))
                        return arrays
                    
                    found_arrays = find_arrays(data)
                    if found_arrays:
                        logger.info(f"Найдены потенциальные массивы товаров: {[path for path, _ in found_arrays]}")
                        # Берем первый найденный массив
                        _, products_data = found_arrays[0]
                        logger.info(f"Пробуем использовать массив из {found_arrays[0][0]} с {len(products_data)} элементами")
                        # Обрабатываем найденный массив
                        for item in products_data[:10]:  # Ограничиваем для теста
                            try:
                                product_id = item.get('id') or item.get('nmId') or item.get('nm_id')
                                name = item.get('name') or item.get('title') or item.get('goodsName') or ''
                                if name:
                                    product = {
                                        'id': str(product_id) if product_id else None,
                                        'name': name.strip(),
                                        'price': float(item.get('price', 0) or item.get('salePriceU', 0) / 100 if item.get('salePriceU') else 0),
                                        'url': f"{self.BASE_URL}/catalog/{product_id}/detail.aspx" if product_id else f"{self.BASE_URL}/catalog/0/search.aspx?search={quote(name[:50])}",
                                        'source': 'wildberries'
                                    }
                                    if self.validate_data(product):
                                        products.append(product)
                            except:
                                continue
            
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

