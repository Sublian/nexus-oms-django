import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domain', '0007_orderworkflowlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='invoice_external_id',
            field=models.CharField(blank=True, help_text='ID externo de factura de Nubefact o Mock', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='invoice_status',
            field=models.CharField(choices=[('pending', 'Pendiente'), ('issued', 'Emitida'), ('failed', 'Fallida')], default='pending', help_text='Estado de facturación: pending | issued | failed', max_length=20),
        ),
        migrations.CreateModel(
            name='CompanyInvoiceConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('api_base_url', models.URLField(help_text='URL base de API Nubefact (ej: https://api.nubefact.com/api)')),
                ('endpoint_url', models.CharField(help_text='Endpoint específico (ej: invoices, documents)', max_length=255)),
                ('token', models.CharField(help_text='Token/API key para autenticación', max_length=255)),
                ('enabled', models.BooleanField(default=True, help_text='Si está deshabilitado, usa MockNubefactClient')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_items', to='domain.organization')),
            ],
            options={
                'verbose_name': 'Configuración de Facturación',
                'verbose_name_plural': 'Configuraciones de Facturación',
            },
        ),
    ]
