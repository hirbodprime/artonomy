# marketplace/forms.py
from decimal import Decimal
from django import forms
from posts.models import Category
from django.utils.translation import gettext_lazy as _

CURRENCY_CHOICES = [
    ("TOMAN", "Toman"),   # localized in template
]

PRICING_CHOICES = [
    ("NEGOTIABLE", _("Negotiable")),
    ("FIXED",      _("Fixed")),
    ("RANGE",      _("Range")),
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


class Step3PricingForm(forms.Form):
    pricing_type = forms.ChoiceField(
        choices=PRICING_CHOICES,
        initial="NEGOTIABLE",
        widget=forms.RadioSelect
    )
    # Fixed
    price = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, label="Price"
    )
    # Range
    price_min = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, label="Min price"
    )
    price_max = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, label="Max price"
    )

    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        initial="TOMAN",
        required=False,
    )

    def clean(self):
        cleaned = super().clean()
        ptype = cleaned.get("pricing_type")
        price = cleaned.get("price")
        pmin  = cleaned.get("price_min")
        pmax  = cleaned.get("price_max")

        if ptype == "FIXED":
            if price is None:
                self.add_error("price", "Please enter a price.")
        elif ptype == "RANGE":
            if pmin is None:
                self.add_error("price_min", "Please enter a minimum price.")
            if pmax is None:
                self.add_error("price_max", "Please enter a maximum price.")
            if pmin is not None and pmax is not None and pmin > pmax:
                self.add_error("price_max", "Max price must be greater than or equal to min price.")
        # NEGOTIABLE: no amounts required

        return cleaned


class Step4ConfirmForm(forms.Form):
    publish = forms.BooleanField(
        required=False,
        label="Publish now (otherwise saved as Draft)"
    )
