from django.utils import timezone
from .models import SpotlightSettings, StarTransaction, SpotlightBoost, Referral

def add_stars(profile, amount, reason):
    profile.stars += amount
    profile.save(update_fields=["stars"])
    StarTransaction.objects.create(profile=profile, amount=amount, reason=reason)


def try_reward_referral(invited_profile):
    """Called AFTER invited user verifies email + reaches 100%"""

    try:
        ref = invited_profile.referral
    except Referral.DoesNotExist:
        return

    if ref.rewarded:
        return

    settings = SpotlightSettings.get()

    if not invited_profile.verified_email:
        return

    if invited_profile.completion < 100:
        return

    inviter = ref.inviter
    if not inviter.verified_email:
        return

    # OK GIVE REWARDS
    ref.rewarded = True
    ref.save(update_fields=["rewarded"])

    add_stars(inviter, settings.referral_reward, "پاداش دعوت موفق")
    add_stars(invited_profile, settings.invited_reward, "پاداش ثبت‌نام از طریق دعوت")


def activate_spotlight(profile):
    """Consumes stars & boosts position"""
    settings = SpotlightSettings.get()

    if profile.stars < settings.spotlight_cost:
        return False, "ستاره کافی ندارید."

    add_stars(profile, -settings.spotlight_cost, "استفاده از اسپات‌لایت")

    from datetime import timedelta
    expires = timezone.now() + timedelta(hours=settings.spotlight_hours)

    SpotlightBoost.objects.update_or_create(
        profile=profile,
        defaults={"expires_at": expires}
    )
    return True, "پروفایل شما فعال شد!"
