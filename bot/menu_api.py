import requests
import logging

logger = logging.getLogger(__name__)

class MenuAPI:
    API_BASE_URL = ""
    STORE_SLUG = ""
    
    @classmethod
    def get_categories(cls):
        """Fetch categories from main API"""
        try:
            response = requests.get(
                f"{cls.API_BASE_URL}/categories/store/slug/{cls.STORE_SLUG}",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API Error: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Failed to fetch categories: {e}")
            return []
    
    @classmethod
    def get_products(cls, category_id=None):
        """Fetch products from main API"""
        try:
            url = f"{cls.API_BASE_URL}/products/public-store/slug/{cls.STORE_SLUG}"
            params = {"category": category_id} if category_id else {}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API Error: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Failed to fetch products: {e}")
            return []
    
    @classmethod
    def get_store_info(cls):
        """Fetch store information"""
        try:
            response = requests.get(
                f"{cls.API_BASE_URL}/stores/public/slug/{cls.STORE_SLUG}",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to fetch store info: {e}")
            return None