import secrets
import string

from django.db import migrations, models
import django.db.models.deletion


def populate_referral_codes(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    alphabet = string.ascii_uppercase + string.digits
    used_codes = set(User.objects.exclude(referral_code__isnull=True).values_list("referral_code", flat=True))
    for user in User.objects.filter(referral_code__isnull=True).iterator():
        while True:
            code = "VF-" + "".join(secrets.choice(alphabet) for _ in range(8))
            if code not in used_codes:
                used_codes.add(code)
                break
        User.objects.filter(pk=user.pk).update(referral_code=code)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="referral_code",
            field=models.CharField(blank=True, max_length=12, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="user",
            name="referred_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="referred_users",
                to="accounts.user",
            ),
        ),
        migrations.RunPython(populate_referral_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="referral_code",
            field=models.CharField(blank=True, max_length=12, unique=True),
        ),
    ]