# marketplace/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import Product, ProductImage, Service, ServiceImage, ArtPost, ArtPostImage


# Parent editors (if you already have them, keep yours)
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "title", "description", "price_type", "price_amount", "currency",
            "quantity", "condition", "is_active", "order"
        ]

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            "title", "description", "tags", "pricing_model",
            "currency", "min_price", "max_price", "is_active", "order"
        ]

class ArtPostForm(forms.ModelForm):
    class Meta:
        model = ArtPost
        fields = [
            "title",
            "description",
            "is_active",
            "order",
            "image",
            "video",
        ]


ArtPostImageFormSet = inlineformset_factory(
    parent_model=ArtPost,
    model=ArtPostImage,
    fields=["image", "alt_text", "order", "is_primary"],
    extra=1,
    max_num=5,
    can_delete=True,
)

ProductImageFormSet = inlineformset_factory(
    parent_model=Product,
    model=ProductImage,
    fields=["image", "alt_text", "order", "is_primary"],
    extra=5,           # we will add more on the fly in the UI
    max_num=5,
    can_delete=True
)

ServiceImageFormSet = inlineformset_factory(
    parent_model=Service,
    model=ServiceImage,
    fields=["image", "alt_text", "order", "is_primary"],
    extra=1,
    max_num=5,
    can_delete=True
)
