import uuid

from django.db import models


class Country(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=2, unique=True, help_text="ISO 3166-1 alpha-2, e.g. KE")
    name = models.CharField(max_length=80)
    currency_code = models.CharField(max_length=3, default="KES")
    phone_prefix = models.CharField(max_length=8, default="+254")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Countries"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class County(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="counties")
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Counties"
        ordering = ["name"]
        unique_together = [("country", "name")]

    def __str__(self):
        return self.name