# support/admin.py
from django.contrib import admin
from .models import Ticket, TicketMessage


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 1
    fields = ("body", "attachment", "is_staff_reply", "created_at")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # می‌خوای مرتب‌سازی تو ادمین هم به ترتیب زمان باشه
        return qs.order_by("created_at")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "user", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("subject", "user__username", "user__email")
    inlines = [TicketMessageInline]

    def save_formset(self, request, form, formset, change):
        """
        هر وقت ادمین یک TicketMessage جدید اضافه کند:
        - sender به صورت خودکار = request.user
        - is_staff_reply = True
        - وضعیت تیکت = ANSWERED
        """
        instances = formset.save(commit=False)

        for obj in instances:
            is_new = obj.pk is None  # پیام جدید یا ویرایش؟

            # تنظیم اتوماتیک روی پیام‌های تازه
            if is_new:
                if not obj.sender_id:
                    obj.sender = request.user
                # اگر کاربر ادمین/استاف است، پاسخ پشتیبانی حسابش کن
                if request.user.is_staff:
                    obj.is_staff_reply = True

                # تیکت رو answered کن
                ticket = obj.ticket
                if ticket.status != Ticket.STATUS_CLOSED:
                    ticket.status = Ticket.STATUS_ANSWERED
                    ticket.save(update_fields=["status", "updated_at"])

            obj.save()

        # اگر m2m بود
        formset.save_m2m()
