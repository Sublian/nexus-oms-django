# Tests para Sprint 1: CreateInvoiceUseCase con tenant-aware config + providers

import pytest
from django.test import TestCase
from src.domain.models import Order, Organization, CompanyInvoiceConfig
from src.application.usecases.create_invoice import CreateInvoiceUseCase
from src.application.providers.mock_nubefact_client import MockNubefactClient
from src.domain.models.order_constants import OrderStatus


@pytest.mark.django_db
class TestCreateInvoiceUseCase(TestCase):

    def setUp(self):
        # Setup: Crear organización y orden
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
        # Sprint 1: Config encontrada → crear factura
        config = CompanyInvoiceConfig.objects.create(
            organization=self.org,
            api_base_url="https://api.nubefact.test",
            endpoint_url="invoices",
            token="test-token",
            enabled=True
        )

        usecase = CreateInvoiceUseCase()
        result = usecase.execute(self.order)

        # Verificar resultado
        assert result['status'] == 'issued'
        assert result['external_id'].startswith('MOCK-')
        assert result['error'] is None

        # Verificar order actualizada
        self.order.refresh_from_db()
        assert self.order.invoice_status == 'issued'
        assert self.order.invoice_external_id == result['external_id']

    def test_create_invoice_without_config(self):
        # Sprint 1: Config faltante → marcar como failed, no romper
        usecase = CreateInvoiceUseCase()
        result = usecase.execute(self.order)

        # Verificar resultado
        assert result['status'] == 'failed'
        assert result['error'] == 'CompanyInvoiceConfig not found'
        assert result['external_id'] is None

        # Verificar order actualizada
        self.order.refresh_from_db()
        assert self.order.invoice_status == 'failed'

    def test_mock_nubefact_client_creates_valid_id(self):
        # MockNubefactClient genera ID válido
        config = CompanyInvoiceConfig.objects.create(
            organization=self.org,
            api_base_url="https://api.nubefact.test",
            endpoint_url="invoices",
            token="test-token",
            enabled=False
        )

        client = MockNubefactClient(config)
        result = client.create_invoice(self.order)

        # ID debe empezar con MOCK-
        assert result['external_id'].startswith('MOCK-')
        assert result['status'] == 'issued'
        assert len(result['external_id']) > 5

    def test_provider_resolves_dynamically_by_enabled(self):
        # Resolver provider dinámicamente: enabled=False → Mock
        config = CompanyInvoiceConfig.objects.create(
            organization=self.org,
            api_base_url="https://api.nubefact.test",
            endpoint_url="invoices",
            token="test-token",
            enabled=False  # Deshabilitado
        )

        from src.application.providers.factory import get_invoice_provider
        provider = get_invoice_provider(config)

        # Siempre Mock en Sprint 1 (NubefactClient viene en Fase 2.5)
        assert isinstance(provider, MockNubefactClient)

    def test_invoice_external_id_unique_per_execution(self):
        # Cada ejecución genera ID único (no determinístico)
        config = CompanyInvoiceConfig.objects.create(
            organization=self.org,
            api_base_url="https://api.nubefact.test",
            endpoint_url="invoices",
            token="test-token",
            enabled=True
        )

        usecase = CreateInvoiceUseCase()
        result1 = usecase.execute(self.order)

        # Reset order para próxima ejecución
        self.order.invoice_status = 'pending'
        self.order.invoice_external_id = None
        self.order.save()

        result2 = usecase.execute(self.order)

        # Los IDs deben ser diferentes (cada uno único)
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

        # Verificar que el external_id en DB no cambio
        self.order.refresh_from_db()
        assert self.order.invoice_external_id == 'MOCK-EXISTING'
