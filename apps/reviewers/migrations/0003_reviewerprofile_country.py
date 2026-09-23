from django.db import migrations, models
import django.db.models.deletion


def set_default_country(apps, schema_editor):
    ReviewerProfile = apps.get_model("reviewers", "ReviewerProfile")
    Country = apps.get_model("geo", "Country")
    default_country = Country.objects.filter(code="KE").first()
    if default_country:
        ReviewerProfile.objects.filter(country__isnull=True).update(country=default_country)


class Migration(migrations.Migration):
    dependencies = [
        ("geo", "0001_initial"),
        ("reviewers", "0002_premium_unlocked_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="reviewerprofile",
            name="country",
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text="Country where the reviewer is based.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reviewer_profiles",
                to="geo.country",
            ),
        ),
        migrations.RunPython(set_default_country, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="reviewerprofile",
            name="country",
            field=models.ForeignKey(
                help_text="Country where the reviewer is based.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reviewer_profiles",
                to="geo.country",
            ),
        ),
    ]
