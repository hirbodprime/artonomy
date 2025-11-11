from django.shortcuts import render

from accounts.models import Profile
from advertisement.models import HomepageAd 
from .models import  SiteSettings


def home_view(req):
    NUM_SLOTS = 20

    settings_obj = SiteSettings.get_solo()
    show_ads = settings_obj.show_homepage_ads

    # اگر خاموش باشد، هیچ جایگاهی برای تبلیغ نداریم
    AD_POSITIONS = [1, 2, 6, 12, 18, 20] if show_ads else []

    # تبلیغات فعال فقط اگر show_ads روشن باشد
    ads_by_position = {}
    if show_ads:
        all_ads = HomepageAd.objects.filter(
            is_active=True,
            position__in=AD_POSITIONS,
        )
        ads_by_position = {
            ad.position: ad
            for ad in all_ads
            if ad.is_currently_visible
        }

    # تعداد پروفایل‌ها = کل اسلات‌ها - تعداد اسلات‌های تبلیغی (ثابت)
    profiles_needed = NUM_SLOTS - len(AD_POSITIONS)

    profiles_qs = (
        Profile.objects
        .filter(completion=100)
        .select_related('user')
        .order_by('-id')
    )
    profiles = list(profiles_qs[:profiles_needed])
    profiles_iter = iter(profiles)

    homepage_slots = []
    for pos in range(1, NUM_SLOTS + 1):
        if pos in AD_POSITIONS:
            # این اسلات مخصوص تبلیغ است
            ad = ads_by_position.get(pos)
            if ad:
                homepage_slots.append({
                    "kind": "ad",
                    "position": pos,
                    "ad": ad,
                })
            else:
                # بدون تبلیغ → placeholder (فقط وقتی show_ads روشن است)
                homepage_slots.append({
                    "kind": "empty_ad",
                    "position": pos,
                })
        else:
            # اسلات هنرمند
            try:
                prof = next(profiles_iter)
            except StopIteration:
                prof = None

            if prof:
                homepage_slots.append({
                    "kind": "profile",
                    "position": pos,
                    "profile": prof,
                })

    return render(req, 'core/index.html', {"homepage_slots": homepage_slots})


def contact_view(req):
    return render(req, 'core/contacts.html')

def about_view(req):
    return render(req, 'core/about.html')
