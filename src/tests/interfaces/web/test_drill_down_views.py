"""
Tests for FASE 2A drill-down views:
  - queue_detail_view      /operations/queue/
  - integration_logs_view  /operations/integrations/
  - accounting_detail_view /operations/accounting/

Covers: HTTP 200, tenant isolation, filter parameters.
Does NOT test template rendering in detail (visual coverage only).
"""

import pytest
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from src.domain.models import Order, AccountingEntry
from src.domain.models.invoicing import InvoiceSyncQueue
from src.domain.models.integrations import ExternalRequestLog
from src.domain.models.order_constants import OrderStatus


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_order(org, invoice_status='pending'):
    return Order.objects.create(
        organization=org,
        customer_name='Test',
        customer_email='t@t.com',
        status=OrderStatus.PAID,
        total_amount=100,
        invoice_status=invoice_status,
    )


def _make_queue_entry(org, status='pending'):
    order = _make_order(org, invoice_status='sync_pending')
    return InvoiceSyncQueue.objects.create(
        organization=org,
        order=order,
        status=status,
        next_retry_at=timezone.now() + timedelta(minutes=5),
    )


def _make_log(org, provider='nubefact', success=True):
    return ExternalRequestLog.objects.create(
        organization=org,
        provider_name=provider,
        operation='query_status',
        success=success,
        duration_ms=200,
    )


def _make_accounting_entry(org, order):
    return AccountingEntry.objects.create(
        organization=org,
        order=order,
        invoice_external_id='FAC-001',
        amount_gross=100,
        amount_tax=18,
        amount_net=82,
    )


