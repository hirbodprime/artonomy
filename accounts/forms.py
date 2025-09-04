from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.forms import inlineformset_factory
from .models import (
    Profile, SocialLink, SkillTag,
    PersonalValue, HobbyInterest, FunFact,
    Education, Experience, Project, Certification, Course, Award, Book
)
class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "w-full h-11 text-sm rounded-full border border-gray-300 bg-white px-4 focus:outline-none focus:ring-2 focus:ring-purple-500",
            "placeholder": "Give Us Your Email",
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full h-11 text-sm rounded-full border border-gray-300 bg-white pl-4 pr-14 focus:outline-none focus:ring-2 focus:ring-purple-500",
            "placeholder": "Do You Remind It?",
            "id": "login-pass",
        })
    )


# ---------- Personal info ----------

class ProfileBasicsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["title", "phone", "avatar", "cover", "bio"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input rounded-lg w-full p-3"}),
            "phone": forms.TextInput(attrs={"class": "form-input rounded-lg w-full p-3"}),
            "bio":   forms.Textarea(attrs={"rows": 5, "class": "form-input rounded-lg w-full p-3"}),
        }

class SkillsCSVForm(forms.Form):
    skills_csv = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Python, Django, Figma", "class": "form-input rounded-lg w-full p-3"})
    )

class ValuesHobbiesForm(forms.Form):
    values_csv  = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "placeholder": "Values (comma separated)", "class":"form-input rounded-lg w-full p-3"
    }))
    hobbies_csv = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "placeholder": "Hobbies / Interests (comma separated)", "class":"form-input rounded-lg w-full p-3"
    }))

class FunFactsForm(forms.Form):
    funfacts_csv = forms.CharField(required=False, widget=forms.Textarea(attrs={
        "rows":4, "placeholder":"Fun facts (comma or new-line separated)", "class":"form-input rounded-lg w-full p-3"
    }))

class SocialLinkForm(forms.ModelForm):
    class Meta:
        model  = SocialLink
        fields = ["kind", "label", "url"]
        widgets = {
            "kind":  forms.Select(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "label": forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "url":   forms.URLInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
        }

# forms.py (or wherever your formsets live)
SocialLinkFormSet = inlineformset_factory(
    parent_model=Profile,
    model=SocialLink,
    form=SocialLinkForm,
    fields=["kind","label","url"],
    extra=0,          # ← was 3
    can_delete=True
)

# ---------- Portfolio ----------

class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ["school","degree","location","start_date","end_date","is_current","summary"]
        widgets = {
            "school":   forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "degree":   forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "location": forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "start_date":forms.DateInput(attrs={"type":"date","class":"form-input rounded-lg w-full p-3"}),
            "end_date":  forms.DateInput(attrs={"type":"date","class":"form-input rounded-lg w-full p-3"}),
            "is_current":forms.CheckboxInput(attrs={"class":"mr-2"}),
            "summary":  forms.Textarea(attrs={"rows":3,"class":"form-input rounded-lg w-full p-3"}),
        }

class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = ["company","title","location","start_date","end_date","is_current","summary"]
        widgets = {
            "company":  forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "title":    forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "location": forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "start_date":forms.DateInput(attrs={"type":"date","class":"form-input rounded-lg w-full p-3"}),
            "end_date":  forms.DateInput(attrs={"type":"date","class":"form-input rounded-lg w-full p-3"}),
            "is_current":forms.CheckboxInput(attrs={"class":"mr-2"}),
            "summary":  forms.Textarea(attrs={"rows":3,"class":"form-input rounded-lg w-full p-3"}),
        }

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["title","employer","description","tech_stack","url","start_date","end_date","is_current"]
        widgets = {
            "title":   forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "employer":forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "description":forms.Textarea(attrs={"rows":3,"class":"form-input rounded-lg w-full p-3"}),
            "tech_stack": forms.TextInput(attrs={"placeholder":"React, Django, Postgres","class":"form-input rounded-lg w-full p-3"}),
            "url":     forms.URLInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "start_date":forms.DateInput(attrs={"type":"date","class":"form-input rounded-lg w-full p-3"}),
            "end_date":  forms.DateInput(attrs={"type":"date","class":"form-input rounded-lg w-full p-3"}),
            "is_current":forms.CheckboxInput(attrs={"class":"mr-2"}),
        }

class CertificationForm(forms.ModelForm):
    class Meta:
        model = Certification
        fields = ["name","issuer","issue_date","credential_id","url"]
        widgets = {
            "name":   forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "issuer": forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "issue_date":forms.DateInput(attrs={"type":"date","class":"form-input rounded-lg w-full p-3"}),
            "credential_id": forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "url":    forms.URLInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
        }

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["name","org","date","note"]
        widgets = {
            "name": forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "org":  forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "date": forms.DateInput(attrs={"type":"date","class":"form-input rounded-lg w-full p-3"}),
            "note": forms.Textarea(attrs={"rows":2,"class":"form-input rounded-lg w-full p-3"}),
        }

class AwardForm(forms.ModelForm):
    class Meta:
        model = Award
        fields = ["title","organization","date","description"]
        widgets = {
            "title": forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "organization": forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "date":  forms.DateInput(attrs={"type":"date","class":"form-input rounded-lg w-full p-3"}),
            "description": forms.Textarea(attrs={"rows":2,"class":"form-input rounded-lg w-full p-3"}),
        }

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ["title","author","year","note"]
        widgets = {
            "title":  forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "author": forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "year":   forms.TextInput(attrs={"class":"form-input rounded-lg w-full p-3"}),
            "note":   forms.Textarea(attrs={"rows":2,"class":"form-input rounded-lg w-full p-3"}),
        }

# Formsets (inline to Profile)
EducationFS     = inlineformset_factory(Profile, Education,     form=EducationForm,     extra=1, can_delete=True)
ExperienceFS    = inlineformset_factory(Profile, Experience,    form=ExperienceForm,    extra=1, can_delete=True)
ProjectFS       = inlineformset_factory(Profile, Project,       form=ProjectForm,       extra=1, can_delete=True)
CertificationFS = inlineformset_factory(Profile, Certification, form=CertificationForm, extra=1, can_delete=True)
CourseFS        = inlineformset_factory(Profile, Course,        form=CourseForm,        extra=1, can_delete=True)
AwardFS         = inlineformset_factory(Profile, Award,         form=AwardForm,         extra=1, can_delete=True)
BookFS          = inlineformset_factory(Profile, Book,          form=BookForm,          extra=1, can_delete=True)
