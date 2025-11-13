from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model, update_session_auth_hash


from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import Profile
from marketplace.models import Product, Service, ArtPost
from marketplace.forms import ProductImageFormSet, ServiceImageFormSet, ArtPostImageFormSet
from .forms import (
    UserForm, ProfileForm, RoleCategoryForm,
    CounterFormSet, SkillFormSet, SocialLinkFormSet,
    ClientLogoFormSet, TestimonialFormSet,
    ProductFormSet, ServiceFormSet, ArtPostFormSet, LoginForm, SignupForm, PasswordChangeForm
)



User = get_user_model()


def get_featured_artpost():
    """
    Returns the most viewed active ArtPost, newest first on ties.
    """
    return (
        ArtPost.objects
        .filter(is_active=True)
        .order_by("-views", "-updated_at")
        .select_related("profile", "profile__user")
        .first()
    )



@login_required
def profile_dashboard_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    valid = {
        "profile", "counters", "skills", "testimonials", "social",
        "clients", "role", "products", "services", "content",
        "security", "advertisement",      # 👈 جدید
    }

    # 👇 روی POST از hidden استفاده می‌کنیم، روی GET از querystring
    if request.method == "POST":
        tab = request.POST.get("active_tab") or request.GET.get("tab", "profile")
    else:
        tab = request.GET.get("tab", "profile")

    if tab not in valid:
        tab = "profile"
    # 🔒 Normal users (not artist/business) may only access the security tab
    if profile.role not in ("artist", "business"):
        if tab not in ("security", "advertisement"):
            tab = "security"
    # --- helper to construct all forms/formsets ---
    def build_forms(bound: bool):
        kw = (request.POST, request.FILES) if bound else (None, None)

        forms = dict(
            user_form=UserForm(*(kw if bound else ()), instance=request.user),
            form=ProfileForm(*(kw if bound else ()), instance=profile),

            fs_counters=CounterFormSet(
                *(((request.POST,)) if bound and tab == "counters" else ()),
                instance=profile, prefix="cnt"
            ),
            fs_skills=SkillFormSet(
                *(((request.POST,)) if bound and tab == "skills" else ()),
                instance=profile, prefix="sk"
            ),
            fs_social=SocialLinkFormSet(
                *(((request.POST,)) if bound and tab == "social" else ()),
                instance=profile, prefix="soc"
            ),
            fs_clients=ClientLogoFormSet(
                *(((request.POST, request.FILES)) if bound and tab == "clients" else ()),
                instance=profile, prefix="cl"
            ),
            fs_tests=TestimonialFormSet(
                *(((request.POST, request.FILES)) if bound and tab == "testimonials" else ()),
                instance=profile, prefix="ts"
            ),
            role_form=RoleCategoryForm(
                *(kw if bound and tab == "role" else (None, None)),
                instance=profile
            ),

            fs_products=ProductFormSet(
                *(((request.POST, request.FILES)) if bound and tab == "products" else ()),
                instance=profile, prefix="prd"
            ),
            fs_services=ServiceFormSet(
                *(((request.POST, request.FILES)) if bound and tab == "services" else ()),
                instance=profile, prefix="srv"
            ),
            fs_artposts=ArtPostFormSet(
                *(((request.POST, request.FILES)) if bound and tab == "content" else ()),
                instance=profile, prefix="art"
            ),
        )

        # ✅ PasswordChangeForm را همیشه بساز، فقط برای tab=security بایندش کن
        if bound and tab == "security":
            forms["pwd_form"] = PasswordChangeForm(user=request.user, data=request.POST)
        else:
            forms["pwd_form"] = PasswordChangeForm(user=request.user)

        return forms

    # ====== POST ======
    if request.method == "POST":
        f = build_forms(True)
        ok = False

        product_image_fsets = None
        service_image_fsets = None
        artpost_image_fsets = None

        with transaction.atomic():
            if tab == "profile":
                ok = f["user_form"].is_valid() and f["form"].is_valid()
                if ok:
                    f["user_form"].save()
                    f["form"].save()

            elif tab == "counters":
                ok = f["fs_counters"].is_valid()
                if ok:
                    f["fs_counters"].save()

            elif tab == "skills":
                ok = f["fs_skills"].is_valid()
                if ok:
                    f["fs_skills"].save()

            elif tab == "social":
                ok = f["fs_social"].is_valid()
                if ok:
                    f["fs_social"].save()

            elif tab == "clients":
                ok = f["fs_clients"].is_valid()
                if ok:
                    f["fs_clients"].save()

            elif tab == "testimonials":
                ok = f["fs_tests"].is_valid()
                if ok:
                    f["fs_tests"].save()

            elif tab == "role":
                ok = f["role_form"].is_valid()
                if ok:
                    f["role_form"].save()

            # ---------- PRODUCTS ----------
            elif tab == "products":
                if profile.completion < 100:
                    messages.error(request, "برای افزودن یا ویرایش محصولات، ابتدا پروفایل خود را کامل کنید.")
                    return redirect(f"{request.path}?tab=profile")

                ok = f["fs_products"].is_valid()
                product_image_fsets = {}

                if ok:
                    f["fs_products"].save()

                    products_qs = Product.objects.filter(profile=profile)
                    for p in products_qs:
                        prefix = f"prdimg-{p.pk}"
                        mgmt_key = f"{prefix}-TOTAL_FORMS"

                        # فقط اگر این فرم‌ست واقعاً تو POST بوده، bind کن
                        if mgmt_key in request.POST:
                            imgs_fs = ProductImageFormSet(
                                request.POST, request.FILES,
                                instance=p,
                                prefix=prefix,
                            )
                            if imgs_fs.is_valid():
                                imgs_fs.save()
                            else:
                                ok = False
                        else:
                            # برای محصولی که گالری‌اش هنوز ارسال نشده (مثلاً تازه ساخته شده)
                            # فقط یک فرم‌ست خالی برای نمایش در قالب بساز
                            imgs_fs = ProductImageFormSet(
                                instance=p,
                                prefix=prefix,
                            )

                        product_image_fsets[p.pk] = imgs_fs

                else:
                    # اگر خود فرم‌ست محصولات مشکل داشت، فقط برای نمایش، گالری‌ها را unbound بساز
                    products_qs = Product.objects.filter(profile=profile)
                    for p in products_qs:
                        prefix = f"prdimg-{p.pk}"
                        imgs_fs = ProductImageFormSet(
                            instance=p,
                            prefix=prefix,
                        )
                        product_image_fsets[p.pk] = imgs_fs

            # ---------- SERVICES ----------
            elif tab == "services":
                if profile.completion < 100:
                    messages.error(request, "برای افزودن یا ویرایش خدمات ابتدا پروفایل خود را کامل کنید.")
                    return redirect(f"{request.path}?tab=profile")
                ok = f["fs_services"].is_valid()
                service_image_fsets = {}

                if ok:
                    f["fs_services"].save()

                    services_qs = Service.objects.filter(profile=profile)
                    for s in services_qs:
                        prefix = f"srvimg-{s.pk}"
                        mgmt_key = f"{prefix}-TOTAL_FORMS"

                        if mgmt_key in request.POST:
                            imgs_fs = ServiceImageFormSet(
                                request.POST, request.FILES,
                                instance=s,
                                prefix=prefix,
                            )
                            if imgs_fs.is_valid():
                                imgs_fs.save()
                            else:
                                ok = False
                        else:
                            imgs_fs = ServiceImageFormSet(
                                instance=s,
                                prefix=prefix,
                            )

                        service_image_fsets[s.pk] = imgs_fs
                else:
                    services_qs = Service.objects.filter(profile=profile)
                    for s in services_qs:
                        prefix = f"srvimg-{s.pk}"
                        imgs_fs = ServiceImageFormSet(
                            instance=s,
                            prefix=prefix,
                        )
                        service_image_fsets[s.pk] = imgs_fs

            # ---------- CONTENT (ART POSTS) ----------
            elif tab == "content":
                ok = f["fs_artposts"].is_valid()
                artpost_image_fsets = {}

                if ok:
                    f["fs_artposts"].save()

                    posts_qs = ArtPost.objects.filter(profile=profile)
                    for post in posts_qs:
                        prefix = f"artimg-{post.pk}"
                        mgmt_key = f"{prefix}-TOTAL_FORMS"

                        if mgmt_key in request.POST:
                            imgs_fs = ArtPostImageFormSet(
                                request.POST, request.FILES,
                                instance=post,
                                prefix=prefix,
                            )
                            if imgs_fs.is_valid():
                                imgs_fs.save()
                            else:
                                ok = False
                        else:
                            imgs_fs = ArtPostImageFormSet(
                                instance=post,
                                prefix=prefix,
                            )

                        artpost_image_fsets[post.pk] = imgs_fs
                else:
                    posts_qs = ArtPost.objects.filter(profile=profile)
                    for post in posts_qs:
                        prefix = f"artimg-{post.pk}"
                        imgs_fs = ArtPostImageFormSet(
                            instance=post,
                            prefix=prefix,
                        )
                        artpost_image_fsets[post.pk] = imgs_fs

            # ---------- SECURITY (password change) ----------
            elif tab == "security":
                pwd_form = f["pwd_form"]
                ok = pwd_form is not None and pwd_form.is_valid()
                if ok:
                    user = pwd_form.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, "رمز عبور شما با موفقیت تغییر کرد.")

        # ✅ refresh cached percent after any change
        profile.refresh_completion(save=True)

        if ok:
            if tab != "security":
                messages.success(request, "تغییرات ذخیره شد.")
            # NOTE: برای سوییچ تب‌ها از JS استفاده می‌کنیم، ولی بعد submit می‌تونی همین تب را دوباره لود کنی
            return redirect(f"{request.path}?tab={tab}")
        else:
            messages.error(request, "لطفاً خطاها را بررسی کنید.")
            ctx = f
            if tab == "products" and product_image_fsets is not None:
                ctx["product_image_fsets"] = product_image_fsets
            if tab == "services" and service_image_fsets is not None:
                ctx["service_image_fsets"] = service_image_fsets
            if tab == "content" and artpost_image_fsets is not None:
                ctx["artpost_image_fsets"] = artpost_image_fsets

    # ====== GET ======
    else:
        ctx = build_forms(False)

    # ✅ always refresh on GET too
    profile.refresh_completion(save=True)
    missing_items = profile.missing_completion_items()
    # Build subcategory map (هنرمند / زیرشاخه)
    try:
        from artists.models import Category, Subcategory
        subcat_map = {
            c.id: list(
                Subcategory.objects.filter(category=c).values("id", "name")
            )
            for c in Category.objects.all()
        }
    except Exception:
        subcat_map = {}

    # ----- Attach UNBOUND gallery formsets for GET (برای همه تب‌ها) -----
    if request.method == "GET":
        ctx["product_image_fsets"] = {
            p.pk: ProductImageFormSet(instance=p, prefix=f"prdimg-{p.pk}")
            for p in Product.objects.filter(profile=profile)
        }
        ctx["service_image_fsets"] = {
            s.pk: ServiceImageFormSet(instance=s, prefix=f"srvimg-{s.pk}")
            for s in Service.objects.filter(profile=profile)
        }
        ctx["artpost_image_fsets"] = {
            post.pk: ArtPostImageFormSet(instance=post, prefix=f"artimg-{post.pk}")
            for post in ArtPost.objects.filter(profile=profile)
        }

    ctx.update(
        dict(
            profile=profile,
            active_tab=tab,
            subcat_map=subcat_map,
            completion=profile.completion,
            missing_items=missing_items,   # 👈 این
        )
    )
    return render(request, "accounts/dashboard.html", ctx)



