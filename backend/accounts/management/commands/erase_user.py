from django.core.management.base import BaseCommand, CommandError

from accounts.gdpr import erase_user
from accounts.models import User


class Command(BaseCommand):
    help = "GDPR right-of-erasure: anonymize a user and delete their personal data/files"

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--yes", action="store_true", help="Skip confirmation")

    def handle(self, *args, **options):
        user = User.objects.filter(email__iexact=options["email"]).first()
        if user is None:
            raise CommandError(f"No user with email {options['email']}")
        if not options["yes"]:
            answer = input(f"Erase {user.email} (role: {user.role})? This cannot be undone. [y/N] ")
            if answer.lower() != "y":
                self.stdout.write("Aborted.")
                return
        self.stdout.write(erase_user(user))
