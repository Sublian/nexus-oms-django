from unittest.mock import MagicMock, patch

import pytest
import requests as req_lib

from src.application.providers.nubefact_client import NubefactClient
from src.application.providers.mock_nubefact_client import MockNubefactClient
from src.domain.exceptions import NubefactTemporaryError, NubefactPermanentError


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_config(provider_type='nubefact'):
    config = MagicMock()
    config.api_base_url = 'https://api.nubefact.test'
    config.endpoint_url = 'invoices'
    config.token = 'test-token-secret'
    config.provider_type = provider_type
    return config


def _make_order():
    order = MagicMock()
    order.id = 42
    order.customer_name = 'Juan Perez'
    order.customer_email = 'juan@test.com'
    order.total_amount = 118.00
    order.tax_amount = 18.00
    order.subtotal = 100.00
    order.items.all.return_value = []
    return order


def _mock_response(status_code, json_data=None, text=''):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


# ── NubefactClient HTTP behaviour ─────────────────────────────────────────────

class TestNubefactClient:

    def test_success_200_returns_submitted(self):
        config = _make_config()
        order = _make_order()
        response_data = {'serie': 'B001', 'numero': 1, 'hash_cdr': 'ABC123'}

        with patch('requests.post', return_value=_mock_response(200, response_data)):
            client = NubefactClient(config)
            result = client.create_invoice(order)

        assert result['status'] == 'submitted'
        assert result['external_id'] == 'B001-1'
        assert result['hash'] == 'ABC123'
        assert result['error'] is None

    def test_success_202_returns_submitted(self):
        config = _make_config()
        order = _make_order()
        response_data = {'serie': 'B001', 'numero': 7}

        with patch('requests.post', return_value=_mock_response(202, response_data)):
            client = NubefactClient(config)
            result = client.create_invoice(order)

        assert result['status'] == 'submitted'
        assert result['external_id'] == 'B001-7'
        assert result['hash'] is None

    def test_400_raises_permanent_error(self):
        config = _make_config()
        order = _make_order()

        with patch('requests.post', return_value=_mock_response(400, text='bad request')):
            with pytest.raises(NubefactPermanentError, match='400'):
                NubefactClient(config).create_invoice(order)

    def test_401_raises_permanent_error(self):
        config = _make_config()
        order = _make_order()

        with patch('requests.post', return_value=_mock_response(401, text='unauthorized')):
            with pytest.raises(NubefactPermanentError, match='401'):
                NubefactClient(config).create_invoice(order)

    def test_422_raises_permanent_error(self):
        config = _make_config()
        order = _make_order()

        with patch('requests.post', return_value=_mock_response(422, text='invalid payload')):
            with pytest.raises(NubefactPermanentError, match='422'):
                NubefactClient(config).create_invoice(order)

    def test_502_raises_temporary_error(self):
        config = _make_config()
        order = _make_order()

        with patch('requests.post', return_value=_mock_response(502, text='bad gateway')):
            with pytest.raises(NubefactTemporaryError, match='502'):
                NubefactClient(config).create_invoice(order)

    def test_503_raises_temporary_error(self):
        config = _make_config()
        order = _make_order()

        with patch('requests.post', return_value=_mock_response(503, text='service unavailable')):
            with pytest.raises(NubefactTemporaryError, match='503'):
                NubefactClient(config).create_invoice(order)

    def test_timeout_raises_temporary_error(self):
        config = _make_config()
        order = _make_order()

        with patch('requests.post', side_effect=req_lib.exceptions.Timeout()):
            with pytest.raises(NubefactTemporaryError, match='Timeout'):
                NubefactClient(config).create_invoice(order)

    def test_connection_error_raises_temporary_error(self):
        config = _make_config()
        order = _make_order()

        with patch('requests.post', side_effect=req_lib.exceptions.ConnectionError("refused")):
            with pytest.raises(NubefactTemporaryError, match='Connection error'):
                NubefactClient(config).create_invoice(order)

    def test_unknown_non_ok_raises_permanent_error(self):
        # Cualquier codigo no-2xx no clasificado -> permanent
        config = _make_config()
        order = _make_order()

        with patch('requests.post', return_value=_mock_response(418, text="I'm a teapot")):
            with pytest.raises(NubefactPermanentError, match='418'):
                NubefactClient(config).create_invoice(order)

    def test_payload_includes_idempotency_key(self):
        config = _make_config()
        order = _make_order()
        client = NubefactClient(config)

        payload = client._build_payload(order)

        assert payload['externa_id'] == 'ORDER-42'

    def test_payload_has_required_fields(self):
        config = _make_config()
        order = _make_order()
        client = NubefactClient(config)

        payload = client._build_payload(order)

        required = [
            'operacion', 'tipo_de_comprobante', 'serie', 'numero',
            'cliente_denominacion', 'cliente_email',
            'total_gravada', 'total_igv', 'total',
            'detalle', 'externa_id',
        ]
        for field in required:
            assert field in payload, f"Falta campo: {field}"

    def test_token_not_exposed_in_url(self):
        # El token va en headers Authorization, nunca en la URL
        config = _make_config()
        order = _make_order()
        captured_calls = []

        def capture_post(url, **kwargs):
            captured_calls.append({'url': url, 'headers': kwargs.get('headers', {})})
            return _mock_response(200, {'serie': 'B001', 'numero': 1})

        with patch('requests.post', side_effect=capture_post):
            NubefactClient(config).create_invoice(order)

        assert len(captured_calls) == 1
        assert 'test-token-secret' not in captured_calls[0]['url']
        assert captured_calls[0]['headers'].get('Authorization') == 'Token test-token-secret'


# ── Factory resolution ─────────────────────────────────────────────────────────

class TestInvoiceProviderFactory:

    def test_provider_type_nubefact_returns_nubefact_client(self):
        from src.application.providers.factory import get_invoice_provider
        config = _make_config(provider_type='nubefact')

        provider = get_invoice_provider(config)

        assert isinstance(provider, NubefactClient)

    def test_provider_type_mock_returns_mock_client(self):
        from src.application.providers.factory import get_invoice_provider
        config = _make_config(provider_type='mock')

        provider = get_invoice_provider(config)

        assert isinstance(provider, MockNubefactClient)

    def test_provider_type_unknown_defaults_to_mock(self):
        # Cualquier valor no reconocido usa Mock (seguro por defecto)
        from src.application.providers.factory import get_invoice_provider
        config = _make_config(provider_type='unknown_provider')

        provider = get_invoice_provider(config)

        assert isinstance(provider, MockNubefactClient)
