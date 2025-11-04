from typing import Dict, List, Any, Optional
from urllib.parse import quote, urlencode
from .base_maps import BaseMapsParser
from bs4 import BeautifulSoup
import json
import re


class TwoGISParser(BaseMapsParser):
    """Парсер для 2ГИС"""
    
    BASE_URL = "https://2gis.ru"
    SEARCH_URL = "https://2gis.ru/search"
    
    def __init__(self, city: str = "moscow", **kwargs):
        """
        Args:
            city: Город для поиска (moscow, spb, ekb и т.д.)
        """
        super().__init__(base_url=self.BASE_URL, **kwargs)
        self.city = city
        self.session.headers.update({
            'Referer': f'https://2gis.ru/{city}/',
        })
    
    def _build_search_url(self, query: str, location: Optional[str] = None) -> str:
        """Формирует URL для поиска"""
        # 2ГИС использует формат /city/search/query
        search_query = query
        if location and location.lower() != self.city:
            search_query = f"{query} {location}"
        return f"{self.BASE_URL}/{self.city}/search/{quote(search_query)}"
    
    def _extract_organizations(
        self,
        html: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """Извлекает организации из HTML 2ГИС"""
        soup = BeautifulSoup(html, 'lxml')
        organizations = []
        
        # 2ГИС использует data-атрибуты с JSON
        search_results = soup.find_all('div', class_='_11gvyqv') or \
                        soup.find_all('a', class_='_1rehek') or \
                        soup.find_all('div', attrs={'data-id': True})
        
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
                    'source': '2gis'
                }
                
                # Название
                name_elem = result.find('span', class_='_1al0wlf') or \
                           result.find('div', class_='_1hf7139') or \
                           result.find('span', class_='card-title')
                if name_elem:
                    org['name'] = name_elem.get_text(strip=True)
                
                # Если название не найдено, пробуем из data-атрибутов
                if not org['name'] and result.get('data-name'):
                    org['name'] = result['data-name']
                
                # Адрес
                address_elem = result.find('span', class_='_1w9o2np') or \
                              result.find('div', class_='_1p8iqzw') or \
                              result.find('span', class_='card-address')
                if address_elem:
                    org['address'] = address_elem.get_text(strip=True)
                
                # Рейтинг
                rating_elem = result.find('span', class_='_15t2ov5') or \
                             result.find('div', class_='rating')
                if rating_elem:
                    rating_text = rating_elem.get_text(strip=True)
                    # Пытаемся извлечь рейтинг
                    match = re.search(r'(\d+[,.]?\d*)', rating_text)
                    if match:
                        try:
                            org['rating'] = float(match.group(1).replace(',', '.'))
                        except:
                            pass
                
                # Количество отзывов
                reviews_elem = result.find('span', class_='_1yq1mhs') or \
                              result.find('span', class_='reviews-count')
                if reviews_elem:
                    reviews_text = reviews_elem.get_text(strip=True)
                    org['reviews_count'] = self._parse_reviews_count(reviews_text)
                
                # Телефон
                phone_elem = result.find('span', class_='_1a0t4pb') or \
                            result.find('span', class_='phone')
                if phone_elem:
                    org['phone'] = phone_elem.get_text(strip=True)
                
                # Категория
                category_elem = result.find('span', class_='_12l6h96') or \
                               result.find('div', class_='rubric')
                if category_elem:
                    org['category'] = category_elem.get_text(strip=True)
                
                # URL
                if result.name == 'a' and result.get('href'):
                    href = result['href']
                    if href.startswith('/'):
                        org['url'] = f"{self.BASE_URL}{href}"
                    else:
                        org['url'] = href
                else:
                    link_elem = result.find('a', href=True)
                    if link_elem:
                        href = link_elem.get('href', '')
                        if href.startswith('/'):
                            org['url'] = f"{self.BASE_URL}{href}"
                        else:
                            org['url'] = href
                
                # ID организации
                if result.get('data-id'):
                    org['id'] = result['data-id']
                
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
        # Удаляем все кроме цифр
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
            'source': '2gis'
        }
        
        # Часы работы
        hours_section = soup.find('div', class_='schedule')
        if hours_section:
            for day_elem in hours_section.find_all('div', class_='schedule-item'):
                day_name = day_elem.find('span', class_='day')
                day_hours = day_elem.find('span', class_='hours')
                if day_name and day_hours:
                    details['working_hours'][day_name.get_text(strip=True)] = \
                        day_hours.get_text(strip=True)
        
        # Описание
        desc_elem = soup.find('div', class_='description') or \
                   soup.find('div', class_='text')
        if desc_elem:
            details['description'] = desc_elem.get_text(strip=True)
        
        # Фото
        photos_section = soup.find('div', class_='photos') or \
                        soup.find('div', class_='gallery')
        if photos_section:
            for img in photos_section.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src:
                    details['photos'].append(src)
        
        return details

