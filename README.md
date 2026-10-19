# My Watch List — J3 : piloter la watchlist avec une IA (MCP)

Pour ce J3, je suis repartie du dépôt initial (commit `93d4c30`, avant mes modifs du J1),
donc la version simple de la watchlist, sans authentification. Tout le travail du jour est
sur la branche `j3-mcp`.

L'idée : transformer ma watchlist en serveur MCP pour qu'un assistant IA puisse
l'utiliser à ma place, en langage naturel.

## Comment lancer le projet

1. Installer les dépendances : `python -m pip install -r requirements.txt`
2. Copier `.env.example` en `.env` et mettre son token TMDB dans `TMDB_TOKEN`
3. `python manage.py migrate`
4. `python manage.py runserver`

Le serveur MCP est ensuite accessible sur `http://localhost:8000/mcp` (en Streamable HTTP).
Pour vérifier que les outils sont bien déclarés : `python manage.py mcp_inspect`.


## Ce que j'ai compris de MCP

- Le **host**, c'est l'appli qu'on utilise (Claude Desktop, ou MCP Inspector pour tester).
- Le **client MCP** est dans le host : c'est lui qui se connecte au serveur.
- Le **serveur MCP**, c'est ma watchlist : elle annonce ses outils avec un nom,
  une description et les arguments attendus.

Concrètement : le client demande la liste des outils, le modèle lit les descriptions et
choisit lequel appeler, le client fait l'appel, et le serveur renvoie le résultat.
J'ai d'abord testé tout ça avec le serveur d'exemple `everything` dans MCP Inspector,
avant de brancher ma propre application.

## Les outils que j'expose

| Outil | Arguments | À quoi il sert |
|---|---|---|
| `list_watchlist` | aucun | Voir toutes les séries de la watchlist |
| `search_series` | `query` | Chercher une série sur TMDB à partir de son titre |
| `add_series_to_watchlist` | `tmdb_id` | Ajouter une série trouvée avec la recherche |
| `remove_series_from_watchlist` | `watchlist_id` | Supprimer une série |
| `mark_series_as_watched` | `watchlist_id` | Marquer une série comme vue |

## Mes choix

- **Un outil = une seule action.** Pas d'outil fourre-tout avec un paramètre qui change
  ce qu'il fait.
- **Deux identifiants bien séparés** : `tmdb_id` (l'identifiant chez TMDB) et
  `watchlist_id` (l'identifiant dans ma base). J'ai volontairement mis des noms explicites
  pour que l'IA ne les mélange pas.
- **Pour « ajoute Severance à ma watchlist »**, l'IA ne connaît pas d'identifiant. Elle doit
  donc d'abord appeler `search_series("Severance")`, récupérer le `tmdb_id`, puis appeler
  `add_series_to_watchlist`. C'est pour ça que l'ajout prend un `tmdb_id` et pas un titre :
  le vrai titre est récupéré chez TMDB, l'IA ne peut pas l'inventer.
- **La recherche renvoie juste ce qu'il faut** : le `tmdb_id`, le titre, l'année, la note,
  un résumé court, et un champ `already_in_watchlist` pour éviter les doublons.
  
- **Des messages d'erreur clairs** au lieu de tracebacks : par exemple, si on demande
  d'ajouter la série 999999, l'outil répond qu'elle n'existe pas et conseille d'utiliser
  `search_series`.

## Ce que j'ai testé dans MCP Inspector

- recherche d'une série, puis ajout avec le `tmdb_id` obtenu ;
- marquer une série comme vue, puis la supprimer ;
- après chaque action, j'ai vérifié sur `http://localhost:8000` que la page web suivait
  (c'est la même base de données) ;
- les cas d'erreur : identifiant qui n'existe pas, série déjà dans la watchlist.

Au passage, j'ai remarqué que TMDB ne corrige pas les fautes de frappe : en tapant
« severence » au lieu de « Severance », la recherche ne trouve rien.