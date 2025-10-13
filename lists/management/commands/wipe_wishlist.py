from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from lists.models import Item, Wishlist


class Command(BaseCommand):
    help = (
        "Удалить сгенерированные (и не только) данные. "
        "Предпочтительно — по метке --tag, которой помечались сиды."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tag",
            type=str,
            help="Метка из seed_wishlist (например, seed-20251010-134501)."
            " Удалит все Wishlists с заголовком, содержащим [SEED:<tag>].",
        )
        parser.add_argument(
            "--user", type=int, help="Удалить данные только пользователя с таким id (owner)."
        )
        parser.add_argument(
            "--all-users",
            action="store_true",
            help="Удалить по всем пользователям (использовать осторожно).",
        )
        parser.add_argument(
            "--created-after",
            type=str,
            help="Удалить созданные ПОСЛЕ этой даты (YYYY-MM-DD или ISO datetime).",
        )
        parser.add_argument(
            "--created-before",
            type=str,
            help="Удалить созданные ДО этой даты (YYYY-MM-DD или ISO datetime).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Ничего не удалять, только показать, что будет удалено.",
        )
        parser.add_argument(
            "--force", action="store_true", help="Разрешить запуск при DEBUG=False."
        )

    def handle(self, *args, **opts):
        from django.conf import settings

        if not settings.DEBUG and not opts["force"]:
            raise CommandError(
                "DEBUG=False. Добавьте --force, если вы действительно хотите запустить очистку."
            )

        tag = opts.get("tag")
        user_id = opts.get("user")
        all_users = opts.get("all_users")
        created_after = opts.get("created_after")
        created_before = opts.get("created_before")
        dry = opts.get("dry_run")

        if not any([tag, user_id, all_users, created_after, created_before]):
            raise CommandError(
                "Нужно указать хотя бы один фильтр: "
                "--tag/--user/--all-users/--created-after/--created-before."
            )

        qs = Wishlist.objects.all()

        if tag:
            qs = qs.filter(title__icontains=f"[SEED:{tag}]")

        if user_id and not all_users:
            qs = qs.filter(owner_id=user_id)

        if created_after:
            dt = parse_datetime(created_after) or parse_date(created_after)
            if dt is None:
                raise CommandError(
                    "Неверный формат --created-after. "
                    "Используйте YYYY-MM-DD или полноценный ISO datetime."
                )
            if hasattr(dt, "year") and not hasattr(dt, "hour"):
                # Это дата без времени
                from datetime import datetime

                dt = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
            qs = qs.filter(created_at__gte=dt)

        if created_before:
            dt = parse_datetime(created_before) or parse_date(created_before)
            if dt is None:
                raise CommandError(
                    "Неверный формат --created-before."
                    " Используйте YYYY-MM-DD или полноценный ISO datetime."
                )
            if hasattr(dt, "year") and not hasattr(dt, "hour"):
                from datetime import datetime

                dt = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
            qs = qs.filter(created_at__lte=dt)

        wl_count = qs.count()
        it_count = Item.objects.filter(wishlist__in=qs).count()

        if wl_count == 0:
            self.stdout.write(self.style.WARNING("Ничего не найдено под заданные фильтры."))
            return

        self.stdout.write(
            self.style.NOTICE(f"Будет удалено wishlists={wl_count}, items={it_count}")
        )
        if dry:
            self.stdout.write(self.style.SUCCESS("Dry-run: удаление не выполнялось."))
            return

        with transaction.atomic():
            # FK on_delete=CASCADE удалит Items автоматически
            qs.delete()

        self.stdout.write(
            self.style.SUCCESS(f"Готово. Удалено wishlists={wl_count}, items≈{it_count}")
        )
