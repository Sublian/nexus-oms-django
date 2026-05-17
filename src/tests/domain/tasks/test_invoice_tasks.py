import pytest
from unittest.mock import patch

from src.domain.models import Order, CompanyInvoiceConfig
from src.domain.models.order_constants import OrderStatus
from src.domain.tasks.invoice_tasks import create_invoice_task
from src.application.usecases.create_invoice import CreateInvoiceUseCase


def _make_order(organization, invoice_status='pending', invoice_external_id=None, invoice_attempts=0):
    return Order.objects.create(
        organization=organization,
        customer_name="Test User",
        customer_email="test@nexus.com",
        status=OrderStatus.PAID,
        total_amount=100.00,
        invoice_status=invoice_status,
        invoice_external_id=invoice_external_id,
        invoice_attempts=invoice_attempts,
    )


def _make_config(organization):
    return CompanyInvoiceConfig.objects.create(
        organization=organization,
        api_base_url="https://api.nubefact.test",
        endpoint_url="invoices",
        token="test-token",
        enabled=True,
    )


@pytest.mark.django_db
class TestCreateInvoiceTask:

    def test_happy_path_issues_invoice(self, organization):
        _make_config(organization)
        order = _make_order(organization)

        create_invoice_task.delay(order.id)

        order.refresh_from_db()
        assert order.invoice_status == 'issued'
        assert order.invoice_external_id is not None
        assert order.invoice_external_id.startswith('MOCK-')
        assert order.invoice_attempts == 1
        assert order.invoice_last_error is None

    def test_no_config_fails_gracefully(self, organization):
        # Sin CompanyInvoiceConfig — UseCase falla gracefully, no rompe el task
        order = _make_order(organization)

        create_invoice_task.delay(order.id)

        order.refresh_from_db()
        assert order.invoice_status == 'failed'
        assert order.invoice_attempts == 1

    def test_idempotency_already_issued_skips(self, organization):
        # invoice_external_id existe — skip sin incrementar attempts
        order = _make_order(organization, invoice_status='issued', invoice_external_id='MOCK-EXISTING')

        create_invoice_task.delay(order.id)

        order.refresh_from_db()
        assert order.invoice_external_id == 'MOCK-EXISTING'
        assert order.invoice_attempts == 0  # no incrementado

    def test_already_processing_skips(self, organization):
        # Otro worker ya marco processing — skip para evitar doble ejecucion
        order = _make_order(organization, invoice_status='processing')

        create_invoice_task.delay(order.id)

        order.refresh_from_db()
        assert order.invoice_status == 'processing'
        assert order.invoice_attempts == 0  # no incrementado

    def test_invoice_attempts_increments_on_each_valid_run(self, organization):
        _make_config(organization)
        order = _make_order(organization, invoice_attempts=0)

        create_invoice_task.delay(order.id)

        order.refresh_from_db()
        assert order.invoice_attempts == 1

    def test_order_not_found_returns_gracefully(self):
        # Order inexistente — el task no debe levantar excepcion
        result = create_invoice_task.delay(order_id=99999)
        # Si llego aqui sin excepcion, el manejo es correcto

    def test_last_error_cleared_on_success(self, organization):
        # Si habia un error previo y ahora tiene exito, invoice_last_error = None
        _make_config(organization)
        order = _make_order(organization, invoice_status='pending')
        Order.objects.filter(id=order.id).update(invoice_last_error='previous error')

        create_invoice_task.delay(order.id)

        order.refresh_from_db()
        assert order.invoice_status == 'issued'
        assert order.invoice_last_error is None

    def test_unknown_exception_marks_failed_and_reraises(self, organization):
        # Excepcion inesperada: marca failed y re-raise (Celery lo captura para dead-letter)
        order = _make_order(organization)

        with patch.object(CreateInvoiceUseCase, 'execute', side_effect=RuntimeError("unexpected")):
            with pytest.raises(RuntimeError):
                create_invoice_task.delay(order.id)

        order.refresh_from_db()
        assert order.invoice_status == 'failed'
        assert 'unexpected' in order.invoice_last_error

    def test_permanent_error_marks_failed_without_retry(self, organization):
        # NubefactPermanentError: el task marca failed y retorna — no re-raise
        from src.domain.exceptions import NubefactPermanentError
        order = _make_order(organization)

        with patch.object(CreateInvoiceUseCase, 'execute', side_effect=NubefactPermanentError("bad payload")):
            create_invoice_task.delay(order.id)  # no debe raise

        order.refresh_from_db()
        assert order.invoice_status == 'failed'
        assert order.invoice_attempts == 1
        assert 'bad payload' in order.invoice_last_error

    def test_no_config_raises_permanent_error_and_marks_failed(self, organization):
        # Paso 4: UseCase ahora levanta NubefactPermanentError — task lo captura
        order = _make_order(organization)  # sin CompanyInvoiceConfig

        create_invoice_task.delay(order.id)

        order.refresh_from_db()
        assert order.invoice_status == 'failed'
        assert order.invoice_attempts == 1
        assert 'CompanyInvoiceConfig not found' in order.invoice_last_error
