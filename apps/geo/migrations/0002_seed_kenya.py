from django.db import migrations


KENYA_COUNTIES = [
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Uasin Gishu", "Kiambu",
    "Machakos", "Kajiado", "Nyeri", "Meru", "Kakamega", "Bungoma",
    "Kilifi", "Kwale", "Kericho", "Bomet", "Narok", "Kitui", "Embu",
    "Laikipia", "Nyandarua", "Murang'a", "Kirinyaga", "Tharaka-Nithi",
    "Marsabit", "Isiolo", "Samburu", "Turkana", "West Pokot", "Trans Nzoia",
    "Elgeyo-Marakwet", "Nandi", "Vihiga", "Busia", "Siaya", "Homa Bay",
    "Migori", "Kisii", "Nyamira", "Taita-Taveta", "Tana River", "Lamu",
    "Garissa", "Wajir", "Mandera", "Baringo",
]


def seed(apps, schema_editor):
    Country = apps.get_model("geo", "Country")
    County = apps.get_model("geo", "County")

    kenya, _ = Country.objects.get_or_create(
        code="KE",
        defaults={
            "name": "Kenya",
            "currency_code": "KES",
            "phone_prefix": "+254",
            "is_active": True,
        },
    )
    for name in KENYA_COUNTIES:
        County.objects.get_or_create(country=kenya, name=name)


def unseed(apps, schema_editor):
    Country = apps.get_model("geo", "Country")
    Country.objects.filter(code="KE").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("geo", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]