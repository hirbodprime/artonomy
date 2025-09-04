
from django.urls import path
from . import views as v

urlpatterns = [
    path("signup/", v.signup_view, name="signup"),
    path("choose-role/", v.choose_role, name="choose_role"),
    path("choose-categories/", v.choose_categories, name="choose_categories"),
    path("u/<str:username>/", v.profile_view, name="profile_view"),
    path("logout/", v.logout_view, name="logout"),
    # Edit profile hub
    path("settings/", v.settings_profile_start, name="settings_profile"),

    # Personal info wizard
    path("settings/personal/<int:step>/", v.settings_personal_wizard, name="settings_personal"),
    path("settings/personal/", v.settings_personal_wizard, {"step": 1}, name="settings_personal_start"),

    # Portfolio wizard
    path("settings/portfolio/<int:step>/", v.settings_portfolio_wizard, name="settings_portfolio"),
    path("settings/portfolio/", v.settings_portfolio_wizard, {"step": 1}, name="settings_portfolio_start"),
]



