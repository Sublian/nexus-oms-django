import pytest
from django.test import TestCase
from src.domain.models import Order, Organization, CompanyInvoiceConfig
from src.domain.exceptions import NubefactPermanentError
from src.application.usecases.create_invoice import CreateInvoiceUseCase
from src.application.providers.mock_nubefact_client import MockNubefactClient
from src.domain.models.order_constants import OrderStatus


@pytest.mark.django_db
class TestCreateInvoiceUseCase(TestCase):

    def setUp(self):
        self.org = Organization.objects.create(
            name="Test Company",
            slug="test-company",
            admin_email="admin@test.com"
        )
        self.order = Order.objects.create(
            organization=self.org,
            customer_name="Juan Perez",
            customer_email="juan@test.com",
            status=OrderStatus.PAID,
            total_amount=100.00
        )

    def test_create_invoice_with_config_found(self):
        config = CompanyInvoiceConfig.objects.create(
            organization=self.org,
            api_base_url="https://api.nubefact.test",
            endpoint_url="invoices",
            token="test-token",
            enabled=True
        )

        usecase = CreateInvoiceUseCase()
        result = usecase.execute(self.order)

        assert result['status'] == 'issued'
        assert result['external_id'].startswith('MOCK-')
        assert result['error'] is None

        self.order.refresh_from_db()
        assert self.order.invoice_status == 'issued'
        assert self.order.invoice_external_id == result['external_id']

    def test_create_invoice_without_config_raises_permanent_error(self):
        # Config faltante es error permanente — no tiene sentido reintentar
        usecase = CreateInvoiceUseCase()

        with pytest.raises(NubefactPermanentError, match='CompanyInvoiceConfig not found'):
            usecase.execute(self.order)

        # UseCase no modifica el estado — es responsabilidad del task
        self.order.refresh_from_db()
        assert self.order.invoice_status == 'pending'

    def test_mock_nubefact_client_creates_valid_id(self):
        config = CompanyInvoiceConfig.objects.create(
            organization=self.org,
            api_base_url="https://api.nubefact.test",
            endpoint_url="invoices",
            token="test-token",
            enabled=False
        )

        client = MockNubefactClient(config)
        result = client.create_invoice(self.order)

        assert result['external_id'].startswith('MOCK-')
        assert result['status'] == 'issued'
        assert len(result['external_id']) > 5

    def test_provider_resolves_dynamically_by_enabled(self):
        config = CompanyInvoiceConfig.objects.create(
            organization=self.org,
            api_base_url="https://api.nubefact.test",
            endpoint_url="invoices",
            token="test-token",
            enabled=False
        )

        from src.application.providers.factory import get_invoice_provider
        provider = get_invoice_provider(config)

        assert isinstance(provider, MockNubefactClient)

    def test_invoice_external_id_unique_per_execution(self):
        config = CompanyInvoiceConfig.objects.create(
            organization=self.org,
            api_base_url="https://api.nubefact.test",
            endpoint_url="invoices",
            token="test-token",
            enabled=True
        )

        usecase = CreateInvoiceUseCase()
        result1 = usecase.execute(self.order)

        # Reset para simular retry manual o nueva orden
        self.order.invoice_status = 'pending'
        self.order.invoice_external_id = None
        self.order.save()

        result2 = usecase.execute(self.order)

        assert result1['external_id'] != result2['external_id']
        assert result1['external_id'].startswith('MOCK-')
        assert result2['external_id'].startswith('MOCK-')

    def test_idempotency_guard_skips_if_already_issued(self):
        # Guardia de idempotencia: si invoice_external_id ya existe, no crear factura nueva
        self.order.invoice_status = 'issued'
        self.order.invoice_external_id = 'MOCK-EXISTING'
        self.order.save()

        usecase = CreateInvoiceUseCase()
        result = usecase.execute(self.order)

        assert result['status'] == 'issued'
        assert result['external_id'] == 'MOCK-EXISTING'
        assert result['error'] is None

        self.order.refresh_from_db()
        assert self.order.invoice_external_id == 'MOCK-EXISTING'

    def test_provider_exceptions_propagate_to_caller(self):
        # Excepciones del provider deben llegar al task para manejo diferenciado
        from src.domain.exceptions import NubefactTemporaryError
        from unittest.mock import MagicMock

        config = CompanyInvoiceConfig.objects.create(
            organization=self.org,
            api_base_url="https://api.nubefact.test",
            endpoint_url="invoices",
            token="test-token",
            enabled=True
        )

        mock_provider = MagicMock()
        mock_provider.create_invoice.side_effect = NubefactTemporaryError("timeout")

        usecase = CreateInvoiceUseCase(provider=mock_provider)

        with pytest.raises(NubefactTemporaryError, match="timeout"):
            usecase.execute(self.order)
