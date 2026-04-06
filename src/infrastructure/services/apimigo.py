# src\infrastructure\services\apimigo.py
import requests
from django.conf import settings
from datetime import date
from typing import List, Dict, Any, Optional

class APIMigoClient:
    BASE_URL = "https://api.migo.pe/api/v1"
    # El token debe venir de settings (definido en tu .env)
    TOKEN = getattr(settings, 'MIGO_API_TOKEN', '1234567890') 

    @classmethod
    def _post_request(cls, endpoint: str, data: Dict[str, Any]) -> Optional[Any]:
        """Método privado para manejar las peticiones POST."""
        url = f"{cls.BASE_URL}{endpoint}"
        data['token'] = cls.TOKEN
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            print (f"APIMigo Request to {url} with data {data} - Status: {response.status_code} - Response: {response.text}")
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None  # No encontrado
            else:
                # Aquí podrías loguear errores (403, 500, etc.)
                return None
        except requests.RequestException as e:
            # Error de conexión o timeout
            print(f"Error en APIMigo: {e}")
            return None

    @classmethod
    def get_ruc(cls, ruc: str) -> Optional[Dict[str, Any]]:
        """Consulta un RUC individual."""
        return cls._post_request('/ruc', {'ruc': ruc})

    @classmethod
    def get_ruc_batch(cls, rucs: List[str]) -> List[Dict[str, Any]]:
        """
        Consulta RUC masiva (máximo 100 elementos).
        Retorna lista de diccionarios.
        """
        if not rucs:
            return []
        
        # Limitamos a 100 según documentación
        data = cls._post_request('/ruc/collection', {'ruc': rucs[:100]})
        return data if data else []

    @classmethod
    def get_dni(cls, dni: str) -> Optional[Dict[str, Any]]:
        """Consulta un DNI individual."""
        return cls._post_request('/dni', {'dni': dni})
    
    @classmethod
    def get_exchange_rate(cls, fecha: str = None) -> Dict[str, Any]:
        search_date = fecha if fecha else date.today().strftime('%Y-%m-%d')
        data = cls._post_request('/exchange/date', {'fecha': search_date})
        
        # Si falla (404), intentamos con una fecha anterior (ayer) antes de rendirnos
        if not data or not data.get('success'):
            from datetime import timedelta
            yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
            data = cls._post_request('/exchange/date', {'fecha': yesterday})

        # Fallback final si sigue fallando
        if not data or not data.get('success'):
            return {
                'success': False,
                'precio_venta': '3.80', 
                'precio_compra': '3.75',
                'moneda': 'USD'
            }
        return data