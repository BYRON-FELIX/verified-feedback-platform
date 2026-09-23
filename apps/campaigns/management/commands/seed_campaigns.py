"""
Seed the platform with demo campaigns, businesses, and geography.

Usage (local):
    python manage.py seed_campaigns --count 100
    python manage.py seed_campaigns --clear
    python manage.py seed_geo

Usage (render/prod):
    python manage.py seed_campaigns --count 100 --force

Guards:
    - Refuses to run if DEBUG=False unless --force is passed.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
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
from apps.geo.models import Country, County


fake = Faker(["en_GB", "en_US"])


# -------- Geography seed data -------- #

COUNTRIES = [
    # (code, name, currency, phone_prefix, [ (region_name, [cities]) ])
    ("KE", "Kenya", "KES", "+254", [
        ("Nairobi", ["Nairobi CBD", "Westlands", "Karen"]),
        ("Mombasa", ["Nyali", "Diani", "Mombasa Island"]),
        ("Kisumu", ["Kisumu CBD", "Milimani"]),
        ("Nakuru", ["Nakuru CBD", "Naivasha"]),
    ]),
    ("NG", "Nigeria", "NGN", "+234", [
        ("Lagos", ["Ikeja", "Victoria Island", "Lekki"]),
        ("Abuja", ["Garki", "Wuse", "Maitama"]),
        ("Rivers", ["Port Harcourt", "Bonny"]),
    ]),
    ("ZA", "South Africa", "ZAR", "+27", [
        ("Gauteng", ["Johannesburg", "Pretoria", "Sandton"]),
        ("Western Cape", ["Cape Town", "Stellenbosch"]),
        ("KwaZulu-Natal", ["Durban", "Pietermaritzburg"]),
    ]),
    ("IN", "India", "INR", "+91", [
        ("Maharashtra", ["Mumbai", "Pune", "Nagpur"]),
        ("Karnataka", ["Bangalore", "Mysore"]),
        ("Delhi", ["New Delhi", "Gurgaon"]),
        ("Tamil Nadu", ["Chennai", "Coimbatore"]),
    ]),
    ("PK", "Pakistan", "PKR", "+92", [
        ("Punjab", ["Lahore", "Rawalpindi", "Faisalabad"]),
        ("Sindh", ["Karachi", "Hyderabad"]),
        ("Khyber Pakhtunkhwa", ["Peshawar", "Abbottabad"]),
    ]),
    ("BD", "Bangladesh", "BDT", "+880", [
        ("Dhaka", ["Dhaka", "Gazipur"]),
        ("Chittagong", ["Chittagong", "Cox's Bazar"]),
    ]),
    ("PH", "Philippines", "PHP", "+63", [
        ("Metro Manila", ["Manila", "Makati", "Quezon City"]),
        ("Cebu", ["Cebu City", "Mandaue"]),
        ("Davao", ["Davao City"]),
    ]),
    ("ID", "Indonesia", "IDR", "+62", [
        ("Jakarta", ["Jakarta", "Tangerang"]),
        ("Bali", ["Denpasar", "Ubud"]),
        ("West Java", ["Bandung", "Bekasi"]),
    ]),
    ("VN", "Vietnam", "VND", "+84", [
        ("Hanoi", ["Hanoi", "Hai Phong"]),
        ("Ho Chi Minh", ["Ho Chi Minh City", "Thu Duc"]),
        ("Da Nang", ["Da Nang", "Hoi An"]),
    ]),
    ("TH", "Thailand", "THB", "+66", [
        ("Bangkok", ["Bangkok", "Nonthaburi"]),
        ("Chiang Mai", ["Chiang Mai"]),
        ("Phuket", ["Phuket", "Patong"]),
    ]),
    ("MY", "Malaysia", "MYR", "+60", [
        ("Kuala Lumpur", ["Kuala Lumpur", "Petaling Jaya"]),
        ("Penang", ["George Town"]),
        ("Johor", ["Johor Bahru"]),
    ]),
    ("LK", "Sri Lanka", "LKR", "+94", [
        ("Western", ["Colombo", "Negombo"]),
        ("Central", ["Kandy"]),
    ]),
    ("NP", "Nepal", "NPR", "+977", [
        ("Bagmati", ["Kathmandu", "Lalitpur"]),
        ("Gandaki", ["Pokhara"]),
    ]),
    ("BR", "Brazil", "BRL", "+55", [
        ("São Paulo", ["São Paulo", "Campinas"]),
        ("Rio de Janeiro", ["Rio de Janeiro", "Niterói"]),
        ("Bahia", ["Salvador"]),
    ]),
    ("AR", "Argentina", "ARS", "+54", [
        ("Buenos Aires", ["Buenos Aires", "La Plata"]),
        ("Córdoba", ["Córdoba"]),
    ]),
    ("CO", "Colombia", "COP", "+57", [
        ("Bogotá", ["Bogotá"]),
        ("Antioquia", ["Medellín"]),
        ("Valle del Cauca", ["Cali"]),
    ]),
    ("PE", "Peru", "PEN", "+51", [
        ("Lima", ["Lima", "Miraflores"]),
        ("Cusco", ["Cusco"]),
    ]),
    ("CL", "Chile", "CLP", "+56", [
        ("Santiago Metropolitan", ["Santiago", "Providencia"]),
        ("Valparaíso", ["Valparaíso", "Viña del Mar"]),
    ]),
    ("MX", "Mexico", "MXN", "+52", [
        ("Mexico City", ["Mexico City", "Polanco"]),
        ("Jalisco", ["Guadalajara"]),
        ("Nuevo León", ["Monterrey"]),
    ]),
    ("US", "United States", "USD", "+1", [
        ("California", ["Los Angeles", "San Francisco", "San Diego"]),
        ("New York", ["New York City", "Buffalo"]),
        ("Texas", ["Houston", "Dallas", "Austin"]),
        ("Florida", ["Miami", "Orlando"]),
    ]),
    ("CA", "Canada", "CAD", "+1", [
        ("Ontario", ["Toronto", "Ottawa"]),
        ("British Columbia", ["Vancouver", "Victoria"]),
        ("Quebec", ["Montreal", "Quebec City"]),
    ]),
]


# -------- Business seed data -------- #

DEMO_BUSINESS_DATA = [
    ("Nairobi Coffee Collective", "KE", "Hospitality", "Specialty coffee chain in Nairobi."),
    ("Safari Stays Kenya", "KE", "Hospitality", "Boutique lodges across Kenya."),
    ("Lagos Retail Group", "NG", "Retail", "Mid-tier retail chain in Lagos."),
    ("Cape Town Dining Co.", "ZA", "Restaurants", "Casual dining brand in Cape Town."),
    ("Mumbai Telecom Labs", "IN", "Telecom", "Product testing unit for an Indian telco."),
    ("Manila Eats", "PH", "Restaurants", "Cloud kitchen network in Metro Manila."),
    ("Jakarta Ride Co.", "ID", "Transport", "Ride-hailing service in Jakarta."),
    ("São Paulo Bank", "BR", "Banking", "Digital bank for Brazilian consumers."),
    ("Mexico City Retail", "MX", "Retail", "Mid-market retail chain in Mexico City."),
    ("New York SaaS Co.", "US", "Software", "B2B SaaS product company."),
    ("Toronto Grocery", "CA", "Retail", "Grocery delivery service in Toronto."),
    ("Dhaka Foods", "BD", "Restaurants", "Fast-casual chain in Dhaka."),
    ("Karachi Mobile", "PK", "Telecom", "Mobile network operator in Pakistan."),
    ("Hanoi Hotels", "VN", "Hospitality", "Boutique hotel group in Vietnam."),
    ("Bangkok Wellness", "TH", "Beauty", "Wellness and spa chain in Bangkok."),
    ("Kuala Lumpur Bank", "MY", "Banking", "Retail bank serving Malaysian consumers."),
    ("Colombo Apparel", "LK", "Retail", "Apparel retailer in Sri Lanka."),
    ("Kathmandu Tours", "NP", "Hospitality", "Tour operator in Kathmandu."),
    ("Buenos Aires Café", "AR", "Restaurants", "Specialty café chain in Buenos Aires."),
    ("Bogotá Delivery", "CO", "Transport", "Food delivery platform in Bogotá."),
    ("Lima Retail", "PE", "Retail", "Retail chain in Lima."),
    ("Santiago Bank", "CL", "Banking", "Digital bank in Chile."),
]


# -------- Text templates -------- #

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

PRODUCT_NAMES = [
    "mobile app", "loyalty card", "new menu item", "packaging", "self-checkout kiosk",
    "delivery service", "prepaid bundle", "online portal", "feedback kiosk",
]

REQUIREMENT_TEMPLATES = [
    "Must have visited {place} within the last {days} days",
    "Must have made a purchase of at least ${amount} at {place}",
    "Must be 18 years or older",
    "Must currently live in {region}",
    "Must have used the product in the last {days} days",
    "Must have an active payment method used for the purchase",
    "Must be able to describe their experience in at least 50 words",
]

QUESTION_TEMPLATES = {
    CampaignQuestionType.RATING: [
        "How would you rate the overall experience?",
        "How would you rate the value for money?",
        "How would you rate the cleanliness or presentation?",
        "How would you rate the staff or customer service?",
        "How likely are you to recommend this to a friend?",
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


# -------- Commands -------- #

class Command(BaseCommand):
    help = "Seed demo campaigns and businesses."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--businesses", type=int, default=10)
        parser.add_argument("--clear", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--geo", action="store_true",
                            help="Also seed geography (countries, regions).")

    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts["force"]:
            raise CommandError("Refusing to seed when DEBUG=False. Pass --force.")

        if opts["geo"]:
            self._seed_geo()

        if opts["clear"]:
            self._clear()

        businesses = self._ensure_businesses(opts["businesses"])
        categories = list(Category.objects.filter(is_active=True))
        counties = list(County.objects.all())

        if not categories:
            raise CommandError("No categories. Run migrations.")
        if not counties:
            raise CommandError("No regions. Run: python manage.py seed_campaigns --geo")

        created = 0
        for _ in range(opts["count"]):
            self._create_campaign(businesses, categories, counties)
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created} campaigns across {len(businesses)} businesses."
        ))

    # ---- geo ---- #

    def _seed_geo(self):
        created_countries = 0
        created_regions = 0
        for code, name, currency, prefix, regions in COUNTRIES:
            country, c_created = Country.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "currency_code": currency,
                    "phone_prefix": prefix,
                    "is_active": True,
                },
            )
            if c_created:
                created_countries += 1
            for region_name, _cities in regions:
                _, r_created = County.objects.get_or_create(
                    country=country, name=region_name, defaults={"is_active": True},
                )
                if r_created:
                    created_regions += 1
        self.stdout.write(self.style.SUCCESS(
            f"Geo: +{created_countries} countries, +{created_regions} regions."
        ))

    # ---- clear ---- #

    def _clear(self):
        self.stdout.write("Clearing previous seed data...")
        deleted_c = Campaign.objects.filter(is_seed_data=True).delete()[0]
        deleted_b = Business.objects.filter(is_seed_data=True).delete()[0]
        self.stdout.write(self.style.WARNING(
            f"Deleted {deleted_c} campaigns and {deleted_b} businesses."
        ))

    # ---- businesses ---- #

    def _ensure_businesses(self, count):
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
        if seed_owner.has_usable_password():
            seed_owner.set_unusable_password()
            seed_owner.save(update_fields=["password"])

        businesses = list(Business.objects.filter(is_seed_data=True))
        if len(businesses) >= count:
            return businesses[:count]

        target = min(count, len(DEMO_BUSINESS_DATA))
        for name, cc, industry, desc in DEMO_BUSINESS_DATA[:target]:
            b, _ = Business.objects.get_or_create(
                name=name,
                defaults={
                    "owner": seed_owner,
                    "industry": industry,
                    "description": desc,
                    "status": BusinessStatus.APPROVED,
                    "verified_badge": True,
                    "is_seed_data": True,
                    "support_email": f"hello@{name.lower().replace(' ', '')[:20]}.example",
                    "support_phone": "+10000000000",
                    "physical_address": f"{fake.street_address()}",
                },
            )
            businesses.append(b)

        return businesses

    # ---- campaigns ---- #

    def _create_campaign(self, businesses, categories, counties):
        business = random.choice(businesses)
        category = random.choice(categories)
        region = random.choice(counties)

        kind, tmpl = random.choice(CAMPAIGN_TITLE_TEMPLATES)
        title = tmpl.format(
            place=region.name,
            category=category.name,
            product=random.choice(PRODUCT_NAMES),
        )
        suffix = fake.unique.bothify(text="-##??").upper()
        title = f"{title} [{suffix}]"

        campaign_type = self._kind_to_type(kind)

        # USD rewards: 0.50 to 5.00 in small increments
        reward = Decimal(random.choice([
            50, 75, 100, 125, 150, 200, 250, 300, 400, 500,
        ])) / Decimal("100")  # -> 0.50 .. 5.00

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
                reward_amount=reward,
                target_participants=target,
                budget_total=reward * target,
                start_date=start,
                end_date=end,
                county=region,
                location_description=region.name,
                estimated_minutes=random.randint(5, 30),
                is_seed_data=True,
            )

            req_count = random.randint(3, 5)
            templates = random.sample(REQUIREMENT_TEMPLATES, k=req_count)
            for i, t in enumerate(templates):
                CampaignRequirement.objects.create(
                    campaign=campaign,
                    text=t.format(
                        place=region.name,
                        days=random.choice([7, 14, 30]),
                        amount=random.choice([5, 10, 20]),
                        region=region.name,
                    )[:300],
                    is_mandatory=True,
                    order=i,
                )

            q_count = random.randint(3, 7)
            q_types = random.choices(list(QUESTION_TEMPLATES.keys()), k=q_count)
            for i, qtype in enumerate(q_types):
                self._create_question(campaign, qtype, order=i)

        return campaign

    def _create_question(self, campaign, qtype, order):
        if qtype == CampaignQuestionType.SINGLE_CHOICE:
            text, options = random.choice(QUESTION_TEMPLATES[qtype])
            CampaignQuestion.objects.create(
                campaign=campaign, text=text, question_type=qtype,
                options=options, is_required=True, order=order,
            )
        else:
            text = random.choice(QUESTION_TEMPLATES[qtype])
            CampaignQuestion.objects.create(
                campaign=campaign, text=text, question_type=qtype,
                options=[], is_required=True, order=order,
            )

    def _kind_to_type(self, kind):
        return {
            "Review": CampaignType.REVIEW,
            "Survey": CampaignType.SURVEY,
            "Mystery Shopping": CampaignType.MYSTERY_SHOPPING,
            "Product Testing": CampaignType.PRODUCT_TESTING,
            "Service Testing": CampaignType.SERVICE_TESTING,
        }[kind]