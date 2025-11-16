from django import forms
from .models import SupportTicket

class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ["subject", "message"]
        widgets = {
            "subject": forms.TextInput(attrs={
                "placeholder": "مثلاً: مشکل در آپلود تصویر پروفایل",
            }),
            "message": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "مشکل، باگ یا درخواست خود را دقیق توضیح دهید...",
            }),
        }
        labels = {
            "subject": "موضوع",
            "message": "توضیح مشکل / درخواست",
        }
