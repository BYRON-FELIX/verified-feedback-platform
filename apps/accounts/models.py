import uuid
import secrets
import string

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    REVIEWER = "REVIEWER", "Reviewer"
    BUSINESS = "BUSINESS", "Business"
    ADMIN = "ADMIN", "Admin"


class UserManager(BaseUserManager):
    """Custom manager — email is the login identifier, not username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", UserRole.REVIEWER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model.

    - Login is by email (username is kept for Django admin compatibility,
      but is auto-generated from the email).
    - role determines which dashboard the user sees.
    - Verification flags are separate so we can add OTP flows later
      without breaking existing data.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True, db_index=True)

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text="E.164 format, e.g. +254712345678",
    )
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    referral_code = models.CharField(max_length=12, unique=True, blank=True)
    referred_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="referred_users",
    )

    role = models.CharField(
        max_length=16,
        choices=UserRole.choices,
        default=UserRole.REVIEWER,
        db_index=True,
    )

    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.TextField(blank=True)
    suspended_at = models.DateTimeField(blank=True, null=True)

    last_login_ip = models.GenericIPAddressField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        db_table = "users_user"
        indexes = [
            models.Index(fields=["role", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.email

    def save(self, *args, **kwargs):
        # Auto-generate a username from the email if missing.
        if not self.username:
            base = self.email.split("@")[0][:140] or "user"
            candidate = base
            n = 1
            while User.objects.filter(username=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}{n}"
            self.username = candidate
        if not self.referral_code:
            alphabet = string.ascii_uppercase + string.digits
            while True:
                code = "VF-" + "".join(secrets.choice(alphabet) for _ in range(8))
                if not User.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break
        super().save(*args, **kwargs)

    def suspend(self, reason: str):
        self.is_suspended = True
        self.suspension_reason = reason
        self.suspended_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["is_suspended", "suspension_reason", "suspended_at", "is_active"])

    def unsuspend(self):
        self.is_suspended = False
        self.suspension_reason = ""
        self.suspended_at = None
        self.is_active = True
        self.save(update_fields=["is_suspended", "suspension_reason", "suspended_at", "is_active"])

    @property
    def display_name(self) -> str:
        full = (self.get_full_name() or "").strip()
        return full or self.email