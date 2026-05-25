"""
URL resolution tests for the web namespace.

Ensures every named route in src/interfaces/web/urls.py can be reversed
without error. Guards against kebab-case vs snake_case regressions.
"""

import pytest
from django.urls import reverse, NoReverseMatch

SLUG = "test-org"
ORDER_ID = 1
ITEM_ID = 1
CLIENT_ID = 1
PRODUCT_ID = 1


def _r(name, **kwargs):
    """Helper: reverse a web-namespaced URL and assert it resolves."""
    kwargs.setdefault("org_slug", SLUG)
    return reverse(f"web:{name}", kwargs=kwargs)


# ── No-argument routes (only org_slug) ────────────────────────────────────────

@pytest.mark.parametrize("url_name", [
    "dashboard_home",
    "org_settings",
    "org_settings_notifications",
    "org_settings_company",
    "org_settings_shipping",
    "validate_identity",
    "order_list",
    "order_create",
    "search_client",
    "search_product",
    "client_list",
    "client_create",
    "product_list",
    "product_create",
    "exchange_history",
    "operational_dashboard",
])
def test_url_resolves_with_org_slug(url_name):
    url = _r(url_name)
    assert url.startswith(f"/dashboard/{SLUG}/"), (
        f"web:{url_name} resolved to unexpected path: {url}"
    )


# ── Routes with additional parameters ─────────────────────────────────────────

def test_order_detail_resolves():
    assert _r("order_detail", order_id=ORDER_ID)


def test_generate_order_pdf_resolves():
    assert _r("generate_order_pdf", order_id=ORDER_ID)


def test_order_cancel_resolves():
    assert _r("order_cancel", order_id=ORDER_ID)


def test_order_status_resolves():
    assert _r("order_status", order_id=ORDER_ID)


def test_order_pay_resolves():
    assert _r("order_pay", order_id=ORDER_ID)


def test_order_confirm_status_resolves():
    assert _r("order_confirm_status", order_id=ORDER_ID)


def test_order_item_edit_resolves():
    assert _r("order_item_edit", order_id=ORDER_ID, item_id=ITEM_ID)


def test_order_item_delete_resolves():
    assert _r("order_item_delete", order_id=ORDER_ID, item_id=ITEM_ID)


def test_order_item_delete_confirm_resolves():
    assert _r("order_item_delete_confirm", order_id=ORDER_ID, item_id=ITEM_ID)


def test_add_to_order_resolves():
    assert _r("add_to_order", product_id=PRODUCT_ID)


def test_client_detail_resolves():
    assert _r("client_detail", client_id=CLIENT_ID)


def test_client_edit_resolves():
    assert _r("client_edit", client_id=CLIENT_ID)


def test_product_detail_resolves():
    assert _r("product_detail", product_id=PRODUCT_ID)


def test_product_edit_resolves():
    assert _r("product_edit", product_id=PRODUCT_ID)


def test_product_toggle_resolves():
    assert _r("product_toggle", product_id=PRODUCT_ID)


# ── Regression: operational dashboard (the original bug) ──────────────────────

def test_operational_dashboard_reverse():
    """Ensures operational_dashboard route resolves — NoReverseMatch guard."""
    url = reverse("web:operational_dashboard", kwargs={"org_slug": "nike"})
    assert url == "/dashboard/nike/operations/"


def test_no_kebab_case_names_exist():
    """Ensure none of the old kebab-case names are still registered."""
    kebab_names = [
        "org-settings", "org-settings-notifications", "org-settings-company",
        "org-settings-shipping", "validate-identity",
        "order-list", "order-create", "order-cancel", "order-status",
        "order-pay", "order-confirm-status",
        "order-item-edit", "order-item-delete", "order-item-delete-confirm",
        "search-product", "search-client", "add-to-order",
        "client-list", "client-create", "client-detail", "client-edit",
        "product-list", "product-create", "product-detail",
        "product-edit", "product-toggle",
        "exchange-history", "operational-dashboard",
    ]
    for name in kebab_names:
        with pytest.raises(NoReverseMatch):
            reverse(f"web:{name}", kwargs={"org_slug": SLUG})
