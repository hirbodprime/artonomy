from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from .models import Profile, Artwork, Testimonial, PortfolioTheme
from portfolio.utils.images import optimize_image_file

IMAGE_MODELS = (Profile, Artwork, Testimonial, PortfolioTheme)

def _image_fields(instance):
    for field in instance._meta.get_fields():
        if isinstance(field, models.ImageField):
            yield field.name

@receiver(post_save, sender=Profile)
@receiver(post_save, sender=Artwork)
@receiver(post_save, sender=Testimonial)
@receiver(post_save, sender=PortfolioTheme)
def optimize_images_after_save(sender, instance, created, **kwargs):
    changed_any = False
    for fname in _image_fields(instance):
        file_field = getattr(instance, fname, None)
        if file_field:
            changed = optimize_image_file(
                file_field,
                max_side=1920,        # resize ceiling
                jpg_quality=82,
                webp_quality=82,
                allow_webp=True
            )
            changed_any = changed_any or changed
    if changed_any:
        # persist updated file sizes/paths without touching timestamps unnecessarily
        instance.save(update_fields=[f for f in _image_fields(instance)])
