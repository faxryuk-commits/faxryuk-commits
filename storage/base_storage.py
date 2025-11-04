from abc import ABC, abstractmethod
from typing import List, Dict, Any
from models.data_models import Product, Organization


class BaseStorage(ABC):
    """Базовый класс для хранения данных"""
    
    @abstractmethod
    def save_products(self, products: List[Product]) -> bool:
        """Сохраняет список товаров"""
        pass
    
    @abstractmethod
    def save_organizations(self, organizations: List[Organization]) -> bool:
        """Сохраняет список организаций"""
        pass
    
    @abstractmethod
    def get_products(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Получает товары с фильтрацией"""
        pass
    
    @abstractmethod
    def get_organizations(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Получает организации с фильтрацией"""
        pass

