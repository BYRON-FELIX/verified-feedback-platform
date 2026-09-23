from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0002_rename_indexes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="purpose",
            field=models.CharField(
                choices=[
                    ("SURVEY_UNLOCK", "Survey unlock"),
                    ("MPESA_ACCOUNT_VERIFICATION", "M-Pesa account verification"),
                ],
                max_length=32,
            ),
        ),
    ]
