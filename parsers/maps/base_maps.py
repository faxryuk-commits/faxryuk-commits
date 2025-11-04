from typing import Dict, List, Any, Optional
from parsers.base import BaseParser


class BaseMapsParser(BaseParser):
    """Базовый класс для парсеров картографических сервисов"""
    
    def __init__(self, base_url: str, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url
    
    def search_organizations(
        self,
        query: str,
        location: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Ищет организации по запросу
        
        Args:
            query: Поисковый запрос
            location: Локация (город, адрес)
            limit: Максимальное количество результатов
        
        Returns:
            Список организаций
        """
        url = self._build_search_url(query, location)
        response = self._make_request(url)
        
        if not response:
            return []
        
        organizations = self._extract_organizations(response.text, query)
        
        if limit:
            organizations = organizations[:limit]
        
        return organizations
    
    def get_organization_details(self, org_url: str) -> Optional[Dict[str, Any]]:
        """
        Получает детальную информацию об организации
        
        Args:
            org_url: URL организации
        
        Returns:
            Детали организации
        """
        response = self._make_request(org_url)
        
        if not response:
            return None
        
        return self._extract_organization_details(response.text)
    
    def get_organization_full_info(self, org_url: str) -> Optional[Dict[str, Any]]:
        """
        Получает полную информацию об организации включая email
        
        Args:
            org_url: URL организации
        
        Returns:
            Детали организации с email и телефонами
        """
        return self.get_organization_details(org_url)
    
    def _build_search_url(self, query: str, location: Optional[str] = None) -> str:
        """Формирует URL для поиска. Должен быть переопределен"""
        raise NotImplementedError
    
    def _extract_organizations(
        self,
        html: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """Извлекает организации из HTML. Должен быть переопределен"""
        raise NotImplementedError
    
    def _extract_organization_details(self, html: str) -> Dict[str, Any]:
        """Извлекает детали организации из HTML. Должен быть переопределен"""
        raise NotImplementedError
    
    def parse(self, query: str, location: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Реализация базового метода parse"""
        return self.search_organizations(query, location, limit)

