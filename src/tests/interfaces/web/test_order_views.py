
import pytest

from django.urls import reverse

from src.domain.models.sales import Order


@pytest.mark.django_db
def test_order_list_view_status_code(client, admin_user, organization):
    # Usamos admin_user que sí existe en tus fixtures
    client.force_login(admin_user)
    
    # IMPORTANTE: El middleware de tenant necesita que el usuario tenga permiso 
    # o que la URL contenga el slug correcto.
    url = reverse('web:order_list', kwargs={'org_slug': organization.slug})
    response = client.get(url)
    
    assert response.status_code == 200


# ── FASE 2B: Invoice Status Drill-down Filtering ─────────────────────────────────

@pytest.mark.django_db
class TestOrderListInvoiceStatusFilter:
    """FASE 2B tests: drill-down from operational dashboard KPIs"""

    def test_order_list_invoice_status_accepted_filter(self, logged_in_client, organization):
        """Filter orders by invoice_status=accepted"""
        Order.objects.create(organization=organization, customer_name="Aceptada", invoice_status='accepted')
        Order.objects.create(organization=organization, customer_name="Rechazada", invoice_status='rejected')
        Order.objects.create(organization=organization, customer_name="Pendiente", invoice_status='pending')

        url = reverse('web:order_list', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?invoice_status=accepted')

        assert response.status_code == 200
        assert response.context['page_obj'].paginator.count == 1
        assert response.context['active_invoice_status'] == 'accepted'

    def test_order_list_invoice_status_rejected_filter(self, logged_in_client, organization):
        """Filter orders by invoice_status=rejected"""
        Order.objects.create(organization=organization, customer_name="Aceptada", invoice_status='accepted')
        Order.objects.create(organization=organization, customer_name="Rechazada", invoice_status='rejected')
        Order.objects.create(organization=organization, customer_name="Otra Rechazada", invoice_status='rejected')

        url = reverse('web:order_list', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?invoice_status=rejected')

        assert response.status_code == 200
        assert response.context['page_obj'].paginator.count == 2
        assert response.context['active_invoice_status'] == 'rejected'

    def test_order_list_invoice_status_submitted_filter(self, logged_in_client, organization):
        """Filter orders by invoice_status=submitted (en tránsito)"""
        Order.objects.create(organization=organization, customer_name="Submitted", invoice_status='submitted')
        Order.objects.create(organization=organization, customer_name="Sync Pending", invoice_status='sync_pending')
        Order.objects.create(organization=organization, customer_name="Accepted", invoice_status='accepted')

        url = reverse('web:order_list', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?invoice_status=submitted')

        assert response.status_code == 200
        assert response.context['page_obj'].paginator.count == 1

    def test_order_list_combine_invoice_status_with_order_status(self, logged_in_client, organization):
        """Filter by both order status and invoice_status"""
        Order.objects.create(
            organization=organization, customer_name="Paid Accepted",
            status='PAID', invoice_status='accepted'
        )
        Order.objects.create(
            organization=organization, customer_name="Paid Rejected",
            status='PAID', invoice_status='rejected'
        )
        Order.objects.create(
            organization=organization, customer_name="Draft Accepted",
            status='DRAFT', invoice_status='accepted'
        )

        url = reverse('web:order_list', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?status=PAID&invoice_status=accepted')

        assert response.status_code == 200
        assert response.context['page_obj'].paginator.count == 1

    def test_order_list_combine_invoice_status_with_search(self, logged_in_client, organization):
        """Filter by search query and invoice_status"""
        Order.objects.create(
            organization=organization, customer_name="Juan Pérez",
            invoice_status='accepted'
        )
        Order.objects.create(
            organization=organization, customer_name="María García",
            invoice_status='accepted'
        )
        Order.objects.create(
            organization=organization, customer_name="Pedro López",
            invoice_status='rejected'
        )

        url = reverse('web:order_list', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?q=Juan&invoice_status=accepted')

        assert response.status_code == 200
        assert response.context['page_obj'].paginator.count == 1

    def test_order_list_invoice_status_tenant_isolation(self, logged_in_client, organization, org_factory):
        """invoice_status filter respects tenant boundary (multi-tenant isolation)"""
        other_org = org_factory('Other Org')

        # Create orders in both orgs with same invoice_status
        Order.objects.create(organization=organization, customer_name="Org1 Accepted", invoice_status='accepted')
        Order.objects.create(organization=other_org, customer_name="Org2 Accepted", invoice_status='accepted')

        url = reverse('web:order_list', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url + '?invoice_status=accepted')

        assert response.status_code == 200
        assert response.context['page_obj'].paginator.count == 1
        assert response.context['page_obj'].object_list[0].organization_id == organization.id

    def test_order_list_no_invoice_status_filter_shows_all(self, logged_in_client, organization):
        """Without invoice_status filter, all orders visible"""
        Order.objects.create(organization=organization, customer_name="Accepted", invoice_status='accepted')
        Order.objects.create(organization=organization, customer_name="Rejected", invoice_status='rejected')
        Order.objects.create(organization=organization, customer_name="Pending", invoice_status='pending')

        url = reverse('web:order_list', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)

        assert response.status_code == 200
        assert response.context['page_obj'].paginator.count == 3
        assert response.context['active_invoice_status'] is None

    def test_order_list_invoice_status_choices_in_context(self, logged_in_client, organization):
        """Verify invoice_status_choices provided to template"""
        url = reverse('web:order_list', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)

        assert response.status_code == 200
        assert 'invoice_status_choices' in response.context
        choices = response.context['invoice_status_choices']
        assert any(code == 'accepted' for code, label in choices)
        assert any(code == 'rejected' for code, label in choices)
        assert any(code == 'submitted' for code, label in choices)


@pytest.mark.django_db
class TestOrderWebViews:
    def test_order_list_view(self, logged_in_client, organization):
        url = reverse('web:order_list', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)
        assert response.status_code == 200

    def test_order_create_view_get(self, logged_in_client, organization):
        url = reverse('web:order_create', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)
        assert response.status_code == 200

    def test_create_order_view_post_success(self, logged_in_client, organization, product):
        from src.domain.models.inventory import Stock, Warehouse

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=100, organization=organization)

        url = reverse('web:order_create', kwargs={'org_slug': organization.slug})
        data = {
            'customer_name': 'Juan Test',
            'customer_email': 'juan@test.com',
            'product': product.id,
            'quantity': 2
        }

        response = logged_in_client.post(url, data)
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert Order.objects.filter(customer_name='Juan Test').exists()

    def test_order_detail_partial(self, logged_in_client, organization):
        order = Order.objects.create(organization=organization, customer_name="Detalle Test")

        url = reverse('web:order_detail', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id
        })
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert "Detalle Test" in response.content.decode()

    def test_order_item_edit_increase_quantity(self, logged_in_client, organization, product):
        """Edit item: increase quantity should validate and reserve additional stock"""
        from src.domain.models.inventory import Stock, Warehouse
        from src.domain.models.sales import OrderItem
        from decimal import Decimal

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=100, organization=organization)

        order = Order.objects.create(
            organization=organization,
            customer_name="Edit Test",
            status='DRAFT',
            subtotal=Decimal('50.00'),
            tax_amount=Decimal('9.00'),
            total_amount=Decimal('59.00')
        )
        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=5,
            price_at_order=Decimal('10.00'),
            organization=organization
        )
        # After creating OrderItem, signal decrements stock: 100 - 5 = 95

        url = reverse('web:order_item_edit', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id,
            'item_id': item.id
        })

        # POST to edit: increase from 5 to 8 (needs 3 more items from stock)
        response = logged_in_client.post(url, {'quantity': 8})
        assert response.status_code == 200

        # Verify item quantity updated
        item.refresh_from_db()
        assert item.quantity == 8

        # Verify stock was decremented by additional 3: 95 - 3 = 92
        stock = Stock.objects.get(product=product, organization=organization)
        assert stock.quantity == 92

    def test_order_item_edit_decrease_quantity(self, logged_in_client, organization, product):
        """Edit item: decrease quantity should restore stock"""
        from src.domain.models.inventory import Stock, Warehouse
        from src.domain.models.sales import OrderItem
        from decimal import Decimal

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=95, organization=organization)

        order = Order.objects.create(
            organization=organization,
            customer_name="Edit Test 2",
            status='DRAFT',
            subtotal=Decimal('50.00'),
            tax_amount=Decimal('9.00'),
            total_amount=Decimal('59.00')
        )
        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=5,
            price_at_order=Decimal('10.00'),
            organization=organization
        )
        # After creating OrderItem, signal decrements stock: 95 - 5 = 90

        url = reverse('web:order_item_edit', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id,
            'item_id': item.id
        })

        # POST to edit: decrease from 5 to 2 (restores 3 items to stock)
        response = logged_in_client.post(url, {'quantity': 2})
        assert response.status_code == 200

        # Verify item quantity updated
        item.refresh_from_db()
        assert item.quantity == 2

        # Verify stock was incremented by returned 3: 90 + 3 = 93
        stock = Stock.objects.get(product=product, organization=organization)
        assert stock.quantity == 93

    def test_order_item_edit_insufficient_stock(self, logged_in_client, organization, product):
        """Edit item: should fail if increasing quantity beyond available stock"""
        from src.domain.models.inventory import Stock, Warehouse
        from src.domain.models.sales import OrderItem
        from decimal import Decimal

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=5, organization=organization)

        order = Order.objects.create(
            organization=organization,
            customer_name="Stock Test",
            status='DRAFT',
            subtotal=Decimal('50.00'),
            tax_amount=Decimal('9.00'),
            total_amount=Decimal('59.00')
        )
        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=2,
            price_at_order=Decimal('10.00'),
            organization=organization
        )

        url = reverse('web:order_item_edit', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id,
            'item_id': item.id
        })

        # Try to increase from 2 to 10 (needs 8 more but only 5 available)
        response = logged_in_client.post(url, {'quantity': 10})
        assert response.status_code == 200  # Form re-renders with error

        # Item quantity should NOT change
        item.refresh_from_db()
        assert item.quantity == 2

    def test_order_item_delete(self, logged_in_client, organization, product):
        """Delete item (non-last): should remove item and restore stock"""
        from src.domain.models.inventory import Stock, Warehouse
        from src.domain.models.sales import OrderItem
        from decimal import Decimal

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=95, organization=organization)

        order = Order.objects.create(
            organization=organization,
            customer_name="Delete Test",
            status='DRAFT',
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('18.00'),
            total_amount=Decimal('118.00')
        )
        # Create TWO items so deletion of one doesn't trigger "empty order" check
        item1 = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=5,
            price_at_order=Decimal('10.00'),
            organization=organization
        )
        item2 = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=5,
            price_at_order=Decimal('10.00'),
            organization=organization
        )
        # After creating items, signal decrements stock: 95 - 5 - 5 = 85

        url = reverse('web:order_item_delete', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id,
            'item_id': item1.id
        })

        # POST to delete (no nota needed since item2 remains)
        response = logged_in_client.post(url)
        assert response.status_code == 200

        # Verify item1 was deleted
        assert not OrderItem.objects.filter(id=item1.id).exists()
        # Verify item2 still exists
        assert OrderItem.objects.filter(id=item2.id).exists()

        # Verify stock was restored: 85 + 5 (restored) = 90
        stock = Stock.objects.get(product=product, organization=organization)
        assert stock.quantity == 90

    def test_order_item_edit_not_allowed_in_paid_status(self, logged_in_client, organization, product):
        """Edit item: should not allow editing when order status is PAID"""
        from src.domain.models.inventory import Stock, Warehouse
        from src.domain.models.sales import OrderItem
        from decimal import Decimal

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=100, organization=organization)

        order = Order.objects.create(
            organization=organization,
            customer_name="Status Test",
            status='PAID',  # Not DRAFT or PENDING
            subtotal=Decimal('50.00'),
            tax_amount=Decimal('9.00'),
            total_amount=Decimal('59.00')
        )
        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=5,
            price_at_order=Decimal('10.00'),
            organization=organization
        )

        url = reverse('web:order_item_edit', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id,
            'item_id': item.id
        })

        # Try to edit
        response = logged_in_client.post(url, {'quantity': 8})
        assert response.status_code == 400  # Not permitted

    def test_delete_last_item_requires_nota(self, logged_in_client, organization, product):
        """Delete last item: should require 'nota' field when order becomes empty"""
        from src.domain.models.inventory import Stock, Warehouse
        from src.domain.models.sales import OrderItem
        from decimal import Decimal

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=100, organization=organization)

        order = Order.objects.create(
            organization=organization,
            customer_name="Delete Last Item Test",
            status='DRAFT',
            subtotal=Decimal('50.00'),
            tax_amount=Decimal('9.00'),
            total_amount=Decimal('59.00')
        )
        # Create single item (will be last)
        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=5,
            price_at_order=Decimal('10.00'),
            organization=organization
        )

        url = reverse('web:order_item_delete', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id,
            'item_id': item.id
        })

        # Try DELETE without nota
        response = logged_in_client.post(url, {})
        assert response.status_code == 200
        assert 'La nota es obligatoria' in response.content.decode()

        # Item should still exist (not deleted yet)
        assert OrderItem.objects.filter(id=item.id).exists()

    def test_delete_last_item_with_nota_auto_cancels_order(self, logged_in_client, organization, product):
        """Delete last item + nota: should auto-cancel order and zero totals"""
        from src.domain.models.inventory import Stock, Warehouse
        from src.domain.models.sales import OrderItem
        from decimal import Decimal

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=100, organization=organization)

        order = Order.objects.create(
            organization=organization,
            customer_name="Auto Cancel Test",
            status='DRAFT',
            subtotal=Decimal('50.00'),
            tax_amount=Decimal('9.00'),
            total_amount=Decimal('59.00')
        )
        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=5,
            price_at_order=Decimal('10.00'),
            organization=organization
        )

        url = reverse('web:order_item_delete', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id,
            'item_id': item.id
        })

        # DELETE with nota
        response = logged_in_client.post(url, {'nota': 'Cliente canceló la compra'})
        assert response.status_code == 200

        # Item should be deleted
        assert not OrderItem.objects.filter(id=item.id).exists()

        # Order should be auto-cancelled with nota
        order.refresh_from_db()
        assert order.status == 'CANCELLED'
        assert order.nota == 'Cliente canceló la compra'
        assert order.subtotal == Decimal('0.00')
        assert order.tax_amount == Decimal('0.00')
        assert order.total_amount == Decimal('0.00')

    def test_delete_non_last_item_recalculates_totals(self, logged_in_client, organization, product):
        """Delete one item (but not last): should recalculate totals, not auto-cancel"""
        from src.domain.models.inventory import Stock, Warehouse
        from src.domain.models.sales import OrderItem
        from decimal import Decimal

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=100, organization=organization)

        order = Order.objects.create(
            organization=organization,
            customer_name="Delete One of Many",
            status='DRAFT',
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('18.00'),
            total_amount=Decimal('118.00')
        )

        # Create two items
        item1 = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=5,
            price_at_order=Decimal('10.00'),
            organization=organization
        )
        item2 = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=5,
            price_at_order=Decimal('10.00'),
            organization=organization
        )

        url = reverse('web:order_item_delete', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id,
            'item_id': item1.id
        })

        # DELETE first item (second still remains)
        response = logged_in_client.post(url, {})
        assert response.status_code == 200

        # First item deleted
        assert not OrderItem.objects.filter(id=item1.id).exists()

        # Second item still exists
        assert OrderItem.objects.filter(id=item2.id).exists()

        # Order should NOT be cancelled (has remaining items)
        order.refresh_from_db()
        assert order.status == 'DRAFT'  # Not cancelled
        assert order.nota == ''  # No nota needed
        # Recalculated: 1 item (qty=5, price=10) = 50 total_with_tax
        assert order.total_amount == Decimal('50.00')