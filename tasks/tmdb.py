import os

import requests

BASE_URL = "https://api.themoviedb.org/3"
WATCH_REGION = "FR"

PROVIDERS = {
    "netflix": {"id": 8, "label": "Netflix"},
    "prime": {"id": 119, "label": "Amazon Prime Video"},
    "apple": {"id": 350, "label": "Apple TV"},
}


def discover_top_series(provider_id, page=1):
    """Appelle TMDB et renvoie une page de séries les mieux notées pour une plateforme."""
    response = requests.get(
        f"{BASE_URL}/discover/tv",
        headers={
            "Authorization": f"Bearer {os.environ['TMDB_TOKEN']}",
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
        timeout=10,
    )
    response.raise_for_status()
    return response.json()