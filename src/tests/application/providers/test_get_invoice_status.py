"""
Tests para get_invoice_status en NubefactClient y MockNubefactClient.
Cubre: contrato de retorno, clasificacion de errores HTTP, timeout,
connection error, y escenarios del mock.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests as req_lib

from src.application.providers.nubefact_client import NubefactClient
from src.application.providers.mock_nubefact_client import MockNubefactClient
from src.domain.exceptions import NubefactTemporaryError, NubefactPermanentError


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_config():
    cfg = MagicMock()
    cfg.api_base_url = 'https://api.nubefact.test'
    cfg.endpoint_url = 'invoices'
    cfg.token = 'tok-secret'
    cfg.provider_type = 'nubefact'
    return cfg


def _mock_response(status_code, json_data=None, text=''):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


ACCEPTED_RESPONSE = {
    'aceptado_por_sunat': True,
    'observado': False,
    'hash': 'abc123hash',
    'hash_cpe': None,
    'enlace_del_cdi': 'https://nubefact.test/cdi/B001-42',
    'codigo_de_la_respuesta_sunat': '0',
    'descripcion_de_la_respuesta_sunat': 'La Factura ha sido aceptada',
}

OBSERVED_RESPONSE = {
    'aceptado_por_sunat': True,
    'observado': True,
    'hash': 'obs456hash',
    'enlace_del_cdi': 'https://nubefact.test/cdi/B001-43',
    'codigo_de_la_respuesta_sunat': '2108',
    'descripcion_de_la_respuesta_sunat': 'El IGV no coincide',
}

REJECTED_RESPONSE = {
    'aceptado_por_sunat': False,
    'observado': False,
    'hash': None,
    'enlace_del_cdi': None,
    'codigo_de_la_respuesta_sunat': '2800',
    'descripcion_de_la_respuesta_sunat': 'El RUC del emisor no existe',
}

PENDING_RESPONSE = {
    'aceptado_por_sunat': False,
    'observado': False,
    'hash': None,
    'codigo_de_la_respuesta_sunat': None,
}


# ── NubefactClient.get_invoice_status ────────────────────────────────────────

class TestNubefactClientGetStatus:

    def test_accepted_maps_correctly(self):
        with patch('requests.post', return_value=_mock_response(200, ACCEPTED_RESPONSE)):
            result = NubefactClient(_make_config()).get_invoice_status('B001-42')

        assert result['accepted'] is True
        assert result['observed'] is False
        assert result['rejected'] is False
        assert result['hash'] == 'abc123hash'
        assert result['provider_reference'] == 'https://nubefact.test/cdi/B001-42'
        assert result['raw_response'] == ACCEPTED_RESPONSE

    def test_observed_maps_correctly(self):
        with patch('requests.post', return_value=_mock_response(200, OBSERVED_RESPONSE)):
            result = NubefactClient(_make_config()).get_invoice_status('B001-43')

        assert result['accepted'] is True
        assert result['observed'] is True
        assert result['rejected'] is False
        assert result['hash'] == 'obs456hash'

    def test_rejected_maps_correctly(self):
        with patch('requests.post', return_value=_mock_response(200, REJECTED_RESPONSE)):
            result = NubefactClient(_make_config()).get_invoice_status('B001-44')

        assert result['accepted'] is False
        assert result['rejected'] is True
        assert result['hash'] is None

    def test_pending_sunat_all_flags_false(self):
        with patch('requests.post', return_value=_mock_response(200, PENDING_RESPONSE)):
            result = NubefactClient(_make_config()).get_invoice_status('B001-45')

        assert result['accepted'] is False
        assert result['observed'] is False
        assert result['rejected'] is False

    def test_502_raises_temporary_error(self):
        with patch('requests.post', return_value=_mock_response(502, text='bad gateway')):
            with pytest.raises(NubefactTemporaryError, match='502'):
                NubefactClient(_make_config()).get_invoice_status('B001-42')

    def test_401_raises_permanent_error(self):
        with patch('requests.post', return_value=_mock_response(401, text='unauthorized')):
            with pytest.raises(NubefactPermanentError, match='401'):
                NubefactClient(_make_config()).get_invoice_status('B001-42')

    def test_timeout_raises_temporary_error(self):
        with patch('requests.post', side_effect=req_lib.exceptions.Timeout()):
            with pytest.raises(NubefactTemporaryError, match='Timeout'):
                NubefactClient(_make_config()).get_invoice_status('B001-42')

    def test_connection_error_raises_temporary_error(self):
        with patch('requests.post', side_effect=req_lib.exceptions.ConnectionError('refused')):
            with pytest.raises(NubefactTemporaryError, match='Connection error'):
                NubefactClient(_make_config()).get_invoice_status('B001-42')

    def test_token_sent_in_header_not_url(self):
        captured = []

        def capture(url, **kwargs):
            captured.append({'url': url, 'headers': kwargs.get('headers', {})})
            return _mock_response(200, ACCEPTED_RESPONSE)

        with patch('requests.post', side_effect=capture):
            NubefactClient(_make_config()).get_invoice_status('B001-42')

        assert 'tok-secret' not in captured[0]['url']
        assert captured[0]['headers']['Authorization'] == 'Token tok-secret'

    def test_external_id_parsed_into_serie_numero(self):
        captured_payloads = []

        def capture(url, **kwargs):
            captured_payloads.append(kwargs.get('json', {}))
            return _mock_response(200, ACCEPTED_RESPONSE)

        with patch('requests.post', side_effect=capture):
            NubefactClient(_make_config()).get_invoice_status('B001-42')

        payload = captured_payloads[0]
        assert payload['serie']  == 'B001'
        assert payload['numero'] == '42'
        assert payload['operacion'] == 'consultar_comprobante'


# ── MockNubefactClient.get_invoice_status ────────────────────────────────────

class TestMockNubefactClientGetStatus:

    def test_default_scenario_is_accepted(self):
        client = MockNubefactClient(_make_config())
        result = client.get_invoice_status('MOCK-ABC')

        assert result['accepted'] is True
        assert result['observed'] is False
        assert result['rejected'] is False
        assert result['hash'] is not None
        assert result['raw_response']['mock'] is True

    def test_observed_scenario(self):
        client = MockNubefactClient(_make_config())
        client.status_scenario = 'observed'
        result = client.get_invoice_status('MOCK-ABC')

        assert result['observed'] is True
        assert result['accepted'] is False
        assert result['rejected'] is False
        assert result['hash'] is not None

    def test_rejected_scenario(self):
        client = MockNubefactClient(_make_config())
        client.status_scenario = 'rejected'
        result = client.get_invoice_status('MOCK-ABC')

        assert result['rejected'] is True
        assert result['accepted'] is False
        assert result['hash'] is None

    def test_pending_scenario_all_flags_false(self):
        client = MockNubefactClient(_make_config())
        client.status_scenario = 'pending'
        result = client.get_invoice_status('MOCK-ABC')

        assert result['accepted'] is False
        assert result['observed'] is False
        assert result['rejected'] is False

    def test_timeout_scenario_raises_temporary_error(self):
        client = MockNubefactClient(_make_config())
        client.status_scenario = 'timeout'

        with pytest.raises(NubefactTemporaryError, match='Mock timeout'):
            client.get_invoice_status('MOCK-ABC')

    def test_error_scenario_raises_temporary_error(self):
        client = MockNubefactClient(_make_config())
        client.status_scenario = 'error'

        with pytest.raises(NubefactTemporaryError, match='Mock network error'):
            client.get_invoice_status('MOCK-ABC')

    def test_result_includes_all_contract_keys(self):
        client = MockNubefactClient(_make_config())
        result = client.get_invoice_status('MOCK-XYZ')

        required_keys = ['accepted', 'observed', 'rejected', 'hash', 'provider_reference', 'raw_response']
        for key in required_keys:
            assert key in result, f"Falta clave en contrato: {key}"
