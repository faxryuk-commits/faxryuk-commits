from typing import Dict, List, Any, Optional
from urllib.parse import urlencode, quote
from .base_marketplace import BaseMarketplaceParser


class WildberriesParser(BaseMarketplaceParser):
    """Парсер для Wildberries"""
    
    BASE_URL = "https://www.wildberries.ru"
    SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v4/search"
    
    def __init__(self, **kwargs):
        super().__init__(base_url=self.BASE_URL, **kwargs)
    
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
            'dest': -1257786,
            'lang': 'ru',
            'locale': 'ru',
            'reg': 0,
            'regions': '80,38,83,4,64,33,68,70,30,40,86,75,69,1,31,66,22,48,71',
        }
        return f"{self.SEARCH_URL}?{urlencode(params)}"
    
    def _extract_products(self, html: str) -> List[Dict[str, Any]]:
        """Извлекает товары из JSON ответа API"""
        try:
            import json
            data = json.loads(html)
            
            products = []
            if 'data' in data and 'products' in data['data']:
                for item in data['data']['products']:
                    product = {
                        'id': item.get('id'),
                        'name': item.get('name', ''),
                        'brand': item.get('brand', ''),
                        'price': item.get('salePriceU', 0) / 100 if item.get('salePriceU') else 0,
                        'rating': item.get('rating', 0),
                        'reviews_count': item.get('feedbacks', 0),
                        'url': f"{self.BASE_URL}/catalog/{item.get('id')}/detail.aspx",
                        'image_url': self._get_image_url(item.get('id'), item.get('root')),
                        'source': 'wildberries'
                    }
                    
                    if self.validate_data(product):
                        products.append(product)
            
            return products
            
        except Exception as e:
            import logging
            logging.error(f"Ошибка извлечения товаров: {e}")
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

