import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from storage.base_storage import BaseStorage
from models.data_models import Product, Organization


class JSONStorage(BaseStorage):
    """Хранилище данных в JSON формате"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Args:
            data_dir: Директория для хранения JSON файлов
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.products_file = self.data_dir / "products.json"
        self.organizations_file = self.data_dir / "organizations.json"
        
        # Инициализация файлов если их нет
        if not self.products_file.exists():
            self._init_file(self.products_file)
        if not self.organizations_file.exists():
            self._init_file(self.organizations_file)
    
    def _init_file(self, file_path: Path):
        """Инициализирует пустой JSON файл"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    
    def _load_json(self, file_path: Path) -> List[Dict]:
        """Загружает данные из JSON файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки {file_path}: {e}")
            return []
    
    def _save_json(self, file_path: Path, data: List[Dict]):
        """Сохраняет данные в JSON файл"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Ошибка сохранения {file_path}: {e}")
            return False
    
    def save_products(self, products: List[Product]) -> bool:
        """Сохраняет товары в JSON"""
        existing = self._load_json(self.products_file)
        
        # Конвертируем в словари
        new_products = [p.dict() for p in products]
        
        # Объединяем с существующими (можно добавить дедупликацию)
        existing.extend(new_products)
        
        return self._save_json(self.products_file, existing)
    
    def save_organizations(self, organizations: List[Organization]) -> bool:
        """Сохраняет организации в JSON"""
        existing = self._load_json(self.organizations_file)
        
        # Конвертируем в словари
        new_orgs = [org.dict() for org in organizations]
        
        # Объединяем с существующими
        existing.extend(new_orgs)
        
        return self._save_json(self.organizations_file, existing)
    
    def get_products(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Получает товары с фильтрацией"""
        products = self._load_json(self.products_file)
        
        if not filters:
            return products
        
        # Простая фильтрация
        filtered = []
        for product in products:
            match = True
            for key, value in filters.items():
                if key not in product or product[key] != value:
                    match = False
                    break
            if match:
                filtered.append(product)
        
        return filtered
    
    def get_organizations(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Получает организации с фильтрацией"""
        organizations = self._load_json(self.organizations_file)
        
        if not filters:
            return organizations
        
        # Простая фильтрация
        filtered = []
        for org in organizations:
            match = True
            for key, value in filters.items():
                if key not in org or org[key] != value:
                    match = False
                    break
            if match:
                filtered.append(org)
        
        return filtered

