"""
Tests for DateRangeService — all temporal range resolution paths.
"""

import calendar
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from src.domain.services.date_range_service import DateRangeService, DateRangeValidationError


def _mock_request(**params):
    req = MagicMock()
    req.GET = params  # plain dict — has a real .get()
    return req


@pytest.mark.django_db
class TestPrimitiveConstructors:

    def test_today_range_same_day(self):
        svc = DateRangeService()
        start, end = svc.today_range()
        assert start.date() == end.date()
        assert start.hour == 0 and start.minute == 0
        assert end.hour == 23 and end.minute == 59

    def test_today_range_timezone_aware(self):
        svc = DateRangeService()
        start, end = svc.today_range()
        assert timezone.is_aware(start)
        assert timezone.is_aware(end)

    def test_week_range_start_is_monday(self):
        svc = DateRangeService()
        start, _ = svc.week_range()
        assert start.weekday() == 0  # Monday

    def test_week_range_timezone_aware(self):
        svc = DateRangeService()
        start, end = svc.week_range()
        assert timezone.is_aware(start)
        assert timezone.is_aware(end)

    def test_month_range_current_month(self):
        svc = DateRangeService()
        now = timezone.now()
        start, end = svc.month_range()
        assert start.month == now.month
        assert start.day == 1
        assert end.month == now.month
        _, last_day = calendar.monthrange(now.year, now.month)
        assert end.day == last_day

    def test_month_range_specific_month(self):
        svc = DateRangeService()
        start, end = svc.month_range(month=2, year=2024)  # leap year
        assert start.day == 1
        assert end.day == 29  # 2024 is leap

    def test_month_range_invalid_month(self):
        svc = DateRangeService()
        with pytest.raises(DateRangeValidationError):
            svc.month_range(month=13)

    def test_month_range_zero_month(self):
        svc = DateRangeService()
        with pytest.raises(DateRangeValidationError):
            svc.month_range(month=0)

    def test_rolling_n_days(self):
        svc = DateRangeService()
        start, end = svc.rolling_n_days(14)
        assert timezone.is_aware(start)
        delta = end - start
        assert 13 <= delta.days <= 14  # allow sub-second drift

    def test_rolling_30_days_delegates(self):
        svc = DateRangeService()
        start1, end1 = svc.rolling_30_days()
        start2, end2 = svc.rolling_n_days(30)
        # Both should be within a second of each other
        assert abs((start1 - start2).total_seconds()) < 2

    def test_year_range_current_year(self):
        svc = DateRangeService()
        start, end = svc.year_range()
        now = timezone.now()
        assert start.year == now.year
        assert start.month == 1 and start.day == 1
        assert end.month == 12 and end.day == 31

    def test_year_range_specific_year(self):
        svc = DateRangeService()
        start, end = svc.year_range(year=2023)
        assert start.year == 2023 and start.month == 1
        assert end.year == 2023 and end.month == 12

    def test_year_range_timezone_aware(self):
        svc = DateRangeService()
        start, end = svc.year_range()
        assert timezone.is_aware(start)
        assert timezone.is_aware(end)


@pytest.mark.django_db
class TestCustomRange:

    def test_valid_range(self):
        svc = DateRangeService()
        start, end = svc.custom_range('2026-01-01', '2026-01-31')
        assert start.day == 1
        assert end.day == 31
        assert end.hour == 23 and end.minute == 59

    def test_timezone_aware_output(self):
        svc = DateRangeService()
        start, end = svc.custom_range('2026-03-01', '2026-03-15')
        assert timezone.is_aware(start)
        assert timezone.is_aware(end)

    def test_invalid_date_format(self):
        svc = DateRangeService()
        with pytest.raises(DateRangeValidationError):
            svc.custom_range('01-01-2026', '31-01-2026')

    def test_start_after_end_raises(self):
        svc = DateRangeService()
        with pytest.raises(DateRangeValidationError):
            svc.custom_range('2026-02-01', '2026-01-01')

    def test_range_exceeds_max_days(self):
        svc = DateRangeService()
        with pytest.raises(DateRangeValidationError):
            svc.custom_range('2025-01-01', '2026-12-31')

    def test_single_day_range_valid(self):
        svc = DateRangeService()
        start, end = svc.custom_range('2026-05-01', '2026-05-01')
        assert start.date() == end.date()


