# core/middleware.py
import uuid
from .models import Visit

EXCLUDE_PREFIXES = ("/admin/", "/static/", "/media/")

def get_client_ip(request):
    # اگر پشت Caddy / proxy هستی معمولاً این کار می‌کند
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # ممکن است چند IP باشد → اولین را بردار
        ip = xff.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip

class VisitTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # skip admin/static/media
        if any(request.path.startswith(p) for p in EXCLUDE_PREFIXES):
            return response

        try:
            visitor_id = request.COOKIES.get("visitor_id")
            if not visitor_id:
                visitor_id = uuid.uuid4().hex
                response.set_cookie(
                    "visitor_id",
                    visitor_id,
                    max_age=60 * 60 * 24 * 365,  # 1 سال
                    samesite="Lax",
                )

            Visit.objects.create(
                visitor_id=visitor_id,
                path=request.path,
                referrer=request.META.get("HTTP_REFERER", "")[:500],
                utm_source=request.GET.get("utm_source", "")[:100],
                utm_medium=request.GET.get("utm_medium", "")[:100],
                utm_campaign=request.GET.get("utm_campaign", "")[:100],
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
                user=request.user if request.user.is_authenticated else None,
            )
        except Exception:
            # اگر چیزی خراب شد، نذار سایت بخوابه
            pass

        return response
