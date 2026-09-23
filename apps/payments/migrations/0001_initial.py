import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("purpose", models.CharField(choices=[("SURVEY_UNLOCK", "Survey unlock")], max_length=32)),
                ("amount_usd", models.DecimalField(decimal_places=2, max_digits=12)),
                ("amount_kes", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("QUEUED", "Queued"), ("SUCCESS", "Successful"), ("FAILED", "Failed")], default="QUEUED", max_length=16)),
                ("external_reference", models.CharField(max_length=80, unique=True)),
                ("provider_reference", models.CharField(blank=True, max_length=100)),
                ("checkout_request_id", models.CharField(blank=True, max_length=100)),
                ("provider_response", models.JSONField(blank=True, default=dict)),
                ("failure_reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["user", "purpose", "status"], name="payments_pa_user_id_7ec6cc_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["status", "-created_at"], name="payments_pa_status_8e2a41_idx"),
        ),
    ]
