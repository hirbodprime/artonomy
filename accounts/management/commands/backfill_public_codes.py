# users/management/commands/backfill_public_codes.py
from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User, PublicNumberCounter

class Command(BaseCommand):
    help = "Assign A-<n> public codes to users missing them."

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            counter, _ = PublicNumberCounter.objects.select_for_update().get_or_create(name="global")
            qs = User.objects.filter(public_number__isnull=True).order_by("date_joined", "id")
            assigned = 0
            for u in qs:
                counter.last_number += 1
                u.public_number = counter.last_number
                u.public_code = f"A-{counter.last_number}"
                u.save(update_fields=["public_number", "public_code"])
                assigned += 1
            counter.save(update_fields=["last_number"])
        self.stdout.write(self.style.SUCCESS(f"Assigned {assigned} public codes."))
