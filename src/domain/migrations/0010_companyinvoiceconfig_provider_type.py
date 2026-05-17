from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domain', '0009_order_invoice_attempts_last_error_status_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyinvoiceconfig',
            name='provider_type',
            field=models.CharField(
                choices=[('mock', 'Mock (desarrollo)'), ('nubefact', 'Nubefact (producción)')],
                default='mock',
                help_text='Proveedor activo: mock (desarrollo) | nubefact (producción)',
                max_length=20,
            ),
        ),
    ]
