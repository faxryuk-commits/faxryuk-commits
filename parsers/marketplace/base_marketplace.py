from typing import Dict, List, Any, Optional
from parsers.base import BaseParser
from bs4 import BeautifulSoup


class BaseMarketplaceParser(BaseParser):
    """Базовый класс для парсеров маркетплейсов"""
    
    def __init__(self, base_url: str, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url
    
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
        url = self._build_search_url(query)
        response = self._make_request(url)
        
        if not response:
            return []
        
        products = self._extract_products(response.text)
        
        if limit:
            products = products[:limit]
        
        return products
    
    def parse_product(self, product_url: str) -> Optional[Dict[str, Any]]:
        """
        Парсит детальную информацию о товаре
        
        Args:
            product_url: URL товара
        
        Returns:
            Данные о товаре
        """
        response = self._make_request(product_url)
        
        if not response:
            return None
        
        return self._extract_product_details(response.text)
    
    def _build_search_url(self, query: str) -> str:
        """Формирует URL для поиска. Должен быть переопределен"""
        raise NotImplementedError
    
    def _extract_products(self, html: str) -> List[Dict[str, Any]]:
        """Извлекает товары из HTML. Должен быть переопределен"""
        raise NotImplementedError
    
    def _extract_product_details(self, html: str) -> Dict[str, Any]:
        """Извлекает детали товара из HTML. Должен быть переопределен"""
        raise NotImplementedError
    
    def _parse_html(self, html: str) -> BeautifulSoup:
        """Парсит HTML в BeautifulSoup"""
        return BeautifulSoup(html, 'lxml')
    
    def parse(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Реализация базового метода parse"""
        return self.parse_search(query, limit)

