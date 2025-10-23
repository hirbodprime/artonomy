# portfolio/context_processors.py
from .models import UserPortfolio

def portfolio_bar(request):
    if not request.user.is_authenticated:
        return {}
    sites = UserPortfolio.objects.filter(user=request.user).select_related("theme")
    return {
        "my_portfolio_sites": sites,
        "my_active_portfolio": next((s for s in sites if s.is_primary), None),
    }
