"""
Seed the platform with demo campaigns and demo businesses.

Usage (local):
    python manage.py seed_campaigns --count 100
    python manage.py seed_campaigns --clear       # remove all seed data

Usage (render/prod):
    python manage.py seed_campaigns --count 100 --force

Guards:
    - Refuses to run if DEBUG=False unless --force is passed (prevents accidents)
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker

from apps.accounts.models import User, UserRole
from apps.businesses.models import Business, BusinessStatus
from apps.campaigns.models import (
    Campaign,
    CampaignQuestion,
    CampaignQuestionType,
    CampaignRequirement,
    CampaignStatus,
    CampaignType,
    Category,
)
from apps.geo.models import County


fake = Faker("en_GB")  # en_GB gives a slightly more international flavor

# ---------------------------------------------------------------- #

DEMO_BUSINESS_DATA = [
    {
        "name": "Nairobi Coffee Collective",
        "industry": "Hospitality",
        "description": "A specialty coffee chain with locations across Nairobi.",
    },
    {
        "name": "Safari Stays Kenya",
        "industry": "Hospitality",
        "description": "Boutique lodges and short-stay apartments in Kenya's tourist circuits.",
    },
    {
        "name": "Kilimani Retail Group",
        "industry": "Retail",
        "description": "Mid-tier retail chain operating in Nairobi and Mombasa.",
    },
    {
        "name": "Safaricom Test Lab",
        "industry": "Telecom",
        "description": "Product testing unit for a major Kenyan telco.",
    },
    {
        "name": "Mama Oliech Foods",
        "industry": "Restaurants",
        "description": "Popular casual dining brand with locations in Nairobi and Kisumu.",
    },
]

# ---------------------------------------------------------------- #

CAMPAIGN_TITLE_TEMPLATES = [
    ("Review", "Share your experience at {place}"),
    ("Review", "{category} experience study: {place}"),
    ("Survey", "{category} customer satisfaction survey"),
    ("Survey", "{category} service quality questionnaire"),
    ("Mystery Shopping", "Mystery shop: {place}"),
    ("Mystery Shopping", "Service quality check at {place}"),
    ("Product Testing", "Test our new {product} and give feedback"),
    ("Product Testing", "Product trial: {product}"),
    ("Service Testing", "Try our {place} service and report back"),
    ("Service Testing", "{category} app/service experience test"),
]

PLACE_NAMES = [
    "Nairobi CBD", "Westlands", "Kilimani", "Karen", "Lavington", "Parklands",
    "Mombasa", "Nyali", "Diani", "Kisumu", "Nakuru", "Eldoret", "Thika",
    "Nyeri", "Meru", "Kakamega", "Machakos", "Naivasha",
]

PRODUCT_NAMES = [
    "mobile app", "loyalty card", "new menu item", "packaging", "self-checkout kiosk",
    "delivery service", "prepaid bundle", "online portal", "feedback kiosk",
]

REQUIREMENT_TEMPLATES = [
    "Must have visited {place} within the last {days} days",
    "Must have made a purchase of at least KSh {amount} at {place}",
    "Must be 18 years or older",
    "Must currently live in {county} County",
    "Must have used the product in the last {days} days",
    "Must be willing to upload a receipt or order number",
    "Must have an active mobile money or card used for the purchase",
    "Must be able to describe their experience in at least 50 words",
]

QUESTION_TEMPLATES = {
    CampaignQuestionType.RATING: [
        "How would you rate the overall experience?",
        "How would you rate the value for money?",
        "How would you rate the cleanliness or presentation?",
        "How would you rate the staff or customer service?",
        "How likely are you to recommend this to a friend? (1=not likely, 5=very likely)",
    ],
    CampaignQuestionType.TEXT: [
        "What did you buy or use?",
        "Who did you interact with?",
        "Where exactly was the location?",
        "What was the best thing about the experience?",
    ],
    CampaignQuestionType.LONG_TEXT: [
        "Please describe your experience in detail.",
        "What could have been better?",
        "What did you enjoy most?",
        "Would you return? Why or why not?",
    ],
    CampaignQuestionType.YES_NO: [
        "Was the service you received within the promised time?",
        "Was the product in stock when you arrived?",
        "Did you feel the price was fair for what you received?",
        "Would you recommend this to a friend?",
    ],
    CampaignQuestionType.SINGLE_CHOICE: [
        ("How did you hear about this place or product?", [
            "Word of mouth", "Social media", "Walked past", "Google search", "Other",
        ]),
        ("When did you visit or use this?", [
            "This week", "In the last 2 weeks", "In the last month", "Over a month ago",
        ]),
        ("What best describes you?", [
            "First-time customer", "Occasional customer", "Regular customer",
        ]),
    ],
}


# ---------------------------------------------------------------- #

class Command(BaseCommand):
    help = "Seed demo campaigns and businesses."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100,
                            help="Number of campaigns to create.")
        parser.add_argument("--businesses", type=int, default=5,
                            help="Number of demo businesses to create (if missing).")
        parser.add_argument("--clear", action="store_true",
                            help="Delete all previously seeded data first.")
        parser.add_argument("--force", action="store_true",
                            help="Allow running when DEBUG=False.")

    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts["force"]:
            raise CommandError(
                "Refusing to seed when DEBUG=False. Pass --force if you really mean it."
            )

        if opts["clear"]:
            self._clear()

        business_count = opts["businesses"]
        campaign_count = opts["count"]

        businesses = self._ensure_businesses(business_count)
        categories = list(Category.objects.filter(is_active=True))
        counties = list(County.objects.filter(is_active=True))

        if not categories:
            raise CommandError("No categories exist. Run migrations and seed categories first.")
        if not counties:
            raise CommandError("No counties exist. Run migrations and seed counties first.")

        created = 0
        for _ in range(campaign_count):
            self._create_campaign(businesses, categories, counties)
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created} campaigns across {len(businesses)} businesses."
        ))

    # ---------- helpers ---------- #

    def _clear(self):
        self.stdout.write("Clearing previous seed data...")
        deleted_c = Campaign.objects.filter(is_seed_data=True).delete()[0]
        deleted_b = Business.objects.filter(is_seed_data=True).delete()[0]
        self.stdout.write(self.style.WARNING(
            f"Deleted {deleted_c} campaigns and {deleted_b} businesses."
        ))

    def _ensure_businesses(self, count):
        # Look for any seed owners we've created before
        seed_owner, _ = User.objects.get_or_create(
            email="seed-owner@vfplatform.local",
            defaults={
                "username": "seed-owner",
                "first_name": "Seed",
                "last_name": "Owner",
                "role": UserRole.BUSINESS,
                "is_email_verified": True,
                "is_active": True,
            },
        )
        if not seed_owner.has_usable_password():
            seed_owner.set_unusable_password()
            seed_owner.save()

        businesses = list(Business.objects.filter(is_seed_data=True))
        if len(businesses) >= count:
            return businesses[:count]

        target = min(count, len(DEMO_BUSINESS_DATA))
        for data in DEMO_BUSINESS_DATA[:target]:
            b, _ = Business.objects.get_or_create(
                name=data["name"],
                defaults={
                    "owner": seed_owner,
                    "industry": data["industry"],
                    "description": data["description"],
                    "status": BusinessStatus.APPROVED,
                    "verified_badge": True,
                    "is_seed_data": True,
                    "support_email": f"hello@{slugify(data['name'])[:20]}.ke",
                    "support_phone": "+254700000000",
                    "physical_address": f"{fake.street_address()}, Nairobi",
                },
            )
            businesses.append(b)

        return businesses

    def _create_campaign(self, businesses, categories, counties):
        business = random.choice(businesses)
        category = random.choice(categories)
        county = random.choice(counties)

        # Title
        kind, tmpl = random.choice(CAMPAIGN_TITLE_TEMPLATES)
        title = tmpl.format(
            place=random.choice(PLACE_NAMES),
            category=category.name,
            product=random.choice(PRODUCT_NAMES),
        )
        # Ensure uniqueness
        suffix = fake.unique.bothify(text="-##??").upper()
        title = f"{title} [{suffix}]"

        campaign_type = self._kind_to_type(kind)

        reward = Decimal(random.choice([50, 75, 100, 125, 150, 175, 200, 250, 300]))
        target = random.randint(20, 100)

        start = timezone.now().date() - timedelta(days=random.randint(0, 7))
        end = start + timedelta(days=random.randint(14, 60))

        with transaction.atomic():
            campaign = Campaign.objects.create(
                business=business,
                category=category,
                title=title[:160],
                description=(
                    f"We're running a research study to understand what customers really "
                    f"experience at our {category.name.lower()} touchpoints. "
                    f"Your honest feedback helps us improve. This is not about positive "
                    f"ratings — we want to hear what actually happened."
                ),
                instructions=(
                    "1. Make sure your experience was recent (see requirements).\n"
                    "2. Answer each question honestly.\n"
                    "3. Provide written feedback in your own words.\n"
                    "4. Do not fabricate information — submissions are verified."
                ),
                campaign_type=campaign_type,
                status=CampaignStatus.ACTIVE,
                reward_amount_ksh=reward,
                target_participants=target,
                budget_total_ksh=reward * target,
                start_date=start,
                end_date=end,
                county=county,
                location_description=random.choice(PLACE_NAMES),
                estimated_minutes=random.randint(5, 30),
                min_days_since_experience=random.choice([7, 14, 30, 60]),
                required_evidence_types=random.sample(
                    ["RECEIPT", "BOOKING_CONFIRMATION", "PHOTOGRAPH", "ORDER_NUMBER"],
                    k=random.randint(1, 2),
                ),
                is_seed_data=True,
            )

            # Requirements: 3–5
            req_count = random.randint(3, 5)
            templates = random.sample(REQUIREMENT_TEMPLATES, k=req_count)
            for i, t in enumerate(templates):
                CampaignRequirement.objects.create(
                    campaign=campaign,
                    text=t.format(
                        place=random.choice(PLACE_NAMES),
                        days=random.choice([7, 14, 30]),
                        amount=random.choice([200, 500, 1000]),
                        county=county.name,
                    )[:300],
                    is_mandatory=True,
                    order=i,
                )

            # Questions: 3–7 mixed types
            q_count = random.randint(3, 7)
            q_types = random.choices(
                list(QUESTION_TEMPLATES.keys()),
                k=q_count,
            )
            for i, qtype in enumerate(q_types):
                self._create_question(campaign, qtype, order=i)

        return campaign

    def _create_question(self, campaign, qtype, order):
        if qtype == CampaignQuestionType.SINGLE_CHOICE:
            text, options = random.choice(QUESTION_TEMPLATES[qtype])
            CampaignQuestion.objects.create(
                campaign=campaign,
                text=text,
                question_type=qtype,
                options=options,
                is_required=True,
                order=order,
            )
        else:
            text = random.choice(QUESTION_TEMPLATES[qtype])
            CampaignQuestion.objects.create(
                campaign=campaign,
                text=text,
                question_type=qtype,
                options=[],
                is_required=True,
                order=order,
            )

    def _kind_to_type(self, kind):
        return {
            "Review": CampaignType.REVIEW,
            "Survey": CampaignType.SURVEY,
            "Mystery Shopping": CampaignType.MYSTERY_SHOPPING,
            "Product Testing": CampaignType.PRODUCT_TESTING,
            "Service Testing": CampaignType.SERVICE_TESTING,
        }[kind]