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


class CampaignWithSubmissionsDeletionTests(TestCase):
    def test_campaign_with_submissions_can_be_deleted(self):
        """Submissions and answers remain available after campaign deletion."""
        from datetime import date, timedelta
        from apps.campaigns.models import CampaignApplication, CampaignQuestion
        from apps.submissions.models import Submission, SubmissionAnswer

        owner = User.objects.create_user(email="owner@test.com", phone_number="+254700000000")
        reviewer = User.objects.create_user(
            email="reviewer@test.com",
            phone_number="+254700000001",
        )
        business = Business.objects.create(
            owner=owner,
            name="Test Business",
            slug="test-business",
        )

        category = Category.objects.create(name="Test Category")
        tomorrow = date.today() + timedelta(days=1)
        campaign = Campaign.objects.create(
            business=business,
            category=category,
            title="Test Campaign",
            slug="test-campaign",
            description="Test Description",
            reward_amount=10.00,
            target_participants=5,
            start_date=date.today(),
            end_date=tomorrow,
        )

        application = CampaignApplication.objects.create(
            campaign=campaign,
            reviewer=reviewer,
            status="ACCEPTED",
        )

        submission = Submission.objects.create(
            application=application,
            campaign=campaign,
            reviewer=reviewer,
            status="VERIFIED",
        )
        question = CampaignQuestion.objects.create(campaign=campaign, text="How was it?")
        answer = SubmissionAnswer.objects.create(
            submission=submission,
            question=question,
            answer_text="Great",
        )

        self.assertTrue(Submission.objects.filter(id=submission.id).exists())
        self.assertIsNotNone(submission.campaign)

        campaign.delete()

        self.assertFalse(Campaign.objects.filter(id=campaign.id).exists())
        submission.refresh_from_db()
        answer.refresh_from_db()
        self.assertIsNone(submission.campaign)
        self.assertIsNone(submission.application)
        self.assertIsNone(answer.question)
        self.assertIn("Deleted campaign", str(submission))
        self.assertIn("Deleted question", str(answer))

    def test_deleting_business_cascades_to_its_campaigns(self):
        from datetime import date, timedelta

        owner = User.objects.create_user(email="owner@test.com", phone_number="+254700000000")
        business = Business.objects.create(
            owner=owner,
            name="Test Business",
            slug="test-business",
        )
        today = date.today()
        campaign = Campaign.objects.create(
            business=business,
            category=Category.objects.create(name="Test Category"),
            title="Test Campaign",
            slug="test-campaign",
            description="Test Description",
            reward_amount=10.00,
            target_participants=5,
            start_date=today,
            end_date=today + timedelta(days=1),
        )

        business.delete()

        self.assertFalse(Campaign.objects.filter(pk=campaign.pk).exists())
