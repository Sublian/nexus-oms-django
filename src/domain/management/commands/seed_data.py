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
    help = 'Nexus Master Seed — Tenant-Aware con datos realistas de facturación'

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
            {'name': 'Adidas',           'slug': 'adidas',           'tax': 15.00, 'email': 'ventas@adidas.com',      'p_color': '#0070AC', 's_color': '#FFFFFF', 'ruc': '20999888777', 'addr': 'Real Plaza Salaverry'},
            {'name': 'Minorista',        'slug': 'minorista',        'tax': 12.00, 'email': 'contacto@minorista.com', 'p_color': '#059669', 's_color': '#ECFDF5', 'ruc': '10444555666', 'addr': 'Jr. Ucayali 456, Lima'},
            {'name': 'Mykonos Shop',     'slug': 'mykonos-shop',     'tax': 18.00, 'email': 'sales@mykonos.pe',       'p_color': '#4B5563', 's_color': '#FFFBEB', 'ruc': '20778899441', 'addr': 'CC Camino Real, San Isidro'},
        ]

        for config in org_configs:
            try:
                with transaction.atomic():
                    org, _ = Organization.objects.update_or_create(
                        slug=config['slug'],
                        defaults={
                            'name':            config['name'],
                            'admin_email':     config['email'],
                            'primary_color':   config['p_color'],
                            'secondary_color': config['s_color'],
                            'ruc':             config['ruc'],
                            'address':         config['addr'],
                        },
                    )

                    set_current_organization(org.id)

                    tax_rate_dec = Decimal(str(config['tax']))
                    TaxConfiguration.objects.update_or_create(
                        organization=org, is_default=True,
                        defaults={'name': f'IGV/IVA {org.name}', 'rate': tax_rate_dec},
                    )

                    warehouse, _ = Warehouse.objects.get_or_create(
                        name='Bodega Central', organization=org
                    )

                    db_products = self._setup_catalog(org, warehouse)
                    db_clients  = self._generate_clients(org, num_clients)

                    if db_products and db_clients:
                        self.stdout.write(f'  🛒 Generando {num_orders} pedidos para {org.name}...')
                        orders = self._generate_orders(
                            org, db_products, db_clients, num_orders, tax_rate_dec
                        )
                        self._seed_invoice_data(org, orders)
                        self._seed_invoice_sync_queue(org)
                        self._seed_external_service_configs(org)
                        self._seed_external_request_logs(org, orders)

                    self._create_org_user(org)
                    self.stdout.write(self.style.SUCCESS(f'  ✅ {org.name} procesada correctamente.'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Error procesando {config["slug"]}: {e}'))
                import traceback; traceback.print_exc()
            finally:
                clear_current_organization()

    # ── Superuser / org user ──────────────────────────────────────────────────

    def _create_superuser(self):
        email = 'superadmin@nexus.com'
        if not CustomUser.objects.filter(email=email).exists():
            CustomUser.objects.create_superuser(email=email, password='nexus_super1234')
            self.stdout.write(self.style.SUCCESS(f'  👑 Superuser creado: {email} / nexus_super1234'))
        else:
            self.stdout.write(f'  👑 Superuser ya existe: {email}')

    def _create_org_user(self, org):
        email = f'admin@{org.slug}.com'
        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                'organization': org,
                'role':         UserRole.ADMIN,
                'first_name':   'Admin',
                'last_name':    org.name,
                'is_staff':     False,
            },
        )
        if created:
            user.set_password('nexus1234')
            user.save()
            self.stdout.write(f'  👤 Usuario creado: {email} / nexus1234')
        else:
            self.stdout.write(f'  👤 Usuario ya existe: {email}')

    # ── Catalog ───────────────────────────────────────────────────────────────

    def _setup_catalog(self, org, warehouse):
        category, _ = Category.objects.get_or_create(
            name='Fragancias' if org.slug == 'mykonos-shop' else 'General',
            organization=org,
        )
        if org.slug == 'mykonos-shop':
            items = [
                ('Aqua di Gio Profondo 30ml',    'ADG-P-30',  random.randint(40, 100)),
                ('Asad de Lataffa 30ml',          'ASAD-30',   random.randint(40, 100)),
                ('Invictus Intense 30ml',          'INV-I-30',  random.randint(40, 100)),
                ('Blue de Polo 30ml',              'POLO-B-30', random.randint(40, 100)),
                ('Creed Silver Mountain 30ml',     'SMC-30',    random.randint(40, 100)),
            ]
        else:
            items = [
                (f'Prod {i} {org.slug}', f'SKU-{i}-{org.slug}', random.randint(50, 200))
                for i in range(10)
            ]
        products = []
        for name, sku, price in items:
            p, _ = Product.objects.update_or_create(
                sku=sku.upper(), organization=org,
                defaults={'name': name, 'price': Decimal(str(price)), 'category': category},
            )
            Stock.objects.update_or_create(
                product=p, warehouse=warehouse, organization=org,
                defaults={'quantity': 500},
            )
            products.append(p)
        return products

    # ── Clients ───────────────────────────────────────────────────────────────

    def _generate_clients(self, org, count):
        first_names = ['Juan','María','Luis','Ana','Carlos','Elena','Roberto','Lucía',
                       'Diego','Carmen','Jorge','Patricia','Andrés','Rosa','Miguel',
                       'Valeria','Fernando','Claudia','Oscar','Silvia']
        last_names  = ['García','Rodríguez','Pérez','Flores','Quispe','Mamani',
                       'Soto','Sánchez','Vargas','Reyes','Torres','Huanca',
                       'Chávez','Mendoza','Castro','Ramos','Cruz','Vega']
        districts   = ['Miraflores','San Isidro','Surco','La Molina','Barranco',
                       'Lince','San Borja','Jesús María','Pueblo Libre','Magdalena']
        streets     = ['Av. Larco','Av. Benavides','Jr. Lima','Calle Los Pinos',
                       'Av. Javier Prado','Calle Las Flores']
        companies   = ['Corporación','Inversiones','Servicios','Distribuidora','Importaciones']

        clients, seen_docs = [], set()
        for i in range(count):
            is_company = (i % 5 == 4)
            if is_company:
                company_name = f'{random.choice(companies)} {random.choice(last_names)} S.A.C.'
                doc_type     = 'RUC'
                doc          = str(random.randint(20_000_000_000, 20_999_999_999))
                email_slug   = company_name.lower().replace(' ', '').replace('.', '')[:15]
            else:
                first        = random.choice(first_names)
                last1, last2 = random.choice(last_names), random.choice(last_names)
                company_name = f'{first} {last1} {last2}'
                doc_type     = random.choice(['DNI', 'DNI', 'DNI', 'CE'])
                doc          = str(random.randint(10_000_000, 99_999_999)) if doc_type == 'DNI' else str(random.randint(100_000, 999_999))
                email_slug   = f'{first.lower()}.{last1.lower()}'
            while doc in seen_docs:
                doc = str(random.randint(10_000_000, 99_999_999))
            seen_docs.add(doc)
            address = (
                f'{random.choice(streets)} {random.randint(100, 999)}, {random.choice(districts)}'
                if random.random() > 0.3 else None
            )
            client, _ = Client.objects.update_or_create(
                organization=org, document_number=doc,
                defaults={
                    'document_type': doc_type,
                    'name':          company_name.upper(),
                    'email':         f'{email_slug}@example.com',
                    'phone':         f'9{random.randint(10_000_000, 99_999_999)}',
                    'address':       address,
                },
            )
            clients.append(client)
        return clients

    # ── Orders ────────────────────────────────────────────────────────────────

    def _generate_reference(self, method):
        if method == 'CARD':
            num = str(random.randint(1, 10**12 - 1)).zfill(12)
            return f'{num[:4]}.{num[4:8]}.{num[8:]}' if random.random() < 0.3 else num
        elif method == 'TRANSFER':
            length = random.choice([10, 12, 14])
            num    = str(random.randint(1, 10**length - 1)).zfill(length)
            return f'{num[:3]}.{num[3:]}' if random.random() < 0.4 else num
        elif method == 'WALLET':
            num = str(random.randint(100_000_000, 999_999_999))
            return f'{num[:3]}.{num[3:6]}.{num[6:]}' if random.random() < 0.5 else num
        return None

    def _generate_orders(self, org, products, clients, count, tax_rate):
        """Create orders distributed over 90 days. Returns list of created orders."""
        orders, now = [], timezone.now()
        shipping_fee = org.default_shipping_fee

        for i in range(count):
            # Weighted temporal distribution: 40% last 30d, 35% 30-60d, 25% 60-90d
            bucket = self._weighted_choice([(30, 0.40), (60, 0.35), (90, 0.25)])
            days_ago  = random.randint(bucket - 30, bucket - 1)
            hours_ago = random.randint(0, 23)
            order_date = now - timedelta(days=days_ago, hours=hours_ago,
                                         minutes=random.randint(0, 59))
            client = random.choice(clients)

            delivery_type    = random.choice(['PICKUP', 'PICKUP', 'DELIVERY'])
            order_shipping   = shipping_fee if delivery_type == 'DELIVERY' else Decimal('0.00')
            delivery_address = (
                f'Av. {random.choice(["Lima","Larco","Javier Prado","Benavides"])} '
                f'{random.randint(100,999)}, '
                f'{random.choice(["Miraflores","San Isidro","Surco","La Molina"])}'
                if delivery_type == 'DELIVERY' else ''
            )

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
            order.refresh_from_db()

            subtotal = Decimal('0.00')
            items_to_create = []
            for _ in range(random.randint(1, 4)):
                p   = random.choice(products)
                qty = random.randint(1, 3)
                items_to_create.append(OrderItem(
                    order=order, product=p, quantity=qty,
                    price_at_order=p.price, organization=org,
                ))
                subtotal += p.price * qty
            OrderItem.objects.bulk_create(items_to_create)

            if org.slug == 'mykonos-shop':
                items_total   = subtotal
                order.subtotal    = (items_total / (1 + tax_rate / Decimal('100'))).quantize(Decimal('0.01'))
                order.tax_amount  = (items_total - order.subtotal).quantize(Decimal('0.01'))
                order.total_amount = items_total + order_shipping
            else:
                order.subtotal    = subtotal
                order.tax_amount  = (subtotal * tax_rate / Decimal('100')).quantize(Decimal('0.01'))
                order.total_amount = subtotal + order.tax_amount + order_shipping
            order.save()

            method = random.choice(['CASH', 'CASH', 'CARD', 'TRANSFER', 'WALLET'])
            fee    = (order.total_amount * Decimal('0.035')).quantize(Decimal('0.01')) if method == 'CARD' else Decimal('0.00')
            Payment.objects.create(
                organization=org, order=order, method=method,
                fee_amount=fee, amount=order.total_amount,
                transaction_reference=self._generate_reference(method),
                payment_date=order_date,
            )
            orders.append(order)
        return orders

    # ── Invoice data seeding ──────────────────────────────────────────────────

    def _seed_invoice_data(self, org, orders):
        """
        Assign invoice_status to orders and create accounting entries.
        Distribution: 70% accepted, 15% pending, 10% observed, 3% rejected, 2% failed.
        Also creates controlled inconsistencies for dashboard metrics testing.
        """
        from src.domain.models.accounting import AccountingEntry, AccountingEntryLine

        if AccountingEntry.all_objects.filter(organization=org).exists():
            self.stdout.write(f'  📊 Invoice data ya existe para {org.name}, omitiendo...')
            return

        DIST = [
            ('accepted', 0.70),
            ('observed', 0.10),
            ('pending',  0.15),
            ('rejected', 0.03),
            ('failed',   0.02),
        ]
        ERRORS = [
            'Error 2103: RUC no existe en SUNAT',
            'Error 1033: Comprobante ya fue emitido anteriormente',
            'Timeout: Servicio SUNAT no disponible (503)',
            'Error 2800: Firma digital inválida',
            'Error 0152: Número de serie no autorizado',
        ]

        accepted_orders = []
        seq = 1

        for order in orders:
            status = self._weighted_choice(DIST)

            updates = {'invoice_status': status}
            if status != 'pending':
                updates['invoice_external_id'] = f'F001-{seq:04d}'
                seq += 1
            if status in ('accepted', 'observed', 'submitted'):
                updates['invoice_hash'] = f'HASH{order.id:06d}{random.randint(1000, 9999)}'
            if status in ('rejected', 'failed'):
                updates['invoice_last_error'] = random.choice(ERRORS)

            Order.all_objects.filter(id=order.id).update(**updates)

            if status in ('accepted', 'observed'):
                order.refresh_from_db()
                accepted_orders.append(order)

        # ── Accounting entries ──────────────────────────────────────────────
        # Leave first 2 accepted WITHOUT entry → missing_entries = 2
        SKIP_COUNT = min(2, len(accepted_orders))
        entries_created = 0

        for i, order in enumerate(accepted_orders):
            if i < SKIP_COUNT:
                continue
            entry = AccountingEntry.objects.create(
                organization=org,
                order=order,
                entry_type=AccountingEntry.EntryType.SALE,
                invoice_external_id=order.invoice_external_id or f'F001-{i:04d}',
                amount_gross=order.total_amount,
                amount_tax=order.tax_amount,
                amount_net=order.subtotal,
                currency='PEN',
                entry_date=order.created_at.date(),
            )
            AccountingEntryLine.objects.bulk_create([
                AccountingEntryLine(
                    entry=entry, account_code='1211',
                    description='Cuentas por Cobrar Comerciales',
                    debit=order.total_amount, credit=Decimal('0.00'),
                ),
                AccountingEntryLine(
                    entry=entry, account_code='7011',
                    description='Ventas de Mercaderías',
                    debit=Decimal('0.00'), credit=order.subtotal,
                ),
                AccountingEntryLine(
                    entry=entry, account_code='4011',
                    description='IGV por Pagar',
                    debit=Decimal('0.00'), credit=order.tax_amount,
                ),
            ])
            entries_created += 1

        # ── Orphan entry: 1 entry on a non-accepted order → orphan_entries = 1
        orphan_order = (
            Order.all_objects.filter(organization=org)
            .exclude(invoice_status__in=['accepted', 'observed'])
            .first()
        )
        if orphan_order and not hasattr(orphan_order, 'accounting_entry'):
            try:
                orphan_entry = AccountingEntry.objects.create(
                    organization=org,
                    order=orphan_order,
                    entry_type=AccountingEntry.EntryType.ADJUSTMENT,
                    invoice_external_id='ORPHAN-SEED-001',
                    amount_gross=orphan_order.total_amount,
                    amount_tax=orphan_order.tax_amount,
                    amount_net=orphan_order.subtotal,
                    currency='PEN',
                    entry_date=timezone.now().date(),
                    notes='[SEED] Asiento huérfano — testing consistencia contable',
                )
                AccountingEntryLine.objects.create(
                    entry=orphan_entry, account_code='9999',
                    description='Ajuste manual (seed)', debit=Decimal('0.00'),
                    credit=orphan_order.total_amount,
                )
            except Exception:
                pass  # OneToOne collision on re-run, safe to ignore

        self.stdout.write(
            f'  📊 Facturas: {len(accepted_orders)} aceptadas/obs, '
            f'{entries_created} asientos, {SKIP_COUNT} faltantes, 1 huérfano'
        )

    # ── InvoiceSyncQueue seeding ──────────────────────────────────────────────

    def _seed_invoice_sync_queue(self, org):
        """Create InvoiceSyncQueue entries matching the invoice_status of each order."""
        from src.domain.models.invoicing import InvoiceSyncQueue, MAX_ATTEMPTS

        if InvoiceSyncQueue.all_objects.filter(organization=org).exists():
            self.stdout.write(f'  📋 Queue ya existe para {org.name}, omitiendo...')
            return

        now    = timezone.now()
        orders = Order.all_objects.filter(organization=org).exclude(invoice_status='pending')

        STATUS_MAP = {
            'accepted':       InvoiceSyncQueue.STATUS_COMPLETED,
            'observed':       InvoiceSyncQueue.STATUS_COMPLETED,
            'rejected':       InvoiceSyncQueue.STATUS_COMPLETED,
            'submitted':      InvoiceSyncQueue.STATUS_PENDING,
            'sync_pending':   InvoiceSyncQueue.STATUS_PENDING,
            'sync_processing': InvoiceSyncQueue.STATUS_PROCESSING,
            'failed':         None,  # varied below
        }

        FAILED_OUTCOMES = [
            InvoiceSyncQueue.STATUS_FAILED,
            InvoiceSyncQueue.STATUS_EXHAUSTED,
            InvoiceSyncQueue.STATUS_DEAD_LETTER,
        ]

        queue_entries = []
        for order in orders:
            inv_status   = order.invoice_status
            queue_status = STATUS_MAP.get(inv_status)

            if queue_status is None:
                queue_status = random.choice(FAILED_OUTCOMES)

            days_ago   = random.randint(0, 60)
            entry_date = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            attempts   = {
                InvoiceSyncQueue.STATUS_COMPLETED:   random.randint(1, 4),
                InvoiceSyncQueue.STATUS_FAILED:      random.randint(3, 7),
                InvoiceSyncQueue.STATUS_EXHAUSTED:   MAX_ATTEMPTS,
                InvoiceSyncQueue.STATUS_DEAD_LETTER: MAX_ATTEMPTS,
                InvoiceSyncQueue.STATUS_PENDING:     random.randint(1, 3),
                InvoiceSyncQueue.STATUS_PROCESSING:  random.randint(1, 2),
            }.get(queue_status, 1)

            entry = InvoiceSyncQueue(
                organization=org,
                order=order,
                status=queue_status,
                attempts=attempts,
                next_retry_at=now + timedelta(minutes=random.randint(5, 60))
                              if queue_status == InvoiceSyncQueue.STATUS_PENDING else now,
            )

            if queue_status == InvoiceSyncQueue.STATUS_COMPLETED:
                entry.completed_at = entry_date + timedelta(hours=random.randint(1, 48))

            if queue_status == InvoiceSyncQueue.STATUS_EXHAUSTED:
                entry.exhausted_at = entry_date + timedelta(days=random.randint(1, 7))
                entry.completed_at = entry.exhausted_at
                entry.last_error   = 'Max attempts reached without SUNAT resolution'

            if queue_status == InvoiceSyncQueue.STATUS_FAILED:
                entry.last_error = random.choice([
                    'NubefactTemporaryError: 503 Service Unavailable',
                    'Connection timeout after 15s',
                    'Error 2103: RUC no registrado',
                ])

            if queue_status == InvoiceSyncQueue.STATUS_DEAD_LETTER:
                entry.last_error = 'Marked as dead_letter after operator intervention'

            # Introduce stale locks: ~10% of pending/processing entries
            if queue_status in (InvoiceSyncQueue.STATUS_PENDING, InvoiceSyncQueue.STATUS_PROCESSING):
                if random.random() < 0.10:
                    entry.locked_at = now - timedelta(minutes=random.randint(11, 30))

            queue_entries.append((entry, entry_date))

        created = InvoiceSyncQueue.objects.bulk_create(
            [e for e, _ in queue_entries]
        )
        for obj, ts in zip(created, [t for _, t in queue_entries]):
            obj.created_at = ts
        InvoiceSyncQueue.objects.bulk_update(created, ['created_at'])

        counts = {}
        for e, _ in queue_entries:
            counts[e.status] = counts.get(e.status, 0) + 1
        self.stdout.write(f'  📋 Queue: {counts}')

    # ── ExternalServiceConfig seeding ─────────────────────────────────────────

    def _seed_external_service_configs(self, org):
        from src.domain.models.integrations import ExternalServiceConfig

        PROVIDERS = [
            {
                'provider_name': 'nubefact',
                'environment':   ExternalServiceConfig.Environment.SANDBOX,
                'base_url':      'https://demo.nubefact.com/api/v1',
                'api_key':       'SEED-NUBEFACT-TOKEN-0000',
                'timeout_seconds': 15,
                'max_retries':     3,
            },
            {
                'provider_name': 'migo',
                'environment':   ExternalServiceConfig.Environment.SANDBOX,
                'base_url':      'https://demo.apimigo.pe/api/v1',
                'api_key':       'SEED-MIGO-TOKEN-0000',
                'timeout_seconds': 10,
                'max_retries':     3,
            },
            {
                'provider_name': 'shopify',
                'environment':   ExternalServiceConfig.Environment.SANDBOX,
                'base_url':      'https://seed-store.myshopify.com/admin/api/2024-01',
                'api_key':       'SEED-SHOPIFY-TOKEN-0000',
                'timeout_seconds': 10,
            },
            {
                'provider_name': 'woocommerce',
                'environment':   ExternalServiceConfig.Environment.SANDBOX,
                'base_url':      'https://seed-store.example.com/wp-json/wc/v3',
                'api_key':       'SEED-WOO-TOKEN-0000',
                'timeout_seconds': 12,
            },
        ]
        for cfg in PROVIDERS:
            ExternalServiceConfig.objects.get_or_create(
                organization=org,
                provider_name=cfg['provider_name'],
                environment=cfg['environment'],
                defaults={k: v for k, v in cfg.items() if k not in ('provider_name', 'environment')},
            )

    # ── ExternalRequestLog seeding ────────────────────────────────────────────

    def _seed_external_request_logs(self, org, orders):
        """
        Simulate API call logs for 4 providers over 90 days.
        Uses bulk_create + bulk_update to backdate created_at.
        """
        from src.domain.models.integrations import ExternalServiceConfig, ExternalRequestLog

        if ExternalRequestLog.all_objects.filter(organization=org).count() > 10:
            self.stdout.write(f'  🔗 Logs ya existen para {org.name}, omitiendo...')
            return

        PROVIDERS = {
            'nubefact': {
                'operations':   ['crear_comprobante', 'consultar_comprobante', 'anular_comprobante'],
                'latency_range': (200, 800),
                'error_rate':    0.08,
                'error_codes':   [400, 422, 503, 504],
                'success_code':  200,
                'count_range':   (30, 60),
            },
            'migo': {
                'operations':   ['process_payment', 'check_payment_status', 'refund_payment'],
                'latency_range': (300, 1200),
                'error_rate':    0.15,
                'error_codes':   [400, 402, 503],
                'success_code':  200,
                'count_range':   (20, 45),
            },
            'shopify': {
                'operations':   ['sync_product', 'update_inventory', 'create_fulfillment'],
                'latency_range': (150, 600),
                'error_rate':    0.05,
                'error_codes':   [400, 422, 429],
                'success_code':  200,
                'count_range':   (15, 35),
            },
            'woocommerce': {
                'operations':   ['sync_product', 'update_order_status', 'get_orders'],
                'latency_range': (200, 900),
                'error_rate':    0.12,
                'error_codes':   [400, 401, 500, 503],
                'success_code':  200,
                'count_range':   (15, 30),
            },
        }

        configs = {
            cfg.provider_name: cfg
            for cfg in ExternalServiceConfig.objects.filter(organization=org)
        }

        now = timezone.now()
        logs_to_create = []
        log_timestamps = []

        for provider_name, spec in PROVIDERS.items():
            service = configs.get(provider_name)
            count   = random.randint(*spec['count_range'])

            for _ in range(count):
                log_time = now - timedelta(
                    days=random.randint(0, 89),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )
                is_success  = random.random() > spec['error_rate']
                duration    = random.randint(*spec['latency_range'])
                operation   = random.choice(spec['operations'])
                status_code = spec['success_code'] if is_success else random.choice(spec['error_codes'])
                error_msg   = None if is_success else f'[{status_code}] Error en {provider_name}.{operation}'
                linked_order = random.choice(orders) if orders and random.random() < 0.5 else None

                logs_to_create.append(ExternalRequestLog(
                    organization=org,
                    service=service,
                    provider_name=provider_name,
                    operation=operation,
                    order=linked_order,
                    request_payload={'provider': provider_name, 'op': operation},
                    response_payload={'status': status_code} if is_success else {},
                    status_code=status_code,
                    duration_ms=duration,
                    success=is_success,
                    error_message=error_msg,
                ))
                log_timestamps.append(log_time)

        created_logs = ExternalRequestLog.objects.bulk_create(logs_to_create)
        for log, ts in zip(created_logs, log_timestamps):
            log.created_at = ts
        ExternalRequestLog.objects.bulk_update(created_logs, ['created_at'])

        self.stdout.write(f'  🔗 {len(created_logs)} logs externos generados')

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _weighted_choice(dist):
        """
        dist: list of (value, weight) where weights sum to ~1.0.
        Returns a randomly selected value.
        """
        r, cumulative = random.random(), 0.0
        for value, weight in dist:
            cumulative += weight
            if r <= cumulative:
                return value
        return dist[-1][0]
