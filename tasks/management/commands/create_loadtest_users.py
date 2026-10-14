from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from tasks.models import Task

PASSWORD = "LoadTest!2026"


class Command(BaseCommand):
    help = "Crée les comptes utilisés par le test de charge (loaduser0, loaduser1, ...)"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=300)

    def handle(self, *args, **options):
        hashed = make_password(PASSWORD)  # un seul hachage, réutilisé pour tous les comptes
        existing = set(
            User.objects.filter(username__startswith="loaduser").values_list("username", flat=True)
        )
        names = [f"loaduser{i}" for i in range(options["count"]) if f"loaduser{i}" not in existing]
        User.objects.bulk_create(User(username=name, password=hashed) for name in names)
        Task.objects.bulk_create(
            Task(user=user, title=f"Série de départ {n}")
            for user in User.objects.filter(username__in=names)
            for n in range(5)
        )
        self.stdout.write(self.style.SUCCESS(f"{len(names)} comptes créés (mot de passe : {PASSWORD})"))