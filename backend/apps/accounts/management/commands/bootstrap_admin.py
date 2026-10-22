"""Create one initial administrator through an explicit, password-prompted command."""
from getpass import getpass

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from apps.accounts.models import Profile

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Create a new administrator and profile. Existing accounts are never modified; "
        "use changepassword to rotate an existing account's password."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Email address for the new administrator.")
        parser.add_argument(
            "--display-name",
            default="",
            help="Optional display name for the administrator profile.",
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(
                f"An account already exists for {email}. No changes were made. "
                f"Use `python manage.py changepassword {email}` to change its password."
            )

        password = getpass("Password: ")
        password_confirmation = getpass("Password (again): ")
        if not password:
            raise CommandError("Password cannot be empty.")
        if password != password_confirmation:
            raise CommandError("The two password entries did not match.")

        candidate = User(
            email=email,
            is_active=True,
            is_staff=True,
            is_superuser=True,
            email_verified=True,
        )
        try:
            candidate.full_clean(exclude=["password"])
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc

        try:
            password_validation.validate_password(password, user=candidate)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc

        try:
            with transaction.atomic():
                admin_user = User.objects.create_superuser(
                    email=email,
                    password=password,
                    is_active=True,
                    email_verified=True,
                )
                Profile.objects.create(
                    user=admin_user,
                    display_name=options["display_name"].strip(),
                )
        except IntegrityError as exc:
            # Covers a concurrent provisioning attempt without modifying the winner.
            raise CommandError(
                f"An account was created concurrently for {email}. No existing account was modified."
            ) from exc

        self.stdout.write(self.style.SUCCESS(f"Created administrator account for {email}."))
