from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("domain", "0012_invoicesyncqueue_dead_letter_exhausted"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoicesyncqueue",
            name="last_attempt_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Timestamp de la ultima consulta efectiva a Nubefact",
            ),
        ),
        migrations.AddField(
            model_name="invoicesyncqueue",
            name="exhausted_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Timestamp en que se agotaron los reintentos (MAX_ATTEMPTS alcanzado)",
            ),
        ),
        migrations.AddField(
            model_name="invoicesyncqueue",
            name="processing_duration_ms",
            field=models.IntegerField(
                null=True,
                blank=True,
                help_text="Duracion de la ultima consulta a Nubefact en ms — placeholder para Sprint 5",
            ),
        ),
    ]
