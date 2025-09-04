# marketplace/forms.py
from decimal import Decimal
from django import forms
from posts.models import Category
from .models import MarketItem

# forms.py (or wherever you define choices)
CURRENCY_CHOICES = [
    ("TOMAN", "Toman"),   # ✅ new default

]


class Step1CategoryForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.order_by("name"),
        required=True,
        label="Category",
        widget=forms.Select(attrs={"class": "mk-select"}),
    )

class Step2DetailsForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        label="Title",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Logo design for startups"})
    )
    description = forms.CharField(
        label="Description",
        widget=forms.Textarea(attrs={"rows": 6, "placeholder": "Describe your service, process, and deliverables…"})
    )

class Step3PricingMediaForm(forms.Form):
    price = forms.DecimalField(
        max_digits=12, decimal_places=2,
        min_value=Decimal("0"),
        label="Price"
    )
    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        initial="TOMAN",   # ✅ change here
    )
    image = forms.ImageField(label="Cover image", required=False)

class Step4ConfirmForm(forms.Form):
    publish = forms.BooleanField(
        required=False,
        label="Publish now (otherwise saved as Draft)"
    )
