from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


class Product(BaseModel):
    """Модель товара с маркетплейса"""
    id: Optional[str] = None
    name: str
    brand: Optional[str] = None
    price: float = 0.0
    rating: float = 0.0
    reviews_count: int = 0
    url: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    characteristics: Dict[str, Any] = Field(default_factory=dict)
    source: str  # wildberries, ozon и т.д.
    parsed_at: datetime = Field(default_factory=datetime.now)


class Organization(BaseModel):
    """Модель организации с карт"""
    id: Optional[str] = None
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    phones: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
    website: Optional[str] = None
    websites: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    rating: float = 0.0
    reviews_count: int = 0
    coordinates: Optional[Dict[str, float]] = None  # {lat, lon}
    url: Optional[str] = None
    description: Optional[str] = None
    working_hours: Dict[str, str] = Field(default_factory=dict)
    photos: List[str] = Field(default_factory=list)
    source: str  # google_maps, yandex_maps, 2gis
    parsed_at: datetime = Field(default_factory=datetime.now)

