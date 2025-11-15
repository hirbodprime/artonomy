# marketplace/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import Product, ProductImage, Service, ServiceImage, ArtPost, ArtPostImage

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "title", "description", "price_type", "price_amount", "currency",
            "quantity", "condition", "is_active"
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "نام محصول — مثل: تابلو طراحی"
            }),
            "description": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "توضیح کوتاه درباره محصول"
            }),
            "price_type": forms.Select(attrs={
                "placeholder": "نوع قیمت — ثابت / توافقی"
            }),
            "price_amount": forms.NumberInput(attrs={
                "placeholder": "مبلغ — مثلاً: ۲۵۰۰۰۰"
            }),
            "currency": forms.Select(attrs={
                "placeholder": "واحد پول — تومان / دلار"
            }),
            "quantity": forms.NumberInput(attrs={
                "placeholder": "تعداد موجودی — مثلاً: ۵"
            }),
            "condition": forms.Select(attrs={
                "placeholder": "وضعیت — نو / دست‌دوم / چاپ محدود"
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "ترتیب نمایش — مثلاً: ۱"
            }),
        }
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            "title", "description", "tags", "pricing_model",
            "currency", "min_price", "max_price", "is_active"
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "نام خدمت — مثل: طراحی گرافیک، تدوین"
            }),
            "description": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "توضیح کوتاه درباره خدمت"
            }),
            "tags": forms.TextInput(attrs={
                "placeholder": "برچسب‌ها — با کاما جدا کنید (مثلاً: طراحی، لوگو، دیجیتال)"
            }),
            "pricing_model": forms.Select(attrs={
                "placeholder": "نوع قیمت‌گذاری — پروژه‌ای / ساعتی"
            }),
            "currency": forms.Select(),
            "min_price": forms.NumberInput(attrs={
                "placeholder": "حداقل مبلغ — مثلاً: ۵۰۰۰۰"
            }),
            "max_price": forms.NumberInput(attrs={
                "placeholder": "حداکثر مبلغ — مثلاً: ۲۰۰۰۰۰"
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "ترتیب نمایش — مثلاً: ۱"
            }),
        }
class ArtPostForm(forms.ModelForm):
    class Meta:
        model = ArtPost
        fields = [
            "title",
            "description",
            "is_active",
            
            "image",
            "video",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "عنوان اثر — مثل: طراحی جدید"
            }),
            "description": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "توضیح درباره اثر"
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "ترتیب نمایش — مثلاً: ۱"
            }),
        }

class ArtPostImageForm(forms.ModelForm):
    class Meta:
        model = ArtPostImage
        fields = ["image", "alt_text",  "is_primary"]
        widgets = {
            "alt_text": forms.TextInput(attrs={
                "placeholder": "توضیح تصویر — برای سئو و دسترسی‌پذیری"
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "ترتیب نمایش — مثلاً: ۱"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].widget.attrs.update({
            "placeholder": "آپلود تصویر",
            "accept": "image/*"
        })
class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "alt_text", "is_primary"]
        widgets = {
            "alt_text": forms.TextInput(attrs={
                "placeholder": "توضیح تصویر محصول — مثلاً: نمای جلو"
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "ترتیب نمایش — مثلاً: ۱"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].widget.attrs.update({
            "placeholder": "آپلود تصویر",
            "accept": "image/*"
        })
class ServiceImageForm(forms.ModelForm):
    class Meta:
        model = ServiceImage
        fields = ["image", "alt_text", "is_primary"]
        widgets = {
            "alt_text": forms.TextInput(attrs={
                "placeholder": "توضیح تصویر — مثل: نمونه کار مرتبط"
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "ترتیب نمایش — مثلاً: ۱"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].widget.attrs.update({
            "placeholder": "آپلود تصویر",
            "accept": "image/*"
        })
ArtPostImageFormSet = inlineformset_factory(
    parent_model=ArtPost,
    model=ArtPostImage,
    form=ArtPostImageForm,
    extra=1,
    max_num=5,
    can_delete=True,
)

ProductImageFormSet = inlineformset_factory(
    parent_model=Product,
    model=ProductImage,
    form=ProductImageForm,
    extra=5,
    max_num=5,
    can_delete=True
)

ServiceImageFormSet = inlineformset_factory(
    parent_model=Service,
    model=ServiceImage,
    form=ServiceImageForm,
    extra=1,
    max_num=5,
    can_delete=True
)
