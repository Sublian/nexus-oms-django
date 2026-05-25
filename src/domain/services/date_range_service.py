"""
DateRangeService — centralised temporal range resolver.

All methods return timezone-aware datetime pairs (start, end).
Views call from_request() to parse HTTP query parameters.

Supported query patterns:
  ?start=YYYY-MM-DD&end=YYYY-MM-DD   explicit custom range
  ?period=month[&month=N&year=Y]      calendar month
  ?period=today | week | year[&year=Y]
  ?range=1d | 7d | 30d | all          legacy rolling window (backwards-compat)
"""

import calendar
from datetime import datetime, timedelta
from typing import Optional, Tuple

ES_MONTHS = {
    1: 'Enero',    2: 'Febrero',   3: 'Marzo',    4: 'Abril',
    5: 'Mayo',     6: 'Junio',     7: 'Julio',    8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}

from django.utils import timezone

DateTimePair = Tuple[Optional[datetime], Optional[datetime]]
RangeResult  = Tuple[Optional[datetime], Optional[datetime], str]


class DateRangeValidationError(ValueError):
    """Raised for invalid or out-of-bounds range parameters."""


class DateRangeService:
    MAX_RANGE_DAYS = 365

    # ── Primitive constructors ────────────────────────────────────────────────

    def today_range(self) -> DateTimePair:
        now = timezone.now()
        start = now.replace(hour=0,  minute=0,  second=0,  microsecond=0)
        end   = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end

    def week_range(self) -> DateTimePair:
        now   = timezone.now()
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return start, now

    def month_range(
        self,
        month: Optional[int] = None,
        year:  Optional[int] = None,
    ) -> DateTimePair:
        now = timezone.now()
        m = month if month is not None else now.month
        y = year  if year  is not None else now.year
        if not (1 <= m <= 12):
            raise DateRangeValidationError(f"Mes inválido: {m}")
        _, last_day = calendar.monthrange(y, m)
        tz    = timezone.get_current_timezone()
        start = timezone.make_aware(datetime(y, m,        1,        0, 0,  0,       0), tz)
        end   = timezone.make_aware(datetime(y, m, last_day, 23, 59, 59, 999999), tz)
        return start, end

    def rolling_30_days(self) -> DateTimePair:
        return self.rolling_n_days(30)

    def rolling_n_days(self, n: int) -> DateTimePair:
        now = timezone.now()
        return now - timedelta(days=n), now

    def year_range(self, year: Optional[int] = None) -> DateTimePair:
        now = timezone.now()
        y  = year if year is not None else now.year
        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime(y,  1,  1,  0,  0,  0,      0), tz)
        end   = timezone.make_aware(datetime(y, 12, 31, 23, 59, 59, 999999), tz)
        return start, end

    def custom_range(self, start_str: str, end_str: str) -> DateTimePair:
        tz = timezone.get_current_timezone()
        try:
            start = timezone.make_aware(
                datetime.strptime(start_str, '%Y-%m-%d'), tz
            )
            end = timezone.make_aware(
                datetime.strptime(end_str, '%Y-%m-%d').replace(
                    hour=23, minute=59, second=59, microsecond=999999
                ), tz
            )
        except ValueError as exc:
            raise DateRangeValidationError(
                f"Formato de fecha inválido (esperado YYYY-MM-DD): {exc}"
            ) from exc

        if start > end:
            raise DateRangeValidationError(
                "La fecha inicio debe ser anterior a la fecha fin."
            )
        if (end - start).days > self.MAX_RANGE_DAYS:
            raise DateRangeValidationError(
                f"El rango no puede superar {self.MAX_RANGE_DAYS} días."
            )
        return start, end

    # ── HTTP request resolver ─────────────────────────────────────────────────

    def from_request(self, request) -> RangeResult:
        """
        Parse temporal range from HTTP query parameters.
        Returns (date_from, date_to, display_label).
        """
        # 1. Explicit custom range
        start_str = request.GET.get('start')
        end_str   = request.GET.get('end')
        if start_str and end_str:
            try:
                start, end = self.custom_range(start_str, end_str)
                return start, end, f"{start_str} — {end_str}"
            except DateRangeValidationError:
                pass  # fall through to next resolution

        # 2. Named period
        period = request.GET.get('period')
        if period == 'month':
            try:
                m_raw = request.GET.get('month')
                y_raw = request.GET.get('year')
                m = int(m_raw) if m_raw else None
                y = int(y_raw) if y_raw else None
                start, end = self.month_range(m, y)
                _m = m or timezone.now().month
                _y = y or timezone.now().year
                label = f"{ES_MONTHS[_m]} {_y}"
                return start, end, label
            except (ValueError, TypeError, DateRangeValidationError):
                pass
        elif period == 'today':
            start, end = self.today_range()
            return start, end, "Hoy"
        elif period == 'week':
            start, end = self.week_range()
            return start, end, "Esta semana"
        elif period == 'year':
            try:
                y = int(request.GET.get('year') or timezone.now().year)
                start, end = self.year_range(y)
                return start, end, str(y)
            except (ValueError, DateRangeValidationError):
                pass

        # 3. Legacy ?range= rolling window
        range_param = request.GET.get('range', '7d')
        now = timezone.now()
        legacy: dict[str, RangeResult] = {
            '1d':  (now - timedelta(days=1),  now, "Últimas 24h"),
            '7d':  (now - timedelta(days=7),  now, "Últimos 7 días"),
            '30d': (now - timedelta(days=30), now, "Últimos 30 días"),
            'all': (None,                     None, "Todo el tiempo"),
        }
        return legacy.get(range_param, legacy['7d'])
