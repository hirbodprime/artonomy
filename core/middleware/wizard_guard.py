# core/middleware/wizard_guard.py

from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.utils.deprecation import MiddlewareMixin

WTYPE = "post_wizard_type"
WPOST = "post_wizard_id"

class WizardGuardMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        # If no draft has been created yet => user is still in early steps (start/media/text).
        # Let them leave freely.
        draft_id = request.session.get(WPOST)
        if not draft_id:
            return None

        # From here on, a draft exists → enforce the lock
        # Allowlist: wizard routes + essentials
        allowed_names = {
            "post_new_start",
            "post_new_media",
            "post_new_text",
            "post_new_category",
            "post_new_review",
            "post_new_reset",
            "logout", "landing", "signup",  # adjust to your actual names if different
        }

        path = request.path
        if path.startswith("/static/") or path.startswith("/media/") or path.startswith("/admin/"):
            return None

        try:
            name = resolve(path).url_name
        except Exception:
            name = None

        if name in allowed_names:
            return None

        # Decide the correct step to push them back to
        from posts.models import Post
        draft = Post.objects.filter(pk=draft_id, author=request.user).first()
        if not draft:
            # Draft missing (deleted?) — clear lock and allow
            request.session.pop(WPOST, None)
            request.session.pop(WTYPE, None)
            return None

        if draft.categories.count() == 0:
            target_name = "post_new_category"
        else:
            target_name = "post_new_review"

        return redirect(reverse(target_name))
