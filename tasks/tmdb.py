import logging
import os

import requests
from django.core.cache import cache

logger = logging.getLogger("tasks.tmdb")

# URL de base configurable : permet de pointer vers un autre hôte (ex. pour simuler une panne)
BASE_URL = os.environ.get("TMDB_BASE_URL", "https://api.themoviedb.org/3")
WATCH_REGION = "FR"
CACHE_TTL = int(os.environ.get("TMDB_CACHE_TTL", "300"))  # 5 minutes ; 0 = pas de cache
TIMEOUT = (3, 5)  # 3 s pour se connecter, 5 s pour recevoir la réponse
DOWN_KEY = "tmdb:down"
DOWN_DURATION = 30  # après une panne, on n'insiste pas pendant 30 s

PROVIDERS = {
    "netflix": {"id": 8, "label": "Netflix"},
    "prime": {"id": 119, "label": "Amazon Prime Video"},
    "apple": {"id": 350, "label": "Apple TV"},
}


class TMDBUnavailable(Exception):
    """TMDB ne répond pas (panne, délai dépassé, limite de requêtes...)."""


def discover_top_series(provider_id, page=1):
    """Renvoie une page des séries les mieux notées d'une plateforme.

    La réponse est mise en cache par plateforme et par page (pas par utilisateur) :
    le résultat TMDB est le même pour tout le monde.
    """
    cache_key = f"tmdb:discover:{provider_id}:{page}"

    if CACHE_TTL:
        data = cache.get(cache_key)
        if data is not None:
            logger.info("TMDB cache HIT provider=%s page=%s", provider_id, page)
            return data

    if cache.get(DOWN_KEY):
        logger.warning("TMDB marqué indisponible, appel évité provider=%s page=%s", provider_id, page)
        raise TMDBUnavailable("TMDB est temporairement indisponible")

    try:
        response = requests.get(
            f"{BASE_URL}/discover/tv",
            headers={
                "Authorization": f"Bearer {os.environ.get('TMDB_TOKEN', '')}",
                "accept": "application/json",
            },
            params={
                "with_watch_providers": provider_id,
                "watch_region": WATCH_REGION,
                "sort_by": "vote_average.desc",
                "vote_count.gte": 200,
                "language": "fr-FR",
                "page": page,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        cache.set(DOWN_KEY, True, DOWN_DURATION)
        logger.error("TMDB ERREUR provider=%s page=%s : %s", provider_id, page, exc)
        raise TMDBUnavailable("TMDB est temporairement indisponible") from exc

    logger.info("TMDB appel OK provider=%s page=%s (%.0f ms)",
                provider_id, page, response.elapsed.total_seconds() * 1000)
    if CACHE_TTL:
        cache.set(cache_key, data, CACHE_TTL)
    return data