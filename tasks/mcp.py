"""Outils MCP de la watchlist.

Chaque fonction décorée par @mcp.tool() devient un outil MCP :
- le nom de la fonction est le nom de l'outil ;
- la docstring est la description que lit l'agent IA ;
- les paramètres typés deviennent le schéma des arguments.
"""
from asgiref.sync import sync_to_async
from mcp.server.fastmcp.exceptions import ToolError
from mcp_server import mcp_server as mcp

from . import tmdb
from .models import Task


def _serie(task):
    return {
        "watchlist_id": task.id,
        "title": task.title,
        "watched": task.complete,
        "tmdb_id": task.tmdb_id,
    }


async def _get_task(watchlist_id):
    try:
        return await Task.objects.aget(id=watchlist_id)
    except Task.DoesNotExist:
        raise ToolError(
            f"Aucune série avec watchlist_id={watchlist_id} dans la watchlist. "
            "Appelle list_watchlist pour obtenir les watchlist_id existants."
        )


@mcp.tool()
async def list_watchlist() -> dict:
    """Liste toutes les séries de la watchlist de l'utilisateur, des plus récentes aux plus anciennes.

    Renvoie pour chaque série : watchlist_id (identifiant interne à utiliser pour
    remove_series_from_watchlist et mark_series_as_watched), title, watched (true si déjà vue)
    et tmdb_id. À appeler avant toute suppression ou marquage pour connaître le bon watchlist_id.
    """
    series = [_serie(t) async for t in Task.objects.order_by("-created")]
    return {"count": len(series), "series": series}


@mcp.tool()
async def search_series(query: str) -> dict:
    """Cherche des séries TV sur TMDB à partir d'un titre (ou d'une partie de titre).

    À utiliser quand l'utilisateur nomme une série à ajouter : la recherche donne le tmdb_id
    à passer ensuite à add_series_to_watchlist. Renvoie au plus 5 résultats, les plus
    populaires d'abord, avec tmdb_id, title, original_title, year, rating (note sur 10),
    overview (résumé court) et already_in_watchlist. Si plusieurs résultats correspondent,
    demande à l'utilisateur de choisir plutôt que de deviner.
    """
    query = query.strip()
    if not query:
        raise ToolError("La recherche est vide : donne au moins un mot du titre de la série.")
    try:
        results = await sync_to_async(tmdb.search_tv)(query)
    except tmdb.TMDBError as exc:
        raise ToolError(f"Recherche impossible : {exc}")

    results = sorted(results, key=lambda r: r.get("popularity", 0), reverse=True)[:5]
    ids = [r["id"] for r in results]
    in_watchlist = {
        tmdb_id async for tmdb_id in Task.objects.filter(tmdb_id__in=ids).values_list("tmdb_id", flat=True)
    }
    series = [
        {
            "tmdb_id": r["id"],
            "title": r.get("name"),
            "original_title": r.get("original_name"),
            "year": (r.get("first_air_date") or "")[:4] or None,
            "rating": r.get("vote_average"),
            "overview": (r.get("overview") or "")[:200],
            "already_in_watchlist": r["id"] in in_watchlist,
        }
        for r in results
    ]
    if not series:
        return {"count": 0, "series": [], "message": f"Aucune série trouvée pour « {query} »."}
    return {"count": len(series), "series": series}


@mcp.tool()
async def add_series_to_watchlist(tmdb_id: int) -> dict:
    """Ajoute une série à la watchlist à partir de son tmdb_id.

    Le tmdb_id doit provenir de search_series : n'invente jamais d'identifiant.
    Le titre est récupéré automatiquement depuis TMDB. Renvoie la série ajoutée
    avec son watchlist_id. Échoue si la série est déjà dans la watchlist.
    """
    existing = await Task.objects.filter(tmdb_id=tmdb_id).afirst()
    if existing:
        raise ToolError(
            f"« {existing.title} » est déjà dans la watchlist (watchlist_id={existing.id}). Rien n'a été ajouté."
        )
    try:
        data = await sync_to_async(tmdb.get_tv)(tmdb_id)
    except tmdb.TMDBNotFound:
        raise ToolError(
            f"Aucune série TMDB avec le tmdb_id {tmdb_id}. "
            "Utilise search_series avec le titre de la série pour trouver le bon tmdb_id."
        )
    except tmdb.TMDBError as exc:
        raise ToolError(f"Ajout impossible : {exc}")

    task = await Task.objects.acreate(title=data.get("name") or f"Série {tmdb_id}", tmdb_id=tmdb_id)
    return {"message": f"« {task.title} » a été ajoutée à la watchlist.", "series": _serie(task)}


@mcp.tool()
async def remove_series_from_watchlist(watchlist_id: int) -> dict:
    """Supprime UNE série de la watchlist à partir de son watchlist_id (obtenu avec list_watchlist).

    Attention : watchlist_id n'est pas le tmdb_id. La suppression est définitive.
    Pour supprimer plusieurs séries, appelle cet outil une fois par série ; si l'utilisateur
    demande de tout supprimer, fais-lui confirmer la liste avant.
    """
    task = await _get_task(watchlist_id)
    title = task.title
    await task.adelete()
    return {"message": f"« {title} » a été supprimée de la watchlist.", "watchlist_id": watchlist_id}


@mcp.tool()
async def mark_series_as_watched(watchlist_id: int) -> dict:
    """Marque une série de la watchlist comme vue, à partir de son watchlist_id (obtenu avec list_watchlist).

    Attention : watchlist_id n'est pas le tmdb_id. Renvoie la série mise à jour.
    """
    task = await _get_task(watchlist_id)
    if task.complete:
        return {"message": f"« {task.title} » était déjà marquée comme vue.", "series": _serie(task)}
    task.complete = True
    await task.asave(update_fields=["complete"])
    return {"message": f"« {task.title} » est maintenant marquée comme vue.", "series": _serie(task)}