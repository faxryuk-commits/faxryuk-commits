from typing import Dict, List, Any, Optional
from urllib.parse import urlencode, quote
from .base_marketplace import BaseMarketplaceParser
import re
import logging

logger = logging.getLogger(__name__)


class UzumParser(BaseMarketplaceParser):
    """Парсер для Uzum Market (uzum.uz)"""
    
    BASE_URL = "https://uzum.uz"
    SEARCH_URL = "https://uzum.uz/ru/search"
    
    def __init__(self, **kwargs):
        super().__init__(base_url=self.BASE_URL, **kwargs)
        # Устанавливаем заголовки для Uzum
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,uz;q=0.8',
            'Referer': f'{self.BASE_URL}/',
            'Origin': self.BASE_URL,
        })
        # Инициализируем сессию
        self._init_session()
    
    def _init_session(self):
        """Инициализирует сессию, получая куки с главной страницы"""
        try:
            response = self.session.get(self.BASE_URL, timeout=10)
            if response.status_code == 200:
                logger.info("Сессия Uzum Market инициализирована")
            else:
                logger.warning(f"Не удалось получить куки, статус: {response.status_code}")
        except Exception as e:
            logger.warning(f"Ошибка инициализации сессии: {e}")
    
    def _build_search_url(self, query: str) -> str:
        """Формирует URL для поиска"""
        return f"{self.SEARCH_URL}?query={quote(query)}"
    
    def _extract_products(self, html: str) -> List[Dict[str, Any]]:
        """Извлекает товары из HTML страницы"""
        soup = self._parse_html(html)
        products = []
        
        # Ищем карточки товаров - пробуем разные селекторы
        product_cards = []
        
        # Пробуем разные варианты селекторов
        selectors = [
            soup.find_all('div', class_='product-card'),
            soup.find_all('div', {'data-product-id': True}),
            soup.find_all('article', class_='product'),
            soup.find_all('div', class_='item'),
            soup.find_all('a', href=True, class_=lambda x: x and 'product' in x.lower()),
            soup.find_all('div', class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower())),
            # Универсальные селекторы
            soup.find_all('div', {'data-id': True}),
            soup.find_all('article'),
            # По структуре - если есть ссылка и изображение, возможно это товар
            [elem for elem in soup.find_all('div') if elem.find('a') and elem.find('img')],
        ]
        
        for selector_result in selectors:
            if selector_result:
                product_cards = selector_result
                logger.info(f"Найдено {len(product_cards)} карточек товаров используя селектор")
                break
        
        if not product_cards:
            logger.warning("Карточки товаров не найдены. Пробуем универсальный подход.")
            # Пробуем найти все div с ссылками и изображениями
            all_divs = soup.find_all('div')
            for div in all_divs:
                if div.find('a') and div.find('img') and div.find(string=True):
                    product_cards.append(div)
                    if len(product_cards) >= 20:  # Ограничиваем количество проверок
                        break
            logger.info(f"Найдено {len(product_cards)} потенциальных карточек универсальным методом")
            
            # Если всё еще ничего не найдено, логируем структуру HTML для отладки
            if not product_cards:
                logger.error(f"Карточки товаров не найдены. Первые 1000 символов HTML: {html[:1000]}")
                # Пробуем найти хотя бы любые ссылки
                all_links = soup.find_all('a', href=True)
                logger.warning(f"Найдено {len(all_links)} ссылок на странице")
                if all_links:
                    # Берем первые 10 ссылок как потенциальные товары
                    for link in all_links[:10]:
                        parent = link.find_parent('div') or link.find_parent('article')
                        if parent:
                            product_cards.append(parent)
                    logger.info(f"Добавлено {len(product_cards)} карточек на основе ссылок")
        
        for i, card in enumerate(product_cards):
            try:
                product = self._extract_product_from_card(card)
                
                if not product:
                    logger.debug(f"Карточка {i+1}: не удалось извлечь данные")
                    continue
                
                # Валидация обязательных полей перед добавлением
                if self._validate_product_data(product):
                    products.append(product)
                    logger.debug(f"Карточка {i+1}: товар добавлен - {product.get('name', 'N/A')[:50]}")
                else:
                    logger.warning(f"Карточка {i+1}: товар не прошел валидацию - {product.get('name', 'N/A')[:50]}, поля: name={bool(product.get('name'))}, url={bool(product.get('url'))}, source={bool(product.get('source'))}")
                    
            except Exception as e:
                logger.warning(f"Ошибка обработки карточки товара {i+1}: {e}", exc_info=True)
                continue
        
        logger.info(f"Итого извлечено {len(products)} валидных товаров из {len(product_cards)} карточек")
        
        return products
    
    def _extract_product_from_card(self, card) -> Dict[str, Any]:
        """Извлекает данные товара из карточки"""
        # Название товара - пробуем разные варианты
        name = ''
        name_selectors = [
            ('h3', None),
            ('h2', None),
            ('h4', None),
            ('a', {'class': lambda x: x and 'product-title' in str(x).lower()}),
            ('a', {'class': lambda x: x and 'title' in str(x).lower()}),
            ('span', {'class': lambda x: x and 'product-name' in str(x).lower()}),
            ('span', {'class': lambda x: x and 'name' in str(x).lower()}),
            ('div', {'class': lambda x: x and 'title' in str(x).lower()}),
            ('a', {'href': True}),
        ]
        
        for tag, attrs in name_selectors:
            if attrs:
                name_elem = card.find(tag, attrs) if isinstance(attrs, dict) else card.find(tag, class_=attrs)
            else:
                name_elem = card.find(tag)
            
            if name_elem:
                name = name_elem.get_text(strip=True)
                if name and len(name) > 3:  # Минимальная длина названия
                    break
        
        # Если название не найдено, пробуем взять текст из всей карточки
        if not name or len(name) < 3:
            # Находим ссылку и берем её текст или title
            link = card.find('a', href=True)
            if link:
                name = link.get_text(strip=True) or link.get('title', '') or link.get('aria-label', '')
                if not name:
                    # Берем href и извлекаем из него
                    href = link.get('href', '')
                    import re
                    match = re.search(r'/([^/]+)/?$', href)
                    if match:
                        name = match.group(1).replace('-', ' ').replace('_', ' ')
        
        # Если название все еще пустое, пропускаем
        if not name or len(name) < 3:
            logger.debug(f"Название товара не найдено в карточке")
            return {}
        
        # URL товара
        link_elem = card.find('a', href=True)
        url = ''
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('http'):
                url = href
            elif href.startswith('/'):
                url = f"{self.BASE_URL}{href}"
            else:
                url = f"{self.BASE_URL}/{href}"
        
        # Если URL пустой, создаем из названия (fallback)
        if not url:
            url = f"{self.SEARCH_URL}?query={quote(name[:50])}"
            logger.debug(f"URL создан из названия (fallback): {url}")
        
        # Цена - пробуем разные варианты
        price_text = '0'
        price_selectors = [
            ('span', {'class': lambda x: x and 'price' in str(x).lower()}),
            ('div', {'class': lambda x: x and 'price' in str(x).lower()}),
            ('span', {'data-price': True}),
            ('ins', {'class': lambda x: x and 'price' in str(x).lower()}),
            ('strong', {'class': lambda x: x and 'price' in str(x).lower()}),
            ('b', {'class': lambda x: x and 'price' in str(x).lower()}),
        ]
        
        for tag, attrs in price_selectors:
            price_elem = card.find(tag, attrs) if isinstance(attrs, dict) else card.find(tag, class_=attrs)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                if price_text and re.search(r'\d', price_text):
                    break
        
        # Если цена не найдена, ищем любые числа, похожие на цены
        if not price_text or price_text == '0':
            # Ищем все числа в тексте карточки
            card_text = card.get_text()
            import re
            numbers = re.findall(r'\d+[\s,]*\d*', card_text)
            if numbers:
                # Берем самое большое число (вероятно это цена)
                try:
                    max_num = max([int(re.sub(r'[\s,]', '', n)) for n in numbers if len(n) > 3])
                    if max_num > 1000:  # Разумная минимальная цена
                        price_text = str(max_num)
                except:
                    pass
        
        price = self._parse_price(price_text)
        
        # ID товара
        product_id = (
            card.get('data-product-id') or
            card.get('data-id') or
            self._extract_id_from_url(url)
        )
        
        # Рейтинг
        rating_elem = (
            card.find('span', class_='rating') or
            card.find('div', class_='rating') or
            card.find('span', {'data-rating': True})
        )
        rating = 0.0
        if rating_elem:
            rating_text = rating_elem.get('data-rating') or rating_elem.get_text(strip=True)
            try:
                rating = float(re.search(r'[\d.]+', str(rating_text)).group())
            except:
                rating = 0.0
        
        # Количество отзывов
        reviews_elem = (
            card.find('span', class_='reviews') or
            card.find('div', class_='reviews-count')
        )
        reviews_count = 0
        if reviews_elem:
            reviews_text = reviews_elem.get_text(strip=True)
            match = re.search(r'\d+', reviews_text)
            if match:
                reviews_count = int(match.group())
        
        # Изображение
        img_elem = card.find('img')
        image_url = ''
        if img_elem:
            image_url = (
                img_elem.get('src') or
                img_elem.get('data-src') or
                img_elem.get('data-lazy-src') or
                ''
            )
            if image_url and not image_url.startswith('http'):
                if image_url.startswith('//'):
                    image_url = f"https:{image_url}"
                elif image_url.startswith('/'):
                    image_url = f"{self.BASE_URL}{image_url}"
        
        # Бренд (опционально)
        brand_elem = (
            card.find('span', class_='brand') or
            card.find('div', class_='brand') or
            card.find('a', class_='brand-link')
        )
        brand = brand_elem.get_text(strip=True) if brand_elem else None
        
        # Формируем словарь товара
        product = {
            'id': str(product_id) if product_id else None,
            'name': name.strip(),
            'brand': brand,
            'price': float(price),
            'rating': float(rating),
            'reviews_count': int(reviews_count),
            'url': url.strip(),
            'image_url': image_url,
            'source': 'uzum'
        }
        
        return product
    
    def _parse_price(self, price_text: str) -> float:
        """Парсит цену из текста (в сумах)"""
        # Удаляем все кроме цифр и пробелов
        cleaned = re.sub(r'[^\d\s]', '', price_text.replace(',', ' '))
        # Удаляем все пробелы и извлекаем число
        cleaned = cleaned.replace(' ', '')
        try:
            return float(cleaned) if cleaned else 0.0
        except (ValueError, AttributeError):
            return 0.0
    
    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Извлекает ID товара из URL"""
        if not url:
            return None
        
        # Пытаемся найти ID в URL (разные форматы)
        patterns = [
            r'/product/(\d+)',
            r'/item/(\d+)',
            r'/p/(\d+)',
            r'id=(\d+)',
            r'/(\d+)/',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _validate_product_data(self, product: Dict[str, Any]) -> bool:
        """Строгая валидация данных товара перед добавлением"""
        if not product or not isinstance(product, dict):
            return False
        
        # Проверяем обязательные поля для модели Product
        required_fields = ['name', 'url', 'source']
        
        for field in required_fields:
            if field not in product:
                logger.debug(f"Отсутствует обязательное поле: {field}")
                return False
            
            value = product[field]
            if not value or (isinstance(value, str) and not value.strip()):
                # Для URL разрешаем fallback (поисковый запрос)
                if field == 'url' and self.SEARCH_URL in str(value):
                    continue
                logger.debug(f"Поле {field} пустое или невалидное: {value}")
                return False
        
        # Проверяем типы данных
        if not isinstance(product.get('name'), str):
            return False
        
        if not isinstance(product.get('url'), str):
            return False
        
        if not isinstance(product.get('source'), str):
            return False
        
        # Проверяем, что цена не отрицательная
        price = product.get('price', 0)
        if price < 0:
            product['price'] = 0.0
        
        # Нормализуем числовые поля
        try:
            product['price'] = float(product.get('price', 0))
            product['rating'] = float(product.get('rating', 0))
            product['reviews_count'] = int(product.get('reviews_count', 0))
        except (ValueError, TypeError):
            product['price'] = 0.0
            product['rating'] = 0.0
            product['reviews_count'] = 0
        
        return True
    
    def _extract_product_details(self, html: str) -> Dict[str, Any]:
        """Извлекает детальную информацию о товаре"""
        soup = self._parse_html(html)
        
        details = {
            'description': '',
            'characteristics': {},
            'source': 'uzum'
        }
        
        # Описание
        desc_elem = (
            soup.find('div', class_='description') or
            soup.find('div', class_='product-description') or
            soup.find('div', {'data-description': True})
        )
        if desc_elem:
            details['description'] = desc_elem.get_text(strip=True)
        
        # Характеристики
        char_section = (
            soup.find('div', class_='characteristics') or
            soup.find('table', class_='specifications') or
            soup.find('dl', class_='specs')
        )
        
        if char_section:
            # Пробуем разные форматы характеристик
            rows = char_section.find_all('tr') or char_section.find_all('div', class_='spec-row')
            
            for row in rows:
                if row.name == 'tr':
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value:
                            details['characteristics'][key] = value
                elif 'spec-row' in str(row.get('class', [])):
                    key_elem = row.find('span', class_='spec-key') or row.find('div', class_='key')
                    value_elem = row.find('span', class_='spec-value') or row.find('div', class_='value')
                    if key_elem and value_elem:
                        key = key_elem.get_text(strip=True)
                        value = value_elem.get_text(strip=True)
                        if key and value:
                            details['characteristics'][key] = value
        
        return details
