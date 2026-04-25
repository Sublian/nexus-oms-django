from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domain', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT',     'Borrador'),
                    ('PENDING',   'Pendiente'),
                    ('COURTESY',  'Cortesía'),
                    ('PAID',      'Pagado'),
                    ('SHIPPED',   'Enviado'),
                    ('DELIVERED', 'Entregado'),
                    ('COMPLETED', 'Completado'),
                    ('RETURNED',  'Retornado'),
                    ('CANCELLED', 'Cancelado'),
                ],
                default='DRAFT',
                max_length=20,
            ),
        ),
    ]
