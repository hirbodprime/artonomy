from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from .models import Profile, ProfileCounter, Skill, SocialLink, ClientLogo, Testimonial, BUSINESS_KINDS
from artists.models import Category, Subcategory
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from django.utils.translation import gettext_lazy as _
import re


User = get_user_model()

class RoleCategoryForm(forms.ModelForm):
    category      = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label="دسته هنری",
    )
    subcategory   = forms.ModelChoiceField(
        queryset=Subcategory.objects.none(),
        required=False,
        label="زیرشاخه",
    )
    business_kind = forms.ChoiceField(
        choices=(("", "— انتخاب کنید —"),) + BUSINESS_KINDS,
        required=False,
        label="نوع کسب‌وکار",
    )
    custom_subcategory = forms.CharField(
        required=False,
        max_length=120,
        label="زیرشاخه دلخواه",
        widget=forms.TextInput(attrs={
            "placeholder": "مثلاً: تصویرسازی کتاب کودک",
        }),
    )

    class Meta:
        model  = Profile
        fields = ("category", "subcategory", "business_kind", "custom_subcategory")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cat = None

        # اگر فرم POST شده، دسته را از data بخوان
        if self.is_bound:
            try:
                cat_id = int(self.data.get(self.add_prefix("category")) or 0)
                if cat_id:
                    cat = Category.objects.filter(id=cat_id).first()
            except (TypeError, ValueError):
                pass

        # اگر هنوز cat پیدا نشده، از instance بگیر
        if not cat and self.instance and self.instance.category_id:
            cat = self.instance.category

        # کوئری‌ست زیرشاخه‌ها
        if cat:
            self.fields["subcategory"].queryset = Subcategory.objects.filter(category=cat)
        else:
            self.fields["subcategory"].queryset = Subcategory.objects.none()

        if self.instance and self.instance.pk:
            self.fields["custom_subcategory"].initial = self.instance.custom_subcategory

    def clean(self):
        cleaned = super().clean()
        role   = self.instance.role  # نقش از خود پروفایل
        cat    = cleaned.get("category")
        sub    = cleaned.get("subcategory")
        biz    = cleaned.get("business_kind")
        custom = (cleaned.get("custom_subcategory") or "").strip()

        if role == "artist":
            if not cat:
                self.add_error("category", "دسته هنری را انتخاب کنید.")
            if not sub:
                self.add_error("subcategory", "زیرشاخه مرتبط را انتخاب کنید.")
            if cat and sub and sub.category_id != cat.id:
                self.add_error("subcategory", "این زیرشاخه متعلق به دسته انتخاب‌شده نیست.")

            if sub:
                name = (sub.name or "").strip()
                slug = (sub.slug or "").strip().lower()
                is_other = (name == "سایر") or (name.lower() == "other") or (slug == "other")
                if is_other and not custom:
                    self.add_error(
                        "custom_subcategory",
                        "وقتی «سایر» را انتخاب می‌کنید، لطفاً نام زیرشاخه دلخواه را وارد کنید.",
                    )
                elif not is_other:
                    cleaned["custom_subcategory"] = ""

            cleaned["business_kind"] = ""

        elif role == "business":
            if not biz:
                self.add_error("business_kind", "نوع کسب‌وکار را انتخاب کنید.")
            cleaned["category"] = None
            cleaned["subcategory"] = None
            cleaned["custom_subcategory"] = ""

        else:  # normal
            cleaned["category"] = None
            cleaned["subcategory"] = None
            cleaned["business_kind"] = ""
            cleaned["custom_subcategory"] = ""

        return cleaned

    def save(self, commit=True):
        profile = super().save(commit=False)
        if profile.role == "artist" and self.cleaned_data.get("subcategory"):
            profile.category = self.cleaned_data["subcategory"].category
        if commit:
            profile.save()
        return profile

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name")
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "نام"}),
            "last_name": forms.TextInput(attrs={"placeholder": "نام خانوادگی"}),
        }
class ProfileCounterForm(forms.ModelForm):
    class Meta:
        model = ProfileCounter
        fields = ("label", "value", "order")
        widgets = {
            "label": forms.TextInput(attrs={
                "placeholder": "مثلاً: تعداد پروژه‌ها / نمایشگاه‌ها / مشتریان",
            }),
            "value": forms.NumberInput(attrs={
                "placeholder": "مثلاً: ۱۲",
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "مثلاً: ۱",
            }),
        }
class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ("name", "percent", "order")
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "مهارت — مثل عکاسی، طراحی، تدوین..."
            }),
            "percent": forms.NumberInput(attrs={
                "placeholder": "درصد — مثلاً: ۸۰"
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "ترتیب نمایش — مثلاً: ۱"
            }),
        }
