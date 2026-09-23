from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="payment",
            new_name="payments_pa_user_id_8a80d2_idx",
            old_name="payments_pa_user_id_7ec6cc_idx",
        ),
        migrations.RenameIndex(
            model_name="payment",
            new_name="payments_pa_status_21ed42_idx",
            old_name="payments_pa_status_8e2a41_idx",
        ),
    ]
