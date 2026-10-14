"""Scénario de charge avec TMDB (partie 2).

Même parcours que locustfile.py, mais les utilisateurs cliquent aussi
massivement sur les boutons « Ajouter 10 séries » (Netflix, Prime, Apple TV).
"""
import random

from locust import task

import locustfile


class WatchListTMDBUser(locustfile.WatchListUser):
    @task(3)
    def ajouter_10_series(self):
        provider = random.choice(["netflix", "prime", "apple"])
        with self.client.post(
            f"/add/{provider}/",
            data={"csrfmiddlewaretoken": self.csrf()},
            name="ajouter 10 séries (TMDB)",
            catch_response=True,
        ) as resp:
            if "momentanément indisponible" in resp.text:
                resp.failure("TMDB indisponible")