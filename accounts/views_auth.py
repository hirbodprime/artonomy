from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as _

from .models import EmailOTP
from .forms import (
    EmailVerifyStartForm, EmailVerifyCodeForm,
    PasswordResetStartForm, PasswordResetConfirmForm
)

User = get_user_model()

BRAND_PURPLE = "#570080"
BRAND_GREEN  = "#11C865"

# -------- Email verification (after signup) --------

@login_required
def email_verify_start(request):
    if request.user.email_verified:
        messages.info(request, _("Your email is already verified."))
        return redirect("profile_view", request.user.username)

    if request.method == "POST":
        form = EmailVerifyStartForm(request.POST, user=request.user)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()

            otp = EmailOTP.create_code(
                request.user, email, EmailOTP.Purpose.VERIFY_EMAIL, ttl_minutes=15
            )

            try:
                send_mail(
                    subject=_("Your verification code"),
                    message=_("Your Artonomy verification code is: {code}\nThis code expires in 15 minutes.").format(code=otp.code),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
                    recipient_list=[email],
                    html_message=(
                        f"<div style='font-family:Inter,Segoe UI,Roboto,Arial,sans-serif'>"
                        f"<h2 style='color:{BRAND_PURPLE};margin:0 0 8px'>{_('Verify your email')}</h2>"
                        f"<p style='margin:0 0 12px'>{_('Use this code within 15 minutes')}:</p>"
                        f"<div style='font-size:28px;font-weight:800;letter-spacing:6px;"
                        f"padding:12px 16px;border:2px dashed {BRAND_GREEN};display:inline-block;color:{BRAND_GREEN}'>{otp.code}</div>"
                        f"</div>"
                    ),
                )
            except Exception:
                pass

            request.session["verify_email"] = email
            messages.success(request, _("Code sent to your email."))
            return redirect("email_verify_confirm")
    else:
        form = EmailVerifyStartForm(user=request.user)

    return render(request, "accounts/email_verify_start.html", {"form": form})


@login_required
def email_verify_confirm(request):
    email = request.session.get("verify_email") or request.user.email

    if request.method == "POST":
        form = EmailVerifyCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()

            otp = (
                EmailOTP.objects
                .filter(user=request.user, email__iexact=email, purpose=EmailOTP.Purpose.VERIFY_EMAIL)
                .order_by("-created_at")
                .first()
            )
            if not otp:
                messages.error(request, _("No code found. Please request a new one."))
                return redirect("email_verify_start")

            otp.attempts += 1
            otp.save(update_fields=["attempts"])

            if otp.is_valid(code):
                otp.is_used = True
                otp.save(update_fields=["is_used"])
                request.user.email_verified = True
                request.user.save(update_fields=["email_verified"])
                messages.success(request, _("Your email has been verified ✅"))
                request.session.pop("verify_email", None)
                return redirect("profile_view", request.user.username)
            else:
                messages.error(request, _("Invalid or expired code."))
    else:
        form = EmailVerifyCodeForm()

    return render(request, "accounts/email_verify_confirm.html", {"form": form, "email": email})

# -------- Password reset (OTP) --------

def password_reset_start(request):
    if request.method == "POST":
        form = PasswordResetStartForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()

            user = User.objects.filter(email__iexact=email).first()
            if user:
                otp = EmailOTP.create_code(user, email, EmailOTP.Purpose.RESET_PASSWORD, ttl_minutes=15)

                try:
                    send_mail(
                        subject=_("Your password reset code"),
                        message=_("Your Artonomy reset code is: {code}\nThis code expires in 15 minutes.").format(code=otp.code),
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
                        recipient_list=[email],
                        html_message=(
                            f"<div style='font-family:Inter,Segoe UI,Roboto,Arial,sans-serif'>"
                            f"<h2 style='color:{BRAND_PURPLE};margin:0 0 8px'>{_('Reset your password')}</h2>"
                            f"<p style='margin:0 0 12px'>{_('Use this code within 15 minutes')}:</p>"
                            f"<div style='font-size:28px;font-weight:800;letter-spacing:6px;"
                            f"padding:12px 16px;border:2px dashed {BRAND_GREEN};display:inline-block;color:{BRAND_GREEN}'>{otp.code}</div>"
                            f"</div>"
                        ),
                    )
                except Exception:
                    pass

            request.session["reset_email"] = email
            messages.success(request, _("If that email exists, we sent a code."))
            return redirect("password_reset_confirm")
    else:
        form = PasswordResetStartForm()

    return render(request, "accounts/password_reset_start.html", {"form": form})


def password_reset_confirm(request):
    email = request.session.get("reset_email")
    if not email:
        return redirect("password_reset_start")

    if request.method == "POST":
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            code  = form.cleaned_data["code"].strip()

            user  = User.objects.filter(email__iexact=email).first()
            if not user:
                messages.error(request, _("Invalid code or email."))
                return redirect("password_reset_start")

            otp = (
                EmailOTP.objects
                .filter(user=user, email__iexact=email, purpose=EmailOTP.Purpose.RESET_PASSWORD)
                .order_by("-created_at")
                .first()
            )
            if not otp:
                messages.error(request, _("No code found. Please request a new one."))
                return redirect("password_reset_start")

            otp.attempts += 1
            otp.save(update_fields=["attempts"])

            if otp.is_valid(code):
                user.set_password(form.cleaned_data["new_password1"])
                user.save(update_fields=["password"])
                otp.is_used = True
                otp.save(update_fields=["is_used"])
                messages.success(request, _("Password changed successfully. You can log in now."))
                request.session.pop("reset_email", None)
                return redirect("landing")  # or your login page
            else:
                messages.error(request, _("Invalid or expired code."))
    else:
        form = PasswordResetConfirmForm(initial={"email": email})

    return render(request, "accounts/password_reset_confirm.html", {"form": form, "email": email})
