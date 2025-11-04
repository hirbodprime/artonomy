# marketplace/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import BusinessProfile, JoinRequest, Product
class ProductForm(forms.ModelForm):
    # Show as radios: Service / Physical Product
    is_service = forms.TypedChoiceField(
        label=_("Listing Type"),
        choices=[(True, _("Service")), (False, _("Physical Product"))],
        coerce=lambda v: v in (True, "True", "true", "1", 1),
        widget=forms.RadioSelect
    )

    class Meta:
        model = Product
        fields = ["title", "description", "category", "price", "currency",
                  "is_service", "image", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }

class JoinPickKindForm(forms.Form):
    """
    Step 1: Are you a solo artist or some kind of business?
    We normalize all options into BusinessProfile.Kind.
    """
    kind = forms.ChoiceField(
        choices=[
            ("SOLO_ARTIST",   _("I'm a solo artist")),
            ("GALLERY",       _("Gallery")),
            ("STUDIO",        _("Studio")),
            ("CONCEPT_STORE", _("Concept store")),
            ("OTHER",         _("Other creative business")),
        ],
        widget=forms.RadioSelect
    )


class ProfileSetupForm(forms.ModelForm):
    """
    Step 2: we are building the dramatic public profile.
    """
    class Meta:
        model = BusinessProfile
        fields = [
            "display_name",
            "tagline",
            "bio_long",
            "location",
            "avatar",
            "cover",
        ]
        widgets = {
            "display_name": forms.TextInput(attrs={
                "placeholder": _("Your public / artist / studio name")
            }),
            "tagline": forms.TextInput(attrs={
                "placeholder": _("Example: Brutalist ceramics with Persian soul")
            }),
            "bio_long": forms.Textarea(attrs={
                "rows": 6,
                "placeholder": _(
                    "Tell your story. Be dramatic. What do you create, "
                    "what do you believe, what makes you different?"
                )
            }),
            "location": forms.TextInput(attrs={
                "placeholder": _("City, Country")
            }),
        }


class PaymentUploadForm(forms.ModelForm):
    """
    Step 3: upload proof of payment.
    We don't choose price plans yet (you can add plan later).
    """
    class Meta:
        model = JoinRequest
        fields = ["payment_image"]
        widgets = {
            "payment_image": forms.ClearableFileInput(attrs={"accept": "image/*"})
        }
        labels = {
            "payment_image": _("Upload payment screenshot"),
        }
