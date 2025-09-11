
from django.urls import path
from . import views as v
from . import views_auth

urlpatterns = [
    path("signup/", v.signup_view, name="signup"),
    path("choose-role/", v.choose_role, name="choose_role"),
    path("choose-categories/", v.choose_categories, name="choose_categories"),
    path("u/<str:username>/", v.profile_view, name="profile_view"),
    path("logout/", v.logout_view, name="logout"),
    # Edit profile hub
    path("settings/", v.settings_profile_start, name="settings_profile"),
    path("<str:username>/suggested/", v.profile_suggested_posts, name="profile_suggested"),

    # Personal info wizard
    path("settings/personal/<int:step>/", v.settings_personal_wizard, name="settings_personal"),
    path("settings/personal/", v.settings_personal_wizard, {"step": 1}, name="settings_personal_start"),

    # Portfolio wizard
    path("settings/portfolio/<int:step>/", v.settings_portfolio_wizard, name="settings_portfolio"),
    path("settings/portfolio/", v.settings_portfolio_wizard, {"step": 1}, name="settings_portfolio_start"),
    path("set-language/", v.set_user_language, name="account_set_language"),
    path("auth/email/", views_auth.email_verify_start, name="email_verify_start"),
    path("auth/email/confirm/", views_auth.email_verify_confirm, name="email_verify_confirm"),

    # Password reset (OTP)
    path("auth/password/forgot/", views_auth.password_reset_start, name="password_reset_start"),
    path("auth/password/reset/",  views_auth.password_reset_confirm, name="password_reset_confirm"),

]



