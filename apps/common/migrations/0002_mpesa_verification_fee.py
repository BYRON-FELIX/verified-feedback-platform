from decimal import Decimal

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0001_platformsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="mpesa_account_verification_fee_usd",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("1.00"),
                help_text="One-time PayHero fee required before M-Pesa withdrawals.",
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
            ),
        ),
    ]
