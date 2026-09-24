from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0004_mpesa_transaction_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="purpose",
            field=models.CharField(
                choices=[
                    ("SURVEY_UNLOCK", "Survey unlock"),
                    ("MPESA_ACCOUNT_VERIFICATION", "M-Pesa account verification"),
                    ("STKPUSH_TEST", "STK push test"),
                ],
                max_length=32,
            ),
        ),
    ]