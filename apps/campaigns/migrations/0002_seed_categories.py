from django.db import migrations
from django.utils.text import slugify


CATEGORIES = [
    ("Hotels & Hospitality", "bi-building"),
    ("Restaurants & Food", "bi-cup-hot"),
    ("Retail & Shopping", "bi-bag"),
    ("Telecom", "bi-phone"),
    ("Banking & Finance", "bi-bank"),
    ("Transport & Ride-hailing", "bi-car-front"),
    ("Healthcare", "bi-heart-pulse"),
    ("E-commerce", "bi-cart"),
    ("Software & Apps", "bi-app-indicator"),
    ("Beauty & Wellness", "bi-flower1"),
    ("Entertainment", "bi-music-note-beamed"),
    ("Other", "bi-three-dots"),
]


def seed(apps, schema_editor):
    Category = apps.get_model("campaigns", "Category")
    for name, icon in CATEGORIES:
        Category.objects.get_or_create(
            slug=slugify(name),
            defaults={"name": name, "icon": icon, "is_active": True},
        )


def unseed(apps, schema_editor):
    Category = apps.get_model("campaigns", "Category")
    Category.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]