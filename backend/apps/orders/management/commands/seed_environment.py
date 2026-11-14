"""Named entry point for the existing demo seed's complete local profiles."""

from .seed_demo import Command as DemoCommand


class Command(DemoCommand):
    def add_arguments(self, parser):
        parser.add_argument("--env", choices=("dev", "qa"), required=True)
        parser.add_argument("--dry-run", action="store_true")
