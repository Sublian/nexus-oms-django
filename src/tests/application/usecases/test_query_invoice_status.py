"""
Tests para InvoiceStatusQueryUseCase.

Cubre: mapeo de estados, actualizacion de Order, persistencia de hash,
idempotencia, sin config, sin external_id, propagacion de excepciones.
"""
import pytest
from unittest.mock import MagicMock, patch

from src.application.usecases.query_invoice_status import InvoiceStatusQueryUseCase
from src.domain.exceptions import NubefactTemporaryError, NubefactPermanentError


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_sync_entry(
    external_id='B001-42',
    current_status='sync_pending',
    existing_hash=None,
    org_id=1,
):
    order = MagicMock()
    order.id = 42
    order.invoice_external_id = external_id
    order.invoice_status = current_status
    order.invoice_hash = existing_hash
    order.organization_id = org_id

    entry = MagicMock()
    entry.order = order
    return entry


def _make_provider(accepted=True, observed=False, rejected=False, hash_val='hash-abc'):
    provider = MagicMock()
    provider.get_invoice_status.return_value = {
        'accepted':           accepted,
        'observed':           observed,
        'rejected':           rejected,
        'hash':               hash_val if (accepted or observed) else None,
        'provider_reference': 'REF-001',
        'raw_response':       {},
    }
    return provider


# ── status resolution ─────────────────────────────────────────────────────────

class TestInvoiceStatusQueryUseCase:

    def test_accepted_sets_order_status_accepted(self):
        entry = _make_sync_entry()
        provider = _make_provider(accepted=True)

        InvoiceStatusQueryUseCase(provider=provider).execute(entry)

        assert entry.order.invoice_status == 'accepted'

    def test_observed_sets_order_status_observed(self):
        entry = _make_sync_entry()
        provider = _make_provider(accepted=True, observed=True)

        InvoiceStatusQueryUseCase(provider=provider).execute(entry)

        assert entry.order.invoice_status == 'observed'

    def test_rejected_sets_order_status_rejected(self):
        entry = _make_sync_entry()
        provider = _make_provider(accepted=False, rejected=True, hash_val=None)

        InvoiceStatusQueryUseCase(provider=provider).execute(entry)

        assert entry.order.invoice_status == 'rejected'

    def test_pending_sunat_sets_sync_pending(self):
        entry = _make_sync_entry()
        provider = _make_provider(accepted=False, observed=False, rejected=False, hash_val=None)

        InvoiceStatusQueryUseCase(provider=provider).execute(entry)

        assert entry.order.invoice_status == 'sync_pending'

    def test_hash_persisted_when_received_for_first_time(self):
        entry = _make_sync_entry(existing_hash=None)
        provider = _make_provider(accepted=True, hash_val='cdr-hash-xyz')

        InvoiceStatusQueryUseCase(provider=provider).execute(entry)

        assert entry.order.invoice_hash == 'cdr-hash-xyz'

    def test_hash_not_overwritten_if_already_set(self):
        entry = _make_sync_entry(existing_hash='original-hash')
        provider = _make_provider(accepted=True, hash_val='new-hash')

        InvoiceStatusQueryUseCase(provider=provider).execute(entry)

        assert entry.order.invoice_hash == 'original-hash'

    def test_order_save_called_with_update_fields(self):
        entry = _make_sync_entry(existing_hash=None)
        provider = _make_provider(accepted=True, hash_val='h')

        InvoiceStatusQueryUseCase(provider=provider).execute(entry)

        entry.order.save.assert_called_once()
        call_kwargs = entry.order.save.call_args[1]
        assert 'invoice_status' in call_kwargs['update_fields']
        assert 'invoice_hash' in call_kwargs['update_fields']

    def test_no_external_id_raises_permanent_error(self):
        entry = _make_sync_entry(external_id=None)
        provider = _make_provider()

        with pytest.raises(NubefactPermanentError, match='no tiene invoice_external_id'):
            InvoiceStatusQueryUseCase(provider=provider).execute(entry)

    def test_provider_temporary_error_propagates(self):
        entry = _make_sync_entry()
        provider = MagicMock()
        provider.get_invoice_status.side_effect = NubefactTemporaryError('timeout')

        with pytest.raises(NubefactTemporaryError):
            InvoiceStatusQueryUseCase(provider=provider).execute(entry)

    def test_provider_permanent_error_propagates(self):
        entry = _make_sync_entry()
        provider = MagicMock()
        provider.get_invoice_status.side_effect = NubefactPermanentError('401')

        with pytest.raises(NubefactPermanentError):
            InvoiceStatusQueryUseCase(provider=provider).execute(entry)

    def test_returns_provider_result_dict(self):
        entry = _make_sync_entry()
        provider = _make_provider(accepted=True, hash_val='h')

        result = InvoiceStatusQueryUseCase(provider=provider).execute(entry)

        assert result['accepted'] is True
        assert result['hash'] == 'h'

    def test_no_config_raises_permanent_error(self):
        entry = _make_sync_entry()

        from src.domain.models.config import CompanyInvoiceConfig
        with patch.object(
            CompanyInvoiceConfig.objects,
            'get',
            side_effect=CompanyInvoiceConfig.DoesNotExist,
        ):
            with pytest.raises(NubefactPermanentError, match='CompanyInvoiceConfig'):
                InvoiceStatusQueryUseCase().execute(entry)