@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)

            next_url = request.GET.get("next") or "/"
            return redirect(next_url)
    else:
        form = LoginForm()

    return render(request, "accounts/auth.html", {
        "active_tab": "login",
        "login_form": form,
        "signup_form": SignupForm(),  # برای نمایش همزمان
        "featured_artpost": get_featured_artpost(),  # ⭐️ این خط
    })


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.create_user()
            login(request, user)
            messages.success(request, "ثبت‌نام با موفقیت انجام شد.")
            return redirect("/")
    else:
        form = SignupForm()

    return render(request, "accounts/auth.html", {
        "active_tab": "signup",
        "login_form": LoginForm(),
        "signup_form": form,
        "featured_artpost": get_featured_artpost(),  # ⭐️ این خط
    })



def logout_view(request):
    logout(request)
    return redirect("/")


def public_profile_view(request, username):
    user = get_object_or_404(User, username=username)
    profile = user.profile
    skills = profile.skills.all()
    testimonials = profile.testimonials.all()
    social_links = profile.social_links.all()
    counters = profile.counters.all()
    client_logos = profile.clients.all()
    profile.refresh_completion(save=False)

    products = profile.products.filter(is_active=True)
    services = profile.services.filter(is_active=True)

    has_products = products.exists()
    has_services = services.exists()

    # 🔹 اطلاعات تماس برای نمایش در پاپ‌آپ
    contact_phone = (profile.phone_number or "").strip()
    contact_email = (profile.public_email or "").strip() or user.email

    return render(request, "accounts/profile.html", {
        "profile": profile,
        "products": products,
        "services": services,
        "has_products": has_products,
        "has_services": has_services,

        "skills": skills,
        "testimonials": testimonials,
        "social_links": social_links,
        "counters": counters,
        "client_logos": client_logos,
        "completion": profile.completion,

        "contact_phone": contact_phone,
        "contact_email": contact_email,
    })
