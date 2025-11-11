import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from accounts.models import Profile


class Command(BaseCommand):
    help = "Import user roles (ARTIST/AUDIENCE) from old DB CSV and map them to Profile.role."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to user_roles.csv")

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        User = get_user_model()

        updated_profiles = 0
        skipped_rows = 0
        missing_users = 0

        self.stdout.write(f"Reading roles from: {csv_path}")

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = (row.get("email") or "").strip()
                username = (row.get("username") or "").strip()
                old_role = (row.get("role") or "").strip()  # ARTIST / AUDIENCE / maybe empty

                if not (email or username):
                    skipped_rows += 1
                    continue

                user = None

                # Try to find user in NEW DB (first by email, then by username)
                if email:
                    user = User.objects.filter(email=email).first()
                if not user and username:
                    user = User.objects.filter(username=username).first()

                if not user:
                    missing_users += 1
                    continue

                profile, _ = Profile.objects.get_or_create(user=user)

                # Map old roles to new Profile.role
                if old_role == "ARTIST":
                    profile.role = "artist"    # هنرمند
                elif old_role == "AUDIENCE":
                    profile.role = "normal"    # مخاطب هنر
                else:
                    # Unknown/empty role → do not touch
                    skipped_rows += 1
                    continue

                profile.save(update_fields=["role"])
                updated_profiles += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. profiles_updated={updated_profiles}, missing_users={missing_users}, skipped_rows={skipped_rows}"
        ))
