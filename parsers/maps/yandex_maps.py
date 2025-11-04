from typing import Dict, List, Any, Optional
from urllib.parse import quote, urlencode
from .base_maps import BaseMapsParser
from bs4 import BeautifulSoup
import json
import re


class YandexMapsParser(BaseMapsParser):
    """Парсер для Яндекс.Карт"""
    
    BASE_URL = "https://yandex.ru/maps"
    SEARCH_API_URL = "https://yandex.ru/maps/api/search"
    
    def __init__(self, **kwargs):
        super().__init__(base_url=self.BASE_URL, **kwargs)
        # Яндекс.Карты требуют специальные заголовки
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Referer': 'https://yandex.ru/',
            'Origin': 'https://yandex.ru',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        })
    
    def _build_search_url(self, query: str, location: Optional[str] = None) -> str:
        """Формирует URL для поиска"""
        search_query = query
        if location:
            search_query = f"{query}, {location}"
        return f"{self.BASE_URL}/?text={quote(search_query)}"
    
    def _extract_organizations(
        self,
        html: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """Извлекает организации из HTML Яндекс.Карт"""
        soup = BeautifulSoup(html, 'lxml')
        organizations = []
        
        # Поиск результатов в JSON (Яндекс часто использует JSON в data атрибутах)
        scripts = soup.find_all('script', type='application/json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Парсинг JSON структуры Яндекс.Карт
                if isinstance(data, dict) and 'searchResults' in data:
                    results = data['searchResults']
                    # Обработка результатов...
            except:
                continue
        
        # Альтернативный способ - парсинг HTML
        search_results = soup.find_all('li', class_='search-snippet-view') or \
                        soup.find_all('div', class_='search-business-snippet-view')
        
        for result in search_results:
            try:
                org = {
                    'name': '',
                    'address': '',
                    'rating': 0.0,
                    'reviews_count': 0,
                    'phone': '',
                    'category': '',
                    'coordinates': None,
                    'source': 'yandex_maps'
                }
                
                # Название
                name_elem = result.find('span', class_='search-snippet-view__body-title') or \
                           result.find('a', class_='search-business-snippet-view__title')
                if name_elem:
                    org['name'] = name_elem.get_text(strip=True)
                
                # Адрес
                address_elem = result.find('span', class_='search-snippet-view__address') or \
                              result.find('span', class_='business-contacts-view__address')
                if address_elem:
                    org['address'] = address_elem.get_text(strip=True)
                
                # Рейтинг
                rating_elem = result.find('span', class_='rating-view__rating')
                if rating_elem:
                    rating_text = rating_elem.get_text(strip=True)
                    try:
                        org['rating'] = float(rating_text.replace(',', '.'))
                    except:
                        pass
                
                # Количество отзывов
                reviews_elem = result.find('span', class_='rating-view__count')
                if reviews_elem:
                    reviews_text = reviews_elem.get_text(strip=True)
                    org['reviews_count'] = self._parse_reviews_count(reviews_text)
                
                # Телефон
                phone_elem = result.find('span', class_='business-contacts-view__phone')
                if phone_elem:
                    org['phone'] = phone_elem.get_text(strip=True)
                
                # Категория
                category_elem = result.find('div', class_='search-snippet-view__body-subtitle')
                if category_elem:
                    org['category'] = category_elem.get_text(strip=True)
                
                # URL
                link_elem = result.find('a', href=True)
                if link_elem:
                    href = link_elem.get('href', '')
                    if href.startswith('/'):
                        org['url'] = f"{self.BASE_URL}{href}"
                    else:
                        org['url'] = href
                
                # Координаты (из data атрибутов)
                if result.get('data-coordinates'):
                    coords = result['data-coordinates'].split(',')
                    if len(coords) == 2:
                        org['coordinates'] = {
                            'lat': float(coords[0]),
                            'lon': float(coords[1])
                        }
                
                if self.validate_data(org) and org['name']:
                    organizations.append(org)
                    
            except Exception as e:
                import logging
                logging.warning(f"Ошибка парсинга организации: {e}")
                continue
        
        return organizations
    
    def _parse_reviews_count(self, text: str) -> int:
        """Парсит количество отзывов"""
        import re
        # Удаляем скобки и пробелы
        cleaned = re.sub(r'[^\d]', '', text)
        try:
            return int(cleaned)
        except:
            return 0
    
    def _extract_organization_details(self, html: str) -> Dict[str, Any]:
        """Извлекает детальную информацию об организации"""
        soup = BeautifulSoup(html, 'lxml')
        
        details = {
            'description': '',
            'working_hours': {},
            'photos': [],
            'source': 'yandex_maps'
        }
        
        # Часы работы
        hours_section = soup.find('div', class_='business-contacts-view__schedule')
        if hours_section:
            for day_elem in hours_section.find_all('div', class_='business-contacts-view__schedule-day'):
                day_name = day_elem.find('span', class_='business-contacts-view__schedule-day-name')
                day_hours = day_elem.find('span', class_='business-contacts-view__schedule-day-hours')
                if day_name and day_hours:
                    details['working_hours'][day_name.get_text(strip=True)] = \
                        day_hours.get_text(strip=True)
        
        # Описание
        desc_elem = soup.find('div', class_='business-description-view__description')
        if desc_elem:
            details['description'] = desc_elem.get_text(strip=True)
        
        # Фото
        photos_section = soup.find('div', class_='business-photos-view')
        if photos_section:
            for img in photos_section.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src:
                    details['photos'].append(src)
        
        return details

