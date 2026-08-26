import json

from django.core.management.base import BaseCommand, CommandError

from accounts.gdpr import export_user_data
from accounts.models import User


class Command(BaseCommand):
    help = "GDPR data portability: dump all data about a user as JSON to stdout"

    def add_arguments(self, parser):
        parser.add_argument("email")

    def handle(self, *args, **options):
        user = User.objects.filter(email__iexact=options["email"]).first()
        if user is None:
            raise CommandError(f"No user with email {options['email']}")
        self.stdout.write(json.dumps(export_user_data(user), ensure_ascii=False, indent=2))
