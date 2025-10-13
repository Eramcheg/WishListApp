import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from faker import Faker

from lists.models import Item, Wishlist


class Command(BaseCommand):
    help = "Seed wishlists and items for load testing / pagination demos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=int,
            help="User ID (owner) for whom to create data. "
            "If not specified — --all-users or --create-users is required.",
        )
        parser.add_argument(
            "--wl",
            type=int,
            default=100,
            help="How many wishlists to create for each user (default: 100).",
        )
        parser.add_argument(
            "--items",
            type=int,
            default=50,
            help="How many items to create for each wishlist (default: 50).",
        )
        parser.add_argument(
            "--all-users",
            action="store_true",
            help="Generate for all existing users.",
        )
        parser.add_argument(
            "--create-users",
            type=int,
            default=0,
            help="Generate N new test-users (user1..userN) and generate aurh data for them.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Fixed seed for generated data (for example 42).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow generating with DEBUG=False "
            "(by default code will refuse, to avoid"
            " cluttering production with unnecessary data ).",
        )
        parser.add_argument(
            "--tag",
            type=str,
            default=None,
            help="Метка сева. Будет добавлена к title в формате [SEED:<tag>]."
            " Удобно для последующей очистки.",
        )

    def handle(self, *args, **options):
        from django.conf import settings

        if not settings.DEBUG and not options["force"]:
            raise CommandError("DEBUG=False. Add --force, if you are sure about your actions.")

        wl_count = options["wl"]
        items_per_wl = options["items"]
        seed = options["seed"]
        all_users = options["all_users"]
        create_users = options["create_users"]
        user_id = options["user"]
        tag = options["tag"]

        fake = Faker()
        if seed is not None:
            random.seed(seed)
            Faker.seed(seed)

        User = get_user_model()

        owners = []

        if user_id:
            try:
                owners = [User.objects.get(pk=user_id)]
            except User.DoesNotExist:
                raise CommandError(f"User with id={user_id} was not found.")
        if tag is None:
            from datetime import datetime

            tag = datetime.now().strftime("seed-%Y%m%d-%H%M%S")
        if all_users:
            owners.extend(list(User.objects.all()))

        if create_users > 0:
            for i in range(create_users):
                username = f"seed_user_{fake.unique.user_name()}"
                u = User.objects.create_user(username=username, password="seed_password")
                owners.append(u)

        owners = list({o.pk: o for o in owners}.values())
        self.stdout.write(self.style.NOTICE(f"Using tag: {tag}"))
        if not owners:
            raise CommandError(
                "Не указан ни один владелец. Используйте --user, --all-users or --create-users."
            )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Seeding: owners={len(owners)}, "
                f"wishlists_per_owner={wl_count}, items_per_wishlist={items_per_wl}"
            )
        )

        total_wl = 0
        total_items = 0

        for owner in owners:
            self.stdout.write(
                self.style.NOTICE(
                    f" → Owner id={owner.pk} ({getattr(owner, 'username', owner.pk)})"
                )
            )
            with transaction.atomic():
                # Создаём wishlists батчем
                wl_batch = []
                now = timezone.now()
                for _ in range(wl_count):
                    wl_batch.append(
                        Wishlist(
                            owner=owner,
                            title=f"[SEED:{tag}] " + fake.sentence(nb_words=3),
                            description=fake.text(max_nb_chars=200),
                            is_public=random.choice([True, False, False]),
                            created_at=now,
                        )
                    )
                created_wl = Wishlist.objects.bulk_create(wl_batch, batch_size=1000)
                total_wl += len(created_wl)

                item_batch = []
                for wl in created_wl:
                    for _ in range(items_per_wl):
                        item_batch.append(
                            Item(
                                wishlist=wl,
                                title=fake.sentence(nb_words=3).rstrip("."),
                                url=fake.url(),
                                price_currency=random.choice(["USD", "EUR", "CZK"]),
                                price_amount=round(random.uniform(5, 500), 2),
                                note=fake.text(max_nb_chars=120),
                                image_url=fake.image_url(),
                                is_purchased=random.choice([False, False, True]),
                            )
                        )
                BATCH = 5000
                for i in range(0, len(item_batch), BATCH):
                    chunk = item_batch[i : i + BATCH]
                    Item.objects.bulk_create(chunk, batch_size=1000)
                total_items += len(item_batch)
        self.stdout.write(
            self.style.SUCCESS(f"Done. Created wishlists={total_wl}, items={total_items}")
        )
