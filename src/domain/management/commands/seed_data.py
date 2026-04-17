import random
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from src.domain.models import (
    Organization, Product, Category, Warehouse, 
    Stock, TaxConfiguration, Order, OrderItem,
    Payment, Client
)
from src.infrastructure.multitenancy.thread_local import (
    set_current_organization, clear_current_organization
)

class Command(BaseCommand):
    help = 'Nexus Master Seed - Versión Refactorizada (Tenant-Aware)'

    def add_arguments(self, parser):
        parser.add_argument('--orders', type=int, default=30)
        parser.add_argument('--clients', type=int, default=10)

    def handle(self, *args, **options):
        num_orders = options['orders']
        num_clients = options['clients']
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Iniciando Nexus Master Seed..."))

        org_configs = [
            {'name': 'Tienda Principal', 'slug': 'tienda-principal', 'tax': 18.00, 'email': 'admin@main.com', 'p_color': '#4F46E5', 's_color': '#F8FAFC', 'ruc': '20123456789', 'addr': 'Av. Larco 123, Miraflores'},
            {'name': 'Nike', 'slug': 'nike', 'tax': 15.00, 'email': 'vende@nike.com', 'p_color': '#000000', 's_color': '#FFFFFF', 'ruc': '20555666777', 'addr': 'Jockey Plaza, Surco'},
            {'name': 'Adidas', 'slug': 'adidas', 'tax': 15.00, 'email': 'ventas@adidas.com', 'p_color': '#0070AC', 's_color': '#FFFFFF', 'ruc': '20999888777', 'addr': 'Real Plaza Salaverry'},
            {'name': 'Minorista', 'slug': 'minorista', 'tax': 12.00, 'email': 'contacto@minorista.com', 'p_color': '#059669', 's_color': '#ECFDF5', 'ruc': '10444555666', 'addr': 'Jr. Ucayali 456, Lima'},
            {'name': 'Mykonos Shop', 'slug': 'mykonos-shop', 'tax': 18.00, 'email': 'sales@mykonos.pe', 'p_color': '#4B5563', 's_color': '#FFFBEB', 'ruc': '20778899441', 'addr': 'CC Camino Real, San Isidro'},
        ]
        
        for config in org_configs:
            try:
                with transaction.atomic():
                    # Crear/Actualizar Organización (Global)
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
                    
                    # 🛡️ ACTIVAR CONTEXTO DE TENANT
                    set_current_organization(org.id)
                    
                    # 1. Impuestos (Usando TenantManager implícito)
                    tax_rate_dec = Decimal(str(config['tax']))
                    TaxConfiguration.objects.update_or_create(
                        organization=org, is_default=True,
                        defaults={'name': f'IGV/IVA {org.name}', 'rate': tax_rate_dec}
                    )

                    # 2. Infraestructura
                    warehouse, _ = Warehouse.objects.get_or_create(name=f"Bodega Central", organization=org)
                    
                    # 3. Catálogo (Productos + Stock)
                    db_products = self._setup_catalog(org, warehouse)

                    # 4. Clientes (Ahora como TenantModel)
                    db_clients = self._generate_clients(org, num_clients)

                    # 5. Órdenes vinculadas
                    if db_products and db_clients:
                        self.stdout.write(f"🛒 Generando {num_orders} pedidos para {org.name}...")
                        self._generate_orders(org, db_products, db_clients, num_orders, tax_rate_dec)

                    self.stdout.write(self.style.SUCCESS(f"✅ {org.name} procesada correctamente."))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error procesando {config['slug']}: {e}"))
            
            finally:
                # 🧹 LIMPIEZA DE HILO: Vital para evitar contaminación entre organizaciones
                clear_current_organization()

    def _generate_clients(self, org, count):
        first_names = ['Juan', 'Maria', 'Luis', 'Ana', 'Carlos', 'Elena', 'Roberto', 'Lucia', 'Diego', 'Carmen']
        last_names = ['Garcia', 'Rodriguez', 'Perez', 'Flores', 'Quispe', 'Mamani', 'Soto', 'Sanchez', 'Vargas', 'Reyes']
        
        clients = []
        for _ in range(count):
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            doc = str(random.randint(10000000, 99999999))
            
            # Client.objects ahora usa TenantManager
            client, _ = Client.objects.update_or_create(
                organization=org,
                document_number=doc,
                defaults={
                    'document_type': 'DNI',
                    'name': name.upper(),
                    'email': f"{name.lower().replace(' ', '.')}@example.com",
                    'phone': f"9{random.randint(10000000, 99999999)}"
                }
            )
            clients.append(client)
        return clients

    def _setup_catalog(self, org, warehouse):
        category, _ = Category.objects.get_or_create(
            name="Fragancias" if org.slug == 'mykonos-shop' else "General", 
            organization=org
        )
        
        if org.slug == 'mykonos-shop':
            items = [
                ('Aqua di Gio Profondo 30ml', 'ADG-P-30', random.randint(40, 100)),
                ('Asad de Lataffa 30ml', 'ASAD-30', random.randint(40, 100)),
                ('Invictus Intense 30ml', 'INV-I-30', random.randint(40, 100)),
                ('Blue de Polo 30ml', 'POLO-B-30', random.randint(40, 100)),
                ('Creed Silver Mountain 30ml', 'SMC-30', random.randint(40, 100)),
            ]
        else:
            items = [(f"Prod {i} {org.slug}", f"SKU-{i}-{org.slug}", random.randint(50, 200)) for i in range(10)]

        products = []
        for name, sku, price in items:
            p, _ = Product.objects.update_or_create(
                sku=sku.upper(),
                organization=org, # Necesario para la restricción de base de datos
                defaults={
                    'name': name,
                    'price': Decimal(str(price)),
                    'category': category,
                }
            )
            Stock.objects.update_or_create(
                product=p, warehouse=warehouse, organization=org,
                defaults={'quantity': 500}
            )
            products.append(p)
        return products

    def _generate_orders(self, org, products, clients, count, tax_rate):
        now = timezone.now()
        for i in range(count):
            days_ago = random.randint(0, 60)
            order_date = now - timedelta(days=days_ago)
            client = random.choice(clients)
            
            # Crear Orden (TenantModel implícito)
            order = Order.objects.create(
                organization=org,
                client=client,
                customer_name=client.name,
                customer_email=client.email,
                status=random.choice(['PAID', 'DELIVERED', 'SHIPPED'])
            )
            # Override de fecha (created_at es auto_now_add=True)
            Order.objects.filter(id=order.id).update(created_at=order_date)
            
            subtotal = Decimal('0.00')
            items_to_create = []
            for _ in range(random.randint(1, 4)):
                p = random.choice(products)
                qty = random.randint(1, 3)
                
                items_to_create.append(OrderItem(
                    order=order, product=p, quantity=qty, 
                    price_at_order=p.price, organization=org
                ))
                subtotal += (p.price * qty)
            
            # Optimización: Bulk create para los items de la orden
            OrderItem.objects.bulk_create(items_to_create)
            
            # Lógica Financiera Mykonos vs General
            if org.slug == 'mykonos-shop':
                total = subtotal
                order.subtotal = (total / (1 + (tax_rate / Decimal('100')))).quantize(Decimal('0.01'))
                order.tax_amount = (total - order.subtotal).quantize(Decimal('0.01'))
                order.total_amount = total
            else:
                order.subtotal = subtotal
                order.tax_amount = (subtotal * (tax_rate / Decimal('100'))).quantize(Decimal('0.01'))
                order.total_amount = subtotal + order.tax_amount
            
            order.save()

            # Registrar Pago
            method = random.choice(['CASH', 'CARD', 'TRANSFER', 'WALLET'])
            fee = (order.total_amount * Decimal('0.035')).quantize(Decimal('0.01')) if method == 'CARD' else Decimal('0.00')
                
            Payment.objects.create(
                organization=org,
                order=order,
                method=method,
                fee_amount=fee,
                amount=order.total_amount,
                payment_date=order_date
            )