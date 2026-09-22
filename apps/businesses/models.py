import uuid

from django.conf import settings
from django.db import models


class BusinessStatus(models.TextChoices):
    PENDING = "PENDING", "Pending approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    SUSPENDED = "SUSPENDED", "Suspended"


class Business(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_businesses",
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    is_seed_data = models.BooleanField(default=False, db_index=True)
    description = models.TextField(blank=True)

    registration_number = models.CharField(max_length=60, blank=True)
    kra_pin = models.CharField(max_length=40, blank=True)
    physical_address = models.CharField(max_length=240, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="business_logos/", blank=True, null=True)
    industry = models.CharField(max_length=80, blank=True)
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=20, blank=True)

    status = models.CharField(
        max_length=16, choices=BusinessStatus.choices, default=BusinessStatus.PENDING
    )
    verified_badge = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def display_initial(self):
        return (self.name or "?")[:1].upper()

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.name)[:160] or "business"
            candidate = base
            n = 1
            while Business.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)