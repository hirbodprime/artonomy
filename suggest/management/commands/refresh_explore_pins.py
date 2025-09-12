from django.core.management.base import BaseCommand
from django.utils import timezone
from suggest.explore_pins import select_today_pins
from suggest.models import ExplorePin  # adjust import

class Command(BaseCommand):
    help = "Pick and store the daily Explore pins."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB")
        parser.add_argument("--force", action="store_true", help="Delete today's pins and repick")

    def handle(self, *args, **opts):
        if opts["force"] and not opts["dry_run"]:
            today = timezone.localdate()
            deleted = ExplorePin.objects.filter(date=today).delete()[0]
            self.stdout.write(self.style.WARNING(f"Removed {deleted} existing pin(s) for today."))

        posts = select_today_pins(dry_run=opts["dry_run"])
        ids = [p.id for p in posts]
        titles = [getattr(p, "title", "") for p in posts]
        self.stdout.write(self.style.SUCCESS(f"Selected {len(posts)} pin(s): {ids}"))
        if titles:
            self.stdout.write(f"Titles: {titles}")
