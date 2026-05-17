from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domain', '0008_order_invoice_external_id_order_invoice_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='invoice_attempts',
            field=models.IntegerField(default=0, help_text='Número de intentos de facturación realizados'),
        ),
        migrations.AddField(
            model_name='order',
            name='invoice_last_error',
            field=models.TextField(blank=True, null=True, help_text='Último error de facturación (para debugging y retry manual)'),
        ),
        migrations.AlterField(
            model_name='order',
            name='invoice_status',
            field=models.CharField(
                choices=[
                    ('pending',    'Pendiente'),
                    ('processing', 'Procesando'),
                    ('issued',     'Emitida'),
                    ('retrying',   'Reintentando'),
                    ('failed',     'Fallida'),
                ],
                default='pending',
                help_text='Estado de facturación: pending | processing | issued | retrying | failed',
                max_length=20,
            ),
        ),
    ]
