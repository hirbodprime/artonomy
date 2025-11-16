from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import Profile
from spotlight.utils import try_reward_referral


@receiver(post_save, sender=Profile)
def check_referral_reward(sender, instance, **kwargs):
    try_reward_referral(instance)
