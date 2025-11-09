import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from accounts.models import Profile  # مهم


class Command(BaseCommand):
    help = "Import old users from CSV and set a common password for all."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to users_export.csv")
        parser.add_argument(
            "--password",
            required=True,
            help="Common password to set for all imported users",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        common_password = options["password"]
        User = get_user_model()

        created_users = 0
        updated_users = 0
        skipped_users = 0

        self.stdout.write(f"Reading users from: {csv_path}")

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                username = (row.get("username") or "").strip()
                email = (row.get("email") or "").strip()

                if not username:
                    skipped_users += 1
                    continue

                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={"email": email},
                )

                # اگر کاربری ادمین/سوپرادمین هست، پسوردش را دست نزنیم
                if not created and (user.is_staff or user.is_superuser):
                    skipped_users += 1
                    continue

                # ایمیل را آپدیت کن
                if email and user.email != email:
                    user.email = email

                user.set_password(common_password)
                user.save()

                # 📌 پروفایل‌اش را نیز بسازیم/بگیریم و کد را ست کنیم
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.ensure_code()

                if created:
                    created_users += 1
                else:
                    updated_users += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. users_created={created_users}, users_updated={updated_users}, skipped={skipped_users}"
        ))
