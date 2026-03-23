import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from decimal import Decimal

from src.domain.models import (
    Organization, Product, Category, Warehouse, 
    Stock, TaxConfiguration, Order, OrderItem
)
from src.infrastructure.multitenancy.thread_local import (
    set_current_organization, clear_current_organization
)

class Command(BaseCommand):
    help = 'Nexus Master Seed - Carga completa de todas las organizaciones'

    def add_arguments(self, parser):
        parser.add_argument('--orders', type=int, default=30)

    def handle(self, *args, **options):
        num_orders = options['orders']
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Iniciando Nexus Master Seed Total..."))

        # Restauramos todas las tiendas que tenías originalmente
        org_configs = [
            {'name': 'Tienda Principal', 'slug': 'main', 'tax': 18.00, 'email': 'admin@main.com'},
            {'name': 'Nike', 'slug': 'nike', 'tax': 15.00, 'email': 'vende@nike.com'},
            {'name': 'Adidas', 'slug': 'adidas', 'tax': 15.00, 'email': 'ventas@adidas.com'},
            {'name': 'Tienda Minorista', 'slug': 'minorista', 'tax': 12.00, 'email': 'contacto@minorista.com'},
        ]

        catalogs = {
            'Nike': {
                'Calzado': [
                    {'name': 'Air Max 90', 'sku': 'NIKE-AM90', 'price': 120.00},
                    {'name': 'Jordan Retro', 'sku': 'NIKE-JR1', 'price': 180.00},
                ],
                'Ropa': [{'name': 'Camiseta Dri-FIT', 'sku': 'NIKE-DFT-01', 'price': 35.00}]
            },
            'Adidas': {
                'Running': [{'name': 'Ultraboost 22', 'sku': 'ADI-UB22', 'price': 150.00}],
                'Casual': [{'name': 'Stan Smith', 'sku': 'ADI-SS', 'price': 85.00}]
            },
            'Tienda Minorista': {
                'Accesorios': [
                    {'name': 'Gorra Genérica', 'sku': 'MIN-GOR-01', 'price': 15.00},
                    {'name': 'Mochila Urbana', 'sku': 'MIN-MOCH-02', 'price': 45.00},
                ]
            },
            'Tienda Principal': {
                'Accesorios': [
                    {'name': 'Mochila Nice', 'sku': 'NIC-MOCH-02', 'price': 85.00},
                    {'name': 'Gorra Nice', 'sku': 'NIC-GOR-01', 'price': 45.00}
                ],
                'Ropa': [{'name': 'Camiseta Premium', 'sku': 'NIC-CP-01', 'price': 55.00}]
            }
        }

        for config in org_configs:
            with transaction.atomic():
                # 1. Organización
                org, _ = Organization.objects.get_or_create(
                    slug=config['slug'],
                    defaults={'name': config['name'], 'admin_email': config['email']}
                )
                set_current_organization(org.id)
                
                # 2. Impuestos
                tax_cfg, _ = TaxConfiguration.objects.update_or_create(
                    organization=org, is_default=True,
                    defaults={'name': f'IVA {org.name}', 'rate': Decimal(str(config['tax']))}
                )

                # 3. Bodega
                warehouse, _ = Warehouse.objects.get_or_create(
                    name=f"Bodega {org.name}", organization=org
                )

                # 4. Catálogo
                db_products = []
                org_catalog = catalogs.get(org.name, {})
                for cat_name, products in org_catalog.items():
                    category, _ = Category.objects.get_or_create(name=cat_name, organization=org)
                    for p_data in products:
                        # Nota: Si el SKU es unique=True global, le agregamos el slug para evitar el error
                        final_sku = f"{p_data['sku']}-{org.slug}".upper()
                        
                        product, _ = Product.objects.update_or_create(
                            sku=final_sku,
                            defaults={
                                'name': p_data['name'], 
                                'price': Decimal(str(p_data['price'])),
                                'category': category, 
                                'organization': org
                            }
                        )
                        Stock.objects.update_or_create(
                            product=product, warehouse=warehouse, organization=org,
                            defaults={'quantity': 100}
                        )
                        db_products.append(product)

                # 5. Órdenes
                if db_products:
                    self.stdout.write(f"🛒 Generando {num_orders} pedidos para {org.name}...")
                    self._generate_orders(org, db_products, num_orders, tax_cfg.rate)

                clear_current_organization()
                self.stdout.write(self.style.SUCCESS(f"✅ {org.name} lista."))

    def _generate_orders(self, org, products, count, tax_rate):
        now = timezone.now()
        for i in range(count):
            days_ago = random.randint(0, 45)
            order_date = now - timedelta(days=days_ago)
            
            order = Order.objects.create(
                organization=org,
                customer_name=f"Cliente {org.slug} {i}",
                customer_email=f"user{i}@{org.slug}.com",
                status='PAID'
            )
            Order.objects.filter(id=order.id).update(created_at=order_date)
            
            subtotal = Decimal('0.00')
            for _ in range(random.randint(1, 3)):
                p = random.choice(products)
                qty = random.randint(1, 2)
                
                OrderItem.objects.create(
                    order=order, product=p, quantity=qty, 
                    price_at_order=p.price, organization=org
                )
                subtotal += (p.price * qty)
            
            tax = subtotal * (tax_rate / 100)
            order.subtotal = subtotal
            order.tax_amount = tax
            order.total_amount = subtotal + tax
            order.save()