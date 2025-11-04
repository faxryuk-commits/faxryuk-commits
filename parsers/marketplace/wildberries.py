from typing import Dict, List, Any, Optional
from urllib.parse import urlencode, quote
from .base_marketplace import BaseMarketplaceParser


class WildberriesParser(BaseMarketplaceParser):
    """Парсер для Wildberries"""
    
    BASE_URL = "https://www.wildberries.ru"
    SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v4/search"
    
    def __init__(self, **kwargs):
        super().__init__(base_url=self.BASE_URL, **kwargs)
        # Добавляем специфичные заголовки для Wildberries API
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    
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
        response = self._make_request(url)
        
        if not response:
            logger.warning("Не удалось получить ответ от API, пробуем веб-версию")
            # Fallback на веб-версию
            web_url = f"{self.BASE_URL}/catalog/0/search.aspx?search={quote(query)}"
            response = self._make_request(web_url)
            if not response:
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
            
            # Ищем карточки товаров (селекторы могут меняться)
            product_cards = soup.find_all('article', class_='product-card') or \
                          soup.find_all('div', class_='product-card') or \
                          soup.find_all('div', {'data-product-id': True})
            
            logger.info(f"Найдено {len(product_cards)} карточек товаров в HTML")
            
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
                            match = re.search(r'/(\d+)/', href)
                            if match:
                                product_id = match.group(1)
                    
                    # Название
                    name_elem = card.find('span', class_='product-card__name') or \
                               card.find('a', class_='product-card__name') or \
                               card.find('h3') or \
                               card.find('span', {'data-product-name': True})
                    name = name_elem.get_text(strip=True) if name_elem else ''
                    
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
                    
                    if name and product_id:
                        product = {
                            'id': str(product_id),
                            'name': name,
                            'brand': '',
                            'price': price,
                            'rating': rating,
                            'reviews_count': 0,
                            'url': f"{self.BASE_URL}/catalog/{product_id}/detail.aspx",
                            'image_url': '',
                            'source': 'wildberries'
                        }
                        products.append(product)
                        
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
            
            if 'data' in data and 'products' in data['data']:
                products_data = data['data']['products']
            elif 'products' in data:
                products_data = data['products']
            elif 'data' in data and isinstance(data['data'], list):
                products_data = data['data']
            
            if products_data:
                logger.info(f"Найдено {len(products_data)} товаров в ответе API")
                for item in products_data:
                    try:
                        product = {
                            'id': str(item.get('id', '')) if item.get('id') else None,
                            'name': item.get('name', '') or item.get('title', '') or '',
                            'brand': item.get('brand', '') or item.get('brandName', ''),
                            'price': (item.get('salePriceU', 0) / 100) if item.get('salePriceU') else (item.get('priceU', 0) / 100) if item.get('priceU') else 0,
                            'rating': item.get('rating', 0) or item.get('reviewRating', 0),
                            'reviews_count': item.get('feedbacks', 0) or item.get('reviewCount', 0),
                            'url': f"{self.BASE_URL}/catalog/{item.get('id')}/detail.aspx" if item.get('id') else '',
                            'image_url': self._get_image_url(item.get('id'), item.get('root')),
                            'source': 'wildberries'
                        }
                        
                        if self.validate_data(product) and product.get('name'):
                            products.append(product)
                    except Exception as e:
                        logger.warning(f"Ошибка обработки товара: {e}")
                        continue
            
            if not products:
                logger.warning(f"Товары не найдены. Структура ответа: {list(data.keys())[:5]}")
                # Пробуем веб-версию как fallback
                if not html.startswith('{'):
                    return self._extract_products_from_html(html)
            
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

