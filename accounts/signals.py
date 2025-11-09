from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete
from .models import Profile, ProfileCounter, Skill, Testimonial, ClientLogo
User = get_user_model()

@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance, defaults={"role": "normal"})


def _touch_profile(instance):
    profile = getattr(instance, "profile", None)
    if profile:
        profile.refresh_completion()

@receiver(post_save, sender=Profile)
def _profile_saved(sender, instance, **kwargs):
    instance.refresh_completion()

@receiver([post_save, post_delete], sender=ProfileCounter)
def _counters_changed(sender, instance, **kwargs):
    _touch_profile(instance)

@receiver([post_save, post_delete], sender=Skill)
def _skills_changed(sender, instance, **kwargs):
    _touch_profile(instance)

@receiver([post_save, post_delete], sender=Testimonial)
def _testimonials_changed(sender, instance, **kwargs):
    _touch_profile(instance)

@receiver([post_save, post_delete], sender=ClientLogo)
def _logos_changed(sender, instance, **kwargs):
    _touch_profile(instance)
