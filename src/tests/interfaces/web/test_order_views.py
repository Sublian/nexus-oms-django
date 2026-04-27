
import pytest

from django.urls import reverse

from src.domain.models.sales import Order


@pytest.mark.django_db
def test_order_list_view_status_code(client, admin_user, organization):
    # Usamos admin_user que sí existe en tus fixtures
    client.force_login(admin_user)
    
    # IMPORTANTE: El middleware de tenant necesita que el usuario tenga permiso 
    # o que la URL contenga el slug correcto.
    url = reverse('web:order-list', kwargs={'org_slug': organization.slug})
    response = client.get(url)
    
    assert response.status_code == 200


@pytest.mark.django_db
class TestOrderWebViews:
    def test_order_list_view(self, logged_in_client, organization):
        url = reverse('web:order-list', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)
        assert response.status_code == 200

    def test_order_create_view_get(self, logged_in_client, organization):
        url = reverse('web:order-create', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)
        assert response.status_code == 200

    def test_create_order_view_post_success(self, logged_in_client, organization, product):
        from src.domain.models.inventory import Stock, Warehouse

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=100, organization=organization)

        url = reverse('web:order-create', kwargs={'org_slug': organization.slug})
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

        url = reverse('web:order-item-edit', kwargs={
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

        url = reverse('web:order-item-edit', kwargs={
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

        url = reverse('web:order-item-edit', kwargs={
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
        """Delete item: should remove item and restore stock"""
        from src.domain.models.inventory import Stock, Warehouse
        from src.domain.models.sales import OrderItem
        from decimal import Decimal

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=95, organization=organization)

        order = Order.objects.create(
            organization=organization,
            customer_name="Delete Test",
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

        url = reverse('web:order-item-delete', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id,
            'item_id': item.id
        })

        # POST to delete
        response = logged_in_client.post(url)
        assert response.status_code == 200

        # Verify item was deleted
        assert not OrderItem.objects.filter(id=item.id).exists()

        # Verify stock was restored: 90 + 5 (restored) = 95
        stock = Stock.objects.get(product=product, organization=organization)
        assert stock.quantity == 95

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

        url = reverse('web:order-item-edit', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id,
            'item_id': item.id
        })

        # Try to edit
        response = logged_in_client.post(url, {'quantity': 8})
        assert response.status_code == 400  # Not permitted