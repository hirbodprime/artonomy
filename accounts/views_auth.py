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
    print("👉 Entered email_verify_start view")  # DEBUG

    if request.user.email_verified:
        print("✅ User already verified")
        messages.info(request, _("Your email is already verified."))
        return redirect("profile_view", request.user.username)

    if request.method == "POST":
        print("📩 POST received for email verification")
        form = EmailVerifyStartForm(request.POST, user=request.user)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            print(f"✔️ Form valid, target email = {email}")

            otp = EmailOTP.create_code(
                request.user, email, EmailOTP.Purpose.VERIFY_EMAIL, ttl_minutes=15
            )
            print(f"🔑 OTP generated: {otp.code}")

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
                print("📤 Email sent successfully")
            except Exception as e:
                print(f"❌ Email sending failed: {e}")

            request.session["verify_email"] = email
            messages.success(request, _("Code sent to your email."))
            return redirect("email_verify_confirm")
        else:
            print("❌ Form invalid")
    else:
        print("📥 GET request, showing form")
        form = EmailVerifyStartForm(user=request.user)

    return render(request, "accounts/email_verify_start.html", {"form": form})


@login_required
def email_verify_confirm(request):
    print("👉 Entered email_verify_confirm view")  # DEBUG
    email = request.session.get("verify_email") or request.user.email
    print(f"🔎 Using email: {email}")

    if request.method == "POST":
        print("📩 POST received for verification confirm")
        form = EmailVerifyCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()
            print(f"✔️ Code entered by user: {code}")

            otp = (
                EmailOTP.objects
                .filter(user=request.user, email__iexact=email, purpose=EmailOTP.Purpose.VERIFY_EMAIL)
                .order_by("-created_at")
                .first()
            )
            if not otp:
                print("❌ No OTP found")
                messages.error(request, _("No code found. Please request a new one."))
                return redirect("email_verify_start")

            print(f"🔑 OTP found: {otp.code}, attempts={otp.attempts}, used={otp.is_used}")
            otp.attempts += 1
            otp.save(update_fields=["attempts"])

            if otp.is_valid(code):
                print("✅ OTP valid")
                otp.is_used = True
                otp.save(update_fields=["is_used"])
                request.user.email_verified = True
                request.user.save(update_fields=["email_verified"])
                messages.success(request, _("Your email has been verified ✅"))
                request.session.pop("verify_email", None)
                return redirect("profile_view", request.user.username)
            else:
                print("❌ Invalid or expired OTP")
                messages.error(request, _("Invalid or expired code."))
        else:
            print("❌ Form invalid for code confirm")
    else:
        print("📥 GET request, showing confirm form")
        form = EmailVerifyCodeForm()

    return render(request, "accounts/email_verify_confirm.html", {"form": form, "email": email})

# -------- Password reset (OTP) --------

def password_reset_start(request):
    print("👉 Entered password_reset_start view")  # DEBUG
    if request.method == "POST":
        print("📩 POST received for reset start")
        form = PasswordResetStartForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            print(f"✔️ Reset request for email = {email}")

            user = User.objects.filter(email__iexact=email).first()
            if user:
                print(f"👤 User found: {user}")
                otp = EmailOTP.create_code(user, email, EmailOTP.Purpose.RESET_PASSWORD, ttl_minutes=15)
                print(f"🔑 Reset OTP generated: {otp.code}")

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
                    print("📤 Reset email sent successfully")
                except Exception as e:
                    print(f"❌ Reset email sending failed: {e}")
            else:
                print("⚠️ No user found with that email (still showing success)")

            request.session["reset_email"] = email
            messages.success(request, _("If that email exists, we sent a code."))
            return redirect("password_reset_confirm")
        else:
            print("❌ Reset form invalid")
    else:
        print("📥 GET request, showing reset form")
        form = PasswordResetStartForm()

    return render(request, "accounts/password_reset_start.html", {"form": form})


def password_reset_confirm(request):
    print("👉 Entered password_reset_confirm view")  # DEBUG
    email = request.session.get("reset_email")
    print(f"🔎 Email from session: {email}")
    if not email:
        print("❌ No reset email in session, redirecting")
        return redirect("password_reset_start")

    if request.method == "POST":
        print("📩 POST received for reset confirm")
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            code  = form.cleaned_data["code"].strip()
            print(f"✔️ Reset confirm: email={email}, code={code}")

            user  = User.objects.filter(email__iexact=email).first()
            if not user:
                print("❌ No user for this email")
                messages.error(request, _("Invalid code or email."))
                return redirect("password_reset_start")

            otp = (
                EmailOTP.objects
                .filter(user=user, email__iexact=email, purpose=EmailOTP.Purpose.RESET_PASSWORD)
                .order_by("-created_at")
                .first()
            )
            if not otp:
                print("❌ No OTP found for reset")
                messages.error(request, _("No code found. Please request a new one."))
                return redirect("password_reset_start")

            print(f"🔑 OTP found: {otp.code}, attempts={otp.attempts}, used={otp.is_used}")
            otp.attempts += 1
            otp.save(update_fields=["attempts"])

            if otp.is_valid(code):
                print("✅ Reset OTP valid, setting new password")
                user.set_password(form.cleaned_data["new_password1"])
                user.save(update_fields=["password"])
                otp.is_used = True
                otp.save(update_fields=["is_used"])
                messages.success(request, _("Password changed successfully. You can log in now."))
                request.session.pop("reset_email", None)
                return redirect("landing")  # or your login page
            else:
                print("❌ Invalid or expired reset OTP")
                messages.error(request, _("Invalid or expired code."))
        else:
            print("❌ Reset confirm form invalid")
    else:
        print("📥 GET request, showing reset confirm form")
        form = PasswordResetConfirmForm(initial={"email": email})

    return render(request, "accounts/password_reset_confirm.html", {"form": form, "email": email})