@pytest.mark.django_db
class TestFromRequest:

    def test_explicit_start_end_takes_priority(self):
        svc = DateRangeService()
        req = _mock_request(start='2026-04-01', end='2026-04-30', range='7d')
        start, end, label = svc.from_request(req)
        assert start.month == 4 and start.day == 1
        assert '2026-04-01' in label

    def test_period_month_current(self):
        svc = DateRangeService()
        req = _mock_request(period='month')
        start, end, label = svc.from_request(req)
        now = timezone.now()
        assert start.month == now.month
        assert str(now.year) in label

    def test_period_month_with_explicit_month(self):
        svc = DateRangeService()
        req = _mock_request(period='month', month='3', year='2026')
        start, end, label = svc.from_request(req)
        assert start.month == 3
        assert start.year == 2026
        assert 'Marzo 2026' in label

    def test_period_today(self):
        svc = DateRangeService()
        req = _mock_request(period='today')
        start, end, label = svc.from_request(req)
        assert start.date() == timezone.now().date()
        assert label == "Hoy"

    def test_period_week(self):
        svc = DateRangeService()
        req = _mock_request(period='week')
        start, end, label = svc.from_request(req)
        assert start.weekday() == 0
        assert label == "Esta semana"

    def test_period_year_current(self):
        svc = DateRangeService()
        req = _mock_request(period='year')
        start, end, label = svc.from_request(req)
        assert start.month == 1 and start.day == 1
        assert label == str(timezone.now().year)

    def test_period_year_explicit(self):
        svc = DateRangeService()
        req = _mock_request(period='year', year='2025')
        start, end, label = svc.from_request(req)
        assert start.year == 2025
        assert label == '2025'

    def test_legacy_range_1d(self):
        svc = DateRangeService()
        req = _mock_request(range='1d')
        start, end, label = svc.from_request(req)
        assert label == "Últimas 24h"
        delta = end - start
        assert 0 < delta.total_seconds() <= 86401  # ~1 day

    def test_legacy_range_7d(self):
        svc = DateRangeService()
        req = _mock_request(range='7d')
        _, _, label = svc.from_request(req)
        assert label == "Últimos 7 días"

    def test_legacy_range_30d(self):
        svc = DateRangeService()
        req = _mock_request(range='30d')
        _, _, label = svc.from_request(req)
        assert label == "Últimos 30 días"

    def test_legacy_range_all_returns_none_dates(self):
        svc = DateRangeService()
        req = _mock_request(range='all')
        start, end, label = svc.from_request(req)
        assert start is None and end is None
        assert label == "Todo el tiempo"

    def test_default_falls_back_to_7d(self):
        svc = DateRangeService()
        req = _mock_request()  # no params
        _, _, label = svc.from_request(req)
        assert label == "Últimos 7 días"

    def test_invalid_start_end_falls_through_to_period(self):
        svc = DateRangeService()
        # invalid dates + valid period — should use period
        req = _mock_request(start='bad', end='date', period='today')
        _, _, label = svc.from_request(req)
        assert label == "Hoy"

    def test_invalid_start_end_falls_through_to_range(self):
        svc = DateRangeService()
        req = _mock_request(start='bad', end='date', range='30d')
        _, _, label = svc.from_request(req)
        assert label == "Últimos 30 días"

    def test_all_outputs_timezone_aware(self):
        svc = DateRangeService()
        for params in [
            {'range': '7d'},
            {'period': 'today'},
            {'period': 'week'},
            {'start': '2026-01-01', 'end': '2026-01-31'},
        ]:
            req = _mock_request(**params)
            start, end, _ = svc.from_request(req)
            if start is not None:
                assert timezone.is_aware(start), f"start not aware for {params}"
            if end is not None:
                assert timezone.is_aware(end), f"end not aware for {params}"
