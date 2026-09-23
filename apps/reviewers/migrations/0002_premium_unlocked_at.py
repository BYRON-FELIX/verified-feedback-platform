from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reviewers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="reviewerprofile",
            name="premium_unlocked_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When the reviewer paid to unlock surveys.",
                null=True,
            ),
        ),
    ]