class SocialLinkForm(forms.ModelForm):
    class Meta:
        model = SocialLink
        fields = ("title", "url", "order")
        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "نام شبکه اجتماعی — اینستاگرام / تیک‌تاک / پورتفولیو"
            }),
            "url": forms.URLInput(attrs={
                "placeholder": "لینک کامل — مثل: https://instagram.com/user"
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "ترتیب نمایش — مثلاً: ۱"
            }),
        }
class ClientLogoForm(forms.ModelForm):
    class Meta:
        model = ClientLogo
        fields = ("title", "url", "image", "order")
        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "نام مشتری یا برند"
            }),
            "url": forms.URLInput(attrs={
                "placeholder": "لینک مربوطه (اختیاری)"
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "ترتیب نمایش — مثلاً: ۱"
            }),
        }
class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ("person_name", "quote", "source_label", "source_url", "background_image", "order")
        widgets = {
            "person_name": forms.TextInput(attrs={
                "placeholder": "نام فرد — مثلاً: علی احمدی"
            }),
            "quote": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "متن نظر / تجربه مشتری — یک پاراگراف کوتاه"
            }),
            "source_label": forms.TextInput(attrs={
                "placeholder": "منبع — اینستاگرام / سایت / لینکدین"
            }),
            "source_url": forms.URLInput(attrs={
                "placeholder": "لینک منبع (اختیاری)"
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "ترتیب نمایش — مثلاً: ۱"
            }),
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "header_background",
            "header_subtitle",
            "story_subtitle",
            "story_paragraph_1",
            "story_paragraph_2",
            "avatar",  # 🔹 NEW
            "phone_number",     # 🔹 NEW
            "public_email",     # 🔹 NEW
            "contact_note",     # 🔹 NEW
        ]
        widgets = {
            "story_paragraph_1": forms.Textarea(attrs={"rows": 5}),
            "story_paragraph_2": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # use a plain file input (no "Currently / Clear" line)
        self.fields["header_background"].widget = forms.FileInput(
            attrs={"accept": "image/*"}
        )
        # می‌تونی برای آواتار هم accept بزاری اگر خواستی:
        self.fields["avatar"].widget = forms.FileInput(
            attrs={"accept": "image/*"}
        )
        
CounterFormSet = inlineformset_factory(
    Profile, ProfileCounter,
    form=ProfileCounterForm,
    extra=2, can_delete=True
)

SkillFormSet = inlineformset_factory(
    Profile, Skill,
    form=SkillForm,
    extra=2, can_delete=True
)

SocialLinkFormSet = inlineformset_factory(
    Profile, SocialLink,
    form=SocialLinkForm,
    extra=2, can_delete=True
)

ClientLogoFormSet = inlineformset_factory(
    Profile, ClientLogo,
    form=ClientLogoForm,
    extra=2, can_delete=True
)

TestimonialFormSet = inlineformset_factory(
    Profile, Testimonial,
    form=TestimonialForm,
    extra=1, can_delete=True
)


class LoginForm(forms.Form):
    username_or_email = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
    remember = forms.BooleanField(required=False)

    def clean(self):
        cleaned = super().clean()
        ident = cleaned.get("username_or_email")
        password = cleaned.get("password")
        user = None

        if ident and password:
            # تلاش با username
            user = authenticate(username=ident, password=password)
            if not user:
                # اگر نشد، با ایمیل پیدا کن و دوباره authenticate
                try:
                    u = User.objects.get(email__iexact=ident)
                    user = authenticate(username=u.username, password=password)
                except User.DoesNotExist:
                    user = None

        if not user:
            raise ValidationError("نام کاربری/ایمیل یا گذرواژه نادرست است.")
        if not user.is_active:
            raise ValidationError("حساب کاربری غیرفعال است.")
        cleaned["user"] = user
        return cleaned


class SignupForm(forms.Form):
    ROLE_CHOICES = (
        ("artist",   "هنرمند"),
        ("business", "صاحب کسب و کار(گالری،استودیو،استور)"),
        ("normal",   "مخاظب هنر"),
    )

    first_name = forms.CharField(max_length=150)
    last_name  = forms.CharField(max_length=150)
    username   = forms.CharField(max_length=150)
    email      = forms.EmailField()
    role       = forms.ChoiceField(choices=ROLE_CHOICES, initial="artist")
    password   = forms.CharField(min_length=8, widget=forms.PasswordInput)
    password2  = forms.CharField(min_length=8, widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        # فقط حروف کوچک
        if username.lower() != username:
            raise ValidationError("لطفاً فقط از حروف کوچک انگلیسی برای نام کاربری استفاده کنید.")

        # الگوی مجاز: حروف کوچک، عدد، نقطه، زیرخط
        if not re.fullmatch(r"[a-z0-9._]{3,30}", username):
            raise ValidationError(
                "نام کاربری فقط می‌تواند شامل حروف کوچک انگلیسی، اعداد، نقطه و زیرخط باشد (۳ تا ۳۰ کاراکتر)."
            )

        # یکتا بودن
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("این نام کاربری قبلاً ثبت شده است.")

        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password2"):
            raise ValidationError("تکرار گذرواژه با گذرواژه یکسان نیست.")
        return cleaned

    def create_user(self):
        from .models import Profile  # already imported at top but safe

        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )

        # پروفایل اتوماتیک با سیگنال ساخته می‌شود؛ اینجا نقش را ست می‌کنیم
        profile, created = Profile.objects.get_or_create(user=user)
        profile.role = data.get("role", "normal")
        profile.save(update_fields=["role"])

        return user



from django.forms import inlineformset_factory
from marketplace.models import Product, Service, ArtPost

# ... بقیه فایل بدون تغییر ...
from marketplace.forms import ProductForm, ServiceForm, ArtPostForm


ProductFormSet = inlineformset_factory(
    Profile, Product,
    form=ProductForm,
    extra=1,
    can_delete=True,
)

ServiceFormSet = inlineformset_factory(
    Profile, Service,
    form=ServiceForm,
    extra=1,
    can_delete=True,
)

ArtPostFormSet = inlineformset_factory(
    Profile, ArtPost,
    form=ArtPostForm,
    extra=1,
    can_delete=True,
)



class PasswordChangeForm(DjangoPasswordChangeForm):
    """
    فرم فارسی‌شده‌ی تغییر رمز عبور برای داشبورد.
    تمام پیام‌های خطا (از جمله پیام‌های داخلی Django) اینجا ترجمه می‌شوند.
    """

    error_messages = {
        "password_incorrect": _(
            "رمز عبور فعلی شما اشتباه است. لطفاً دوباره تلاش کنید."
        ),
        "password_mismatch": _(
            "رمز عبورهای جدید با هم مطابقت ندارند."
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # برچسب‌ها
        self.fields["old_password"].label = "رمز عبور فعلی"
        self.fields["new_password1"].label = "رمز عبور جدید"
        self.fields["new_password2"].label = "تکرار رمز عبور جدید"

        # placeholder و کلاس (با استایل فعلی‌ات مچ می‌شود)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("placeholder", field.label)

        # راهنمایی (help_text) برای رمز جدید
        self.fields["new_password1"].help_text = _(
            "رمز عبور باید حداقل ۸ کاراکتر باشد، خیلی ساده نباشد و فقط از اعداد تشکیل نشده باشد."
        )

    def _post_clean(self):
        """
        بعد از اعتبارسنجی پیش‌فرض Django، پیام‌های خطا را فارسی می‌کنیم.
        """
        super()._post_clean()

        if "new_password2" in self._errors:
            translated = []
            for msg in self._errors["new_password2"]:
                text = str(msg).lower().strip()

                if "too short" in text:
                    translated.append("رمز عبور خیلی کوتاه است. باید حداقل ۸ کاراکتر باشد.")
                elif "too common" in text:
                    translated.append("این رمز عبور خیلی رایج است. لطفاً رمز قوی‌تری انتخاب کنید.")
                elif "entirely numeric" in text:
                    translated.append("رمز عبور نباید فقط از اعداد تشکیل شده باشد.")
                elif "similar to your" in text or "too similar" in text:
                    # حالت‌های دقیق‌تر
                    if "username" in text:
                        translated.append("رمز عبور جدید بیش از حد شبیه نام کاربری شماست.")
                    elif "first name" in text:
                        translated.append("رمز عبور جدید بیش از حد شبیه نام شماست.")
                    elif "last name" in text:
                        translated.append("رمز عبور جدید بیش از حد شبیه نام خانوادگی شماست.")
                    elif "email" in text:
                        translated.append("رمز عبور جدید بیش از حد شبیه ایمیل شماست.")
                    else:
                        translated.append("رمز عبور جدید بیش از حد شبیه اطلاعات حساب شماست.")
                else:
                    translated.append("رمز عبور قابل قبول نیست. لطفاً شرایط امنیتی را رعایت کنید.")

            self._errors["new_password2"] = self.error_class(translated)
