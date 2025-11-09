from django.shortcuts import render

from accounts.models import Profile


def home_view(req):
    top_n = 12
    profiles = (
        Profile.objects
        .filter(completion=100)
        .filter(Profile.premium_q())
        .select_related('user')
        .order_by('-id')[:top_n]
    )
    return render(req, 'core/index.html', {'top_profiles': profiles})

def contact_view(req):
    return render(req, 'core/contacts.html')
def about_view(req):
    return render(req, 'core/about.html')
