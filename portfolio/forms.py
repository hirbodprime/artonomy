from django import forms
from django.forms import inlineformset_factory, modelformset_factory
from .models import (
    Profile, SocialLink, StatCounter, Skill,
    Education, Experience, Artwork, ServiceItem, Testimonial
)

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = (
            "title", "avatar", "cover", "hero_image",
            "phone", "website", "bio", "location", "email_public"
        )
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 5}),
            "avatar": forms.FileInput(attrs={"class": "file-input", "accept": "image/*"}),
            "cover": forms.FileInput(attrs={"class": "file-input", "accept": "image/*"}),
            "hero_image": forms.FileInput(attrs={"class": "file-input", "accept": "image/*"}),

        }

def make_sociallink_formset():
    from .models import SocialLink, Profile
    return inlineformset_factory(
        parent_model=Profile,
        model=SocialLink,
        fk_name="profile",
        fields=("kind", "label", "url"),
        extra=1,            # start with one; add via JS
        can_delete=True,
    )
class PublishChoicesForm(forms.Form):
    """
    Let the user pick which artworks & services appear on the public portfolio.
    If they pick none, the view will fall back to latest items.
    """
    artworks = forms.ModelMultipleChoiceField(
        queryset=Artwork.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Select artworks to show"
    )
    services = forms.ModelMultipleChoiceField(
        queryset=ServiceItem.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Select services to show"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["artworks"].queryset = (
            Artwork.objects.filter(owner=user, is_published=True).order_by("-created_at")[:30]
        )
        self.fields["services"].queryset = (
            ServiceItem.objects.filter(owner=user, ).order_by("-created_at")[:30]
        )


# ---------- ModelFormSets for owner-based content ----------
CounterFS     = modelformset_factory(
    StatCounter, fields=("icon", "label", "value"), extra=1, can_delete=True
)
SkillFS       = modelformset_factory(
    Skill, fields=("name", "percent"), extra=1, can_delete=True
)
EducationFS   = modelformset_factory(
    Education, fields=("school", "degree", "start_year", "end_year", "summary"), extra=1, can_delete=True
)
ExperienceFS  = modelformset_factory(
    Experience, fields=("company", "title", "start_year", "end_year", "location", "summary"), extra=1, can_delete=True
)
ArtworkFS     = modelformset_factory(
    Artwork, fields=("image", "title", "caption", "is_published"), extra=1, can_delete=True
)
ServiceFS     = modelformset_factory(
    ServiceItem, fields=("icon", "title", "description"), extra=1, can_delete=True
)
TestimonialFS = modelformset_factory(
    Testimonial, fields=("photo", "author_name", "role", "text"), extra=1, can_delete=True
)
