from typing import Dict, List, Any, Optional
from urllib.parse import urlencode, quote
from .base_marketplace import BaseMarketplaceParser


class OzonParser(BaseMarketplaceParser):
    """Парсер для Ozon"""
    
    BASE_URL = "https://www.ozon.ru"
    SEARCH_API_URL = "https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2"
    
    def __init__(self, **kwargs):
        super().__init__(base_url=self.BASE_URL, **kwargs)
    
    def _build_search_url(self, query: str) -> str:
        """Формирует URL для поиска через API"""
        # Ozon использует POST запросы к API, но можно попробовать через веб-версию
        return f"{self.BASE_URL}/search/?text={quote(query)}"
    
    def _extract_products(self, html: str) -> List[Dict[str, Any]]:
        """Извлекает товары из HTML страницы"""
        soup = self._parse_html(html)
        products = []
        
        # Поиск карточек товаров (селекторы могут измениться)
        product_cards = soup.find_all('div', {'data-widget': 'searchResultsV2'})
        
        if not product_cards:
            # Альтернативный селектор
            product_cards = soup.find_all('div', class_='tile-root')
        
        for card in product_cards:
            try:
                # Название товара
                name_elem = card.find('span', class_='tsBodyL') or card.find('a', class_='tile-hover-target')
                name = name_elem.get_text(strip=True) if name_elem else ''
                
                # Цена
                price_elem = card.find('span', class_='tsHeadline')
                price_text = price_elem.get_text(strip=True) if price_elem else '0'
                price = self._parse_price(price_text)
                
                # URL товара
                link_elem = card.find('a', href=True)
                url = f"{self.BASE_URL}{link_elem['href']}" if link_elem else ''
                
                # Рейтинг
                rating_elem = card.find('div', class_='rating')
                rating = float(rating_elem.get('data-rating', 0)) if rating_elem else 0
                
                # ID товара (из URL или data атрибута)
                product_id = None
                if link_elem and link_elem.get('href'):
                    # Пытаемся извлечь ID из URL
                    import re
                    match = re.search(r'/product/(\d+)', link_elem['href'])
                    if match:
                        product_id = match.group(1)
                
                product = {
                    'id': product_id,
                    'name': name,
                    'price': price,
                    'rating': rating,
                    'url': url,
                    'image_url': self._extract_image_url(card),
                    'source': 'ozon'
                }
                
                if self.validate_data(product) and name:
                    products.append(product)
                    
            except Exception as e:
                import logging
                logging.warning(f"Ошибка парсинга карточки товара: {e}")
                continue
        
        return products
    
    def _parse_price(self, price_text: str) -> float:
        """Парсит цену из текста"""
        import re
        # Удаляем все кроме цифр, точки и запятой
        cleaned = re.sub(r'[^\d,.]', '', price_text.replace(' ', ''))
        cleaned = cleaned.replace(',', '.')
        try:
            return float(cleaned)
        except:
            return 0.0
    
    def _extract_image_url(self, card) -> str:
        """Извлекает URL изображения товара"""
        img_elem = card.find('img')
        if img_elem:
            return img_elem.get('src') or img_elem.get('data-src', '')
        return ''
    
    def _extract_product_details(self, html: str) -> Dict[str, Any]:
        """Извлекает детальную информацию о товаре"""
        soup = self._parse_html(html)
        
        details = {
            'description': '',
            'characteristics': {},
            'source': 'ozon'
        }
        
        # Описание
        desc_elem = soup.find('div', {'data-widget': 'webDescription'})
        if desc_elem:
            details['description'] = desc_elem.get_text(strip=True)
        
        # Характеристики
        char_section = soup.find('dl', class_='characteristics')
        if char_section:
            dt_elements = char_section.find_all('dt')
            dd_elements = char_section.find_all('dd')
            
            for dt, dd in zip(dt_elements, dd_elements):
                key = dt.get_text(strip=True)
                value = dd.get_text(strip=True)
                details['characteristics'][key] = value
        
        return details

