# core/middleware/user_language.py
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.shortcuts import redirect
from django.urls import translate_url

LANG_SESSION_KEY = getattr(settings, "LANGUAGE_COOKIE_NAME", "django_language")

def _path_lang(path: str) -> str:
    return "en" if path == "/en" or path.startswith("/en/") else "fa"

class UserLanguageMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, "user", None)
        path = request.path

        # Skip assets/admin quickly
        if any(path.startswith(p) for p in (
            (settings.STATIC_URL or "/static/"),
            (settings.MEDIA_URL or "/media/"),
            "/admin",
            "/i18n/",
        )):
            return None

        # If you sync DB pref -> session, do it here (optional)
        # if user and user.is_authenticated:
        #     pref = getattr(user, "language", settings.LANGUAGE_CODE)
        #     if request.session.get(LANG_SESSION_KEY) != pref:
        #         request.session[LANG_SESSION_KEY] = pref

        # Only normalize URL when needed (GET requests)
        if request.method == "GET":
            # Choose your desired language source:
            # 1) user pref, else
            # 2) session cookie, else
            # 3) project default
            if user and user.is_authenticated and hasattr(user, "language"):
                desired = user.language
            else:
                desired = request.session.get(LANG_SESSION_KEY, settings.LANGUAGE_CODE)

            current = _path_lang(path)
            if current != desired:
                target = translate_url(request.get_full_path(), desired)

                # 🚫 Guard: don’t redirect if target equals current
                if target == request.get_full_path():
                    return None

                return redirect(target)

        return None
