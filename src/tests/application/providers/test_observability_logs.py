"""
Tests for ExternalRequestLog instrumentation and error taxonomy.

Verifica:
1. ExternalRequestLog se crea en NubefactClient.create_invoice()
2. duration_ms se captura correctamente
3. error_message incluye categoría [TEMPORARY], [PERMANENT], etc.
4. classify_error() traduce códigos HTTP a categorías
5. Anti-duplicación: un request HTTP = un log en DB
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from unittest.mock import patch, MagicMock

from src.domain.models import Order, Organization, Client, ExternalRequestLog
from src.domain.observability import classify_error, ErrorCategory
from src.application.providers.nubefact_client import NubefactClient
from src.domain.exceptions import NubefactTemporaryError, NubefactPermanentError
from src.domain.models.config import CompanyInvoiceConfig


@pytest.fixture
def org(db):
    """Organización de test."""
    from src.infrastructure.multitenancy.context import set_current_organization
    org_obj = Organization.objects.create(
        name='Test Org',
        slug='test-org',
        admin_email='test@org.com',
        primary_color='#000000',
        secondary_color='#FFFFFF',
        ruc='20000000000',
        address='Test Address',
    )
    set_current_organization(org_obj.id)
    return org_obj


@pytest.fixture
def client_obj(db, org):
    """Cliente de test."""
    return Client.objects.create(
        organization=org,
        name='Test Client',
        email='client@test.com',
        phone='999999999',
    )


@pytest.fixture
def order(db, org, client_obj):
    """Orden de test."""
    return Order.objects.create(
        organization=org,
        client=client_obj,
        customer_name='Test Customer',
        customer_email='customer@test.com',
        status='draft',
        subtotal=Decimal('100.00'),
        tax_amount=Decimal('18.00'),
        total_amount=Decimal('118.00'),
    )


@pytest.fixture
def mock_config(db, org):
    """Configuración fake de Nubefact."""
    return CompanyInvoiceConfig.objects.create(
        organization=org,
        provider_type='nubefact',
        api_base_url='https://api.nubefact.com',
        endpoint_url='/api/invoice',
        token='test-token-123',
        enabled=True,
    )


@pytest.fixture
def nubefact_client(mock_config):
    """Cliente Nubefact inyectado con config."""
    config = MagicMock()
    config.api_base_url = 'https://api.nubefact.com'
    config.endpoint_url = '/api/invoice'
    config.token = 'test-token-123'
    client = NubefactClient(config)
    return client


class TestClassifyError:
    """Tests para classify_error() function."""

    def test_classify_http_500_as_temporary(self):
        assert classify_error(500) == ErrorCategory.TEMPORARY

    def test_classify_http_502_as_temporary(self):
        assert classify_error(502) == ErrorCategory.TEMPORARY

    def test_classify_http_503_as_temporary(self):
        assert classify_error(503) == ErrorCategory.TEMPORARY

    def test_classify_http_504_as_temporary(self):
        assert classify_error(504) == ErrorCategory.TEMPORARY

    def test_classify_http_400_as_permanent(self):
        assert classify_error(400) == ErrorCategory.PERMANENT

    def test_classify_http_401_as_auth(self):
        assert classify_error(401) == ErrorCategory.AUTH

    def test_classify_http_403_as_auth(self):
        assert classify_error(403) == ErrorCategory.AUTH

    def test_classify_http_422_as_validation(self):
        assert classify_error(422) == ErrorCategory.VALIDATION

    def test_classify_http_429_as_rate_limit(self):
        assert classify_error(429) == ErrorCategory.RATE_LIMIT

    def test_classify_timeout_exception_as_temporary(self):
        exc = NubefactTemporaryError("Timeout after 15s")
        assert classify_error(exc) == ErrorCategory.TEMPORARY

    def test_classify_permanent_exception_as_permanent(self):
        exc = NubefactPermanentError("Invalid payload")
        assert classify_error(exc) == ErrorCategory.PERMANENT


class TestExternalRequestLogCreation:
    """Tests para creación de ExternalRequestLog."""

    @pytest.mark.django_db
    @patch('src.application.providers.nubefact_client.requests.post')
    def test_log_created_on_successful_create_invoice(self, mock_post, nubefact_client, order):
        """create_invoice exitoso debe crear log con success=True."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            'serie': 'B001',
            'numero': '123',
            'hash': 'abc123hash',
        }
        mock_post.return_value = mock_response

        result = nubefact_client.create_invoice(order)

        assert result['status'] == 'submitted'
        assert result['external_id'] == 'B001-123'

        # Verificar que se creó el log
        log = ExternalRequestLog.objects.get(order=order, operation='create_invoice')
        assert log.success is True
        assert log.status_code == 200
        assert log.duration_ms is not None
        assert log.duration_ms >= 0
        assert log.error_message is None
        assert log.provider_name == 'nubefact'

    @pytest.mark.django_db
    @patch('src.application.providers.nubefact_client.requests.post')
    def test_log_created_on_http_400_error(self, mock_post, nubefact_client, order):
        """create_invoice con HTTP 400 debe crear log con error categorizado."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.ok = False
        mock_response.text = "Invalid payload"
        mock_response.json.return_value = {'error': 'Bad request'}
        mock_post.return_value = mock_response

        with pytest.raises(NubefactPermanentError):
            nubefact_client.create_invoice(order)

        # Verificar que se creó el log con categoría
        log = ExternalRequestLog.objects.get(order=order, operation='create_invoice')
        assert log.success is False
        assert log.status_code == 400
        assert '[PERMANENT]' in log.error_message
        assert 'HTTP 400' in log.error_message

    @pytest.mark.django_db
    @patch('src.application.providers.nubefact_client.requests.post')
    def test_log_created_on_http_503_error(self, mock_post, nubefact_client, order):
        """create_invoice con HTTP 503 debe crear log con categoría TEMPORARY."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.ok = False
        mock_response.text = "Service Unavailable"
        mock_response.json.return_value = {'error': 'Unavailable'}
        mock_post.return_value = mock_response

        with pytest.raises(NubefactTemporaryError):
            nubefact_client.create_invoice(order)

        # Verificar que se creó el log con categoría TEMPORARY
        log = ExternalRequestLog.objects.get(order=order, operation='create_invoice')
        assert log.success is False
        assert log.status_code == 503
        assert '[TEMPORARY]' in log.error_message
        assert 'HTTP 503' in log.error_message

    @pytest.mark.django_db
    @patch('src.application.providers.nubefact_client.requests.post')
    def test_log_created_on_timeout(self, mock_post, nubefact_client, order):
        """create_invoice con Timeout debe crear log con categoría TEMPORARY."""
        import requests as requests_module
        mock_post.side_effect = requests_module.exceptions.Timeout("Timeout after 15s")

        with pytest.raises(NubefactTemporaryError):
            nubefact_client.create_invoice(order)

        # Verificar que se creó el log con categoría TEMPORARY
        log = ExternalRequestLog.objects.get(order=order, operation='create_invoice')
        assert log.success is False
        assert log.status_code is None
        assert '[TEMPORARY]' in log.error_message

    @pytest.mark.django_db
    @patch('src.application.providers.nubefact_client.requests.post')
    def test_duration_ms_captured_correctly(self, mock_post, nubefact_client, order):
        """duration_ms debe reflejar el tiempo real del request."""
        import time

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {'serie': 'B001', 'numero': '123', 'hash': 'abc'}

        def slow_response(*args, **kwargs):
            time.sleep(0.01)  # 10ms
            return mock_response

        mock_post.side_effect = slow_response
        nubefact_client.create_invoice(order)

        log = ExternalRequestLog.objects.get(order=order)
        # Verificar que duration_ms está en un rango razonable (>= 10ms)
        assert log.duration_ms >= 10

    @pytest.mark.django_db
    @patch('src.application.providers.nubefact_client.requests.post')
    def test_anti_duplication_one_request_one_log(self, mock_post, nubefact_client, order):
        """Un request HTTP debe crear exactamente un log en DB."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {'serie': 'B001', 'numero': '123', 'hash': 'abc'}
        mock_post.return_value = mock_response

        # Realizar request
        nubefact_client.create_invoice(order)

        # Verificar que hay exactamente 1 log
        logs = ExternalRequestLog.objects.filter(order=order, operation='create_invoice')
        assert logs.count() == 1

    @pytest.mark.django_db
    @patch('src.application.providers.nubefact_client.requests.post')
    def test_log_respects_native_types(self, mock_post, nubefact_client, order):
        """ExternalRequestLog debe respetar tipos nativos exactos."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {'serie': 'B001', 'numero': '123', 'hash': 'abc'}
        mock_post.return_value = mock_response

        nubefact_client.create_invoice(order)

        log = ExternalRequestLog.objects.get(order=order)
        # Verificar tipos de campos
        assert log.order_id == order.id
        assert log.organization_id == order.organization_id
        assert log.provider_name == 'nubefact'
        assert isinstance(log.status_code, int)
        assert isinstance(log.duration_ms, int)
        assert isinstance(log.success, bool)
        assert log.service_id is None  # nullable cuando no hay config
