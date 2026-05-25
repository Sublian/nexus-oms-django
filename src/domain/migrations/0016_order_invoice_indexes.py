from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domain', '0015_integration_layer'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='order',
            index=models.Index(
                fields=['organization', 'invoice_status'],
                name='order_org_invoice_status_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(
                fields=['organization', 'created_at'],
                name='order_org_created_at_idx',
            ),
        ),
    ]
