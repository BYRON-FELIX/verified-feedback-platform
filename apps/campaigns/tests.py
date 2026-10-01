from datetime import date

from django.test import TestCase

from apps.accounts.models import User
from apps.businesses.models import Business

from .models import Campaign, Category


class CategoryDeletionTests(TestCase):
    def test_deleting_category_preserves_campaign(self):
        owner = User.objects.create_user(email="business@example.com", password="test")
        business = Business.objects.create(
            owner=owner,
            name="Test business",
            slug="test-business",
        )
        category = Category.objects.create(name="Test category", slug="test-category")
        campaign = Campaign.objects.create(
            business=business,
            category=category,
            title="Test campaign",
            slug="test-campaign",
            description="Campaign description",
            reward_amount="5.00",
            target_participants=1,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 2),
        )

        category.delete()

        campaign.refresh_from_db()
        self.assertIsNone(campaign.category)
