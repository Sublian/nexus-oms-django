"""
Operational Dashboard Services — Sprint 4

Read-only query layer for the operational dashboard.
All aggregation logic lives here, not in views or templates.

Prepared for future wiring to Prometheus/OpenTelemetry (Sprint 5).
"""

from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone

STALE_LOCK_MINUTES = 10


# ── Invoice Metrics ────────────────────────────────────────────────────────────

class InvoiceMetricsService:
    """
    Aggregates Order.invoice_status counts for the operational dashboard.
    Uses all_objects to query across all tenants; filtered by organization arg.
    """

    TRACKED_STATUSES = [
        'pending', 'queued', 'processing', 'submitted',
        'sync_pending', 'sync_processing',
        'accepted', 'observed', 'rejected',
        'retrying', 'failed', 'cancelled',
    ]

    def get_metrics(self, organization, date_from=None, date_to=None) -> dict:
        from src.domain.models import Order

        qs = Order.all_objects.filter(organization=organization)
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        raw = dict(
            qs.values_list('invoice_status')
            .annotate(n=Count('id'))
        )

        by_status = {s: raw.get(s, 0) for s in self.TRACKED_STATUSES}

        terminal_ok  = by_status['accepted'] + by_status['observed']
        terminal_err = by_status['rejected'] + by_status['failed']
        in_flight    = (
            by_status['submitted'] + by_status['sync_pending'] +
            by_status['sync_processing'] + by_status['processing'] +
            by_status['queued'] + by_status['retrying']
        )
        total_invoiced = sum(raw.get(s, 0) for s in self.TRACKED_STATUSES if s != 'pending')

        return {
            'by_status':      by_status,
            'terminal_ok':    terminal_ok,
            'terminal_err':   terminal_err,
            'in_flight':      in_flight,
            'total_invoiced': total_invoiced,
            'has_alert':      terminal_err > 0 or by_status['retrying'] > 0,
        }


# ── Queue Health ───────────────────────────────────────────────────────────────

class QueueHealthService:
    """
    Aggregates InvoiceSyncQueue health metrics.
    Detects stale locks, exhausted entries, and oldest pending items.
    """

    def get_health(self, organization) -> dict:
        from src.domain.models import InvoiceSyncQueue

        qs = InvoiceSyncQueue.all_objects.filter(organization=organization)

        raw = dict(
            qs.values_list('status')
            .annotate(n=Count('id'))
        )

        now = timezone.now()
        stale_cutoff = now - timedelta(minutes=STALE_LOCK_MINUTES)
        stale_locks = qs.filter(locked_at__lt=stale_cutoff).count()

        oldest = (
            qs.filter(status=InvoiceSyncQueue.STATUS_PENDING)
            .order_by('created_at')
            .first()
        )
        oldest_age_mins = None
        if oldest:
            oldest_age_mins = int((now - oldest.created_at).total_seconds() / 60)

        exhausted   = raw.get('exhausted', 0)
        dead_letter = raw.get('dead_letter', 0)
        has_alert   = stale_locks > 0 or exhausted > 0 or dead_letter > 0

        return {
            'pending':          raw.get('pending', 0),
            'processing':       raw.get('processing', 0),
            'completed':        raw.get('completed', 0),
            'failed':           raw.get('failed', 0),
            'exhausted':        exhausted,
            'dead_letter':      dead_letter,
            'stale_locks':      stale_locks,
            'oldest_age_mins':  oldest_age_mins,
            'has_alert':        has_alert,
        }


# ── Integration Health ─────────────────────────────────────────────────────────

class IntegrationHealthService:
    """
    Aggregates ExternalRequestLog metrics per provider.
    Returns empty state gracefully when no logs exist yet.
    """

    def get_health(self, organization, date_from=None, date_to=None) -> dict:
        from src.domain.models.integrations import ExternalRequestLog

        qs = ExternalRequestLog.all_objects.filter(organization=organization)
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        agg = (
            qs.values('provider_name')
            .annotate(
                total=Count('id'),
                success_count=Count('id', filter=Q(success=True)),
                failed_count=Count('id', filter=Q(success=False)),
                avg_duration=Avg('duration_ms'),
            )
            .order_by('provider_name')
        )

        by_provider = {}
        total_requests = 0
        total_failed = 0

        for row in agg:
            name = row['provider_name']
            total = row['total']
            failed = row['failed_count']
            error_rate = round((failed / total) * 100, 1) if total else 0

            last_error_log = (
                qs.filter(provider_name=name, success=False)
                .order_by('-created_at')
                .values_list('error_message', flat=True)
                .first()
            )

            by_provider[name] = {
                'total':        total,
                'success':      row['success_count'],
                'failed':       failed,
                'error_rate':   error_rate,
                'avg_duration': int(row['avg_duration']) if row['avg_duration'] else None,
                'last_error':   last_error_log,
                'has_alert':    error_rate > 10,
            }
            total_requests += total
            total_failed += failed

        overall_error_rate = (
            round((total_failed / total_requests) * 100, 1)
            if total_requests else 0
        )

        return {
            'by_provider':         by_provider,
            'total_requests':      total_requests,
            'overall_error_rate':  overall_error_rate,
            'has_data':            total_requests > 0,
        }


# ── Accounting Consistency ─────────────────────────────────────────────────────

class AccountingConsistencyService:
    """
    Checks consistency between accepted invoices and generated AccountingEntries.

    Critical invariant: every Order with invoice_status='accepted' must have
    exactly one AccountingEntry. Violations indicate a bug in the pipeline.
    """

    def get_consistency(self, organization) -> dict:
        from src.domain.models import Order, AccountingEntry

        accepted_orders = Order.all_objects.filter(
            organization=organization,
            invoice_status='accepted',
        )
        accepted_count = accepted_orders.count()

        entries = AccountingEntry.all_objects.filter(organization=organization)
        entries_count = entries.count()

        # Orders accepted but without an accounting entry (pipeline gap)
        missing = accepted_orders.filter(accounting_entry__isnull=True).count()

        # Entries on orders NOT in accepted state (should be 0)
        orphans = entries.exclude(
            order__invoice_status='accepted'
        ).count()

        return {
            'accepted_orders':  accepted_count,
            'entries_generated': entries_count,
            'missing_entries':  missing,
            'orphan_entries':   orphans,
            'consistency_ok':   missing == 0 and orphans == 0,
            'has_alert':        missing > 0 or orphans > 0,
        }


# ── Facade ─────────────────────────────────────────────────────────────────────

class OperationalDashboardService:
    """
    Aggregates all dashboard services into a single call.
    Views call only this facade — individual services remain testable.
    """

    def __init__(self):
        self._invoice     = InvoiceMetricsService()
        self._queue       = QueueHealthService()
        self._integration = IntegrationHealthService()
        self._accounting  = AccountingConsistencyService()

    def get_dashboard_data(self, organization, date_from=None, date_to=None) -> dict:
        return {
            'invoice_metrics':     self._invoice.get_metrics(organization, date_from, date_to),
            'queue_health':        self._queue.get_health(organization),
            'integration_health':  self._integration.get_health(organization, date_from, date_to),
            'accounting':          self._accounting.get_consistency(organization),
        }
