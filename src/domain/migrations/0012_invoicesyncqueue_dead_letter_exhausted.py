from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("domain", "0011_invoicesyncqueue_and_order_invoice_states"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invoicesyncqueue",
            name="status",
            field=models.CharField(
                max_length=20,
                default="pending",
                choices=[
                    ("pending",     "Pendiente"),
                    ("processing",  "Procesando"),
                    ("completed",   "Completada"),
                    ("failed",      "Fallida"),
                    ("dead_letter", "Dead Letter"),
                    ("exhausted",   "Reintentos Agotados"),
                ],
            ),
        ),
    ]