# ── Queue Detail View ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestQueueDetailView:

    def test_returns_200(self, logged_in_client, organization):
        url = reverse('web:operations_queue', kwargs={'org_slug': organization.slug})
        assert logged_in_client.get(url).status_code == 200

    def test_status_filter_pending(self, logged_in_client, organization):
        _make_queue_entry(organization, status='pending')
        _make_queue_entry(organization, status='failed')
        url = reverse('web:operations_queue', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?status=pending')
        assert response.status_code == 200
        assert response.context['page_obj'].paginator.count == 1

    def test_status_filter_dead_letter(self, logged_in_client, organization):
        _make_queue_entry(organization, status='dead_letter')
        _make_queue_entry(organization, status='pending')
        url = reverse('web:operations_queue', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?status=dead_letter')
        assert response.status_code == 200
        assert response.context['page_obj'].paginator.count == 1

    def test_status_filter_exhausted(self, logged_in_client, organization):
        _make_queue_entry(organization, status='exhausted')
        url = reverse('web:operations_queue', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?status=exhausted')
        assert response.status_code == 200
        assert response.context['page_obj'].paginator.count == 1

    def test_stale_filter(self, logged_in_client, organization):
        entry = _make_queue_entry(organization, status='processing')
        # Force locked_at to be >10 min ago
        stale_time = timezone.now() - timedelta(minutes=15)
        InvoiceSyncQueue.objects.filter(pk=entry.pk).update(locked_at=stale_time)

        url = reverse('web:operations_queue', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?status=stale')
        assert response.status_code == 200
        assert response.context['page_obj'].paginator.count == 1

    def test_stale_filter_excludes_non_stale(self, logged_in_client, organization):
        entry = _make_queue_entry(organization, status='processing')
        # locked_at = 2 min ago — NOT stale
        InvoiceSyncQueue.objects.filter(pk=entry.pk).update(
            locked_at=timezone.now() - timedelta(minutes=2)
        )
        url = reverse('web:operations_queue', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?status=stale')
        assert response.context['page_obj'].paginator.count == 0

    def test_tenant_isolation(self, logged_in_client, organization, org_factory):
        other_org = org_factory('Other Queue Org')
        _make_queue_entry(other_org, status='dead_letter')
        url = reverse('web:operations_queue', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?status=dead_letter')
        assert response.context['page_obj'].paginator.count == 0

    def test_no_filter_returns_all_org_entries(self, logged_in_client, organization):
        _make_queue_entry(organization, status='pending')
        _make_queue_entry(organization, status='failed')
        url = reverse('web:operations_queue', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)
        assert response.context['page_obj'].paginator.count == 2


# ── Integration Logs View ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestIntegrationLogsView:

    def test_returns_200(self, logged_in_client, organization):
        url = reverse('web:operations_integrations', kwargs={'org_slug': organization.slug})
        assert logged_in_client.get(url).status_code == 200

    def test_no_logs_returns_empty(self, logged_in_client, organization):
        url = reverse('web:operations_integrations', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)
        assert response.context['page_obj'].paginator.count == 0

    def test_provider_filter(self, logged_in_client, organization):
        _make_log(organization, provider='nubefact')
        _make_log(organization, provider='shopify')
        url = reverse('web:operations_integrations', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?provider=nubefact')
        assert response.context['page_obj'].paginator.count == 1

    def test_error_status_filter(self, logged_in_client, organization):
        _make_log(organization, success=True)
        _make_log(organization, success=False)
        _make_log(organization, success=False)
        url = reverse('web:operations_integrations', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?status=error')
        assert response.context['page_obj'].paginator.count == 2

    def test_combined_provider_and_error_filter(self, logged_in_client, organization):
        _make_log(organization, provider='nubefact', success=False)
        _make_log(organization, provider='nubefact', success=True)
        _make_log(organization, provider='shopify', success=False)
        url = reverse('web:operations_integrations', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?provider=nubefact&status=error')
        assert response.context['page_obj'].paginator.count == 1

    def test_tenant_isolation(self, logged_in_client, organization, org_factory):
        other_org = org_factory('Other Logs Org')
        _make_log(other_org, provider='nubefact')
        url = reverse('web:operations_integrations', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?provider=nubefact')
        assert response.context['page_obj'].paginator.count == 0

    def test_providers_list_in_context(self, logged_in_client, organization):
        _make_log(organization, provider='nubefact')
        _make_log(organization, provider='shopify')
        url = reverse('web:operations_integrations', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)
        assert 'nubefact' in response.context['providers']
        assert 'shopify' in response.context['providers']


# ── Accounting Detail View ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAccountingDetailView:

    def test_returns_200(self, logged_in_client, organization):
        url = reverse('web:operations_accounting', kwargs={'org_slug': organization.slug})
        assert logged_in_client.get(url).status_code == 200

    def test_default_shows_accepted_orders(self, logged_in_client, organization):
        _make_order(organization, invoice_status='accepted')
        _make_order(organization, invoice_status='pending')
        url = reverse('web:operations_accounting', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)
        assert response.context['page_obj'].paginator.count == 1
        assert response.context['show_mode'] == 'orders'

    def test_missing_entries_filter(self, logged_in_client, organization):
        order_no_entry  = _make_order(organization, invoice_status='accepted')
        order_with_entry = _make_order(organization, invoice_status='accepted')
        _make_accounting_entry(organization, order_with_entry)

        url = reverse('web:operations_accounting', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?filter=missing_entries')
        assert response.context['page_obj'].paginator.count == 1
        assert response.context['page_obj'].object_list[0].id == order_no_entry.id

    def test_orphan_entries_filter(self, logged_in_client, organization):
        # Order with wrong status gets an accounting entry → orphan
        order = _make_order(organization, invoice_status='rejected')
        _make_accounting_entry(organization, order)
        url = reverse('web:operations_accounting', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?filter=orphan_entries')
        assert response.context['page_obj'].paginator.count == 1
        assert response.context['show_mode'] == 'entries'

    def test_orphan_filter_excludes_valid_entries(self, logged_in_client, organization):
        order = _make_order(organization, invoice_status='accepted')
        _make_accounting_entry(organization, order)
        url = reverse('web:operations_accounting', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?filter=orphan_entries')
        assert response.context['page_obj'].paginator.count == 0

    def test_tenant_isolation_missing(self, logged_in_client, organization, org_factory):
        other_org = org_factory('Other Accounting Org')
        _make_order(other_org, invoice_status='accepted')
        url = reverse('web:operations_accounting', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?filter=missing_entries')
        assert response.context['page_obj'].paginator.count == 0

    def test_tenant_isolation_orphans(self, logged_in_client, organization, org_factory):
        other_org = org_factory('Other Orphan Org')
        order = _make_order(other_org, invoice_status='rejected')
        _make_accounting_entry(other_org, order)
        url = reverse('web:operations_accounting', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?filter=orphan_entries')
        assert response.context['page_obj'].paginator.count == 0


# ── FASE 3: Invoice Detail & Timeline (Observable) ──────────────────────────────

@pytest.mark.django_db
class TestInvoiceDetailView:
    """FASE 3: Invoice observable timeline, T6 security (superuser isolation)"""

    def test_invoice_detail_returns_200(self, logged_in_client, organization):
        order = _make_order(organization, invoice_status='accepted')
        url = reverse('web:invoice_detail', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id
        })
        response = logged_in_client.get(url)
        assert response.status_code == 200

    def test_invoice_detail_renders_order_metadata(self, logged_in_client, organization):
        order = Order.objects.create(
            organization=organization,
            customer_name='Test',
            customer_email='t@t.com',
            status='PAID',
            total_amount=100,
            invoice_status='accepted',
            invoice_external_id='FAC-001-001',
            invoice_hash='abc123def456',
        )
        url = reverse('web:invoice_detail', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id
        })
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'FAC-001-001' in response.content.decode()
        assert 'abc123def456' in response.content.decode()
        assert order.invoice_status.upper() in response.content.decode()

    def test_invoice_detail_timeline_includes_workflow_logs(self, logged_in_client, organization):
        from src.domain.models.workflow_audit import OrderWorkflowLog

        order = _make_order(organization, invoice_status='accepted')
        OrderWorkflowLog.objects.create(
            organization=organization,
            order=order,
            action='invoicing_triggered',
            status='processing',
            metadata={'reason': 'paid_order'}
        )

        url = reverse('web:invoice_detail', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id
        })
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'Línea de Tiempo' in response.content.decode()
        assert 'Facturación disparada' in response.content.decode()

    def test_invoice_detail_timeline_includes_sync_queue(self, logged_in_client, organization):
        from src.domain.models.invoicing import InvoiceSyncQueue

        order = _make_order(organization, invoice_status='sync_pending')
        queue = InvoiceSyncQueue.objects.create(
            organization=organization,
            order=order,
            status='pending',
            next_retry_at=timezone.now() + timedelta(minutes=5),
            last_response={'status': 'processing'}
        )

        url = reverse('web:invoice_detail', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id
        })
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'encolada para sincronización' in response.content.decode()
        assert 'Cola de Sincronización' in response.content.decode()

    def test_invoice_detail_timeline_includes_accounting_entry(self, logged_in_client, organization):
        order = _make_order(organization, invoice_status='accepted')
        entry = _make_accounting_entry(organization, order)

        url = reverse('web:invoice_detail', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id
        })
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'Asiento Contable' in response.content.decode()
        assert str(entry.amount_gross) in response.content.decode()

    def test_invoice_detail_tenant_isolation(self, logged_in_client, organization, org_factory):
        """T6 Mitigation: Superuser cannot access other tenant's invoice"""
        other_org = org_factory('Other Invoice Org')
        order = _make_order(other_org, invoice_status='accepted')

        # Try to access other org's invoice via first org's slug
        url = reverse('web:invoice_detail', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id
        })
        response = logged_in_client.get(url)
        assert response.status_code == 404  # Order not found in this org

    def test_invoice_detail_state_badge_rendering(self, logged_in_client, organization):
        """Test state_color badge appears correctly"""
        test_cases = [
            ('accepted', 'green'),
            ('rejected', 'red'),
            ('pending', 'gray'),
            ('sync_processing', 'orange'),
        ]
        for status, expected_color in test_cases:
            order = Order.objects.create(
                organization=organization,
                customer_name=f'Test {status}',
                customer_email='t@t.com',
                status='PAID',
                total_amount=100,
                invoice_status=status,
            )
            url = reverse('web:invoice_detail', kwargs={
                'org_slug': organization.slug,
                'order_id': order.id
            })
            response = logged_in_client.get(url)
            assert response.status_code == 200
            # Verify state_color is in context (template uses it)
            assert response.context['state_color'] == expected_color
