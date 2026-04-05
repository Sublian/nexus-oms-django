import pytest
import requests_mock
from src.infrastructure.services.apimigo import APIMigoClient

def test_get_ruc_success():
    ruc_number = "20603274742"
    with requests_mock.Mocker() as m:
        # Simulamos la respuesta de la documentación de Migo
        m.post(f"{APIMigoClient.BASE_URL}/ruc", json={
            "success": True,
            "ruc": ruc_number,
            "nombre_o_razon_social": "MIGO S.A.C.",
            "direccion_simple": "AV. JORGE CHAVEZ 204"
        })

        result = APIMigoClient.get_ruc(ruc_number)
        
        assert result['success'] is True
        assert result['nombre_o_razon_social'] == "MIGO S.A.C."

def test_get_exchange_rate_success():
    with requests_mock.Mocker() as m:
        m.post(f"{APIMigoClient.BASE_URL}/exchange/date", json={
            "success": True,
            "precio_venta": "3.850"
        })

        result = APIMigoClient.get_exchange_rate()
        assert result['precio_venta'] == "3.850"