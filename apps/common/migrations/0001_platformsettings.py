from decimal import Decimal

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PlatformSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("verification_trigger_usd", models.DecimalField(
                    decimal_places=2,
                    default=Decimal("30.00"),
                    help_text="Lifetime earnings at which the reviewer must verify their account.",
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                )),
                ("premium_unlock_trigger_usd", models.DecimalField(
                    decimal_places=2,
                    default=Decimal("80.00"),
                    help_text="Lifetime earnings at which surveys are locked until unlocked.",
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                )),
                ("premium_unlock_cost_usd", models.DecimalField(
                    decimal_places=2,
                    default=Decimal("20.00"),
                    help_text="One-time wallet debit required to unlock surveys.",
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                )),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Platform settings",
                "verbose_name_plural": "Platform settings",
            },
        ),
    ]
