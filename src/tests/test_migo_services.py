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

def test_get_ruc_not_found():
    ruc_number = "00000000000"
    with requests_mock.Mocker() as m:
        m.post(f"{APIMigoClient.BASE_URL}/ruc", status_code=404)

        result = APIMigoClient.get_ruc(ruc_number)
        assert result is None

def test_get_ruc_batch_success():
    ruc_numbers = ["20603274742", "20123456789"]
    with requests_mock.Mocker() as m:
        m.post(f"{APIMigoClient.BASE_URL}/ruc/collection", json=[
            {
                "success": True,
                "ruc": "20603274742",
                "nombre_o_razon_social": "MIGO S.A.C.",
                "direccion_simple": "AV. JORGE CHAVEZ 204"
            },
            {
                "success": True,
                "ruc": "20123456789",
                "nombre_o_razon_social": "EMPRESA XYZ S.A.C.",
                "direccion_simple": "AV. PRINCIPAL 123"
            }
        ])

        result = APIMigoClient.get_ruc_batch(ruc_numbers)
        assert len(result) == 2
        assert result[0]['ruc'] == "20603274742"
        assert result[1]['ruc'] == "20123456789"

def test_get_dni_success():
    dni_number = "12345678"
    with requests_mock.Mocker() as m:
        m.post(f"{APIMigoClient.BASE_URL}/dni", json={
            "success": True,
            "dni": dni_number,
            "nombres": "JUAN",
            "apellido_paterno": "PEREZ",
            "apellido_materno": "GOMEZ"
        })

        result = APIMigoClient.get_dni(dni_number)
        assert result['success'] is True
        assert result['nombres'] == "JUAN"
        assert result['apellido_paterno'] == "PEREZ"
        assert result['apellido_materno'] == "GOMEZ"

def test_get_dni_not_found():
    dni_number = "00000000"
    with requests_mock.Mocker() as m:
        m.post(f"{APIMigoClient.BASE_URL}/dni", status_code=404)

        result = APIMigoClient.get_dni(dni_number)
        assert result is None

