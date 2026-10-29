from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.identity.models import RateBucket


class Command(BaseCommand):
    help = "Remove expired security buckets older than 12 hours; run from an OS scheduler."

    def handle(self, *args, **options):
        count, _ = RateBucket.objects.filter(
            expires_at__lt=timezone.now() - timedelta(hours=12)
        ).delete()
        self.stdout.write(f"Removed {count} expired rate buckets.")
