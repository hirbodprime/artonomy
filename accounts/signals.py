# accounts/signals.py
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile,User, PublicNumberCounter
from django.db import transaction

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
# users/signals.py


def _allocate_next_public_number() -> int:
    # One row, locked until commit; create if missing
    with transaction.atomic():
        counter, _ = PublicNumberCounter.objects.select_for_update().get_or_create(name="global")
        counter.last_number += 1
        counter.save(update_fields=["last_number"])
        return counter.last_number

@receiver(post_save, sender=User)
def assign_public_code(sender, instance: User, created: bool, **kwargs):
    if not created:
        return
    if instance.public_number:  # already assigned (rare, e.g., custom management command)
        return
    n = _allocate_next_public_number()
    code = f"A-{n}"
    # Save without retriggering logic
    User.objects.filter(pk=instance.pk).update(public_number=n, public_code=code)
