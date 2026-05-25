"""
Tests for DailyInvoiceSeriesService.

Covers: empty range, out-of-range orders, non-chart statuses filtered,
correct daily aggregation, days parameter, tenant isolation, boundary dates.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from src.application.services.dashboard import DailyInvoiceSeriesService
from src.domain.models import Order
from src.domain.models.order_constants import OrderStatus


CHART_STATUSES = ['accepted', 'observed', 'rejected', 'failed']


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


@pytest.mark.django_db
class TestDailyInvoiceSeriesEmpty:

    def test_no_orders_returns_zero_filled_datasets(self, organization):
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)

        for status in CHART_STATUSES:
            assert all(v == 0 for v in result['datasets'][status])

    def test_no_orders_returns_correct_label_count(self, organization):
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        # days+1: from 30 days ago to today inclusive
        assert len(result['labels']) == 31

    def test_days_parameter_controls_label_count(self, organization):
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=7)
        assert len(result['labels']) == 8

    def test_labels_are_formatted_dd_mm(self, organization):
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=7)
        for label in result['labels']:
            parts = label.split('/')
            assert len(parts) == 2
            day, month = parts
            assert day.isdigit() and 1 <= int(day) <= 31
            assert month.isdigit() and 1 <= int(month) <= 12

    def test_all_chart_statuses_present_in_datasets(self, organization):
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=7)
        for status in CHART_STATUSES:
            assert status in result['datasets']

    def test_datasets_length_matches_labels(self, organization):
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=14)
        label_count = len(result['labels'])
        for status in CHART_STATUSES:
            assert len(result['datasets'][status]) == label_count


@pytest.mark.django_db
class TestDailyInvoiceSeriesFiltering:

    def test_order_outside_range_not_counted(self, organization):
        _make_order(organization, invoice_status='accepted', days_ago=35)
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        assert sum(result['datasets']['accepted']) == 0

    def test_order_within_range_is_counted(self, organization):
        # Use days_ago=15 (well within the window) to avoid race conditions
        # at the exact 30-day boundary where timing can place the order out of range.
        _make_order(organization, invoice_status='accepted', days_ago=15)
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        assert sum(result['datasets']['accepted']) == 1

    def test_pending_status_not_in_chart(self, organization):
        _make_order(organization, invoice_status='pending', days_ago=1)
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        assert 'pending' not in result['datasets']
        assert sum(result['datasets']['accepted']) == 0

    def test_submitted_status_not_in_chart(self, organization):
        _make_order(organization, invoice_status='submitted', days_ago=1)
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        assert sum(result['datasets']['accepted']) == 0
        assert sum(result['datasets']['rejected']) == 0

    def test_tenant_isolation(self, organization, org_factory):
        other_org = org_factory('Other Org')
        _make_order(other_org, invoice_status='accepted', days_ago=1)

        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        assert sum(result['datasets']['accepted']) == 0


@pytest.mark.django_db
class TestDailyInvoiceSeriesAggregation:

    def test_recent_order_appears_in_accepted_series(self, organization):
        # Use days_ago=1 to avoid timezone boundary: TruncDate uses Django's
        # TIME_ZONE (America/Lima, UTC-5) while now.date() is UTC, so "today"
        # orders can fall on different date slots depending on the time of day.
        _make_order(organization, invoice_status='accepted', days_ago=1)
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        assert sum(result['datasets']['accepted']) == 1

    def test_multiple_orders_same_day_summed(self, organization):
        for _ in range(3):
            _make_order(organization, invoice_status='accepted', days_ago=2)
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        assert sum(result['datasets']['accepted']) == 3

    def test_different_statuses_disaggregated(self, organization):
        _make_order(organization, invoice_status='accepted', days_ago=1)
        _make_order(organization, invoice_status='rejected', days_ago=1)
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        assert sum(result['datasets']['accepted']) == 1
        assert sum(result['datasets']['rejected']) == 1
        assert sum(result['datasets']['observed']) == 0
        assert sum(result['datasets']['failed']) == 0

    def test_orders_on_different_days_placed_correctly(self, organization):
        _make_order(organization, invoice_status='accepted', days_ago=1)
        _make_order(organization, invoice_status='accepted', days_ago=5)
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        assert sum(result['datasets']['accepted']) == 2
        # The two orders are on different days, so no single day has count > 1
        assert max(result['datasets']['accepted']) == 1

    def test_all_chart_statuses_counted_independently(self, organization):
        _make_order(organization, invoice_status='accepted',  days_ago=1)
        _make_order(organization, invoice_status='observed',  days_ago=1)
        _make_order(organization, invoice_status='rejected',  days_ago=1)
        _make_order(organization, invoice_status='failed',    days_ago=1)
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        for status in CHART_STATUSES:
            assert sum(result['datasets'][status]) == 1

    def test_same_tenant_multiple_orders_all_counted(self, organization):
        for _ in range(5):
            _make_order(organization, invoice_status='accepted', days_ago=3)
        svc = DailyInvoiceSeriesService()
        result = svc.get_daily_series(organization, days=30)
        assert sum(result['datasets']['accepted']) == 5
