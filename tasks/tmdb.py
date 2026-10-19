"""Accès à l'API TMDB (repris du J1)."""
import os

import requests

BASE_URL = "https://api.themoviedb.org/3"
TIMEOUT = (3, 5)  # 3 s pour se connecter, 5 s pour la réponse


class TMDBError(Exception):
    """TMDB n'a pas pu répondre correctement."""


class TMDBNotFound(TMDBError):
    """L'identifiant demandé n'existe pas chez TMDB."""


def _get(path, **params):
    token = os.environ.get("TMDB_TOKEN")
    if not token:
        raise TMDBError("TMDB_TOKEN est absent du fichier .env.")
    try:
        response = requests.get(
            f"{BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}", "accept": "application/json"},
            params={"language": "fr-FR", **params},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise TMDBError("TMDB ne répond pas, réessaie dans quelques secondes.") from exc
    if response.status_code == 404:
        raise TMDBNotFound("introuvable chez TMDB")
    if response.status_code == 429:
        raise TMDBError("TMDB limite les requêtes, réessaie dans quelques secondes.")
    if not response.ok:
        raise TMDBError(f"TMDB a répondu une erreur {response.status_code}.")
    return response.json()


def search_tv(query):
    """Cherche des séries par titre. Renvoie la liste brute des résultats TMDB."""
    return _get("/search/tv", query=query)["results"]


def get_tv(tmdb_id):
    """Renvoie la fiche d'une série TMDB à partir de son identifiant."""
    return _get(f"/tv/{tmdb_id}")