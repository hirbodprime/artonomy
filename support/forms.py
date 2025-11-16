from django import forms
from .models import Ticket, TicketMessage


class TicketCreateForm(forms.ModelForm):
    first_message = forms.CharField(
        label="متن پیام",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "مشکل یا سوال خود را توضیح دهید..."}),
    )
    attachment = forms.FileField(
        label="فایل ضمیمه (اختیاری)",
        required=False,
    )

    class Meta:
        model = Ticket
        fields = ["subject"]

        widgets = {
            "subject": forms.TextInput(attrs={
                "placeholder": "مثلاً: مشکل در آپلود تصویر پروفایل"
            }),
        }


class TicketMessageForm(forms.ModelForm):
    class Meta:
        model = TicketMessage
        fields = ["body", "attachment"]
        widgets = {
            "body": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "پیام خود را بنویسید..."
            }),
        }
