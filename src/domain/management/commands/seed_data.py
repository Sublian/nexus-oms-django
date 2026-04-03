import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from decimal import Decimal

from src.domain.models import (
    Organization, Product, Category, Warehouse, 
    Stock, TaxConfiguration, Order, OrderItem,
    Payment
)
from src.infrastructure.multitenancy.thread_local import (
    set_current_organization, clear_current_organization
)

class Command(BaseCommand):
    help = 'Nexus Master Seed - Carga optimizada con persistencia financiera'

    def add_arguments(self, parser):
        parser.add_argument('--orders', type=int, default=30)

    def handle(self, *args, **options):
        num_orders = options['orders']
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Iniciando Nexus Master Seed..."))

        org_configs = [
            {'name': 'Tienda Principal', 'slug': 'tienda-principal', 'tax': 18.00, 'email': 'admin@main.com', 'p_color': '#4F46E5', 's_color': '#F8FAFC', 'ruc': '20123456789', 'addr': 'Av. Larco 123, Miraflores'},
            {'name': 'Nike', 'slug': 'nike', 'tax': 15.00, 'email': 'vende@nike.com', 'p_color': '#000000', 's_color': '#FFFFFF', 'ruc': '20555666777', 'addr': 'Jockey Plaza, Surco'},
            {'name': 'Adidas', 'slug': 'adidas', 'tax': 15.00, 'email': 'ventas@adidas.com', 'p_color': '#0070AC', 's_color': '#FFFFFF', 'ruc': '20999888777', 'addr': 'Real Plaza Salaverry'},
            {'name': 'Minorista', 'slug': 'minorista', 'tax': 12.00, 'email': 'contacto@minorista.com', 'p_color': '#059669', 's_color': '#ECFDF5', 'ruc': '10444555666', 'addr': 'Jr. Ucayali 456, Lima'},
            # NUEVA TIENDA: Mykonos Shop
            {
                'name': 'Mykonos Shop', 
                'slug': 'mykonos-shop', 
                'tax': 18.00, 
                'email': 'sales@mykonos.pe', 
                'p_color': '#4B5563', # Gris azulado elegante
                's_color': '#FFFBEB', # Crema suave
                'ruc': '20778899441', 
                'addr': 'Centro Comercial Camino Real, San Isidro'
            },
        ]
        
        for config in org_configs:
            with transaction.atomic():
                # 1. Organización
                org, _ = Organization.objects.update_or_create(
                    slug=config['slug'],
                    defaults={
                        'name': config['name'], 
                        'admin_email': config['email'],
                        'primary_color': config['p_color'],
                        'secondary_color': config['s_color'],
                        'ruc': config['ruc'],
                        'address': config['addr']
                    }
                )
                set_current_organization(org.id)
                
                # 2. Impuestos (Normalizados a Decimal)
                tax_rate_dec = Decimal(str(config['tax']))
                tax_cfg, _ = TaxConfiguration.objects.update_or_create(
                    organization=org, is_default=True,
                    defaults={'name': f'IGV/IVA {org.name}', 'rate': tax_rate_dec}
                )

                # 3. Bodega y Categorías
                warehouse, _ = Warehouse.objects.get_or_create(name=f"Bodega Central", organization=org)
                
                # 4. Productos (Ejemplo rápido)
                db_products = self._setup_catalog(org, warehouse)

                # 5. Órdenes
                if db_products:
                    self.stdout.write(f"🛒 Generando pedidos para {org.name}...")
                    self._generate_orders(org, db_products, num_orders, tax_rate_dec)

                clear_current_organization()
                self.stdout.write(self.style.SUCCESS(f"✅ {org.name} procesada."))

    def _setup_catalog(self, org, warehouse):
        # Simplificación para el ejemplo, puedes expandir según tu dict de 'catalogs'
        category, _ = Category.objects.get_or_create(name="Fragancias" if org.slug == 'mykonos-shop' else "General", organization=org)
        
        items = []
        if org.slug == 'mykonos-shop':
            items = [
                ('Aqua di Gio Profondo 30ml', 'ADG-P-30', random.randint(55, 60)),
                ('Asad de Lataffa 30ml', 'ASAD-30', random.randint(40, 45)),
                ('Invictus Intense Paco Rabanne 30ml', 'INV-I-30', random.randint(50, 60)),
                ('Blue de Polo 30ml', 'POLO-B-30', random.randint(45, 55)),
                ('Silver Mountain de Creed 30ml', 'SMC-30', random.randint(58, 60)),
            ]
        else:
            items = [(f"Producto {i} {org.name}", f"PROD-{i}-{org.slug}", random.randint(50, 500)) for i in range(5)]

        products = []
        for name, sku, price in items:
            p, _ = Product.objects.update_or_create(
                sku=sku.upper(),
                defaults={
                    'name': name,
                    'price': Decimal(str(price)),
                    'category': category,
                    'organization': org
                }
            )
            Stock.objects.update_or_create(
                product=p, warehouse=warehouse, organization=org,
                defaults={'quantity': 100}
            )
            products.append(p)
        return products

    def _generate_orders(self, org, products, count, tax_rate):
        now = timezone.now()
        for i in range(count):
            days_ago = random.randint(0, 45)
            order_date = now - timedelta(days=days_ago)
            
            # Crear Orden
            order = Order.objects.create(
                organization=org,
                customer_name=f"Cliente {i}",
                customer_email=f"cliente{i}@example.com",
                status='PAID'
            )
            # Forzar fecha pasada
            Order.objects.filter(id=order.id).update(created_at=order_date)
            
            # Crear Items
            subtotal = Decimal('0.00')
            for _ in range(random.randint(1, 3)):
                p = random.choice(products)
                qty = random.randint(1, 2)
                OrderItem.objects.create(
                    order=order, product=p, quantity=qty, 
                    price_at_order=p.price, organization=org
                )
                subtotal += (p.price * qty)
            
            # Cálculos Financieros Persistentes (Correctos)
            tax_amount = (subtotal * (tax_rate / Decimal('100'))).quantize(Decimal('0.01'))
            order.subtotal = subtotal
            order.tax_amount = tax_amount
            order.total_amount = subtotal + tax_amount
            order.save()

            # Pago y Comisiones
            method = random.choice(['CASH', 'CARD', 'TRANSFER', 'WALLET'])
            fee = Decimal('0.00')
            if method == 'CARD':
                fee = (order.total_amount * Decimal('0.035')).quantize(Decimal('0.01'))

            Payment.objects.create(
                organization=org,
                order=order,
                method=method,
                amount=order.total_amount,
                fee_amount=fee,
                payment_date=order_date # Sincronizado con la orden
            )