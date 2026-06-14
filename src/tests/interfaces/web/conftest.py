# src/tests/interfaces/web/conftest.py
# Web interface tests require pre-populated ExchangeRate to avoid HTTP leaks

import pytest


@pytest.fixture(autouse=True)
def _auto_populate_exchange_rate(exchange_rate_fixture):
    """Auto-use exchange_rate_fixture only in web interface tests.

    This ensures context processors don't attempt HTTP calls to APIMigo,
    while allowing service-level tests to control their own DB state.
    """
    pass
