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
from src.domain.models.users import CustomUser, UserRole
from src.domain.models.order_constants import OrderStatus
from src.infrastructure.multitenancy.thread_local import (
    set_current_organization, clear_current_organization
)

class Command(BaseCommand):
    help = 'Nexus Master Seed - Versión Refactorizada (Tenant-Aware)'

    def add_arguments(self, parser):
        parser.add_argument('--orders', type=int, default=30)
        parser.add_argument('--clients', type=int, default=15)

    def handle(self, *args, **options):
        num_orders = options['orders']
        num_clients = options['clients']
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Iniciando Nexus Master Seed..."))

        self._create_superuser()
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

                    self._create_org_user(org)
                    self.stdout.write(self.style.SUCCESS(f"✅ {org.name} procesada correctamente."))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error procesando {config['slug']}: {e}"))
            
            finally:
                # 🧹 LIMPIEZA DE HILO: Vital para evitar contaminación entre organizaciones
                clear_current_organization()

    def _create_superuser(self):
        email = 'superadmin@nexus.com'
        if not CustomUser.objects.filter(email=email).exists():
            user = CustomUser.objects.create_superuser(email=email, password='nexus_super1234')
            self.stdout.write(self.style.SUCCESS(f"  👑 Superuser creado: {email} / nexus_super1234"))
        else:
            self.stdout.write(f"  👑 Superuser ya existe: {email}")

    def _create_org_user(self, org):
        email = f'admin@{org.slug}.com'
        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                'organization': org,
                'role': UserRole.ADMIN,
                'first_name': 'Admin',
                'last_name': org.name,
                'is_staff': False,
            }
        )
        if created:
            user.set_password('nexus1234')
            user.save()
            self.stdout.write(f"  👤 Usuario creado: {email} / nexus1234")
        else:
            self.stdout.write(f"  👤 Usuario ya existe: {email}")

    def _generate_clients(self, org, count):
        first_names = [
            'Juan', 'María', 'Luis', 'Ana', 'Carlos', 'Elena', 'Roberto', 'Lucía',
            'Diego', 'Carmen', 'Jorge', 'Patricia', 'Andrés', 'Rosa', 'Miguel',
            'Valeria', 'Fernando', 'Claudia', 'Oscar', 'Silvia',
        ]
        last_names = [
            'García', 'Rodríguez', 'Pérez', 'Flores', 'Quispe', 'Mamani',
            'Soto', 'Sánchez', 'Vargas', 'Reyes', 'Torres', 'Huanca',
            'Chávez', 'Mendoza', 'Castro', 'Ramos', 'Cruz', 'Vega',
        ]
        districts = [
            'Miraflores', 'San Isidro', 'Surco', 'La Molina', 'Barranco',
            'Lince', 'San Borja', 'Jesús María', 'Pueblo Libre', 'Magdalena',
        ]
        streets = ['Av. Larco', 'Av. Benavides', 'Jr. Lima', 'Calle Los Pinos', 'Av. Javier Prado', 'Calle Las Flores']
        companies = [
            'Corporación', 'Inversiones', 'Servicios', 'Distribuidora', 'Importaciones',
        ]

        clients = []
        seen_docs = set()

        for i in range(count):
            is_company = (i % 5 == 4)  # every 5th client is a company (RUC)

            if is_company:
                company_name = f"{random.choice(companies)} {random.choice(last_names)} S.A.C."
                doc_type = 'RUC'
                doc = str(random.randint(20_000_000_000, 20_999_999_999))
                email_slug = company_name.lower().replace(' ', '').replace('.', '')[:15]
            else:
                first = random.choice(first_names)
                last1 = random.choice(last_names)
                last2 = random.choice(last_names)
                company_name = f"{first} {last1} {last2}"
                doc_type = random.choice(['DNI', 'DNI', 'DNI', 'CE'])  # mostly DNI
                doc = str(random.randint(10_000_000, 99_999_999)) if doc_type == 'DNI' else str(random.randint(100_000, 999_999))
                email_slug = f"{first.lower()}.{last1.lower()}"

            # avoid duplicate doc numbers within the org
            while doc in seen_docs:
                doc = str(random.randint(10_000_000, 99_999_999))
            seen_docs.add(doc)

            address = f"{random.choice(streets)} {random.randint(100, 999)}, {random.choice(districts)}" if random.random() > 0.3 else None

            client, _ = Client.objects.update_or_create(
                organization=org,
                document_number=doc,
                defaults={
                    'document_type': doc_type,
                    'name': company_name.upper(),
                    'email': f"{email_slug}@example.com",
                    'phone': f"9{random.randint(10_000_000, 99_999_999)}",
                    'address': address,
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

    def _generate_reference(self, method):
        """Genera referencias de pago realistas para métodos no-efectivo."""
        if method == 'CARD':
            # Niubiz/Izipay: 12 dígitos, puede tener ceros iniciales
            num = str(random.randint(1, 10**12 - 1)).zfill(12)
            if random.random() < 0.3:
                return f"{num[:4]}.{num[4:8]}.{num[8:]}"
            return num
        elif method == 'TRANSFER':
            # Número de operación bancaria: 10–14 dígitos
            length = random.choice([10, 12, 14])
            num = str(random.randint(1, 10**length - 1)).zfill(length)
            if random.random() < 0.4:
                return f"{num[:3]}.{num[3:]}"
            return num
        elif method == 'WALLET':
            # Yape/Plin: código de operación de 9 dígitos
            num = str(random.randint(100_000_000, 999_999_999))
            if random.random() < 0.5:
                return f"{num[:3]}.{num[3:6]}.{num[6:]}"
            return num
        return None

    def _generate_orders(self, org, products, clients, count, tax_rate):
        now = timezone.now()
        shipping_fee = org.default_shipping_fee
        for i in range(count):
            days_ago = random.randint(0, 60)
            order_date = now - timedelta(days=days_ago)
            client = random.choice(clients)

            delivery_type = random.choice(['PICKUP', 'PICKUP', 'DELIVERY'])  # 1/3 delivery
            order_shipping = shipping_fee if delivery_type == 'DELIVERY' else Decimal('0.00')
            delivery_address = f"Av. {random.choice(['Lima', 'Larco', 'Javier Prado', 'Benavides'])} {random.randint(100, 999)}, {random.choice(['Miraflores', 'San Isidro', 'Surco', 'La Molina'])}" if delivery_type == 'DELIVERY' else ''

            order = Order.objects.create(
                organization=org,
                client=client,
                customer_name=client.name,
                customer_email=client.email,
                status=random.choice([OrderStatus.PAID, OrderStatus.DELIVERED, OrderStatus.SHIPPED]),
                delivery_type=delivery_type,
                delivery_address=delivery_address,
                shipping_fee=order_shipping,
            )
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

            OrderItem.objects.bulk_create(items_to_create)

            if org.slug == 'mykonos-shop':
                items_total = subtotal
                order.subtotal = (items_total / (1 + (tax_rate / Decimal('100')))).quantize(Decimal('0.01'))
                order.tax_amount = (items_total - order.subtotal).quantize(Decimal('0.01'))
                order.total_amount = items_total + order_shipping
            else:
                order.subtotal = subtotal
                order.tax_amount = (subtotal * (tax_rate / Decimal('100'))).quantize(Decimal('0.01'))
                order.total_amount = subtotal + order.tax_amount + order_shipping

            order.save()

            method = random.choice(['CASH', 'CASH', 'CARD', 'TRANSFER', 'WALLET'])  # efectivo más frecuente
            fee = (order.total_amount * Decimal('0.035')).quantize(Decimal('0.01')) if method == 'CARD' else Decimal('0.00')
            reference = self._generate_reference(method)

            Payment.objects.create(
                organization=org,
                order=order,
                method=method,
                fee_amount=fee,
                amount=order.total_amount,
                transaction_reference=reference,
                payment_date=order_date,
            )