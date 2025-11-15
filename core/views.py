from django.shortcuts import render

from accounts.models import Profile
from advertisement.models import HomepageAd 
from .models import  SiteSettings

def home_view(req):
    NUM_SLOTS = 20
    FULL_AD_POSITIONS = [1, 2, 6, 12, 18, 20]

    settings_obj = SiteSettings.get_solo()
    show_placeholders = settings_obj.show_homepage_ads

    all_ads = HomepageAd.objects.filter(
        is_active=True,
        position__in=FULL_AD_POSITIONS,
    )

    ads_by_position = {
        ad.position: ad
        for ad in all_ads
        if ad.is_currently_visible
    }

    if show_placeholders:
        reserved_positions = set(FULL_AD_POSITIONS)
    else:
        reserved_positions = set(ads_by_position.keys())

    profiles_needed = NUM_SLOTS - len(reserved_positions)

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
        ad = ads_by_position.get(pos)

        if ad:
            homepage_slots.append({
                "kind": "ad",
                "position": pos,
                "ad": ad,
            })
        elif show_placeholders and pos in FULL_AD_POSITIONS:
            homepage_slots.append({
                "kind": "empty_ad",
                "position": pos,
            })
        else:
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

    # 🔒 Limit for visitors (not logged in)
    if not req.user.is_authenticated:
        MAX_PUBLIC_SLOTS = 4
        homepage_slots = homepage_slots[:MAX_PUBLIC_SLOTS]
        homepage_slots.append({
            "kind": "signup_cta",
            "position": MAX_PUBLIC_SLOTS + 1,
        })

    return render(req, 'core/index.html', {
        "homepage_slots": homepage_slots,
    })

def contact_view(req):
    return render(req, 'core/contacts.html')

def about_view(req):
    return render(req, 'core/about.html')
