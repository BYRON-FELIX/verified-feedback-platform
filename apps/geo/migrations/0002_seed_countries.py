from django.db import migrations


COUNTRIES = [
    ("AR", "Argentina", "ARS", "+54"),
    ("BD", "Bangladesh", "BDT", "+880"),
    ("BR", "Brazil", "BRL", "+55"),
    ("CA", "Canada", "CAD", "+1"),
    ("CL", "Chile", "CLP", "+56"),
    ("CO", "Colombia", "COP", "+57"),
    ("ID", "Indonesia", "IDR", "+62"),
    ("IN", "India", "INR", "+91"),
    ("KE", "Kenya", "KES", "+254"),
    ("LK", "Sri Lanka", "LKR", "+94"),
    ("MX", "Mexico", "MXN", "+52"),
    ("MY", "Malaysia", "MYR", "+60"),
    ("NP", "Nepal", "NPR", "+977"),
    ("NG", "Nigeria", "NGN", "+234"),
    ("PK", "Pakistan", "PKR", "+92"),
    ("PE", "Peru", "PEN", "+51"),
    ("PH", "Philippines", "PHP", "+63"),
    ("ZA", "South Africa", "ZAR", "+27"),
    ("TH", "Thailand", "THB", "+66"),
    ("US", "United States", "USD", "+1"),
    ("VN", "Vietnam", "VND", "+84"),
]


def seed_countries(apps, schema_editor):
    Country = apps.get_model("geo", "Country")
    for code, name, currency_code, phone_prefix in COUNTRIES:
        Country.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "currency_code": currency_code,
                "phone_prefix": phone_prefix,
                "is_active": True,
            },
        )


def remove_seeded_countries(apps, schema_editor):
    Country = apps.get_model("geo", "Country")
    Country.objects.filter(code__in=[country[0] for country in COUNTRIES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("geo", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_countries, remove_seeded_countries),
    ]
