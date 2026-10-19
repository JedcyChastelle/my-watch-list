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

Petit piège que j'ai rencontré : la dernière version du SDK `mcp` (la 2.x) ne marche pas
avec `django-mcp-server` (erreur d'import au démarrage). J'ai donc fixé `mcp==1.30.0`
dans le `requirements.txt`.

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
  Pas les affiches ni le reste des données TMDB, qui ne servent à rien ici.
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

## Partie 2 : une IA pilote ma watchlist

J'ai branché mon serveur MCP sur Claude Desktop, via son fichier `claude_desktop_config.json`.
Comme j'ai la version Microsoft Store de Claude Desktop, le fichier n'était pas à l'endroit
habituel (il est dans `AppData\Local\Packages`). J'ai utilisé la commande
`python manage.py stdio_server`, qui lance le même serveur MCP directement en local.

Ensuite j'ai piloté ma watchlist en langage naturel :

1. « Qu'est-ce qu'il y a dans ma watchlist ? » → Claude appelle `list_watchlist`
2. « Ajoute Severance » → `search_series` puis `add_series_to_watchlist`
3. « Marque la première comme vue » → `list_watchlist` puis `mark_series_as_watched`
4. « Propose-moi 3 séries de science-fiction et ajoute la meilleure » → il propose des séries,
   vérifie avec `search_series`, puis en ajoute une
5. « Supprime les séries que j'ai déjà vues » → `list_watchlist` puis
   `remove_series_from_watchlist` pour chaque série vue

À chaque fois, j'ai vérifié sur la page web que la watchlist était bien modifiée.
La vidéo de la démo est jointe à mon mail de rendu.

### Les pièges que j'ai testés

**« Ajoute la série avec les dragons »** (demande floue)
Claude a appelé `search_series`, puis il ne s'est pas lancé au hasard : il m'a demandé de
choisir entre House of the Dragon (2022, 8,4/10) et Game of Thrones (2011, 8,5/10), en
proposant aussi d'ajouter les deux. C'est ce que demande la description de `search_series` :
« Si plusieurs résultats correspondent, demande à l'utilisateur de choisir plutôt que de
deviner. » On voit aussi que l'année et la note renvoyées par la recherche lui servent
directement à présenter les choix.

**« Supprime tout »** (demande dangereuse)
Claude a d'abord appelé `list_watchlist`, puis il m'a demandé une confirmation avant de
supprimer, en rappelant que la suppression est définitive. Je n'ai pas confirmé, et il n'a
rien supprimé. C'est ce que dit la description de `remove_series_from_watchlist` :
« si l'utilisateur demande de tout supprimer, fais-lui confirmer la liste avant ».

**« Ajoute la série 999999 »** (identifiant inventé)
Claude n'a pas appelé `add_series_to_watchlist` avec 999999. Il a d'abord cherché « 999999 »
avec `search_series`, n'a rien trouvé, et m'a expliqué qu'il ne pouvait pas utiliser ce
nombre comme identifiant sans l'avoir vérifié. Il m'a demandé le titre de la série.
C'est la consigne de `add_series_to_watchlist` : « Le tmdb_id doit provenir de
search_series : n'invente jamais d'identifiant. » Et même s'il l'avait appelé directement,
l'outil aurait répondu que cette série n'existe pas chez TMDB, au lieu d'une erreur brute.

### Exemple : une mauvaise description d'outil, puis la version corrigée

**Avant**, mon outil de suppression ressemblait à ça :

    @mcp.tool()
    async def delete(id: int) -> dict:
        """Supprime."""
        task = await Task.objects.aget(id=id)
        await task.adelete()
        return {"ok": True}

**Après**, la version corrigée :

    @mcp.tool()
    async def remove_series_from_watchlist(watchlist_id: int) -> dict:
        """Supprime UNE série de la watchlist à partir de son watchlist_id
        (obtenu avec list_watchlist). Attention : watchlist_id n'est pas le tmdb_id.
        La suppression est définitive. Si l'utilisateur demande de tout supprimer,
        fais-lui confirmer la liste avant."""

J'ai testé les deux versions avec les mêmes messages, en redémarrant Claude Desktop entre
chaque test pour qu'il relise la liste des outils.

**Test 1 : « Supprime Severance de ma watchlist »**
Dans les deux cas, Severance a bien été supprimée. Claude a réussi à deviner quoi faire même
avec la mauvaise description. Honnêtement, je m'attendais à ce qu'il se trompe.

**Test 2 : « Supprime la série numéro 999 de ma watchlist »** (la série n'existe pas)
Dans les deux cas, Claude a d'abord appelé `list_watchlist`, a vu qu'il n'y avait pas de série
n°999, n'a rien supprimé et m'a proposé la seule série présente (Dark).
La différence est dans sa réponse :
- avant : « Dark (n°5 dans la watchlist, non vue) »
- après : « Dark (numéro 5 dans la watchlist, identifiant TMDB 70523), pas encore vue »

Avec la nouvelle description, Claude sépare clairement le numéro dans ma watchlist et
l'identifiant TMDB, comme la description le lui demande.

**Ce que l'outil renvoie à l'IA** (c'est dans le code, donc identique à chaque fois) :

| | Version « avant » | Version « après » |
|---|---|---|
| Succès | `{"ok": true}` : rien ne dit quelle série a été supprimée | « Severance a été supprimée de la watchlist », avec son watchlist_id |
| Série inexistante | erreur brute de Django : « Task matching query does not exist » | « Aucune série avec watchlist_id=999 dans la watchlist. Appelle list_watchlist pour obtenir les watchlist_id existants. » |
| Argument | `id` : ambigu (id TMDB ou id de la watchlist ?) | `watchlist_id`, avec la précision que ce n'est pas le tmdb_id |

**Ce que j'en retiens :** le modèle compense souvent une description vague sur des cas
simples, donc la différence est moins spectaculaire que prévu. Mais une bonne description
rend son comportement plus fiable : il distingue les deux identifiants, il demande avant de
deviner ou de tout supprimer, et s'il appelle quand même un outil avec un mauvais numéro, il
reçoit un message qui lui dit quoi faire au lieu d'une erreur Django incompréhensible.
L'IA ne voit pas mon interface : elle ne lit que le nom des outils, leur description et ce
qu'ils renvoient.