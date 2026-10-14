"""Scénario de charge My Watch List.

Chaque utilisateur virtuel se connecte avec son propre compte (loaduserN),
puis consulte sa watchlist, ajoute des séries, en marque comme vues et navigue.
Aucun appel à TMDB : on mesure notre application, pas notre fournisseur.
"""
import itertools
import random
import re

from locust import HttpUser, between, task

PASSWORD = "LoadTest!2026"
_user_ids = itertools.count()
TASK_ID = re.compile(r"/update_task/(\d+)/")


class WatchListUser(HttpUser):
    wait_time = between(1, 3)  # un humain réfléchit entre deux clics

    def csrf(self):
        return self.client.cookies.get("csrftoken", "")

    def on_start(self):
        self.username = f"loaduser{next(_user_ids) % 300}"
        self.client.get("/accounts/login/", name="login (page)")
        with self.client.post(
            "/accounts/login/",
            data={"username": self.username, "password": PASSWORD,
                  "csrfmiddlewaretoken": self.csrf()},
            name="login (POST)",
            catch_response=True,
        ) as resp:
            if "Se déconnecter" not in resp.text:
                resp.failure("connexion échouée")

    def task_ids(self, html):
        return TASK_ID.findall(html)

    @task(5)
    def consulter_watchlist(self):
        self.client.get("/", name="watchlist")

    @task(2)
    def ajouter_serie(self):
        self.client.post(
            "/",
            data={"title": f"Série perso {random.randint(1, 10_000)}",
                  "csrfmiddlewaretoken": self.csrf()},
            name="ajouter série",
        )

    @task(2)
    def marquer_vue(self):
        ids = self.task_ids(self.client.get("/", name="watchlist").text)
        if not ids:
            return
        pk = random.choice(ids)
        self.client.get(f"/update_task/{pk}/", name="modifier (page)")
        self.client.post(
            f"/update_task/{pk}/",
            data={"title": f"Série vue {pk}", "complete": "on",
                  "csrfmiddlewaretoken": self.csrf()},
            name="marquer vue",
        )

    @task(1)
    def naviguer(self):
        ids = self.task_ids(self.client.get("/", name="watchlist").text)
        if ids:
            self.client.get(f"/delete_task/{random.choice(ids)}/", name="supprimer (page)")