import random
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from src.domain.models import (
    Organization, Product, Category, Warehouse,
    Stock, TaxConfiguration, Order, OrderItem,
    Payment, PaymentFeeConfig, Client,
)
from src.domain.models.users import CustomUser, UserRole
from src.domain.models.order_constants import OrderStatus
from src.infrastructure.multitenancy.context import TenantContextManager


class Command(BaseCommand):
    help = 'Nexus Master Seed — Tenant-Aware con datos realistas de facturación y pagos'

    def add_arguments(self, parser):
        parser.add_argument('--orders',  type=int, default=50)
        parser.add_argument('--clients', type=int, default=15)

    def handle(self, *args, **options):
        num_orders  = options['orders']
        num_clients = options['clients']
        self.stdout.write(self.style.MIGRATE_HEADING('🚀 Iniciando Nexus Master Seed...'))

        self._create_superuser()
        org_configs = [
            {'name': 'Tienda Principal', 'slug': 'tienda-principal', 'tax': 18.00, 'email': 'admin@main.com',         'p_color': '#4F46E5', 's_color': '#F8FAFC', 'ruc': '20123456789', 'addr': 'Av. Larco 123, Miraflores'},
            {'name': 'Nike',             'slug': 'nike',             'tax': 15.00, 'email': 'vende@nike.com',         'p_color': '#000000', 's_color': '#FFFFFF', 'ruc': '20555666777', 'addr': 'Jockey Plaza, Surco'},
            {'name': 'Adidas',           'slug': 'adidas',           'tax': 15.00, 'email': 'ventas@adidas.com',      'p_color': '#0070AC', 's_color': '#FFFFFF', 'ruc': '20666777888', 'addr': 'Kennedy, Miraflores'},
        ]

        orgs = {}
        for cfg in org_configs:
            org, _ = Organization.objects.get_or_create(slug=cfg['slug'], defaults={
                'name': cfg['name'],
                'admin_email': cfg['email'],
                'primary_color': cfg['p_color'],
                'secondary_color': cfg['s_color'],
                'ruc': cfg['ruc'],
                'address': cfg['addr'],
            })
            org.name = cfg['name']
            org.admin_email = cfg['email']
            org.primary_color = cfg['p_color']
            org.secondary_color = cfg['s_color']
            org.ruc = cfg['ruc']
            org.address = cfg['addr']
            org.save()
            orgs[cfg['slug']] = org

        for cfg in org_configs:
            org = orgs[cfg['slug']]
            user, _ = CustomUser.objects.get_or_create(email=cfg['email'], defaults={
                'organization': org,
                'first_name': cfg['name'],
                'last_name': 'Admin',
                'role': UserRole.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            })
            user.organization = org
            user.role = UserRole.ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.set_password('admin123')
            user.save()

        # ─── PASO 1: Configuración de tarifas de pago por tenant ───
        self._seed_payment_fee_configs(orgs)

        # ─── PASO 2: Catálogo de productos y stock ───
        self._seed_catalog(orgs, {c['slug']: c['tax'] for c in org_configs}, seed=42)

        # ─── PASO 3: Clientes ───
        self._seed_clients(orgs, num_clients)

        # ─── PASO 4: Órdenes + OrderItems + Pagos ───
        self._seed_orders(orgs, num_orders)

        self.stdout.write(self.style.SUCCESS('✅ Master Seed completado.'))

    def _create_superuser(self):
        admin, _ = CustomUser.objects.get_or_create(email='admin@nexus.local', defaults={
            'first_name': 'Super',
            'last_name': 'Admin',
            'role': UserRole.ADMIN,
            'is_staff': True,
            'is_superuser': True,
        })
        admin.role = UserRole.ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password('admin123')
        admin.save()

    def _seed_payment_fee_configs(self, orgs):
        fee_plans = {
            'tienda-principal': {'cash_rate': 0.00, 'card_rate': 3.50, 'transfer_rate': 0.00, 'wallet_rate': 1.00},
            'nike':             {'cash_rate': 0.00, 'card_rate': 4.00, 'transfer_rate': 0.50, 'wallet_rate': 0.50},
            'adidas':           {'cash_rate': 0.00, 'card_rate': 3.50, 'transfer_rate': 0.00, 'wallet_rate': 1.00},
        }
        for slug, org in orgs.items():
            plan = fee_plans[slug]
            with TenantContextManager(org.id):
                config = PaymentFeeConfig.objects.filter(organization=org).first()
                if config:
                    for field, value in plan.items():
                        setattr(config, field, value)
                    config.provider_type = 'apimigo'
                    config.enabled = True
                    config.save()
                    PaymentFeeConfig.objects.filter(organization=org).exclude(pk=config.pk).delete()
                else:
                    config = PaymentFeeConfig.objects.create(
                        organization=org, provider_type='apimigo', enabled=True, **plan,
                    )
                self.stdout.write(
                    self.style.SUCCESS(f'   Fees {config.organization.name} → CARD {config.card_rate}% / WALLET {config.wallet_rate}%')
                )

    def _seed_catalog(self, orgs, tax_rates, seed=42):
        random.seed(seed)
        products = [
            ('Zapatilla Urbana',   'ZAP-URB-01', 189.90, 'Calzado'),
            ('Zapatilla Running',  'ZAP-RUN-01', 249.90, 'Calzado'),
            ('Zapatilla Básica',   'ZAP-BAS-01', 129.90, 'Calzado'),
            ('Polo Básico',        'POL-BAS-01',  69.90, 'Ropa'),
            ('Polo Premium',       'POL-PRE-01',  99.90, 'Ropa'),
            ('Chaqueta Ligera',    'CHQ-LIG-01', 179.90, 'Ropa'),
            ('Gorra Ajustable',    'GOR-AJU-01',  49.90, 'Accesorios'),
            ('Mochila Urbana',     'MOC-URB-01', 159.90, 'Accesorios'),
        ]

        for slug, org in orgs.items():
            with TenantContextManager(org.id):
                warehouse, _ = Warehouse.objects.get_or_create(
                    name='Almacén Principal', organization=org,
                    defaults={'address': 'Av. Principal 1000'},
                )
                tax, _ = TaxConfiguration.objects.get_or_create(
                    name='IGV', organization=org,
                    defaults={'rate': tax_rates[slug], 'is_default': True},
                )
                tax.rate = tax_rates[slug]
                tax.is_default = True
                tax.save()

                for name, sku, price, cat_name in products:
                    category, _ = Category.objects.get_or_create(name=cat_name, organization=org)
                    product, _ = Product.objects.get_or_create(sku=sku, organization=org, defaults={
                        'name': name,
                        'price': Decimal(str(price)),
                        'description': f'{name} - {cat_name}',
                    })
                    product.name = name
                    product.price = Decimal(str(price))
                    product.is_active = True
                    product.save()

                    stock, _ = Stock.objects.get_or_create(
                        product=product, organization=org, warehouse=warehouse,
                        defaults={'quantity': 250},
                    )
                    stock.quantity = 250
                    stock.save()

    def _seed_clients(self, orgs, num_clients):
        first_names = ['María', 'José', 'Ana', 'Luis', 'Carmen', 'Jorge', 'Lucía', 'Miguel', 'Rosa', 'Pedro', 'Sofía', 'Carlos', 'Valeria', 'Diego', 'Paola']
        last_names  = ['García', 'Rodríguez', 'Martínez', 'López', 'Hernández', 'González', 'Pérez', 'Sánchez', 'Ramírez', 'Torres', 'Flores', 'Rivera', 'Díaz', 'Vargas']

        for org in orgs.values():
            with TenantContextManager(org.id):
                for i in range(num_clients):
                    name = f"{random.choice(first_names)} {random.choice(last_names)}"
                    doc_type = random.choice(['DNI', 'DNI', 'DNI', 'RUC'])
                    if doc_type == 'RUC':
                        doc_number = f"20{random.randint(10000000, 29999999)}"
                    else:
                        doc_number = str(random.randint(10000000, 99999999))
                    Client.objects.get_or_create(
                        organization=org, document_number=doc_number,
                        defaults={
                            'name': name,
                            'document_type': doc_type,
                            'email': f"cliente{org.pk}-{i + 1}@mail.com",
                            'address': f'Av. {random.choice(last_names)} {random.randint(100, 999)}',
                            'phone': f'9{random.randint(10000000, 99999999)}',
                        },
                    )

    def _seed_orders(self, orgs, num_orders):
        clients  = []
        products = []
        tax_rates = {}
        for org in orgs.values():
            with TenantContextManager(org.id):
                clients  += list(Client.objects.all())
                products += list(Product.objects.select_related('organization').all())
                tax_cfg = TaxConfiguration.objects.filter(organization=org, is_default=True).first()
                tax_rates[org.pk] = tax_cfg.rate if tax_cfg else Decimal('0')

        for n in range(1, num_orders + 1):
            org = random.choice(list(orgs.values()))
            org_clients  = [c for c in clients  if c.organization_id == org.pk]
            org_products = [p for p in products if p.organization_id == org.pk]
            if not org_clients or not org_products:
                continue

            client = random.choice(org_clients)
            status = self._pick_order_status(n, num_orders)

            with TenantContextManager(org.id):
                order = Order.objects.create(
                    organization=org,
                    customer_name=client.name,
                    customer_email=client.email,
                    status=status,
                    delivery_type=random.choice(['PICKUP', 'DELIVERY']),
                    delivery_address=client.address,
                    shipping_fee=Decimal('0.00'),
                    subtotal=Decimal('0.00'),
                    tax_amount=Decimal('0.00'),
                    total_amount=Decimal('0.00'),
                )

                for _ in range(random.randint(1, 3)):
                    product = random.choice(org_products)
                    stock = Stock.objects.filter(product=product, organization=org).first()
                    if not stock or stock.quantity <= 0:
                        continue
                    qty = random.randint(1, 3)
                    OrderItem.objects.create(
                        organization=org,
                        order=order,
                        product=product,
                        quantity=qty,
                        price_at_order=product.price,
                    )

                subtotal = sum(
                    (item.price_at_order * item.quantity)
                    for item in OrderItem.objects.filter(order=order)
                )
                tax = (subtotal * tax_rates[org.pk] / Decimal('100')).quantize(Decimal('0.01'))
                order.subtotal = subtotal
                order.tax_amount = tax
                order.total_amount = (subtotal + tax).quantize(Decimal('0.01'))
                order.save()

                if status == OrderStatus.CANCELLED or status == OrderStatus.DRAFT:
                    continue

                self._attach_payment(order, org)

    def _pick_order_status(self, n, num_orders):
        if n <= num_orders * 0.50:
            return random.choice([
                OrderStatus.PAID, OrderStatus.PAID, OrderStatus.PAID,
                OrderStatus.SHIPPED, OrderStatus.DELIVERED,
            ])
        if n <= num_orders * 0.75:
            return OrderStatus.PENDING
        return OrderStatus.CANCELLED

    def _attach_payment(self, order, org):
        fee_config = PaymentFeeConfig.objects.filter(organization=org).first()
        total = order.total_amount

        if order.status in (OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            method = random.choice(['CASH', 'CASH', 'CASH', 'CARD', 'CARD', 'WALLET'])
            fee_rate = fee_config.rate_for(method) if fee_config else Decimal('0')
            fee = (total * fee_rate / Decimal('100')).quantize(Decimal('0.01'))
            paid_at = timezone.now() - timedelta(days=random.randint(0, 20), hours=random.randint(1, 12))

            payment = Payment.objects.create(
                organization=org,
                order=order,
                method=method,
                amount=total,
                status='approved',
                fee_rate=fee_rate,
                fee_amount=fee,
                provider='apimigo',
                transaction_reference=f"PAY-{order.pk}-{random.randint(100000, 999999)}",
                external_reference=f"APM-{random.randint(100000000, 999999999)}",
                approved_at=paid_at,
            )
            Payment.objects.filter(pk=payment.pk).update(payment_date=paid_at)

            order.workflow_processed = True
            order.save()
            return

        if order.status == OrderStatus.PENDING and random.random() < 0.5:
            method = random.choice(['TRANSFER', 'TRANSFER', 'CARD', 'WALLET'])
            fee_rate = fee_config.rate_for(method) if fee_config else Decimal('0')
            fee = (total * fee_rate / Decimal('100')).quantize(Decimal('0.01'))
            Payment.objects.create(
                organization=org,
                order=order,
                method=method,
                amount=total,
                status='pending',
                fee_rate=fee_rate,
                fee_amount=fee,
                provider='apimigo',
                transaction_reference=f"PAY-{order.pk}-{random.randint(100000, 999999)}",
            )
