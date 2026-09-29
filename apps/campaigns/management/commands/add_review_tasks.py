import json
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.campaigns.models import Campaign


class Command(BaseCommand):
    help = "Load review task fixtures and assign their businesses to a superuser."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="fixtures/review_tasks.json",
            help="Fixture path, relative to the project root unless absolute.",
        )
        parser.add_argument(
            "--owner-email",
            help="Email of the active superuser who should own all loaded tasks.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow loading the review task fixture when DEBUG=False.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to load production tasks without --force.")

        fixture_path = Path(options["fixture"])
        if not fixture_path.is_absolute():
            fixture_path = Path(settings.BASE_DIR) / fixture_path
        if not fixture_path.is_file():
            raise CommandError(f"Fixture file does not exist: {fixture_path}")

        try:
            fixture_data = json.loads(fixture_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read fixture {fixture_path}: {exc}") from exc
        if not isinstance(fixture_data, list):
            raise CommandError("Review task fixture must be a JSON list.")
        if any(
            not isinstance(item, dict) or not isinstance(item.get("fields"), dict)
            for item in fixture_data
        ):
            raise CommandError("Every fixture entry must have a model and fields object.")

        task_entries = [
            item
            for item in fixture_data
            if item.get("model") == "campaigns.campaign"
            and item.get("fields", {}).get("is_seed_data", False)
        ]
        if len(task_entries) < 30:
            raise CommandError(
                f"Fixture must contain at least 30 seeded campaigns; found {len(task_entries)}."
            )

        business_ids = {
            str(item["fields"]["business"])
            for item in task_entries
            if item.get("fields", {}).get("business") is not None
        }
        if not business_ids:
            raise CommandError("Review task fixture has no business references.")
        business_entries = [
            item for item in fixture_data
            if item.get("model") == "businesses.business"
        ]
        fixture_business_ids = {str(item.get("pk")) for item in business_entries}
        if not business_ids.issubset(fixture_business_ids):
            raise CommandError(
                "Every review task business must be included in the fixture."
            )

        superusers = User.objects.filter(is_superuser=True, is_active=True)
        if options["owner_email"]:
            superusers = superusers.filter(email__iexact=options["owner_email"])
        owner = superusers.order_by("email").first()
        if owner is None:
            raise CommandError(
                "No active superuser found. Create one first or specify --owner-email."
            )

        campaign_business_ids = business_ids
        fixture_data = [
            item for item in fixture_data
            if item.get("model") != "accounts.user"
        ]
        for item in fixture_data:
            if item.get("model") == "businesses.business":
                item["fields"]["owner"] = str(owner.pk)

        with transaction.atomic():
            with tempfile.TemporaryDirectory(prefix="review-task-fixture-") as temp_dir:
                transformed_fixture = Path(temp_dir) / "review_tasks.json"
                transformed_fixture.write_text(
                    json.dumps(fixture_data),
                    encoding="utf-8",
                )
                call_command("loaddata", str(transformed_fixture), verbosity=0)
            updated_businesses = Business.objects.filter(
                pk__in=campaign_business_ids,
                owner=owner,
            ).count()
            if updated_businesses != len(business_ids):
                raise CommandError(
                    "Not all fixture businesses are owned by the selected superuser."
                )

        task_count = Campaign.objects.filter(
            is_seed_data=True,
            business_id__in=campaign_business_ids,
            business__owner=owner,
        ).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {task_count} review tasks owned by superuser {owner.email}."
            )
        )
