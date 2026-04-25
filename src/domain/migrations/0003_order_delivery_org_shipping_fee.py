from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domain', '0002_order_status_courtesy_returned'),
    ]

    operations = [
        # Organization
        migrations.AddField(
            model_name='organization',
            name='default_shipping_fee',
            field=models.DecimalField(
                decimal_places=2, default=10.0, max_digits=8,
                help_text='Costo de envío por defecto (S/)'
            ),
        ),
        # Order
        migrations.AddField(
            model_name='order',
            name='delivery_type',
            field=models.CharField(
                choices=[('PICKUP', 'Retiro en Tienda'), ('DELIVERY', 'Delivery')],
                default='PICKUP', max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_address',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
    ]
