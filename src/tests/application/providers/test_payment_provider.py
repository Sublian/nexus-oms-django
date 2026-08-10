import pytest

from src.application.providers.factory import get_payment_provider
from src.application.providers.mock_payment_provider import MockPaymentProvider
from src.domain.models import Payment


def _make_payment(**kwargs):
    defaults = {'method': 'CARD', 'transaction_reference': None}
    defaults.update(kwargs)
    return Payment(**defaults)


class TestMockPaymentProvider:
    """Reglas determinísticas del mock, espejo de MockNubefactClient."""

    def test_cash_approved_immediately(self):
        result = MockPaymentProvider(None).process_payment(_make_payment(method='CASH'))
        assert result['status'] == 'approved'
        assert result['external_id'].startswith('PAY-MOCK-')

    def test_card_approved_with_normal_reference(self):
        result = MockPaymentProvider(None).process_payment(
            _make_payment(method='CARD', transaction_reference='TXN-001')
        )
        assert result['status'] == 'approved'

    def test_card_declined_when_reference_starts_with_reject(self):
        result = MockPaymentProvider(None).process_payment(
            _make_payment(method='CARD', transaction_reference='REJECT-999')
        )
        assert result['status'] == 'declined'
        assert result['error']

    def test_transfer_pending_then_approved(self):
        provider = MockPaymentProvider(None)
        payment = _make_payment(method='TRANSFER', transaction_reference='BCP-001')

        first = provider.process_payment(payment)
        assert first['status'] == 'pending'

        confirmed = provider.get_payment_status(payment)
        assert confirmed['status'] == 'approved'

    def test_wallet_pending(self):
        provider = MockPaymentProvider(None)
        payment = _make_payment(method='WALLET', transaction_reference='Yape 999')

        assert provider.process_payment(payment)['status'] == 'pending'
        assert provider.get_payment_status(payment)['status'] == 'approved'

    def test_scenario_override_declined(self):
        provider = MockPaymentProvider(None)
        provider.status_scenario = 'declined'
        assert provider.process_payment(_make_payment(method='CASH'))['status'] == 'declined'

    def test_scenario_override_pending(self):
        provider = MockPaymentProvider(None)
        provider.status_scenario = 'pending'
        assert provider.process_payment(_make_payment(method='CASH'))['status'] == 'pending'


class TestPaymentProviderFactory:

    def test_default_resolves_to_mock(self):
        assert isinstance(get_payment_provider(None), MockPaymentProvider)

    def test_mock_config_resolves_to_mock(self):
        assert isinstance(get_payment_provider(type('Cfg', (), {'provider_type': 'mock'})), MockPaymentProvider)

    def test_izipay_not_implemented_yet(self):
        with pytest.raises(NotImplementedError):
            get_payment_provider(type('Cfg', (), {'provider_type': 'izipay'}))
