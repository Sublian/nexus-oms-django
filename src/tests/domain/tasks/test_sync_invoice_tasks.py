"""
Tests para sync_pending_invoices_task y sync_single_invoice_task.

Cubre: locking, idempotencia, backoff, estados terminales,
errores temporales/permanentes, liberacion de lock, fan-out.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone

from src.domain.models import Order, CompanyInvoiceConfig, InvoiceSyncQueue
from src.domain.models.order_constants import OrderStatus
from src.domain.tasks.sync_invoice_tasks import (
    sync_single_invoice_task,
    sync_pending_invoices_task,
)
from src.domain.exceptions import NubefactTemporaryError, NubefactPermanentError
from src.application.providers.mock_nubefact_client import MockNubefactClient


# ── fixtures ──────────────────────────────────────────────────────────────────

def _make_order(organization):
    return Order.objects.create(
        organization=organization,
        customer_name="Test Client",
        customer_email="test@nexus.com",
        status=OrderStatus.PAID,
        total_amount=118.00,
        invoice_status="submitted",
        invoice_external_id="B001-42",
    )


def _make_config(organization):
    return CompanyInvoiceConfig.objects.create(
        organization=organization,
        api_base_url="https://api.nubefact.test",
        endpoint_url="invoices",
        token="test-token",
        enabled=True,
        provider_type="mock",
    )


def _make_sync_entry(organization, order, minutes_ago=2):
    return InvoiceSyncQueue.objects.create(
        organization=organization,
        order=order,
        status=InvoiceSyncQueue.STATUS_PENDING,
        next_retry_at=timezone.now() - timezone.timedelta(minutes=minutes_ago),
    )


# ── sync_single_invoice_task ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestSyncSingleInvoiceTask:

    def test_accepted_marks_entry_completed(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)

        with patch.object(MockNubefactClient, 'status_scenario', 'accepted'):
            sync_single_invoice_task.delay(entry.id)

        entry.refresh_from_db()
        order.refresh_from_db()
        assert entry.status == InvoiceSyncQueue.STATUS_COMPLETED
        assert entry.completed_at is not None
        assert entry.locked_at is None           # lock liberado
        assert order.invoice_status == 'accepted'

    def test_observed_marks_entry_completed(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)

        with patch.object(MockNubefactClient, 'status_scenario', 'observed'):
            sync_single_invoice_task.delay(entry.id)

        entry.refresh_from_db()
        assert entry.status == InvoiceSyncQueue.STATUS_COMPLETED
        assert entry.locked_at is None

    def test_rejected_marks_entry_completed(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)

        with patch.object(MockNubefactClient, 'status_scenario', 'rejected'):
            sync_single_invoice_task.delay(entry.id)

        entry.refresh_from_db()
        order.refresh_from_db()
        assert entry.status == InvoiceSyncQueue.STATUS_COMPLETED
        assert order.invoice_status == 'rejected'
        assert entry.locked_at is None

    def test_pending_sunat_reschedules_with_backoff(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)
        original_next_retry = entry.next_retry_at

        with patch.object(MockNubefactClient, 'status_scenario', 'pending'):
            sync_single_invoice_task.delay(entry.id)

        entry.refresh_from_db()
        assert entry.status == InvoiceSyncQueue.STATUS_PENDING
        assert entry.next_retry_at > original_next_retry    # backoff aplicado
        assert entry.attempts == 1
        assert entry.locked_at is None

    def test_attempts_incremented_per_run(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)

        with patch.object(MockNubefactClient, 'status_scenario', 'pending'):
            sync_single_invoice_task.delay(entry.id)

        entry.refresh_from_db()
        assert entry.attempts == 1

    def test_temporary_error_reschedules_without_failing(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)

        with patch.object(MockNubefactClient, 'status_scenario', 'timeout'):
            sync_single_invoice_task.delay(entry.id)

        entry.refresh_from_db()
        assert entry.status == InvoiceSyncQueue.STATUS_PENDING    # NO failed
        assert entry.last_error is not None
        assert entry.locked_at is None

    def test_permanent_error_marks_failed(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)

        with patch.object(MockNubefactClient, 'status_scenario', 'error'):
            with patch(
                'src.application.usecases.query_invoice_status.InvoiceStatusQueryUseCase.execute',
                side_effect=NubefactPermanentError("auth error"),
            ):
                sync_single_invoice_task.delay(entry.id)

        entry.refresh_from_db()
        assert entry.status == InvoiceSyncQueue.STATUS_FAILED
        assert 'auth error' in entry.last_error
        assert entry.completed_at is not None
        assert entry.locked_at is None

    def test_lock_released_even_on_unexpected_exception(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)

        with pytest.raises(RuntimeError):
            with patch(
                'src.application.usecases.query_invoice_status.InvoiceStatusQueryUseCase.execute',
                side_effect=RuntimeError("boom"),
            ):
                sync_single_invoice_task.delay(entry.id)

        entry.refresh_from_db()
        assert entry.locked_at is None      # lock siempre liberado en finally

    def test_idempotency_skips_completed_entry(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)
        entry.status = InvoiceSyncQueue.STATUS_COMPLETED
        entry.completed_at = timezone.now()
        entry.save()

        with patch(
            'src.application.usecases.query_invoice_status.InvoiceStatusQueryUseCase.execute',
        ) as mock_execute:
            sync_single_invoice_task.delay(entry.id)

        mock_execute.assert_not_called()     # UseCase no fue invocado

    def test_idempotency_skips_failed_entry(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)
        entry.status = InvoiceSyncQueue.STATUS_FAILED
        entry.completed_at = timezone.now()
        entry.save()

        with patch(
            'src.application.usecases.query_invoice_status.InvoiceStatusQueryUseCase.execute',
        ) as mock_execute:
            sync_single_invoice_task.delay(entry.id)

        mock_execute.assert_not_called()

    def test_fresh_lock_skips_processing(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)
        entry.locked_at = timezone.now()    # lock reciente — otro worker procesando
        entry.status = InvoiceSyncQueue.STATUS_PROCESSING
        entry.save()

        with patch(
            'src.application.usecases.query_invoice_status.InvoiceStatusQueryUseCase.execute',
        ) as mock_execute:
            sync_single_invoice_task.delay(entry.id)

        mock_execute.assert_not_called()

    def test_stale_lock_is_reprocessed(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)
        # Lock de hace 15 minutos — stale, debe reprocessarse
        entry.locked_at = timezone.now() - timezone.timedelta(minutes=15)
        entry.status = InvoiceSyncQueue.STATUS_PROCESSING
        entry.save()

        with patch.object(MockNubefactClient, 'status_scenario', 'accepted'):
            sync_single_invoice_task.delay(entry.id)

        entry.refresh_from_db()
        assert entry.status == InvoiceSyncQueue.STATUS_COMPLETED

    def test_entry_not_found_returns_silently(self):
        sync_single_invoice_task.delay(999999)   # ID inexistente — no debe lanzar

    def test_hash_persisted_on_accepted(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)

        with patch.object(MockNubefactClient, 'status_scenario', 'accepted'):
            sync_single_invoice_task.delay(entry.id)

        order.refresh_from_db()
        assert order.invoice_hash is not None
        assert order.invoice_hash.startswith('MOCK-HASH-')

    def test_last_response_persisted(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)

        with patch.object(MockNubefactClient, 'status_scenario', 'accepted'):
            sync_single_invoice_task.delay(entry.id)

        entry.refresh_from_db()
        assert entry.last_response is not None
        assert entry.last_response.get('mock') is True


# ── sync_pending_invoices_task ────────────────────────────────────────────────

@pytest.mark.django_db
class TestSyncPendingInvoicesTask:

    def test_dispatches_pending_entries_due_for_retry(self, organization):
        _make_config(organization)
        order1 = _make_order(organization)
        order2 = _make_order(organization)
        _make_sync_entry(organization, order1, minutes_ago=5)
        _make_sync_entry(organization, order2, minutes_ago=2)

        with patch.object(MockNubefactClient, 'status_scenario', 'accepted'):
            result = sync_pending_invoices_task.delay()

        assert result.result == 2

    def test_does_not_dispatch_future_entries(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        # next_retry_at en el futuro
        InvoiceSyncQueue.objects.create(
            organization=organization,
            order=order,
            status=InvoiceSyncQueue.STATUS_PENDING,
            next_retry_at=timezone.now() + timezone.timedelta(minutes=30),
        )

        with patch(
            'src.domain.tasks.sync_invoice_tasks.sync_single_invoice_task.delay',
        ) as mock_delay:
            sync_pending_invoices_task.delay()

        mock_delay.assert_not_called()

    def test_does_not_dispatch_completed_entries(self, organization):
        _make_config(organization)
        order = _make_order(organization)
        entry = _make_sync_entry(organization, order)
        entry.status = InvoiceSyncQueue.STATUS_COMPLETED
        entry.completed_at = timezone.now()
        entry.save()

        with patch(
            'src.domain.tasks.sync_invoice_tasks.sync_single_invoice_task.delay',
        ) as mock_delay:
            sync_pending_invoices_task.delay()

        mock_delay.assert_not_called()

    def test_empty_queue_returns_zero(self):
        result = sync_pending_invoices_task.delay()
        assert result.result == 0
