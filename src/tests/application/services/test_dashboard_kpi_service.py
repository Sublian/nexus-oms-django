"""
Tests for DashboardKPIService.

Covers: no data defaults, acceptance rate formula (accepted+observed / terminal),
date range filtering, tenant isolation, avg_latency_ms computation.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from src.application.services.dashboard import DashboardKPIService
from src.domain.models import Order
from src.domain.models.integrations import ExternalRequestLog
from src.domain.models.order_constants import OrderStatus


def _make_order(organization, invoice_status='accepted', days_ago=0):
    order = Order.objects.create(
        organization=organization,
        customer_name='Test',
        customer_email='t@t.com',
        status=OrderStatus.PAID,
        total_amount=100.00,
        invoice_status=invoice_status,
    )
    if days_ago:
        past = timezone.now() - timedelta(days=days_ago)
        Order.objects.filter(pk=order.pk).update(created_at=past)
        order.refresh_from_db()
    return order


def _make_log(organization, provider='nubefact', duration_ms=200, success=True):
    return ExternalRequestLog.objects.create(
        organization=organization,
        provider_name=provider,
        operation='query_status',
        duration_ms=duration_ms,
        success=success,
    )


@pytest.mark.django_db
class TestDashboardKPIServiceNoData:

    def test_no_orders_acceptance_rate_is_zero(self, organization):
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['acceptance_rate'] == 0

    def test_no_orders_terminal_total_is_zero(self, organization):
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['terminal_total'] == 0

    def test_no_logs_avg_latency_is_none(self, organization):
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['avg_latency_ms'] is None

    def test_only_pending_orders_rate_is_zero(self, organization):
        _make_order(organization, invoice_status='pending')
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['acceptance_rate'] == 0
        assert result['terminal_total'] == 0


@pytest.mark.django_db
class TestDashboardKPIServiceAcceptanceRate:

    def test_all_accepted_rate_is_100(self, organization):
        for _ in range(5):
            _make_order(organization, invoice_status='accepted')
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['acceptance_rate'] == 100.0
        assert result['terminal_total'] == 5

    def test_all_rejected_rate_is_zero(self, organization):
        for _ in range(3):
            _make_order(organization, invoice_status='rejected')
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['acceptance_rate'] == 0.0
        assert result['terminal_total'] == 3

    def test_mixed_7_accepted_3_rejected_rate_is_70(self, organization):
        for _ in range(7):
            _make_order(organization, invoice_status='accepted')
        for _ in range(3):
            _make_order(organization, invoice_status='rejected')
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['acceptance_rate'] == 70.0
        assert result['terminal_total'] == 10

    def test_observed_counts_as_accepted_in_rate(self, organization):
        for _ in range(5):
            _make_order(organization, invoice_status='observed')
        for _ in range(5):
            _make_order(organization, invoice_status='rejected')
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['acceptance_rate'] == 50.0
        assert result['terminal_total'] == 10

    def test_failed_counts_as_negative_in_rate(self, organization):
        _make_order(organization, invoice_status='accepted')
        _make_order(organization, invoice_status='failed')
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['acceptance_rate'] == 50.0
        assert result['terminal_total'] == 2

    def test_accepted_and_observed_together_sum_numerator(self, organization):
        _make_order(organization, invoice_status='accepted')
        _make_order(organization, invoice_status='observed')
        _make_order(organization, invoice_status='rejected')
        _make_order(organization, invoice_status='failed')
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        # numerator = accepted(1) + observed(1) = 2 / 4 = 50%
        assert result['acceptance_rate'] == 50.0
        assert result['terminal_total'] == 4

    def test_rate_rounded_to_one_decimal(self, organization):
        # 1/3 ≈ 33.3%
        _make_order(organization, invoice_status='accepted')
        _make_order(organization, invoice_status='rejected')
        _make_order(organization, invoice_status='rejected')
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['acceptance_rate'] == 33.3


@pytest.mark.django_db
class TestDashboardKPIServiceDateFilter:

    def test_date_from_excludes_older_orders(self, organization):
        _make_order(organization, invoice_status='accepted', days_ago=10)
        cutoff = timezone.now() - timedelta(days=5)
        svc = DashboardKPIService()
        result = svc.get_kpis(organization, date_from=cutoff)
        assert result['terminal_total'] == 0
        assert result['acceptance_rate'] == 0

    def test_date_from_includes_orders_after_cutoff(self, organization):
        _make_order(organization, invoice_status='accepted', days_ago=2)
        _make_order(organization, invoice_status='accepted', days_ago=10)
        cutoff = timezone.now() - timedelta(days=5)
        svc = DashboardKPIService()
        result = svc.get_kpis(organization, date_from=cutoff)
        assert result['terminal_total'] == 1
        assert result['acceptance_rate'] == 100.0

    def test_date_to_excludes_newer_orders(self, organization):
        _make_order(organization, invoice_status='rejected', days_ago=0)
        cutoff = timezone.now() - timedelta(days=1)
        svc = DashboardKPIService()
        result = svc.get_kpis(organization, date_to=cutoff)
        assert result['terminal_total'] == 0


@pytest.mark.django_db
class TestDashboardKPIServiceTenantIsolation:

    def test_other_org_orders_not_counted(self, organization, org_factory):
        other = org_factory('Other Org')
        for _ in range(5):
            _make_order(other, invoice_status='accepted')
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['terminal_total'] == 0

    def test_own_org_orders_counted_not_others(self, organization, org_factory):
        other = org_factory('Other Org B')
        _make_order(organization, invoice_status='accepted')
        _make_order(other, invoice_status='rejected')
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['terminal_total'] == 1
        assert result['acceptance_rate'] == 100.0


@pytest.mark.django_db
class TestDashboardKPIServiceLatency:

    def test_single_log_returns_its_duration(self, organization):
        _make_log(organization, duration_ms=350)
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['avg_latency_ms'] == 350

    def test_avg_latency_computed_correctly(self, organization):
        _make_log(organization, duration_ms=100)
        _make_log(organization, duration_ms=300)
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['avg_latency_ms'] == 200

    def test_avg_latency_is_integer(self, organization):
        _make_log(organization, duration_ms=100)
        _make_log(organization, duration_ms=201)
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert isinstance(result['avg_latency_ms'], int)

    def test_latency_includes_failed_requests(self, organization):
        _make_log(organization, duration_ms=500, success=False)
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['avg_latency_ms'] == 500

    def test_latency_tenant_isolation(self, organization, org_factory):
        other = org_factory('Other Latency Org')
        _make_log(other, duration_ms=999)
        svc = DashboardKPIService()
        result = svc.get_kpis(organization)
        assert result['avg_latency_ms'] is None

    def test_latency_date_from_filter(self, organization):
        old_log = _make_log(organization, duration_ms=1000)
        ExternalRequestLog.objects.filter(pk=old_log.pk).update(
            created_at=timezone.now() - timedelta(days=10)
        )
        cutoff = timezone.now() - timedelta(days=5)
        svc = DashboardKPIService()
        result = svc.get_kpis(organization, date_from=cutoff)
        assert result['avg_latency_ms'] is None
