from apps.common.models import PlatformSettings


def get_platform_settings():
    return PlatformSettings.get_solo()


def requires_account_verification(user, wallet=None):
    wallet = wallet or user.wallet
    config = get_platform_settings()
    return (
        wallet.lifetime_earnings >= config.verification_trigger_usd
        and not user.is_phone_verified
    )


def surveys_are_locked(user, wallet=None):
    wallet = wallet or user.wallet
    config = get_platform_settings()
    profile = getattr(user, "reviewer_profile", None)
    return wallet.lifetime_earnings >= config.premium_unlock_trigger_usd and (
        not profile or profile.premium_unlocked_at is None
    )


def task_access_lock_reason(user, wallet=None):
    wallet = wallet or user.wallet
    if requires_account_verification(user, wallet):
        return "account_verification"
    if surveys_are_locked(user, wallet):
        return "premium_upgrade"
    return None
