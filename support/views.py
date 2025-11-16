from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages

from .models import Ticket, TicketMessage
from .forms import TicketCreateForm, TicketMessageForm


@login_required
def ticket_list_view(request):
    tickets = Ticket.objects.filter(user=request.user)
    return render(request, "support/ticket_list.html", {"tickets": tickets})


@login_required
def ticket_create_view(request):
    if request.method == "POST":
        form = TicketCreateForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.status = Ticket.STATUS_OPEN
            ticket.save()

            # پیام اول
            body = form.cleaned_data["first_message"]
            attachment = form.cleaned_data.get("attachment")
            TicketMessage.objects.create(
                ticket=ticket,
                sender=request.user,
                body=body,
                attachment=attachment,
                is_staff_reply=False,
            )

            messages.success(request, "تیکت شما ثبت شد. به زودی پاسخ داده می‌شود.")
            return redirect("support:ticket_detail", pk=ticket.pk)
    else:
        form = TicketCreateForm()

    return render(request, "support/ticket_create.html", {"form": form})


@login_required
def ticket_detail_view(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    messages_qs = ticket.messages.all()

    if request.method == "POST":
        # کاربر پیام جدید می‌فرستد
        form = TicketMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.ticket = ticket
            msg.sender = request.user
            msg.is_staff_reply = False
            msg.save()

            # وقتی کاربر جواب می‌دهد، وضعیت حداقل Open بشود
            if ticket.status == Ticket.STATUS_ANSWERED:
                ticket.status = Ticket.STATUS_OPEN
                ticket.save(update_fields=["status", "updated_at"])

            messages.success(request, "پیام شما ثبت شد.")
            return redirect("support:ticket_detail", pk=ticket.pk)
    else:
        form = TicketMessageForm()

    return render(
        request,
        "support/ticket_detail.html",
        {
            "ticket": ticket,
            "messages": messages_qs,
            "form": form,
        },
    )
