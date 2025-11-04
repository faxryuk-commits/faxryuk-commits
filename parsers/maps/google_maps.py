from typing import Dict, List, Any, Optional
from urllib.parse import quote, urlencode
from .base_maps import BaseMapsParser
from bs4 import BeautifulSoup
import json
import re


class GoogleMapsParser(BaseMapsParser):
    """Парсер для Google Maps"""
    
    BASE_URL = "https://www.google.com/maps"
    SEARCH_URL = "https://www.google.com/maps/search"
    
    def __init__(self, **kwargs):
        super().__init__(base_url=self.BASE_URL, **kwargs)
    
    def _build_search_url(self, query: str, location: Optional[str] = None) -> str:
        """Формирует URL для поиска"""
        search_query = query
        if location:
            search_query = f"{query} {location}"
        return f"{self.SEARCH_URL}/{quote(search_query)}"
    
    def _extract_organizations(
        self,
        html: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Извлекает организации из HTML Google Maps
        
        Примечание: Google Maps использует JavaScript для загрузки данных,
        поэтому для полного парсинга может потребоваться Selenium
        """
        soup = BeautifulSoup(html, 'lxml')
        organizations = []
        
        # Поиск JSON данных в скриптах
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Пытаемся найти JSON с данными
                match = re.search(r'\[null,null,null,null,"([^"]+)"', script.string)
                if match:
                    try:
                        # Google Maps встраивает данные в JSON
                        # Это упрощенная версия - в реальности нужен более сложный парсинг
                        pass
                    except:
                        continue
        
        # Альтернативный способ - парсинг HTML структуры
        results = soup.find_all('div', class_='section-result')
        
        for result in results:
            try:
                org = {
                    'name': '',
                    'address': '',
                    'rating': 0.0,
                    'reviews_count': 0,
                    'phone': '',
                    'website': '',
                    'category': '',
                    'coordinates': None,
                    'source': 'google_maps'
                }
                
                # Название
                name_elem = result.find('h3', class_='section-result-title')
                if name_elem:
                    org['name'] = name_elem.get_text(strip=True)
                
                # Адрес
                address_elem = result.find('span', class_='section-result-location')
                if address_elem:
                    org['address'] = address_elem.get_text(strip=True)
                
                # Рейтинг
                rating_elem = result.find('span', class_='cards-rating-score')
                if rating_elem:
                    try:
                        org['rating'] = float(rating_elem.get_text(strip=True))
                    except:
                        pass
                
                # Количество отзывов
                reviews_elem = result.find('span', class_='section-result-num-ratings')
                if reviews_elem:
                    reviews_text = reviews_elem.get_text(strip=True)
                    org['reviews_count'] = self._parse_reviews_count(reviews_text)
                
                # URL организации
                link_elem = result.find('a', href=True)
                if link_elem:
                    org['url'] = f"{self.BASE_URL}{link_elem.get('href', '')}"
                
                if self.validate_data(org) and org['name']:
                    organizations.append(org)
                    
            except Exception as e:
                import logging
                logging.warning(f"Ошибка парсинга организации: {e}")
                continue
        
        return organizations
    
    def _parse_reviews_count(self, text: str) -> int:
        """Парсит количество отзывов из текста"""
        import re
        match = re.search(r'(\d+)', text.replace(' ', ''))
        if match:
            return int(match.group(1))
        return 0
    
    def _extract_organization_details(self, html: str) -> Dict[str, Any]:
        """Извлекает детальную информацию об организации"""
        soup = BeautifulSoup(html, 'lxml')
        
        details = {
            'description': '',
            'working_hours': {},
            'photos': [],
            'source': 'google_maps'
        }
        
        # Часы работы
        hours_section = soup.find('div', class_='section-open-hours-container')
        if hours_section:
            for day_elem in hours_section.find_all('tr'):
                day_name = day_elem.find('td', class_='section-open-hours-label')
                day_hours = day_elem.find('td', class_='section-open-hours-value')
                if day_name and day_hours:
                    details['working_hours'][day_name.get_text(strip=True)] = \
                        day_hours.get_text(strip=True)
        
        # Описание
        desc_elem = soup.find('div', class_='section-editorial')
        if desc_elem:
            details['description'] = desc_elem.get_text(strip=True)
        
        return details

