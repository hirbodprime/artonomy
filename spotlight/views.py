from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from spotlight.utils import activate_spotlight

@login_required
def activate_spotlight_view(request):
    profile = request.user.profile

    success, msg = activate_spotlight(profile)
    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)

    return redirect("/dashboard?tab=spotlight")
