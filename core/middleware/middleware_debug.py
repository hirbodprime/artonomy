# core/middleware_debug.py
from django.utils.deprecation import MiddlewareMixin

class DebugLangMiddleware(MiddlewareMixin):
    def process_request(self, request):
        print("LANG:", getattr(request, "LANGUAGE_CODE", None), request.path)
