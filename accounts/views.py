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




@login_required
def profile_dashboard_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    # ✅ 1) Make sure every user has a 1-week trial by default
    profile.ensure_trial_default(save=True)

    tab = request.GET.get("tab", "profile")
    valid = {
        "profile","counters","skills","testimonials","social",
        "clients","role","products","services","content","security"
    }

    if tab not in valid:
        tab = "profile"

    # ✅ 2) Gate premium tabs (products/services) for expired trial / no subscription
    # This protects both GET & POST. If they try to access directly, redirect them.
    if tab in {"products", "services"} and not profile.can_use_premium:
        messages.warning(
            request,
            "دوره آزمایشی شما تمام شده است. برای استفاده از «محصولات» و «خدمات» "
            "اشتراک ماهانه (۱ دلار) را فعال کنید."
        )
        return redirect(f"{request.path}?tab=role")

    # --- helper to construct your original forms/formsets (unchanged) ---
    def build_forms(bound: bool):
        kw = (request.POST, request.FILES) if bound else (None, None)
        forms = dict(
            user_form = UserForm(*(kw if bound else ()), instance=request.user),
            form      = ProfileForm(*(kw if bound else ()), instance=profile),

            fs_counters = CounterFormSet(
                *(((request.POST,)) if bound and tab=="counters" else ()),
                instance=profile, prefix="cnt"
            ),
            fs_skills   = SkillFormSet(
                *(((request.POST,)) if bound and tab=="skills" else ()),
                instance=profile, prefix="sk"
            ),
            fs_social   = SocialLinkFormSet(
                *(((request.POST,)) if bound and tab=="social" else ()),
                instance=profile, prefix="soc"
            ),
            fs_clients  = ClientLogoFormSet(
                *(((request.POST, request.FILES)) if bound and tab=="clients" else ()),
                instance=profile, prefix="cl"
            ),
            fs_tests    = TestimonialFormSet(
                *(((request.POST, request.FILES)) if bound and tab=="testimonials" else ()),
                instance=profile, prefix="ts"
            ),
            role_form   = RoleCategoryForm(
                *(kw if bound and tab=="role" else (None, None)),
                instance=profile
            ),

            # parent formsets (profile -> products / services)
            fs_products = ProductFormSet(
                *(((request.POST, request.FILES)) if bound and tab=="products" else ()),
                instance=profile, prefix="prd"
            ),
            fs_services = ServiceFormSet(
                *(((request.POST, request.FILES)) if bound and tab=="services" else ()),
                instance=profile, prefix="srv"
            ),
            fs_artposts = ArtPostFormSet(
                *(((request.POST, request.FILES)) if bound and tab=="content" else ()),
                instance=profile, prefix="art"
            ),
        )
        if tab == "security":
            if bound:
                forms["pwd_form"] = PasswordChangeForm(user=request.user, data=request.POST)
            else:
                forms["pwd_form"] = PasswordChangeForm(user=request.user)
        else:
            forms["pwd_form"] = None

        return forms

    # ====== POST ======
    if request.method == "POST":
        f = build_forms(True)
        ok = False

        # اینها را اینجا تعریف می‌کنیم تا در صورت نیاز در ctx بگذاریم
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
                if ok: f["fs_counters"].save()

            elif tab == "skills":
                ok = f["fs_skills"].is_valid()
                if ok: f["fs_skills"].save()

            elif tab == "social":
                ok = f["fs_social"].is_valid()
                if ok: f["fs_social"].save()

            elif tab == "clients":
                ok = f["fs_clients"].is_valid()
                if ok: f["fs_clients"].save()

            elif tab == "testimonials":
                ok = f["fs_tests"].is_valid()
                if ok: f["fs_tests"].save()

            elif tab == "role":
                ok = f["role_form"].is_valid()
                if ok: f["role_form"].save()

            # ---------- PRODUCTS: save parent rows, then per-item gallery ----------
            elif tab == "products":
                ok = f["fs_products"].is_valid()
                product_image_fsets = {}  # بایندهای همین درخواست را نگه می‌داریم

                if ok:
                    # 1) والدها را ذخیره کن (محصول‌های جدید PK می‌گیرند)
                    f["fs_products"].save()

                    # 2) فرم‌ست گالری برای هر محصول (بایند و ذخیره)
                    products_qs = Product.objects.filter(profile=profile)
                    for p in products_qs:
                        imgs_fs = ProductImageFormSet(
                            request.POST, request.FILES,
                            instance=p,
                            prefix=f"prdimg-{p.pk}",
                        )
                        product_image_fsets[p.pk] = imgs_fs
                        if imgs_fs.is_valid():
                            imgs_fs.save()
                        else:
                            ok = False
                else:
                    # اگر والد نامعتبر بود، باز هم فرم‌ست‌های تصاویر را بایند کن تا ورودی از دست نرود
                    products_qs = Product.objects.filter(profile=profile)
                    for p in products_qs:
                        imgs_fs = ProductImageFormSet(
                            request.POST, request.FILES,
                            instance=p,
                            prefix=f"prdimg-{p.pk}",
                        )
                        product_image_fsets[p.pk] = imgs_fs

            # ---------- SERVICES: save parent rows, then per-item gallery ----------
            elif tab == "services":
                ok = f["fs_services"].is_valid()
                service_image_fsets = {}  # مشابه بالا

                if ok:
                    f["fs_services"].save()

                    services_qs = Service.objects.filter(profile=profile)
                    for s in services_qs:
                        imgs_fs = ServiceImageFormSet(
                            request.POST, request.FILES,
                            instance=s,
                            prefix=f"srvimg-{s.pk}",
                        )
                        service_image_fsets[s.pk] = imgs_fs
                        if imgs_fs.is_valid():
                            imgs_fs.save()
                        else:
                            ok = False
                else:
                    services_qs = Service.objects.filter(profile=profile)
                    for s in services_qs:
                        imgs_fs = ServiceImageFormSet(
                            request.POST, request.FILES,
                            instance=s,
                            prefix=f"srvimg-{s.pk}",
                        )
                        service_image_fsets[s.pk] = imgs_fs
            elif tab == "content":
                ok = f["fs_artposts"].is_valid()
                artpost_image_fsets = {}

                if ok:
                    f["fs_artposts"].save()

                    posts_qs = ArtPost.objects.filter(profile=profile)
                    for post in posts_qs:
                        imgs_fs = ArtPostImageFormSet(
                            request.POST, request.FILES,
                            instance=post,
                            prefix=f"artimg-{post.pk}",   # ✅ prefix دقیقا همین
                        )
                        artpost_image_fsets[post.pk] = imgs_fs
                        if imgs_fs.is_valid():
                            imgs_fs.save()
                        else:
                            ok = False
                else:
                    posts_qs = ArtPost.objects.filter(profile=profile)
                    for post in posts_qs:
                        imgs_fs = ArtPostImageFormSet(
                            request.POST, request.FILES,
                            instance=post,
                            prefix=f"artimg-{post.pk}",
                        )
                        artpost_image_fsets[post.pk] = imgs_fs
            elif tab == "security":
                pwd_form = f["pwd_form"]
                ok = pwd_form is not None and pwd_form.is_valid()
                if ok:
                    user = pwd_form.save()              # رمز جدید ست می‌کند
                    update_session_auth_hash(request, user)  # لاگین را نگه می‌دارد
                    messages.success(request, "رمز عبور شما با موفقیت تغییر کرد.")


        # ✅ refresh cached percent after any change
        profile.refresh_completion(save=True)

        if ok:
            if tab != "security":
                messages.success(request, "تغییرات ذخیره شد.")
            return redirect(f"{request.path}?tab={tab}")

        else:
            messages.error(request, "لطفاً خطاها را بررسی کنید.")
            # برای رندر مجدد با خطاها، فرم‌ها + فرم‌ست‌های بایندشده را بفرست
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

    # ✅ also refresh on GET (cheap and safe)
    profile.refresh_completion(save=True)

    # Build subcategory map (unchanged)
    try:
        from artists.models import Category, Subcategory
        subcat_map = {
            c.id: list(Subcategory.objects.filter(category=c).values("id", "name"))
            for c in Category.objects.all()
        }
    except Exception:
        subcat_map = {}

    # ----- Attach UNBOUND gallery formsets for GET (and for POST when ok==False) -----
    if request.method == "GET":
        if tab == "products":
            product_image_fsets = {
                p.pk: ProductImageFormSet(instance=p, prefix=f"prdimg-{p.pk}")
                for p in Product.objects.filter(profile=profile)
            }
            ctx["product_image_fsets"] = product_image_fsets

        if tab == "services":
            service_image_fsets = {
                s.pk: ServiceImageFormSet(instance=s, prefix=f"srvimg-{s.pk}")
                for s in Service.objects.filter(profile=profile)
            }
            ctx["service_image_fsets"] = service_image_fsets
        if tab == "content":
            artpost_image_fsets = {
                post.pk: ArtPostImageFormSet(instance=post, prefix=f"artimg-{post.pk}")
                for post in ArtPost.objects.filter(profile=profile)
            }
            ctx["artpost_image_fsets"] = artpost_image_fsets

    # وقتی POST انجام شده و ok==False بود، بالاتر already ست شده بود؛
    # اگر POST بود و ok==True، ریدایرکت کردیم و به اینجا نمی‌رسیم.

    ctx.update(dict(
        profile=profile,
        active_tab=tab,
        subcat_map=subcat_map,
        completion=profile.completion,

        # ✅ NEW: subscription / trial info for the template
        can_use_premium=profile.can_use_premium,
        is_trial=profile.in_trial,
        has_subscription=profile.has_subscription,
        subscription_status_label=profile.subscription_status_label,
        premium_days_left=profile.premium_days_left,
    ))
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

            # remember me
            remember = form.cleaned_data.get("remember")
            if remember:
                request.session.set_expiry(1209600)  # 14 روز
            else:
                request.session.set_expiry(0)        # تا بستن مرورگر

            next_url = request.GET.get("next") or "/"
            return redirect(next_url)
    else:
        form = LoginForm()

    # همان auth.html را رندر می‌کنیم؛ تب «ورود» باز است
    return render(request, "accounts/auth.html", {
        "active_tab": "login",
        "login_form": form,
        "signup_form": SignupForm(),  # برای نمایش همزمان
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

    # همان auth.html اما تب «ثبت‌نام» باز باشد
    return render(request, "accounts/auth.html", {
        "active_tab": "signup",
        "login_form": LoginForm(),
        "signup_form": form,
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

    return render(request, "accounts/profile.html", {
        "profile": profile,
        "products": products,
        "services": services,

        "skills": skills,
        "testimonials": testimonials,
        "social_links": social_links,
        "counters": counters,
        "client_logos": client_logos,
        "completion": profile.completion,
    })



