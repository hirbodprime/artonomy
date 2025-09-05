# app/management/commands/refresh_explore_pins.py
from django.core.management.base import BaseCommand
from suggest.explore_pins import select_today_pins

class Command(BaseCommand):
    help = "Pick and store the daily Explore pins."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Do not write to DB')

    def handle(self, *args, **opts):
        posts = select_today_pins(dry_run=opts['dry_run'])
        self.stdout.write(self.style.SUCCESS(f"Selected {len(posts)} pin(s): {[p.id for p in posts]}"))
