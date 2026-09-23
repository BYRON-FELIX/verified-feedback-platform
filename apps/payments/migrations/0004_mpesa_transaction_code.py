from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0003_mpesa_verification_purpose"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="mpesa_transaction_code",
            field=models.CharField(
                blank=True,
                help_text="M-Pesa receipt/transaction code returned by PayHero.",
                max_length=40,
            ),
        ),
    ]
